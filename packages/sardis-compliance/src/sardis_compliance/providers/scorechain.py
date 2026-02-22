"""
Scorechain AML/sanctions screening provider.

Scorechain provides free sanctions screening API with real-time risk scoring:
- Wallet address screening
- Transaction monitoring
- Risk scoring (0-100)
- Sanctions list coverage (OFAC, EU, UN, UK)

Free tier: Unlimited sanctions screening
Paid tier: €500/mo for full analytics (not required for basic sanctions checks)

API Reference: https://api.scorechain.com/v1
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from sardis_compliance.sanctions import (
    SanctionsProvider,
    ScreeningResult,
    WalletScreeningRequest,
    TransactionScreeningRequest,
    SanctionsRisk,
    EntityType,
)

logger = logging.getLogger(__name__)


class ScorechainProvider(SanctionsProvider):
    """
    Scorechain sanctions screening provider implementation.

    Uses Scorechain's free sanctions API for address and transaction screening.
    Maintains in-memory blocklist for custom address blocking.
    """

    BASE_URL = "https://api.scorechain.com/v1"

    # Chain name mapping for Scorechain API
    CHAIN_MAPPING = {
        "ethereum": "Ethereum",
        "base": "Base",
        "polygon": "Polygon",
        "arbitrum": "Arbitrum",
        "optimism": "Optimism",
        "bitcoin": "Bitcoin",
    }

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
    ):
        """
        Initialize Scorechain provider.

        Args:
            api_key: Scorechain API key
            timeout: Request timeout in seconds (default: 30)
        """
        self._api_key = api_key
        self._timeout = timeout
        self._http_client: Optional[httpx.AsyncClient] = None
        self._blocklist: set[str] = set()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=self._timeout,
                headers={
                    "X-API-Key": self._api_key,
                    "Content-Type": "application/json",
                },
            )
        return self._http_client

    def _map_chain(self, chain: str) -> str:
        """
        Map chain name to Scorechain blockchain identifier.

        Args:
            chain: Internal chain name (e.g., "ethereum", "base")

        Returns:
            Scorechain blockchain name (e.g., "Ethereum", "Base")
        """
        mapped = self.CHAIN_MAPPING.get(chain.lower())
        if not mapped:
            logger.warning(f"Unknown chain '{chain}', defaulting to Ethereum")
            return "Ethereum"
        return mapped

    def _map_risk_score(self, score: int, is_sanctioned: bool) -> SanctionsRisk:
        """
        Map Scorechain risk score (0-100) to SanctionsRisk enum.

        Mapping:
        - Sanctioned flag set → BLOCKED
        - 76-100 → SEVERE
        - 51-75 → HIGH
        - 26-50 → MEDIUM
        - 0-25 → LOW

        Args:
            score: Scorechain risk score (0-100)
            is_sanctioned: Whether entity is explicitly sanctioned

        Returns:
            SanctionsRisk level
        """
        if is_sanctioned:
            return SanctionsRisk.BLOCKED

        if score >= 76:
            return SanctionsRisk.SEVERE
        elif score >= 51:
            return SanctionsRisk.HIGH
        elif score >= 26:
            return SanctionsRisk.MEDIUM
        else:
            return SanctionsRisk.LOW

    async def screen_wallet(
        self,
        request: WalletScreeningRequest,
    ) -> ScreeningResult:
        """
        Screen a wallet address via Scorechain.

        Checks internal blocklist first, then queries Scorechain API.
        Fails closed on errors (returns BLOCKED status).
        """
        address = request.address.lower()

        # Check internal blocklist first
        if address in self._blocklist:
            logger.info(f"Address {address} found in internal blocklist")
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=address,
                entity_type=EntityType.WALLET,
                provider="scorechain",
                reason="Address in internal blocklist",
            )

        try:
            client = await self._get_client()
            blockchain = self._map_chain(request.chain)

            response = await client.post(
                "/scoring/address",
                json={
                    "blockchain": blockchain,
                    "address": request.address,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Parse Scorechain response
            risk_score = data.get("risk_score", 0)
            is_sanctioned = data.get("is_sanctioned", False)
            risk_level = self._map_risk_score(risk_score, is_sanctioned)

            # Extract matches if available
            matches = []
            if "matches" in data:
                for match in data.get("matches", []):
                    matches.append({
                        "list": match.get("list"),
                        "name": match.get("name"),
                        "category": match.get("category"),
                    })

            reason = None
            if is_sanctioned:
                reason = "Address on sanctions list"
            elif risk_score >= 76:
                reason = f"High risk score: {risk_score}"

            logger.info(
                f"Scorechain wallet screen: {address} - "
                f"risk={risk_score}, sanctioned={is_sanctioned}"
            )

            return ScreeningResult(
                risk_level=risk_level,
                is_sanctioned=is_sanctioned,
                entity_id=address,
                entity_type=EntityType.WALLET,
                provider="scorechain",
                matches=matches,
                reason=reason,
                lists_checked=request.lists,
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Scorechain API error screening {address}: "
                f"status={e.response.status_code}, body={e.response.text}"
            )
            # Fail closed - block on HTTP errors
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=False,
                entity_id=address,
                entity_type=EntityType.WALLET,
                provider="scorechain",
                reason=f"API error: HTTP {e.response.status_code}",
            )

        except Exception as e:
            logger.error(f"Scorechain wallet screening failed for {address}: {e}")
            # Fail closed - block on any error
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=False,
                entity_id=address,
                entity_type=EntityType.WALLET,
                provider="scorechain",
                reason=f"Screening failed: {str(e)}",
            )

    async def screen_transaction(
        self,
        request: TransactionScreeningRequest,
    ) -> ScreeningResult:
        """
        Screen a transaction via Scorechain.

        Attempts to use transaction hash endpoint if available,
        otherwise screens both from/to addresses and returns worst result.
        Fails closed on errors.
        """
        try:
            client = await self._get_client()
            blockchain = self._map_chain(request.chain)

            # Try transaction endpoint first
            try:
                response = await client.post(
                    "/scoring/transaction",
                    json={
                        "blockchain": blockchain,
                        "hash": request.tx_hash,
                    },
                )
                response.raise_for_status()
                data = response.json()

                risk_score = data.get("risk_score", 0)
                is_sanctioned = data.get("is_sanctioned", False)
                risk_level = self._map_risk_score(risk_score, is_sanctioned)

                matches = []
                if "matches" in data:
                    for match in data.get("matches", []):
                        matches.append({
                            "list": match.get("list"),
                            "name": match.get("name"),
                            "category": match.get("category"),
                        })

                reason = None
                if is_sanctioned:
                    reason = "Transaction involves sanctioned address"

                logger.info(
                    f"Scorechain tx screen: {request.tx_hash} - "
                    f"risk={risk_score}, sanctioned={is_sanctioned}"
                )

                return ScreeningResult(
                    risk_level=risk_level,
                    is_sanctioned=is_sanctioned,
                    entity_id=request.tx_hash,
                    entity_type=EntityType.TRANSACTION,
                    provider="scorechain",
                    matches=matches,
                    reason=reason,
                )

            except httpx.HTTPStatusError as e:
                # Transaction endpoint may not be available, fallback to address screening
                if e.response.status_code == 404:
                    logger.info("Transaction endpoint not available, screening addresses instead")
                else:
                    raise

            # Fallback: Screen both addresses
            from_result = await self.screen_wallet(
                WalletScreeningRequest(
                    address=request.from_address,
                    chain=request.chain,
                )
            )

            to_result = await self.screen_wallet(
                WalletScreeningRequest(
                    address=request.to_address,
                    chain=request.chain,
                )
            )

            # Return worst result
            if from_result.should_block or to_result.should_block:
                return ScreeningResult(
                    risk_level=SanctionsRisk.BLOCKED,
                    is_sanctioned=from_result.is_sanctioned or to_result.is_sanctioned,
                    entity_id=request.tx_hash,
                    entity_type=EntityType.TRANSACTION,
                    provider="scorechain",
                    matches=from_result.matches + to_result.matches,
                    reason="Transaction involves blocked address",
                )

            # Return higher risk level
            risk_order = [
                SanctionsRisk.LOW,
                SanctionsRisk.MEDIUM,
                SanctionsRisk.HIGH,
                SanctionsRisk.SEVERE,
            ]
            from_idx = (
                risk_order.index(from_result.risk_level)
                if from_result.risk_level in risk_order
                else 0
            )
            to_idx = (
                risk_order.index(to_result.risk_level)
                if to_result.risk_level in risk_order
                else 0
            )

            worst_result = from_result if from_idx >= to_idx else to_result

            return ScreeningResult(
                risk_level=worst_result.risk_level,
                is_sanctioned=from_result.is_sanctioned or to_result.is_sanctioned,
                entity_id=request.tx_hash,
                entity_type=EntityType.TRANSACTION,
                provider="scorechain",
                matches=from_result.matches + to_result.matches,
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Scorechain API error screening tx {request.tx_hash}: "
                f"status={e.response.status_code}, body={e.response.text}"
            )
            # Fail closed
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=False,
                entity_id=request.tx_hash,
                entity_type=EntityType.TRANSACTION,
                provider="scorechain",
                reason=f"API error: HTTP {e.response.status_code}",
            )

        except Exception as e:
            logger.error(f"Scorechain transaction screening failed for {request.tx_hash}: {e}")
            # Fail closed
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=False,
                entity_id=request.tx_hash,
                entity_type=EntityType.TRANSACTION,
                provider="scorechain",
                reason=f"Screening failed: {str(e)}",
            )

    async def add_to_blocklist(
        self,
        address: str,
        reason: str,
    ) -> bool:
        """
        Add an address to the internal blocklist.

        Note: This is an in-memory blocklist. For persistent storage,
        consider using database integration like EllipticProvider.
        """
        address = address.lower()
        self._blocklist.add(address)
        logger.info(f"Address {address} added to Scorechain blocklist: {reason}")
        return True

    async def remove_from_blocklist(
        self,
        address: str,
    ) -> bool:
        """Remove an address from the internal blocklist."""
        address = address.lower()
        if address in self._blocklist:
            self._blocklist.discard(address)
            logger.info(f"Address {address} removed from Scorechain blocklist")
            return True
        return False

    async def close(self):
        """Close HTTP client and cleanup resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
