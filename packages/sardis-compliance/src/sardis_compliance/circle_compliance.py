"""Circle Compliance Engine integration.

Provides real-time transaction screening and address risk assessment
via the Circle Web3 Services Compliance Engine API.

Circle Compliance Engine screens addresses and transactions against:
- OFAC/SDN sanctions lists
- Frozen/blocked address registries
- Known blocklists and high-risk entities
- Terrorism financing indicators

API Reference: https://developers.circle.com/w3s/reference/screening-addresses

Magic test address suffixes (for testing without hitting real sanctions):
- 9999 → Sanctions hit (DENY)
- 8888 → Frozen address (FREEZE_AND_DENY)
- 7777 → Blocklisted (DENY)
- 6666 → Terrorism financing (DENY)
- 5555 → High risk (REVIEW)
- 4444 → Medium risk (REVIEW)
- 3333 → Low risk (APPROVE)
- 2222 → No risk (APPROVE)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from sardis_compliance.retry import (
    RetryConfig,
    CircuitBreakerConfig,
    RateLimitConfig,
    create_retryable_client,
)
from sardis_compliance.sanctions import (
    EntityType,
    SanctionsProvider,
    SanctionsRisk,
    ScreeningResult,
    TransactionScreeningRequest,
    WalletScreeningRequest,
)

logger = logging.getLogger(__name__)


# ── Circle API Constants ───────────────────────────────────────────────


CIRCLE_COMPLIANCE_BASE_URL = "https://api.circle.com/v1/w3s/compliance"


class CircleScreeningAction(str, Enum):
    """Circle Compliance Engine screening decisions."""
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    DENY = "DENY"
    FREEZE_AND_DENY = "FREEZE_AND_DENY"


class CircleRiskLevel(str, Enum):
    """Circle Compliance Engine risk levels."""
    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    SEVERE = "SEVERE"


class CircleScreeningType(str, Enum):
    """Types of screening supported."""
    ADDRESS = "ADDRESS"
    TRANSACTION = "TRANSACTION"


# ── Data Models ────────────────────────────────────────────────────────


@dataclass
class CircleScreeningRequest:
    """Request payload for Circle Compliance screening."""
    address: str
    chain: str
    screening_type: CircleScreeningType = CircleScreeningType.ADDRESS


@dataclass
class CircleScreeningMatch:
    """A single match from Circle Compliance screening."""
    list_name: str = ""
    category: str = ""
    description: str = ""
    risk_level: str = ""


@dataclass
class CircleScreeningResponse:
    """Response from Circle Compliance screening."""
    screening_id: str = ""
    address: str = ""
    chain: str = ""
    action: CircleScreeningAction = CircleScreeningAction.APPROVE
    risk_level: CircleRiskLevel = CircleRiskLevel.UNKNOWN
    matches: List[CircleScreeningMatch] = field(default_factory=list)
    screened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_response: Dict[str, Any] = field(default_factory=dict)


class CircleComplianceError(Exception):
    """Error from Circle Compliance Engine."""
    pass


# ── Chain Mapping ──────────────────────────────────────────────────────


# Maps Sardis chain names to Circle blockchain identifiers
CIRCLE_CHAIN_MAP: Dict[str, str] = {
    "ethereum": "ETH",
    "base": "BASE",
    "polygon": "MATIC",
    "arbitrum": "ARB",
    "optimism": "OP",
    "avalanche": "AVAX",
    "solana": "SOL",
    # Testnets
    "base_sepolia": "BASE-SEPOLIA",
    "ethereum_sepolia": "ETH-SEPOLIA",
    "polygon_amoy": "MATIC-AMOY",
}


def _map_chain(chain: str) -> str:
    """Map Sardis chain name to Circle blockchain identifier."""
    return CIRCLE_CHAIN_MAP.get(chain.lower(), chain.upper())


def _map_action_to_risk(action: CircleScreeningAction) -> SanctionsRisk:
    """Map Circle screening action to Sardis SanctionsRisk."""
    mapping = {
        CircleScreeningAction.APPROVE: SanctionsRisk.LOW,
        CircleScreeningAction.REVIEW: SanctionsRisk.HIGH,
        CircleScreeningAction.DENY: SanctionsRisk.BLOCKED,
        CircleScreeningAction.FREEZE_AND_DENY: SanctionsRisk.BLOCKED,
    }
    return mapping.get(action, SanctionsRisk.BLOCKED)


def _is_sanctioned(action: CircleScreeningAction) -> bool:
    """Check if the screening action indicates a sanctions hit."""
    return action in (CircleScreeningAction.DENY, CircleScreeningAction.FREEZE_AND_DENY)


# ── Circle Compliance Client ──────────────────────────────────────────


class CircleComplianceClient:
    """Low-level client for Circle Compliance Engine API.

    Handles authentication, request signing, and HTTP communication
    with Circle's compliance screening endpoints.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = CIRCLE_COMPLIANCE_BASE_URL,
        timeout_seconds: float = 30.0,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        self._retry_client = create_retryable_client(
            name="circle_compliance",
            retry_config=RetryConfig(
                max_retries=3,
                initial_delay_seconds=0.5,
                max_delay_seconds=15.0,
            ),
            circuit_config=CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=120.0,
            ),
            rate_config=RateLimitConfig(
                requests_per_second=10.0,
                burst_size=20,
            ),
        )

    async def screen_address(
        self,
        address: str,
        chain: str,
    ) -> CircleScreeningResponse:
        """Screen a single address via Circle Compliance Engine.

        Args:
            address: Blockchain address to screen.
            chain: Sardis chain name (e.g., "base", "ethereum").

        Returns:
            CircleScreeningResponse with screening decision.
        """
        circle_chain = _map_chain(chain)
        url = f"{self._base_url}/screening/addresses"

        payload = {
            "address": address,
            "chain": circle_chain,
        }

        async def _do_request():
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()

        retry_result = await self._retry_client.execute(_do_request)

        if not retry_result.success:
            raise CircleComplianceError(
                f"Circle Compliance screening failed after "
                f"{retry_result.attempts} attempts: {retry_result.error}"
            )

        return self._parse_screening_response(retry_result.value, address, chain)

    async def screen_transfer(
        self,
        sender_address: str,
        recipient_address: str,
        chain: str,
        amount: Optional[Decimal] = None,
        token: Optional[str] = None,
    ) -> tuple[CircleScreeningResponse, CircleScreeningResponse]:
        """Screen both sides of a transfer.

        Returns:
            Tuple of (sender_screening, recipient_screening).
        """
        sender_result = await self.screen_address(sender_address, chain)
        recipient_result = await self.screen_address(recipient_address, chain)
        return sender_result, recipient_result

    def _parse_screening_response(
        self,
        data: Dict[str, Any],
        address: str,
        chain: str,
    ) -> CircleScreeningResponse:
        """Parse Circle API response into CircleScreeningResponse."""
        result = data.get("result", data)

        action_str = result.get("action", "APPROVE")
        try:
            action = CircleScreeningAction(action_str)
        except ValueError:
            logger.warning(f"Unknown Circle action: {action_str}, treating as DENY")
            action = CircleScreeningAction.DENY

        risk_str = result.get("riskLevel", "UNKNOWN")
        try:
            risk_level = CircleRiskLevel(risk_str)
        except ValueError:
            risk_level = CircleRiskLevel.UNKNOWN

        matches = []
        for match_data in result.get("screeningResults", []):
            matches.append(CircleScreeningMatch(
                list_name=match_data.get("listName", ""),
                category=match_data.get("category", ""),
                description=match_data.get("description", ""),
                risk_level=match_data.get("riskLevel", ""),
            ))

        return CircleScreeningResponse(
            screening_id=result.get("id", ""),
            address=address,
            chain=chain,
            action=action,
            risk_level=risk_level,
            matches=matches,
            raw_response=data,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


# ── SanctionsProvider Implementation ──────────────────────────────────


class CircleComplianceProvider(SanctionsProvider):
    """Circle Compliance Engine as a SanctionsProvider.

    Drop-in replacement for EllipticProvider in the sanctions pipeline.
    Uses Circle's real-time address screening API for compliance checks.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = CIRCLE_COMPLIANCE_BASE_URL,
    ):
        self._client = CircleComplianceClient(api_key, base_url=base_url)
        self._blocklist: set[str] = set()

    async def screen_wallet(
        self,
        request: WalletScreeningRequest,
    ) -> ScreeningResult:
        """Screen a wallet address via Circle Compliance Engine."""
        # Check local blocklist first
        if request.address.lower() in self._blocklist:
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=request.address,
                entity_type=EntityType.WALLET,
                provider="circle_compliance",
                reason="Address is on internal blocklist",
            )

        try:
            response = await self._client.screen_address(
                request.address,
                request.chain,
            )

            matches = []
            for m in response.matches:
                matches.append({
                    "list": m.list_name,
                    "category": m.category,
                    "description": m.description,
                    "risk_level": m.risk_level,
                })

            risk_level = _map_action_to_risk(response.action)
            is_sanctioned = _is_sanctioned(response.action)

            reason = None
            if is_sanctioned:
                reason = f"Circle Compliance: {response.action.value}"
            elif response.action == CircleScreeningAction.REVIEW:
                reason = "Circle Compliance: REVIEW required"

            return ScreeningResult(
                risk_level=risk_level,
                is_sanctioned=is_sanctioned,
                entity_id=request.address,
                entity_type=EntityType.WALLET,
                provider="circle_compliance",
                matches=matches,
                reason=reason,
            )

        except CircleComplianceError as e:
            logger.error(f"Circle Compliance screening failed: {e}")
            # Fail closed - block on error
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=False,
                entity_id=request.address,
                entity_type=EntityType.WALLET,
                provider="circle_compliance",
                reason=f"Screening failed: {str(e)}",
            )

    async def screen_transaction(
        self,
        request: TransactionScreeningRequest,
    ) -> ScreeningResult:
        """Screen a transaction by screening both addresses."""
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
                provider="circle_compliance",
                matches=from_result.matches + to_result.matches,
                reason="Transaction involves flagged address",
            )

        # Return higher risk
        risk_order = [SanctionsRisk.LOW, SanctionsRisk.MEDIUM, SanctionsRisk.HIGH, SanctionsRisk.SEVERE]
        from_idx = risk_order.index(from_result.risk_level) if from_result.risk_level in risk_order else 0
        to_idx = risk_order.index(to_result.risk_level) if to_result.risk_level in risk_order else 0
        worst = from_result if from_idx >= to_idx else to_result

        return ScreeningResult(
            risk_level=worst.risk_level,
            is_sanctioned=False,
            entity_id=request.tx_hash,
            entity_type=EntityType.TRANSACTION,
            provider="circle_compliance",
            matches=from_result.matches + to_result.matches,
            reason=worst.reason,
        )

    async def add_to_blocklist(self, address: str, reason: str) -> bool:
        """Add address to internal blocklist."""
        self._blocklist.add(address.lower())
        logger.info(f"Address {address} added to Circle compliance blocklist: {reason}")
        return True

    async def remove_from_blocklist(self, address: str) -> bool:
        """Remove address from internal blocklist."""
        self._blocklist.discard(address.lower())
        logger.info(f"Address {address} removed from Circle compliance blocklist")
        return True

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.close()


# ── Factory ───────────────────────────────────────────────────────────


def create_circle_compliance_provider(
    api_key: Optional[str] = None,
) -> CircleComplianceProvider:
    """Create a Circle Compliance provider.

    Args:
        api_key: Circle API key. Falls back to CIRCLE_API_KEY env var.

    Returns:
        CircleComplianceProvider instance.

    Raises:
        ValueError: If no API key is available.
    """
    key = api_key or os.getenv("CIRCLE_API_KEY", "")
    if not key:
        raise ValueError(
            "Circle API key required. Set CIRCLE_API_KEY environment variable "
            "or pass api_key parameter."
        )
    return CircleComplianceProvider(api_key=key)
