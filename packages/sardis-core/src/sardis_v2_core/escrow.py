"""Escrow Manager — holds funds in escrow with timelock release.

Supports the full escrow lifecycle:
  ESCROWED → CONFIRMING → RELEASED (happy path)
  ESCROWED → DISPUTING → ARBITRATING → RESOLVED_* (dispute path)
  ESCROWED → AUTO_RELEASING → RELEASED (timelock expiry)

Usage::

    manager = EscrowManager(pool)
    hold = await manager.create_hold(
        payment_object_id="po_abc123",
        amount=Decimal("100.00"),
        timelock_hours=72,
    )
    await manager.confirm_delivery(hold.hold_id, confirmed_by="merchant_xyz")
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.escrow")


class EscrowStatus(str, Enum):
    """Lifecycle states for an escrow hold."""
    HELD = "held"                    # Funds locked in escrow
    CONFIRMING = "confirming"        # Awaiting delivery confirmation
    RELEASED = "released"            # Released to merchant
    AUTO_RELEASED = "auto_released"  # Released by timelock expiry
    DISPUTING = "disputing"          # Dispute filed
    REFUNDED = "refunded"            # Full refund to payer
    SPLIT = "split"                  # Split resolution
    CANCELLED = "cancelled"          # Cancelled before release


ESCROW_VALID_TRANSITIONS: dict[tuple[str, str], str] = {
    (EscrowStatus.HELD, EscrowStatus.CONFIRMING): "await_delivery",
    (EscrowStatus.HELD, EscrowStatus.RELEASED): "release_immediate",
    (EscrowStatus.HELD, EscrowStatus.DISPUTING): "dispute",
    (EscrowStatus.HELD, EscrowStatus.CANCELLED): "cancel",
    (EscrowStatus.CONFIRMING, EscrowStatus.RELEASED): "confirm_delivery",
    (EscrowStatus.CONFIRMING, EscrowStatus.DISPUTING): "dispute",
    (EscrowStatus.CONFIRMING, EscrowStatus.AUTO_RELEASED): "timelock_expire",
    (EscrowStatus.DISPUTING, EscrowStatus.RELEASED): "resolve_release",
    (EscrowStatus.DISPUTING, EscrowStatus.REFUNDED): "resolve_refund",
    (EscrowStatus.DISPUTING, EscrowStatus.SPLIT): "resolve_split",
}


@dataclass
class EscrowHold:
    """An escrow hold on payment funds."""

    hold_id: str = field(default_factory=lambda: f"esc_{uuid4().hex[:12]}")
    payment_object_id: str = ""
    payer_id: str = ""
    merchant_id: str = ""

    # Amounts
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"

    # On-chain
    escrow_contract: str | None = None  # Address of escrow contract
    escrow_tx_hash: str | None = None
    release_tx_hash: str | None = None
    chain: str = "tempo"

    # Timelock
    timelock_expires_at: datetime | None = None
    auto_release: bool = True

    # Status
    status: EscrowStatus = EscrowStatus.HELD
    released_at: datetime | None = None
    released_to: str | None = None
    released_amount: Decimal | None = None

    # Delivery
    delivery_confirmed_at: datetime | None = None
    delivery_confirmed_by: str | None = None
    delivery_evidence: dict[str, Any] = field(default_factory=dict)

    # Audit
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_timelock_expired(self) -> bool:
        if self.timelock_expires_at is None:
            return False
        return datetime.now(UTC) > self.timelock_expires_at

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            EscrowStatus.RELEASED,
            EscrowStatus.AUTO_RELEASED,
            EscrowStatus.REFUNDED,
            EscrowStatus.SPLIT,
            EscrowStatus.CANCELLED,
        )


class EscrowManager:
    """Manages escrow holds for payment objects.

    Uses PostgreSQL for state management and delegates on-chain
    escrow operations to the chain executor.
    """

    def __init__(self, pool) -> None:
        self._pool = pool

    async def create_hold(
        self,
        payment_object_id: str,
        payer_id: str,
        merchant_id: str,
        amount: Decimal,
        currency: str = "USDC",
        timelock_hours: int = 72,
        chain: str = "tempo",
        metadata: dict[str, Any] | None = None,
    ) -> EscrowHold:
        """Create an escrow hold for a payment object."""
        hold = EscrowHold(
            payment_object_id=payment_object_id,
            payer_id=payer_id,
            merchant_id=merchant_id,
            amount=amount,
            currency=currency,
            timelock_expires_at=datetime.now(UTC) + timedelta(hours=timelock_hours),
            chain=chain,
            metadata=metadata or {},
        )

        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO escrow_holds
                   (hold_id, payment_object_id, payer_id, merchant_id,
                    amount, currency, chain, timelock_expires_at,
                    auto_release, status, metadata)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)""",
                hold.hold_id, hold.payment_object_id, hold.payer_id,
                hold.merchant_id, hold.amount, hold.currency, hold.chain,
                hold.timelock_expires_at, hold.auto_release,
                hold.status.value, hold.metadata,
            )

        logger.info("Created escrow hold %s for %s %s", hold.hold_id, amount, currency)
        return hold

    async def confirm_delivery(
        self,
        hold_id: str,
        confirmed_by: str,
        evidence: dict[str, Any] | None = None,
    ) -> EscrowHold:
        """Confirm delivery and release escrow to merchant."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM escrow_holds WHERE hold_id = $1 FOR UPDATE NOWAIT",
                    hold_id,
                )
                if not row:
                    raise ValueError(f"Escrow hold {hold_id} not found")

                current = row["status"]
                if current not in ("held", "confirming"):
                    raise ValueError(f"Cannot confirm delivery: hold is {current}")

                now = datetime.now(UTC)
                await conn.execute(
                    """UPDATE escrow_holds
                       SET status = 'released', released_at = $1, released_to = $2,
                           released_amount = amount, delivery_confirmed_at = $1,
                           delivery_confirmed_by = $3, delivery_evidence = $4,
                           updated_at = $1
                       WHERE hold_id = $5""",
                    now, row["merchant_id"], confirmed_by,
                    evidence or {}, hold_id,
                )

        logger.info("Released escrow %s to merchant", hold_id)
        return await self._get_hold(hold_id)

    async def auto_release_expired(self) -> list[str]:
        """Auto-release all holds with expired timelocks. Returns released hold IDs."""
        released = []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT hold_id FROM escrow_holds
                   WHERE status IN ('held', 'confirming')
                   AND auto_release = true
                   AND timelock_expires_at < now()
                   FOR UPDATE SKIP LOCKED""",
            )
            for row in rows:
                await conn.execute(
                    """UPDATE escrow_holds
                       SET status = 'auto_released', released_at = now(),
                           released_to = merchant_id, released_amount = amount,
                           updated_at = now()
                       WHERE hold_id = $1""",
                    row["hold_id"],
                )
                released.append(row["hold_id"])

        if released:
            logger.info("Auto-released %d expired escrow holds", len(released))
        return released

    async def file_dispute(
        self,
        hold_id: str,
        filed_by: str,
        reason: str,
    ) -> EscrowHold:
        """File a dispute on an escrow hold."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM escrow_holds WHERE hold_id = $1 FOR UPDATE NOWAIT",
                    hold_id,
                )
                if not row:
                    raise ValueError(f"Escrow hold {hold_id} not found")

                current = row["status"]
                if current not in ("held", "confirming"):
                    raise ValueError(f"Cannot dispute: hold is {current}")

                await conn.execute(
                    """UPDATE escrow_holds
                       SET status = 'disputing', updated_at = now(),
                           metadata = metadata || $1
                       WHERE hold_id = $2""",
                    {"dispute_filed_by": filed_by, "dispute_reason": reason},
                    hold_id,
                )

        logger.info("Dispute filed on escrow %s by %s", hold_id, filed_by)
        return await self._get_hold(hold_id)

    async def _get_hold(self, hold_id: str) -> EscrowHold:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM escrow_holds WHERE hold_id = $1", hold_id
            )
        if not row:
            raise ValueError(f"Escrow hold {hold_id} not found")
        return _row_to_hold(row)


def _row_to_hold(row) -> EscrowHold:
    return EscrowHold(
        hold_id=row["hold_id"],
        payment_object_id=row["payment_object_id"],
        payer_id=row["payer_id"],
        merchant_id=row["merchant_id"],
        amount=row["amount"],
        currency=row["currency"],
        chain=row.get("chain", "tempo"),
        escrow_contract=row.get("escrow_contract"),
        escrow_tx_hash=row.get("escrow_tx_hash"),
        release_tx_hash=row.get("release_tx_hash"),
        timelock_expires_at=row.get("timelock_expires_at"),
        auto_release=row.get("auto_release", True),
        status=EscrowStatus(row["status"]),
        released_at=row.get("released_at"),
        released_to=row.get("released_to"),
        released_amount=row.get("released_amount"),
        delivery_confirmed_at=row.get("delivery_confirmed_at"),
        delivery_confirmed_by=row.get("delivery_confirmed_by"),
        delivery_evidence=row.get("delivery_evidence") or {},
        metadata=row.get("metadata") or {},
        created_at=row["created_at"],
    )
