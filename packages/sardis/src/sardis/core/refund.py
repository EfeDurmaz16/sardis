"""Refund service — reverse completed payments with audit trail.

Supports full and partial refunds. Creates a reverse on-chain transaction
(or simulated reversal when SARDIS_CHAIN_MODE != 'live'), updates the
audit trail, and triggers notification webhooks.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class RefundStatus(str, Enum):
    INITIATED = "initiated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Refund:
    """A refund record."""

    refund_id: str = field(default_factory=lambda: f"rfd_{uuid4().hex[:16]}")
    payment_id: str = ""
    org_id: str = ""
    amount: Decimal = Decimal("0")
    currency: str = "USDC"
    reason: str = ""
    status: RefundStatus = RefundStatus.INITIATED
    reverse_tx_hash: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "refund_id": self.refund_id,
            "payment_id": self.payment_id,
            "org_id": self.org_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "reason": self.reason,
            "status": self.status.value,
            "reverse_tx_hash": self.reverse_tx_hash,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class RefundService:
    """Orchestrates refund lifecycle: validate, reverse, audit, notify."""

    def __init__(
        self,
        database: Any = None,
        chain_executor: Any = None,
        notification_service: Any = None,
        ledger: Any = None,
    ):
        self._db = database
        self._chain_executor = chain_executor
        self._notification_svc = notification_service
        self._ledger = ledger
        self._chain_mode = os.getenv("SARDIS_CHAIN_MODE", "simulated")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def initiate_refund(
        self,
        payment_id: str,
        org_id: str,
        reason: str,
        amount: Decimal | None = None,
    ) -> Refund:
        """Initiate a full or partial refund.

        Args:
            payment_id: ID of the completed payment to refund.
            org_id: Organization that owns the payment.
            reason: Human-readable refund reason.
            amount: Partial refund amount. None = full refund.

        Returns:
            Refund record with current status.

        Raises:
            ValueError: Payment not found, wrong status, already refunded,
                        or amount exceeds original.
        """
        # 1. Fetch and validate the payment
        payment = await self._get_payment(payment_id, org_id)
        if payment is None:
            raise ValueError(f"Payment {payment_id} not found")

        if payment.get("status") != "completed":
            raise ValueError(
                f"Payment {payment_id} status is '{payment.get('status')}', "
                "only completed payments can be refunded"
            )

        if payment.get("refund_id"):
            raise ValueError(f"Payment {payment_id} has already been refunded")

        original_amount = Decimal(str(payment.get("amount", "0")))
        refund_amount = amount if amount is not None else original_amount

        if refund_amount <= 0:
            raise ValueError("Refund amount must be positive")
        if refund_amount > original_amount:
            raise ValueError(
                f"Refund amount {refund_amount} exceeds original payment "
                f"amount {original_amount}"
            )

        # 2. Create refund record
        refund = Refund(
            payment_id=payment_id,
            org_id=org_id,
            amount=refund_amount,
            currency=payment.get("currency", "USDC"),
            reason=reason,
            status=RefundStatus.PROCESSING,
        )

        await self._save_refund(refund)

        # 3. Execute reverse transaction
        try:
            reverse_tx_hash = await self._execute_reverse(payment, refund)
            refund.reverse_tx_hash = reverse_tx_hash
            refund.status = RefundStatus.COMPLETED
            refund.completed_at = datetime.now(UTC)
        except Exception as e:
            logger.error(f"Refund reverse tx failed for {payment_id}: {e}")
            refund.status = RefundStatus.FAILED
            refund.error = str(e)
            await self._save_refund(refund)

            # Notify failure
            if self._notification_svc:
                await self._notification_svc.send(
                    org_id=org_id,
                    event_type="payment.refund_failed",
                    payload={
                        "payment_id": payment_id,
                        "refund_id": refund.refund_id,
                        "amount": str(refund_amount),
                        "error": str(e),
                    },
                )
            raise

        # 4. Update payment status and persist refund
        await self._mark_payment_refunded(payment_id, refund.refund_id)
        await self._save_refund(refund)

        # 5. Audit trail
        await self._record_audit_entry(refund, payment)

        # 6. Notify
        if self._notification_svc:
            await self._notification_svc.send(
                org_id=org_id,
                event_type="payment.refunded",
                payload={
                    "payment_id": payment_id,
                    "refund_id": refund.refund_id,
                    "amount": str(refund.amount),
                    "currency": refund.currency,
                    "reason": reason,
                    "reverse_tx_hash": refund.reverse_tx_hash,
                },
            )

        return refund

    async def get_refund(self, payment_id: str, org_id: str) -> Refund | None:
        """Get the refund record for a payment."""
        if self._db is None:
            return None
        try:
            pool = await self._db.get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT refund_id, payment_id, org_id, amount, currency,
                           reason, status, reverse_tx_hash, error,
                           created_at, completed_at
                    FROM refunds
                    WHERE payment_id = $1 AND org_id = $2
                    """,
                    payment_id,
                    org_id,
                )
            if not row:
                return None
            return Refund(
                refund_id=row["refund_id"],
                payment_id=row["payment_id"],
                org_id=row["org_id"],
                amount=Decimal(str(row["amount"])),
                currency=row["currency"],
                reason=row["reason"],
                status=RefundStatus(row["status"]),
                reverse_tx_hash=row["reverse_tx_hash"],
                error=row["error"],
                created_at=row["created_at"],
                completed_at=row["completed_at"],
            )
        except Exception as e:
            logger.error(f"Failed to get refund for {payment_id}: {e}")
            return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _get_payment(self, payment_id: str, org_id: str) -> dict[str, Any] | None:
        """Fetch payment from DB."""
        if self._db is None:
            return None
        try:
            pool = await self._db.get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT payment_id, org_id, amount, currency, status,
                           chain, token, from_address, to_address, tx_hash,
                           refund_id
                    FROM payments
                    WHERE payment_id = $1 AND org_id = $2
                    """,
                    payment_id,
                    org_id,
                )
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to fetch payment {payment_id}: {e}")
            return None

    async def _execute_reverse(
        self, payment: dict[str, Any], refund: Refund
    ) -> str:
        """Execute the reverse on-chain transaction or simulate."""
        if self._chain_mode == "live" and self._chain_executor:
            result = await self._chain_executor.execute(
                from_address=payment.get("to_address", ""),
                to_address=payment.get("from_address", ""),
                amount=refund.amount,
                token=payment.get("token", "USDC"),
                chain=payment.get("chain", "base"),
                memo=f"refund:{refund.refund_id}",
            )
            return result.get("tx_hash", f"0x{uuid4().hex}")
        # Simulated mode
        return f"0xsim_{uuid4().hex[:40]}"

    async def _save_refund(self, refund: Refund) -> None:
        """Persist refund record (upsert)."""
        if self._db is None:
            return
        try:
            pool = await self._db.get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO refunds
                        (refund_id, payment_id, org_id, amount, currency,
                         reason, status, reverse_tx_hash, error,
                         created_at, completed_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (refund_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        reverse_tx_hash = EXCLUDED.reverse_tx_hash,
                        error = EXCLUDED.error,
                        completed_at = EXCLUDED.completed_at
                    """,
                    refund.refund_id,
                    refund.payment_id,
                    refund.org_id,
                    refund.amount,
                    refund.currency,
                    refund.reason,
                    refund.status.value,
                    refund.reverse_tx_hash,
                    refund.error,
                    refund.created_at,
                    refund.completed_at,
                )
        except Exception as e:
            logger.error(f"Failed to save refund {refund.refund_id}: {e}")

    async def _mark_payment_refunded(
        self, payment_id: str, refund_id: str
    ) -> None:
        """Update payment record with refund reference."""
        if self._db is None:
            return
        try:
            pool = await self._db.get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE payments
                    SET status = 'refunded', refund_id = $2, updated_at = now()
                    WHERE payment_id = $1
                    """,
                    payment_id,
                    refund_id,
                )
        except Exception as e:
            logger.error(f"Failed to mark payment {payment_id} as refunded: {e}")

    async def _record_audit_entry(
        self, refund: Refund, payment: dict[str, Any]
    ) -> None:
        """Append refund entry to the audit trail."""
        if self._ledger:
            try:
                await self._ledger.append(
                    entry_type="payment.refunded",
                    actor=f"org:{refund.org_id}",
                    resource=f"payment:{refund.payment_id}",
                    data={
                        "refund_id": refund.refund_id,
                        "amount": str(refund.amount),
                        "currency": refund.currency,
                        "reason": refund.reason,
                        "reverse_tx_hash": refund.reverse_tx_hash,
                        "original_tx_hash": payment.get("tx_hash"),
                    },
                )
            except Exception as e:
                logger.error(f"Failed to record audit entry for refund: {e}")
