"""
OpenSanctions screening provider.

Screens wallet addresses and entities against 330+ global sanctions, PEP, and
enforcement databases aggregated by OpenSanctions. Uses the yente matching API
(self-hosted or cloud at api.opensanctions.org).

Key features:
- CryptoWallet schema matching for Ethereum address screening
- Entity name matching with fuzzy scoring (logic-v2 algorithm)
- Supports self-hosted yente or hosted OpenSanctions API
- Configurable match threshold (default 0.7)
- Fail-closed on API errors
- In-memory custom blocklist

Spec: https://www.opensanctions.org/docs/api/
yente: https://github.com/opensanctions/yente
FollowTheMoney: https://followthemoney.tech/

Issue: #136
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from sardis_compliance.sanctions import (
    EntityType,
    SanctionsList,
    SanctionsProvider,
    SanctionsRisk,
    ScreeningResult,
    TransactionScreeningRequest,
    WalletScreeningRequest,
)

logger = logging.getLogger(__name__)

# Default endpoints
DEFAULT_API_URL = "https://api.opensanctions.org"
DEFAULT_DATASET = "default"  # All datasets (sanctions + PEPs + enforcement)
SANCTIONS_ONLY_DATASET = "sanctions"

# Match score thresholds
DEFAULT_MATCH_THRESHOLD = 0.7
HIGH_CONFIDENCE_THRESHOLD = 0.9

# Risk score mapping from OpenSanctions match score
# score >= 0.9 → BLOCKED (high confidence match)
# score >= 0.7 → SEVERE (likely match, needs review)
# score >= 0.5 → HIGH (possible match)
# score >= 0.3 → MEDIUM (weak match)
# score < 0.3  → LOW
RISK_THRESHOLDS = [
    (0.9, SanctionsRisk.BLOCKED),
    (0.7, SanctionsRisk.SEVERE),
    (0.5, SanctionsRisk.HIGH),
    (0.3, SanctionsRisk.MEDIUM),
]


def _score_to_risk(score: float) -> SanctionsRisk:
    """Map an OpenSanctions match score to a SanctionsRisk level."""
    for threshold, risk in RISK_THRESHOLDS:
        if score >= threshold:
            return risk
    return SanctionsRisk.LOW


class OpenSanctionsProvider(SanctionsProvider):
    """
    Screens addresses and entities against OpenSanctions via the yente API.

    Supports both the hosted API (api.opensanctions.org, requires API key)
    and self-hosted yente instances (no key needed).

    Configuration via environment variables:
        OPENSANCTIONS_API_URL   — API base URL (default: https://api.opensanctions.org)
        OPENSANCTIONS_API_KEY   — API key for hosted service (optional for self-hosted)
        OPENSANCTIONS_DATASET   — Dataset scope (default: "default" = all)
        OPENSANCTIONS_THRESHOLD — Minimum match score (default: 0.7)

    Cost: Free for self-hosted; $99/mo+ for hosted cloud API.
    """

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        dataset: str | None = None,
        match_threshold: float | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_url = (
            api_url
            or os.getenv("OPENSANCTIONS_API_URL", DEFAULT_API_URL)
        ).rstrip("/")
        self._api_key = api_key or os.getenv("OPENSANCTIONS_API_KEY", "")
        self._dataset = dataset or os.getenv(
            "OPENSANCTIONS_DATASET", DEFAULT_DATASET
        )
        self._threshold = match_threshold or float(
            os.getenv("OPENSANCTIONS_THRESHOLD", str(DEFAULT_MATCH_THRESHOLD))
        )
        self._timeout = timeout
        self._custom_blocklist: dict[str, str] = {}  # address → reason

    def _headers(self) -> dict[str, str]:
        """Build request headers."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"ApiKey {self._api_key}"
        return headers

    async def screen_wallet(
        self,
        request: WalletScreeningRequest,
    ) -> ScreeningResult:
        """Screen a wallet address against OpenSanctions.

        Uses the /match endpoint with CryptoWallet schema to check if the
        address belongs to a sanctioned entity. Falls back to text search
        if matching fails.
        """
        address = request.address.strip()

        # Check custom blocklist first
        if address.lower() in self._custom_blocklist:
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=address,
                entity_type=EntityType.WALLET,
                provider="opensanctions",
                reason=f"Custom blocklist: {self._custom_blocklist[address.lower()]}",
                matches=[{"source": "custom_blocklist"}],
            )

        try:
            matches = await self._match_crypto_wallet(address)
            return self._build_wallet_result(address, matches)
        except Exception as exc:
            logger.error(
                "OpenSanctions wallet screening failed for %s: %s",
                address,
                exc,
            )
            # Fail-closed: treat API error as blocked
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=address,
                entity_type=EntityType.WALLET,
                provider="opensanctions",
                reason=f"Screening failed (fail-closed): {exc}",
                matches=[],
            )

    async def screen_transaction(
        self,
        request: TransactionScreeningRequest,
    ) -> ScreeningResult:
        """Screen a transaction by checking both from and to addresses.

        Returns the highest risk result from screening both parties.
        """
        try:
            from_matches = await self._match_crypto_wallet(request.from_address)
            to_matches = await self._match_crypto_wallet(request.to_address)

            # Take the higher-risk result
            from_result = self._build_wallet_result(
                request.from_address, from_matches
            )
            to_result = self._build_wallet_result(
                request.to_address, to_matches
            )

            # Use the higher risk level
            if _risk_severity(to_result.risk_level) > _risk_severity(
                from_result.risk_level
            ):
                result = to_result
            else:
                result = from_result

            # Override entity info for transaction context
            result.entity_id = request.tx_hash or request.from_address
            result.entity_type = EntityType.TRANSACTION
            all_matches = from_result.matches + to_result.matches
            result.matches = all_matches

            return result
        except Exception as exc:
            logger.error(
                "OpenSanctions transaction screening failed: %s", exc
            )
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=request.tx_hash or request.from_address,
                entity_type=EntityType.TRANSACTION,
                provider="opensanctions",
                reason=f"Screening failed (fail-closed): {exc}",
                matches=[],
            )

    async def add_to_blocklist(self, address: str, reason: str) -> bool:
        """Add an address to the in-memory custom blocklist."""
        self._custom_blocklist[address.lower()] = reason
        logger.info("OpenSanctions blocklist: added %s (%s)", address, reason)
        return True

    async def remove_from_blocklist(self, address: str) -> bool:
        """Remove an address from the custom blocklist."""
        removed = self._custom_blocklist.pop(address.lower(), None)
        if removed:
            logger.info("OpenSanctions blocklist: removed %s", address)
            return True
        return False

    # ---- Internal Methods ----

    async def _match_crypto_wallet(
        self, address: str
    ) -> list[dict[str, Any]]:
        """Query the /match endpoint with CryptoWallet schema.

        Args:
            address: Ethereum (or other) wallet address.

        Returns:
            List of matching entities with scores.
        """
        url = f"{self._api_url}/match/{self._dataset}"
        payload = {
            "queries": {
                "wallet": {
                    "schema": "CryptoWallet",
                    "properties": {
                        "publicKey": [address],
                    },
                }
            }
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                url,
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract results for our query
        wallet_response = data.get("responses", {}).get("wallet", {})
        results = wallet_response.get("results", [])

        # Filter by threshold
        return [
            r for r in results if r.get("score", 0) >= self._threshold
        ]

    async def match_entity(
        self,
        name: str,
        schema: str = "LegalEntity",
        birth_date: str | None = None,
        nationality: str | None = None,
    ) -> list[dict[str, Any]]:
        """Match an entity by name and properties.

        Useful for screening counterparties, merchants, or individuals
        beyond just wallet addresses.

        Args:
            name: Entity name to screen.
            schema: FtM schema (Person, Company, LegalEntity, etc.).
            birth_date: Date of birth for Person matches.
            nationality: ISO country code for Person matches.

        Returns:
            List of matching entities with scores.
        """
        url = f"{self._api_url}/match/{self._dataset}"
        properties: dict[str, list[str]] = {"name": [name]}
        if birth_date:
            properties["birthDate"] = [birth_date]
        if nationality:
            properties["nationality"] = [nationality]

        payload = {
            "queries": {
                "entity": {
                    "schema": schema,
                    "properties": properties,
                }
            }
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                url,
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        entity_response = data.get("responses", {}).get("entity", {})
        results = entity_response.get("results", [])
        return [r for r in results if r.get("score", 0) >= self._threshold]

    async def search(
        self, query: str, schema: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Free-text search across all entities.

        Args:
            query: Search string (address, name, etc.).
            schema: Optional FtM schema filter.
            limit: Max results.

        Returns:
            List of matching entities.
        """
        url = f"{self._api_url}/search/{self._dataset}"
        params: dict[str, Any] = {"q": query, "limit": limit}
        if schema:
            params["schema"] = schema

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                url,
                params=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        return data.get("results", [])

    async def health_check(self) -> bool:
        """Check if the OpenSanctions API is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._api_url}/healthz",
                    headers=self._headers(),
                )
                return resp.status_code == 200
        except Exception:
            return False

    def _build_wallet_result(
        self,
        address: str,
        matches: list[dict[str, Any]],
    ) -> ScreeningResult:
        """Convert OpenSanctions match results to a ScreeningResult."""
        if not matches:
            return ScreeningResult(
                risk_level=SanctionsRisk.LOW,
                is_sanctioned=False,
                entity_id=address,
                entity_type=EntityType.WALLET,
                provider="opensanctions",
                matches=[],
                lists_checked=[SanctionsList.ALL],
            )

        # Use highest score for risk assessment
        top_match = max(matches, key=lambda m: m.get("score", 0))
        top_score = top_match.get("score", 0)
        risk = _score_to_risk(top_score)

        # Extract useful match info
        formatted_matches = []
        for m in matches:
            formatted_matches.append({
                "entity_id": m.get("id", ""),
                "schema": m.get("schema", ""),
                "caption": m.get("caption", ""),
                "score": m.get("score", 0),
                "datasets": m.get("datasets", []),
                "properties": {
                    k: v
                    for k, v in m.get("properties", {}).items()
                    if k in ("name", "publicKey", "currency", "holder")
                },
            })

        is_sanctioned = top_score >= HIGH_CONFIDENCE_THRESHOLD
        datasets = top_match.get("datasets", [])
        caption = top_match.get("caption", "Unknown")

        return ScreeningResult(
            risk_level=risk,
            is_sanctioned=is_sanctioned,
            entity_id=address,
            entity_type=EntityType.WALLET,
            provider="opensanctions",
            matches=formatted_matches,
            reason=(
                f"Matched {caption} (score={top_score:.2f}, "
                f"datasets={','.join(datasets)})"
                if matches
                else None
            ),
            lists_checked=[SanctionsList.ALL],
        )


def _risk_severity(risk: SanctionsRisk) -> int:
    """Numeric severity for risk comparison."""
    order = {
        SanctionsRisk.LOW: 0,
        SanctionsRisk.MEDIUM: 1,
        SanctionsRisk.HIGH: 2,
        SanctionsRisk.SEVERE: 3,
        SanctionsRisk.BLOCKED: 4,
    }
    return order.get(risk, 0)
