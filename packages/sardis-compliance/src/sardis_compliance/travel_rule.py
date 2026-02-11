"""
Travel Rule compliance module.

Implements FATF Recommendation 16 (Travel Rule) for virtual asset transfers.
Requires originator and beneficiary information for transfers above threshold.

Threshold: $3,000 USD (US) / $1,000 EUR (EU - TFR regulation)

Supported VASP protocols:
- TRISA (Travel Rule Information Sharing Architecture)
- OpenVASP
- Manual compliance officer workflow (fallback)

Reference: https://www.fatf-gafi.org/en/publications/fatfrecommendations/documents/r15-virtual-assets-vasps.html
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# US threshold: $3,000; EU (TFR): $1,000 equivalent
TRAVEL_RULE_THRESHOLD_USD = Decimal("3000")
TRAVEL_RULE_THRESHOLD_EUR = Decimal("1000")


class TravelRuleStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    SENT = "sent"
    RECEIVED = "received"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class VASPProtocol(str, Enum):
    TRISA = "trisa"
    OPENVASP = "openvasp"
    MANUAL = "manual"


@dataclass
class OriginatorInfo:
    """FATF-required originator information."""
    name: str
    account_id: str  # wallet address or agent ID
    address: Optional[str] = None
    country: Optional[str] = None
    date_of_birth: Optional[str] = None
    national_id: Optional[str] = None


@dataclass
class BeneficiaryInfo:
    """FATF-required beneficiary information."""
    name: str
    account_id: str  # wallet address
    vasp_id: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None


@dataclass
class TravelRuleTransfer:
    """A transfer subject to Travel Rule compliance."""
    transfer_id: str = field(default_factory=lambda: f"tr_{uuid.uuid4().hex[:16]}")
    tx_id: Optional[str] = None
    amount: Decimal = Decimal("0")
    currency: str = "USDC"
    chain: Optional[str] = None
    originator: Optional[OriginatorInfo] = None
    beneficiary: Optional[BeneficiaryInfo] = None
    status: TravelRuleStatus = TravelRuleStatus.PENDING
    protocol: VASPProtocol = VASPProtocol.MANUAL
    vasp_response: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class TravelRuleProvider(ABC):
    """Abstract interface for Travel Rule VASP messaging."""

    @abstractmethod
    async def send_transfer_info(
        self,
        transfer: TravelRuleTransfer,
    ) -> TravelRuleStatus:
        pass

    @abstractmethod
    async def check_transfer_status(
        self,
        transfer_id: str,
    ) -> TravelRuleStatus:
        pass


class ManualTravelRuleProvider(TravelRuleProvider):
    """Fallback provider that flags transfers for manual compliance review."""

    async def send_transfer_info(self, transfer: TravelRuleTransfer) -> TravelRuleStatus:
        logger.info(
            f"Travel Rule transfer {transfer.transfer_id} flagged for manual review: "
            f"{transfer.amount} {transfer.currency}"
        )
        return TravelRuleStatus.PENDING

    async def check_transfer_status(self, transfer_id: str) -> TravelRuleStatus:
        return TravelRuleStatus.PENDING


class TravelRuleService:
    """
    High-level Travel Rule compliance service.

    Checks if transfers require Travel Rule information exchange,
    collects originator/beneficiary data, and sends via configured
    VASP protocol.
    """

    def __init__(
        self,
        provider: Optional[TravelRuleProvider] = None,
        threshold_usd: Decimal = TRAVEL_RULE_THRESHOLD_USD,
        dsn: Optional[str] = None,
    ):
        self._provider = provider or ManualTravelRuleProvider()
        self._threshold = threshold_usd
        self._transfers: Dict[str, TravelRuleTransfer] = {}
        self._dsn = dsn
        self._pool = None

    def requires_travel_rule(self, amount: Decimal, currency: str = "USDC") -> bool:
        """Check if a transfer amount triggers Travel Rule requirements."""
        # Stablecoins are 1:1 USD for threshold purposes
        if currency in ("USDC", "USDT", "PYUSD"):
            return amount >= self._threshold
        if currency == "EURC":
            return amount >= TRAVEL_RULE_THRESHOLD_EUR
        # Conservative: require for unknown tokens above threshold
        return amount >= self._threshold

    async def create_transfer(
        self,
        amount: Decimal,
        currency: str,
        chain: str,
        originator: OriginatorInfo,
        beneficiary: BeneficiaryInfo,
        tx_id: Optional[str] = None,
    ) -> TravelRuleTransfer:
        """Create a Travel Rule transfer record and initiate VASP messaging."""
        transfer = TravelRuleTransfer(
            tx_id=tx_id,
            amount=amount,
            currency=currency,
            chain=chain,
            originator=originator,
            beneficiary=beneficiary,
        )

        # Send via VASP protocol
        status = await self._provider.send_transfer_info(transfer)
        transfer.status = status
        self._transfers[transfer.transfer_id] = transfer

        # Persist to DB if configured
        if self._dsn:
            await self._persist_transfer(transfer)

        return transfer

    async def check_compliance(
        self,
        amount: Decimal,
        currency: str = "USDC",
    ) -> tuple[bool, str]:
        """
        Check if a transaction can proceed from Travel Rule perspective.

        Returns (can_proceed, reason).
        """
        if not self.requires_travel_rule(amount, currency):
            return True, "below_threshold"
        # Above threshold — originator/beneficiary info required
        return False, "travel_rule_info_required"

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            dsn = self._dsn
            if dsn and dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3)
        return self._pool

    async def _persist_transfer(self, transfer: TravelRuleTransfer) -> None:
        import json as _json
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO travel_rule_transfers
                        (transfer_id, tx_id, amount, currency, chain, status,
                         originator_data, beneficiary_data, protocol)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (transfer_id) DO UPDATE SET
                        status = EXCLUDED.status, updated_at = NOW()
                    """,
                    transfer.transfer_id,
                    transfer.tx_id,
                    float(transfer.amount),
                    transfer.currency,
                    transfer.chain,
                    transfer.status.value,
                    _json.dumps({
                        "name": transfer.originator.name,
                        "account_id": transfer.originator.account_id,
                        "country": transfer.originator.country,
                    } if transfer.originator else {}, default=str),
                    _json.dumps({
                        "name": transfer.beneficiary.name,
                        "account_id": transfer.beneficiary.account_id,
                        "vasp_id": transfer.beneficiary.vasp_id,
                    } if transfer.beneficiary else {}, default=str),
                    transfer.protocol.value,
                )
        except Exception as e:
            logger.warning(f"Failed to persist travel rule transfer: {e}")

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None


def create_travel_rule_service(
    dsn: Optional[str] = None,
    threshold_usd: Optional[Decimal] = None,
) -> TravelRuleService:
    """Factory function to create Travel Rule service."""
    return TravelRuleService(
        dsn=dsn,
        threshold_usd=threshold_usd or TRAVEL_RULE_THRESHOLD_USD,
    )
