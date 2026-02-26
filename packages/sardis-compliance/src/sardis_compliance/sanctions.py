"""
Sanctions screening integration module.

Supports Elliptic as the primary sanctions screening provider for:
- OFAC (Office of Foreign Assets Control)
- EU Sanctions
- UN Sanctions
- Wallet/address screening
- Transaction monitoring

Elliptic API: https://www.elliptic.co/
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sardis_compliance.retry import (
    create_retryable_client,
    RetryConfig,
    CircuitBreakerConfig,
    RateLimitConfig,
)

logger = logging.getLogger(__name__)


class SanctionsRisk(str, Enum):
    """Risk level from sanctions screening."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"
    BLOCKED = "blocked"


class SanctionsList(str, Enum):
    """Sanctions lists supported."""
    OFAC = "ofac"  # US Treasury
    EU = "eu"  # European Union
    UN = "un"  # United Nations
    UK = "uk"  # UK HM Treasury
    ALL = "all"  # All lists


class EntityType(str, Enum):
    """Type of entity being screened."""
    WALLET = "wallet"
    TRANSACTION = "transaction"
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"


@dataclass
class ScreeningResult:
    """Result of a sanctions screening check."""
    risk_level: SanctionsRisk
    is_sanctioned: bool
    entity_id: str
    entity_type: EntityType
    provider: str = "elliptic"
    screened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    matches: List[Dict[str, Any]] = field(default_factory=list)
    reason: Optional[str] = None
    lists_checked: List[SanctionsList] = field(default_factory=lambda: [SanctionsList.ALL])
    
    @property
    def should_block(self) -> bool:
        """Check if transaction should be blocked."""
        return self.is_sanctioned or self.risk_level == SanctionsRisk.BLOCKED


@dataclass
class WalletScreeningRequest:
    """Request to screen a wallet address."""
    address: str
    chain: str = "ethereum"
    check_related: bool = True  # Check related addresses
    lists: List[SanctionsList] = field(default_factory=lambda: [SanctionsList.ALL])


@dataclass
class TransactionScreeningRequest:
    """Request to screen a transaction."""
    tx_hash: str
    chain: str
    from_address: str
    to_address: str
    amount: Decimal
    token: str = "USDC"


class SanctionsProvider(ABC):
    """Abstract interface for sanctions screening providers."""

    @abstractmethod
    async def screen_wallet(
        self,
        request: WalletScreeningRequest,
    ) -> ScreeningResult:
        """Screen a wallet address against sanctions lists."""
        pass

    @abstractmethod
    async def screen_transaction(
        self,
        request: TransactionScreeningRequest,
    ) -> ScreeningResult:
        """Screen a transaction against sanctions lists."""
        pass

    @abstractmethod
    async def add_to_blocklist(
        self,
        address: str,
        reason: str,
    ) -> bool:
        """Add an address to the internal blocklist."""
        pass

    @abstractmethod
    async def remove_from_blocklist(
        self,
        address: str,
    ) -> bool:
        """Remove an address from the internal blocklist."""
        pass


class FailoverSanctionsProvider(SanctionsProvider):
    """Sanctions provider wrapper with primary->fallback behavior."""

    def __init__(
        self,
        primary: SanctionsProvider,
        fallback: SanctionsProvider,
        failover_on_provider_error: bool = True,
    ):
        self._primary = primary
        self._fallback = fallback
        self._failover_on_provider_error = failover_on_provider_error

    @staticmethod
    def _looks_like_provider_error(result: ScreeningResult) -> bool:
        reason = (result.reason or "").strip().lower()
        if not reason:
            return False
        return (not result.is_sanctioned) and any(token in reason for token in ("api error", "failed", "timeout"))

    async def screen_wallet(
        self,
        request: WalletScreeningRequest,
    ) -> ScreeningResult:
        try:
            primary_result = await self._primary.screen_wallet(request)
        except Exception as primary_exc:
            logger.warning("Sanctions primary screen_wallet failed; using fallback: %s", primary_exc)
            return await self._fallback.screen_wallet(request)
        if (
            self._failover_on_provider_error
            and primary_result.should_block
            and self._looks_like_provider_error(primary_result)
        ):
            logger.warning(
                "Sanctions primary returned provider-error block; retrying with fallback for address=%s",
                request.address,
            )
            return await self._fallback.screen_wallet(request)
        return primary_result

    async def screen_transaction(
        self,
        request: TransactionScreeningRequest,
    ) -> ScreeningResult:
        try:
            primary_result = await self._primary.screen_transaction(request)
        except Exception as primary_exc:
            logger.warning("Sanctions primary screen_transaction failed; using fallback: %s", primary_exc)
            return await self._fallback.screen_transaction(request)
        if (
            self._failover_on_provider_error
            and primary_result.should_block
            and self._looks_like_provider_error(primary_result)
        ):
            logger.warning(
                "Sanctions primary returned provider-error block; retrying fallback for tx=%s",
                request.tx_hash,
            )
            return await self._fallback.screen_transaction(request)
        return primary_result

    async def add_to_blocklist(
        self,
        address: str,
        reason: str,
    ) -> bool:
        primary_ok = await self._primary.add_to_blocklist(address, reason)
        fallback_ok = await self._fallback.add_to_blocklist(address, reason)
        return bool(primary_ok and fallback_ok)

    async def remove_from_blocklist(
        self,
        address: str,
    ) -> bool:
        primary_ok = await self._primary.remove_from_blocklist(address)
        fallback_ok = await self._fallback.remove_from_blocklist(address)
        return bool(primary_ok and fallback_ok)


class EllipticProvider(SanctionsProvider):
    """
    Elliptic sanctions screening provider implementation.
    
    Elliptic provides:
    - Real-time wallet screening
    - Transaction monitoring
    - Risk scoring
    - Sanctions list coverage
    
    API Reference: https://www.elliptic.co/solutions/connect
    """

    BASE_URL = "https://aml-api.elliptic.co"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        risk_threshold: SanctionsRisk = SanctionsRisk.HIGH,
    ):
        """
        Initialize Elliptic provider.
        
        Args:
            api_key: Elliptic API key
            api_secret: Elliptic API secret for request signing
            risk_threshold: Minimum risk level to flag
        """
        self._api_key = api_key
        self._api_secret = api_secret
        self._risk_threshold = risk_threshold
        self._http_client = None
        self._retry_client = create_retryable_client(
            name="elliptic",
            retry_config=RetryConfig(
                max_retries=3,
                initial_delay_seconds=1.0,
                max_delay_seconds=30.0,
            ),
            circuit_config=CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=120.0,
            ),
            rate_config=RateLimitConfig(
                requests_per_second=5.0,
                burst_size=10,
            ),
        )

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=30,
            )
        return self._http_client

    def _sign_request(
        self,
        method: str,
        path: str,
        body: str = "",
    ) -> Dict[str, str]:
        """Sign request with HMAC."""
        import time
        
        timestamp = str(int(time.time() * 1000))
        message = f"{timestamp}{method}{path}{body}"
        
        signature = hmac.new(
            self._api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return {
            "x-access-key": self._api_key,
            "x-access-sign": signature,
            "x-access-timestamp": timestamp,
            "Content-Type": "application/json",
        }

    async def screen_wallet(
        self,
        request: WalletScreeningRequest,
    ) -> ScreeningResult:
        """Screen a wallet address via Elliptic."""
        client = await self._get_client()
        
        # Map chain to Elliptic subject type
        subject_type = self._map_chain_to_subject(request.chain)
        
        path = f"/v2/wallet/synchronous"
        body = {
            "subject": {
                "asset": subject_type,
                "hash": request.address,
                "type": "address",
            },
            "type": "wallet_exposure",
            "customer_reference": f"sardis_{request.address[:16]}",
        }
        
        import json
        body_str = json.dumps(body)
        headers = self._sign_request("POST", path, body_str)
        
        async def _do_screen():
            response = await client.post(path, content=body_str, headers=headers)
            response.raise_for_status()
            return response.json()

        retry_result = await self._retry_client.execute(_do_screen)

        if not retry_result.success:
            logger.error(
                f"Elliptic screen_wallet failed after {retry_result.attempts} "
                f"attempts: {retry_result.error}"
            )
            # Fail closed - block on error
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=False,
                entity_id=request.address,
                entity_type=EntityType.WALLET,
                provider="elliptic",
                reason=f"Screening failed: {str(retry_result.error)}",
            )

        result = retry_result.value

        # Parse Elliptic response
        risk_score = result.get("risk_score", 0)
        risk_level = self._map_risk_score(risk_score)

        # Check for sanctioned entities
        sanctioned_entities = result.get("sanctioned_entity_exposures", [])
        is_sanctioned = len(sanctioned_entities) > 0

        matches = []
        for entity in sanctioned_entities:
            matches.append({
                "list": entity.get("source"),
                "name": entity.get("name"),
                "category": entity.get("category"),
                "exposure_value": entity.get("exposure_value"),
            })

        return ScreeningResult(
            risk_level=risk_level,
            is_sanctioned=is_sanctioned,
            entity_id=request.address,
            entity_type=EntityType.WALLET,
            provider="elliptic",
            matches=matches,
            reason="Sanctioned entity exposure" if is_sanctioned else None,
        )

    async def screen_transaction(
        self,
        request: TransactionScreeningRequest,
    ) -> ScreeningResult:
        """Screen a transaction via Elliptic."""
        # Screen both addresses
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
                provider="elliptic",
                matches=from_result.matches + to_result.matches,
                reason="Transaction involves sanctioned address",
            )
        
        # Return higher risk
        risk_order = [SanctionsRisk.LOW, SanctionsRisk.MEDIUM, SanctionsRisk.HIGH, SanctionsRisk.SEVERE]
        from_idx = risk_order.index(from_result.risk_level) if from_result.risk_level in risk_order else 0
        to_idx = risk_order.index(to_result.risk_level) if to_result.risk_level in risk_order else 0
        
        worst_result = from_result if from_idx >= to_idx else to_result
        
        return ScreeningResult(
            risk_level=worst_result.risk_level,
            is_sanctioned=False,
            entity_id=request.tx_hash,
            entity_type=EntityType.TRANSACTION,
            provider="elliptic",
            matches=from_result.matches + to_result.matches,
        )

    async def add_to_blocklist(
        self,
        address: str,
        reason: str,
    ) -> bool:
        """Add address to persistent blocklist in PostgreSQL."""
        try:
            from sardis_v2_core.database import Database
            await Database.execute(
                """
                INSERT INTO sanctions_blocklist (address, reason, created_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (address) DO UPDATE SET reason = $2, updated_at = NOW()
                """,
                address.lower(),
                reason,
            )
            logger.info(f"Address {address} added to blocklist: {reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist blocklist entry: {e}")
            return False

    async def remove_from_blocklist(
        self,
        address: str,
    ) -> bool:
        """Remove address from persistent blocklist."""
        try:
            from sardis_v2_core.database import Database
            await Database.execute(
                "DELETE FROM sanctions_blocklist WHERE address = $1",
                address.lower(),
            )
            logger.info(f"Address {address} removed from blocklist")
            return True
        except Exception as e:
            logger.error(f"Failed to remove blocklist entry: {e}")
            return False

    def _map_chain_to_subject(self, chain: str) -> str:
        """Map chain name to Elliptic subject type."""
        chain_map = {
            "ethereum": "holistic",
            "base": "holistic",
            "polygon": "holistic",
            "bitcoin": "btc",
            "solana": "sol",
        }
        return chain_map.get(chain.lower(), "holistic")

    def _map_risk_score(self, score: float) -> SanctionsRisk:
        """Map Elliptic risk score to SanctionsRisk."""
        if score >= 9:
            return SanctionsRisk.BLOCKED
        elif score >= 7:
            return SanctionsRisk.SEVERE
        elif score >= 5:
            return SanctionsRisk.HIGH
        elif score >= 3:
            return SanctionsRisk.MEDIUM
        return SanctionsRisk.LOW

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class MockSanctionsProvider(SanctionsProvider):
    """
    Mock sanctions provider for development and testing.
    
    Simulates Elliptic behavior with configurable responses.
    """

    # Known sanctioned addresses (for testing)
    SANCTIONED_ADDRESSES = {
        "0x0000000000000000000000000000000000000bad",
        "0xsanctioned1234567890123456789012345678",
    }

    def __init__(self):
        self._blocklist: set[str] = set()
        self._custom_results: Dict[str, ScreeningResult] = {}

    async def screen_wallet(
        self,
        request: WalletScreeningRequest,
    ) -> ScreeningResult:
        """Screen wallet with mock logic."""
        address = request.address.lower()
        
        # Check custom results
        if address in self._custom_results:
            return self._custom_results[address]
        
        # Check sanctioned addresses
        if address in self.SANCTIONED_ADDRESSES or address in self._blocklist:
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=address,
                entity_type=EntityType.WALLET,
                provider="mock",
                matches=[{"list": "OFAC", "name": "Test Sanctioned Entity"}],
                reason="Address is on sanctions list",
            )
        
        # Default: low risk
        return ScreeningResult(
            risk_level=SanctionsRisk.LOW,
            is_sanctioned=False,
            entity_id=address,
            entity_type=EntityType.WALLET,
            provider="mock",
        )

    async def screen_transaction(
        self,
        request: TransactionScreeningRequest,
    ) -> ScreeningResult:
        """Screen transaction with mock logic."""
        # Screen both addresses
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
        
        if from_result.should_block or to_result.should_block:
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=request.tx_hash,
                entity_type=EntityType.TRANSACTION,
                provider="mock",
                reason="Transaction involves blocked address",
            )
        
        return ScreeningResult(
            risk_level=SanctionsRisk.LOW,
            is_sanctioned=False,
            entity_id=request.tx_hash,
            entity_type=EntityType.TRANSACTION,
            provider="mock",
        )

    async def add_to_blocklist(
        self,
        address: str,
        reason: str,
    ) -> bool:
        """Add to mock blocklist."""
        self._blocklist.add(address.lower())
        return True

    async def remove_from_blocklist(
        self,
        address: str,
    ) -> bool:
        """Remove from mock blocklist."""
        self._blocklist.discard(address.lower())
        return True

    def set_result(self, address: str, result: ScreeningResult) -> None:
        """Set a custom result for testing."""
        self._custom_results[address.lower()] = result


class SanctionsService:
    """
    High-level sanctions screening service.
    
    Features:
    - Pre-transaction screening
    - Address caching
    - Blocklist management
    - Alert generation
    """

    def __init__(
        self,
        provider: Optional[SanctionsProvider] = None,
        cache_ttl_seconds: int = 3600,  # 1 hour
    ):
        """
        Initialize sanctions service.
        
        Args:
            provider: Sanctions screening provider
            cache_ttl_seconds: How long to cache screening results
        """
        self._provider = provider or MockSanctionsProvider()
        self._cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, tuple[ScreeningResult, datetime]] = {}

    async def screen_address(
        self,
        address: str,
        chain: str = "ethereum",
        force_refresh: bool = False,
    ) -> ScreeningResult:
        """
        Screen an address for sanctions.
        
        Uses cache if available and not expired.
        """
        cache_key = f"{chain}:{address.lower()}"
        
        # Check cache
        if not force_refresh and cache_key in self._cache:
            result, cached_at = self._cache[cache_key]
            age = (datetime.now(timezone.utc) - cached_at).total_seconds()
            if age < self._cache_ttl:
                return result
        
        # Screen address
        result = await self._provider.screen_wallet(
            WalletScreeningRequest(
                address=address,
                chain=chain,
            )
        )
        
        # Cache result
        self._cache[cache_key] = (result, datetime.now(timezone.utc))
        
        return result

    async def screen_transaction(
        self,
        tx_hash: str,
        chain: str,
        from_address: str,
        to_address: str,
        amount: Decimal,
        token: str = "USDC",
    ) -> ScreeningResult:
        """Screen a transaction for sanctions compliance."""
        return await self._provider.screen_transaction(
            TransactionScreeningRequest(
                tx_hash=tx_hash,
                chain=chain,
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                token=token,
            )
        )

    async def is_blocked(
        self,
        address: str,
        chain: str = "ethereum",
    ) -> bool:
        """Check if an address is blocked."""
        result = await self.screen_address(address, chain)
        return result.should_block

    async def block_address(
        self,
        address: str,
        reason: str,
    ) -> bool:
        """Add address to blocklist."""
        success = await self._provider.add_to_blocklist(address, reason)
        
        # Invalidate cache
        for key in list(self._cache.keys()):
            if address.lower() in key:
                del self._cache[key]
        
        return success

    async def unblock_address(
        self,
        address: str,
    ) -> bool:
        """Remove address from blocklist."""
        success = await self._provider.remove_from_blocklist(address)
        
        # Invalidate cache
        for key in list(self._cache.keys()):
            if address.lower() in key:
                del self._cache[key]
        
        return success

    def clear_cache(self) -> None:
        """Clear the screening cache."""
        self._cache.clear()


def create_sanctions_service(
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> SanctionsService:
    """
    Factory function to create sanctions service.
    
    Uses MockSanctionsProvider if no API key is provided.
    """
    if api_key and api_secret:
        provider = EllipticProvider(
            api_key=api_key,
            api_secret=api_secret,
        )
    else:
        import os
        env = os.getenv("SARDIS_ENVIRONMENT", "dev")
        if env in ("prod", "production"):
            raise RuntimeError(
                "Production requires Elliptic sanctions screening provider. "
                "Set ELLIPTIC_API_KEY and ELLIPTIC_API_SECRET environment variables."
            )
        logger.warning("No Elliptic API key provided, using mock provider (dev/test only)")
        provider = MockSanctionsProvider()

    return SanctionsService(provider=provider)
