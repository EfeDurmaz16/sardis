"""x402 settlement module - separates verification from on-chain settlement.

Implements:
- Settlement status tracking (VERIFIED -> SETTLING -> SETTLED)
- Store abstraction for settlement persistence
- X402Settler class for verify/settle operations
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from .x402 import X402Challenge, X402PaymentPayload, verify_payment_payload


class X402SettlementStatus(Enum):
    """Settlement status enum."""
    VERIFIED = "verified"
    SETTLING = "settling"
    SETTLED = "settled"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass(slots=True)
class X402Settlement:
    """Settlement tracking for an x402 payment."""
    payment_id: str
    status: X402SettlementStatus
    challenge: X402Challenge | None = None
    payload: X402PaymentPayload | None = None
    tx_hash: str | None = None
    settled_at: datetime | None = None
    error: str | None = None


class X402SettlementStore(Protocol):
    """Protocol for settlement persistence."""

    async def save(self, settlement: X402Settlement) -> None:
        """Save a new settlement record."""
        ...

    async def get(self, payment_id: str) -> X402Settlement | None:
        """Retrieve settlement by payment_id."""
        ...

    async def update_status(
        self,
        payment_id: str,
        status: X402SettlementStatus,
        **kwargs,
    ) -> None:
        """Update settlement status and optional fields."""
        ...


class InMemorySettlementStore:
    """In-memory implementation of X402SettlementStore."""

    def __init__(self):
        self._settlements: dict[str, X402Settlement] = {}

    async def save(self, settlement: X402Settlement) -> None:
        """Save a new settlement record."""
        self._settlements[settlement.payment_id] = settlement

    async def get(self, payment_id: str) -> X402Settlement | None:
        """Retrieve settlement by payment_id."""
        return self._settlements.get(payment_id)

    async def update_status(
        self,
        payment_id: str,
        status: X402SettlementStatus,
        **kwargs,
    ) -> None:
        """Update settlement status and optional fields."""
        settlement = self._settlements.get(payment_id)
        if settlement is None:
            raise ValueError(f"settlement_not_found: {payment_id}")

        settlement.status = status
        for key, value in kwargs.items():
            if hasattr(settlement, key):
                setattr(settlement, key, value)


class X402Settler:
    """Manages x402 payment verification and settlement."""

    def __init__(
        self,
        store: X402SettlementStore,
        chain_executor: Any | None = None,
    ):
        self.store = store
        self.chain_executor = chain_executor

    async def verify(
        self,
        challenge: X402Challenge,
        payload: X402PaymentPayload,
    ) -> X402Settlement:
        """Verify payment payload against challenge. Does NOT touch blockchain."""
        verification = verify_payment_payload(payload, challenge)

        if not verification.accepted:
            settlement = X402Settlement(
                payment_id=payload.payment_id,
                status=X402SettlementStatus.FAILED,
                challenge=challenge,
                payload=payload,
                error=verification.reason,
            )
            await self.store.save(settlement)
            return settlement

        settlement = X402Settlement(
            payment_id=payload.payment_id,
            status=X402SettlementStatus.VERIFIED,
            challenge=challenge,
            payload=payload,
        )
        await self.store.save(settlement)
        return settlement

    async def settle(self, settlement: X402Settlement) -> X402Settlement:
        """Initiate on-chain settlement for a verified payment."""
        if settlement.status != X402SettlementStatus.VERIFIED:
            raise ValueError(
                f"cannot_settle: settlement must be VERIFIED, got {settlement.status.value}"
            )

        if self.chain_executor is None:
            raise ValueError("cannot_settle: chain_executor not configured")

        try:
            await self.store.update_status(
                settlement.payment_id,
                X402SettlementStatus.SETTLING,
            )

            # TODO: Invoke chain_executor to execute on-chain settlement
            # For now, mark as settled immediately
            tx_hash = f"0x{settlement.payment_id}"  # Placeholder

            await self.store.update_status(
                settlement.payment_id,
                X402SettlementStatus.SETTLED,
                tx_hash=tx_hash,
                settled_at=datetime.utcnow(),
            )

            updated = await self.store.get(settlement.payment_id)
            if updated is None:
                raise ValueError(f"settlement_lost: {settlement.payment_id}")
            return updated

        except Exception as exc:
            await self.store.update_status(
                settlement.payment_id,
                X402SettlementStatus.FAILED,
                error=str(exc),
            )
            updated = await self.store.get(settlement.payment_id)
            if updated is None:
                raise ValueError(f"settlement_lost: {settlement.payment_id}") from exc
            return updated

    async def check_settlement(self, payment_id: str) -> X402Settlement | None:
        """Check settlement status from store."""
        return await self.store.get(payment_id)


__all__ = [
    "X402SettlementStatus",
    "X402Settlement",
    "X402SettlementStore",
    "InMemorySettlementStore",
    "X402Settler",
]
