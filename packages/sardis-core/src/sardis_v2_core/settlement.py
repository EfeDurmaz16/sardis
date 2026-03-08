"""Unified settlement tracking across all payment modes.

Card-aware authorization/capture lifecycle for delegated card execution.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class SettlementMode(str, Enum):
    NATIVE_CRYPTO = "native_crypto"
    OFFRAMP = "offramp"
    DELEGATED_CARD = "delegated_card"


class SettlementStatus(str, Enum):
    INITIATED = "initiated"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    SETTLED = "settled"
    FAILED = "failed"
    DISPUTED = "disputed"
    REFUNDED = "refunded"


@dataclass
class SettlementRecord:
    """Unified settlement record across all modes."""

    settlement_id: str = field(
        default_factory=lambda: f"stl_{uuid.uuid4().hex[:16]}"
    )
    intent_id: str = ""
    receipt_id: str = ""

    # Mode & status
    mode: SettlementMode = SettlementMode.NATIVE_CRYPTO
    status: SettlementStatus = SettlementStatus.INITIATED

    # Amounts
    amount: Decimal = Decimal("0")
    currency: str = "USDC"
    fee: Decimal = Decimal("0")

    # References
    network_reference: str = ""  # tx_hash for crypto, Stripe PI ID for card
    credential_id: Optional[str] = None

    # Card-aware lifecycle fields
    authorization_status: Optional[str] = None  # authorized/captured/voided
    capture_status: Optional[str] = None  # pending_capture/captured/partial
    dispute_status: Optional[str] = None  # none/opened/won/lost
    reversal_reference: Optional[str] = None  # chargeback/reversal ID
    liability_party: Optional[str] = None  # sardis/merchant/network/issuer

    # Timestamps
    initiated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    confirmed_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    expected_settlement_at: Optional[datetime] = None

    # Retry
    retry_count: int = 0
    last_error: Optional[str] = None

    # Extra
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "settlement_id": self.settlement_id,
            "intent_id": self.intent_id,
            "receipt_id": self.receipt_id,
            "mode": self.mode.value,
            "status": self.status.value,
            "amount": str(self.amount),
            "currency": self.currency,
            "fee": str(self.fee),
            "network_reference": self.network_reference,
            "credential_id": self.credential_id,
            "authorization_status": self.authorization_status,
            "capture_status": self.capture_status,
            "dispute_status": self.dispute_status,
            "reversal_reference": self.reversal_reference,
            "liability_party": self.liability_party,
            "initiated_at": self.initiated_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
            "expected_settlement_at": (
                self.expected_settlement_at.isoformat()
                if self.expected_settlement_at else None
            ),
            "retry_count": self.retry_count,
            "last_error": self.last_error,
        }


# ---------------------------------------------------------------------------
# Store protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class SettlementStore(Protocol):
    async def create(self, record: SettlementRecord) -> str: ...
    async def get(self, settlement_id: str) -> Optional[SettlementRecord]: ...
    async def get_by_intent(self, intent_id: str) -> Optional[SettlementRecord]: ...
    async def update_status(
        self, settlement_id: str, status: SettlementStatus,
        **kwargs,
    ) -> None: ...
    async def get_pending(self) -> list[SettlementRecord]: ...
    async def get_summary(
        self, org_id: Optional[str] = None,
    ) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------

class InMemorySettlementStore:
    def __init__(self) -> None:
        self._records: dict[str, SettlementRecord] = {}
        self._by_intent: dict[str, str] = {}

    async def create(self, record: SettlementRecord) -> str:
        self._records[record.settlement_id] = record
        if record.intent_id:
            self._by_intent[record.intent_id] = record.settlement_id
        return record.settlement_id

    async def get(self, settlement_id: str) -> Optional[SettlementRecord]:
        return self._records.get(settlement_id)

    async def get_by_intent(self, intent_id: str) -> Optional[SettlementRecord]:
        sid = self._by_intent.get(intent_id)
        if sid is None:
            return None
        return self._records.get(sid)

    async def update_status(
        self, settlement_id: str, status: SettlementStatus, **kwargs,
    ) -> None:
        rec = self._records.get(settlement_id)
        if rec is None:
            raise KeyError(f"Settlement {settlement_id} not found")
        rec.status = status
        now = datetime.now(timezone.utc)
        if status == SettlementStatus.CONFIRMED:
            rec.confirmed_at = now
        elif status == SettlementStatus.SETTLED:
            rec.settled_at = now
        elif status == SettlementStatus.FAILED:
            rec.failed_at = now
            rec.last_error = kwargs.get("error")
            rec.retry_count += 1
        _ALLOWED_KWARGS = {
            "error", "last_error", "capture_status", "authorization_status",
            "dispute_status", "reversal_reference", "liability_party",
            "expected_settlement_at",
        }
        for k, v in kwargs.items():
            if k in _ALLOWED_KWARGS and hasattr(rec, k):
                setattr(rec, k, v)

    async def get_pending(self) -> list[SettlementRecord]:
        return [
            r for r in self._records.values()
            if r.status in (
                SettlementStatus.INITIATED,
                SettlementStatus.PENDING_CONFIRMATION,
            )
        ]

    async def get_summary(self, org_id: Optional[str] = None) -> dict[str, Any]:
        summary: dict[str, dict[str, Any]] = {}
        for r in self._records.values():
            mode = r.mode.value
            if mode not in summary:
                summary[mode] = {"count": 0, "total_amount": Decimal("0"), "total_fee": Decimal("0")}
            summary[mode]["count"] += 1
            summary[mode]["total_amount"] += r.amount
            summary[mode]["total_fee"] += r.fee
        # Convert Decimal to str for serialization
        for mode_data in summary.values():
            mode_data["total_amount"] = str(mode_data["total_amount"])
            mode_data["total_fee"] = str(mode_data["total_fee"])
        return summary


# ---------------------------------------------------------------------------
# PostgreSQL implementation
# ---------------------------------------------------------------------------

class PostgresSettlementStore:
    def __init__(self, pool) -> None:
        self._pool = pool

    def _row_to_record(self, row: dict) -> SettlementRecord:
        meta = row.get("metadata") or {}
        if isinstance(meta, str):
            import json
            meta = json.loads(meta)
        return SettlementRecord(
            settlement_id=row["settlement_id"],
            intent_id=row.get("intent_id", ""),
            receipt_id=row.get("receipt_id", ""),
            mode=SettlementMode(row["mode"]),
            status=SettlementStatus(row["status"]),
            amount=Decimal(str(row.get("amount", 0))),
            currency=row.get("currency", "USDC"),
            fee=Decimal(str(row.get("fee", 0))),
            network_reference=row.get("network_reference", ""),
            credential_id=row.get("credential_id"),
            authorization_status=row.get("authorization_status"),
            capture_status=row.get("capture_status"),
            dispute_status=row.get("dispute_status"),
            reversal_reference=row.get("reversal_reference"),
            liability_party=row.get("liability_party"),
            initiated_at=row.get("initiated_at", datetime.now(timezone.utc)),
            confirmed_at=row.get("confirmed_at"),
            settled_at=row.get("settled_at"),
            failed_at=row.get("failed_at"),
            expected_settlement_at=row.get("expected_settlement_at"),
            retry_count=row.get("retry_count", 0),
            last_error=row.get("last_error"),
            metadata=meta,
        )

    async def create(self, record: SettlementRecord) -> str:
        import json
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO settlement_records
                    (settlement_id, intent_id, receipt_id, mode, status,
                     amount, currency, fee, network_reference, credential_id,
                     authorization_status, capture_status, dispute_status,
                     reversal_reference, liability_party,
                     expected_settlement_at, metadata)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
                """,
                record.settlement_id,
                record.intent_id,
                record.receipt_id,
                record.mode.value,
                record.status.value,
                record.amount,
                record.currency,
                record.fee,
                record.network_reference,
                record.credential_id,
                record.authorization_status,
                record.capture_status,
                record.dispute_status,
                record.reversal_reference,
                record.liability_party,
                record.expected_settlement_at,
                json.dumps(record.metadata),
            )
        return record.settlement_id

    async def get(self, settlement_id: str) -> Optional[SettlementRecord]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM settlement_records WHERE settlement_id = $1",
                settlement_id,
            )
        if row is None:
            return None
        return self._row_to_record(dict(row))

    async def get_by_intent(self, intent_id: str) -> Optional[SettlementRecord]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM settlement_records WHERE intent_id = $1 ORDER BY created_at DESC LIMIT 1",
                intent_id,
            )
        if row is None:
            return None
        return self._row_to_record(dict(row))

    async def update_status(
        self, settlement_id: str, status: SettlementStatus, **kwargs,
    ) -> None:
        parts = ["status = $2", "updated_at = NOW()"]
        params: list[Any] = [settlement_id, status.value]
        idx = 3
        if status == SettlementStatus.CONFIRMED:
            parts.append(f"confirmed_at = ${idx}")
            params.append(datetime.now(timezone.utc))
            idx += 1
        elif status == SettlementStatus.SETTLED:
            parts.append(f"settled_at = ${idx}")
            params.append(datetime.now(timezone.utc))
            idx += 1
        elif status == SettlementStatus.FAILED:
            parts.append(f"failed_at = ${idx}")
            params.append(datetime.now(timezone.utc))
            idx += 1
            if "error" in kwargs:
                parts.append(f"last_error = ${idx}")
                params.append(kwargs["error"])
                idx += 1
            parts.append(f"retry_count = retry_count + 1")

        set_clause = ", ".join(parts)
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"UPDATE settlement_records SET {set_clause} WHERE settlement_id = $1",
                *params,
            )

    async def get_pending(self) -> list[SettlementRecord]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM settlement_records
                   WHERE status IN ('initiated', 'pending_confirmation')
                   ORDER BY initiated_at ASC""",
            )
        return [self._row_to_record(dict(r)) for r in rows]

    async def get_summary(self, org_id: Optional[str] = None) -> dict[str, Any]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT mode, COUNT(*) as cnt,
                          SUM(amount) as total_amount,
                          SUM(fee) as total_fee
                   FROM settlement_records
                   GROUP BY mode""",
            )
        summary = {}
        for row in rows:
            summary[row["mode"]] = {
                "count": row["cnt"],
                "total_amount": str(row["total_amount"]),
                "total_fee": str(row["total_fee"]),
            }
        return summary


# ---------------------------------------------------------------------------
# Reconciler
# ---------------------------------------------------------------------------

class SettlementReconciler:
    """Batch reconciliation across modes."""

    def __init__(self, settlement_store: SettlementStore) -> None:
        self._store = settlement_store

    async def reconcile_crypto(self, settlement_id: str) -> None:
        """Check on-chain confirmation for crypto settlement."""
        rec = await self._store.get(settlement_id)
        if rec is None or rec.mode != SettlementMode.NATIVE_CRYPTO:
            return
        # In production: check on-chain tx confirmation
        # For now, auto-confirm
        if rec.status == SettlementStatus.PENDING_CONFIRMATION:
            await self._store.update_status(
                settlement_id, SettlementStatus.CONFIRMED,
            )

    async def reconcile_delegated(self, settlement_id: str) -> None:
        """Check Stripe/network status for delegated settlement."""
        rec = await self._store.get(settlement_id)
        if rec is None or rec.mode != SettlementMode.DELEGATED_CARD:
            return
        # In production: check Stripe API for status
        # For now, auto-confirm
        if rec.status == SettlementStatus.PENDING_CONFIRMATION:
            await self._store.update_status(
                settlement_id, SettlementStatus.CONFIRMED,
            )

    async def reconcile_all_pending(self) -> int:
        """Batch reconciliation of all pending settlements."""
        pending = await self._store.get_pending()
        reconciled = 0
        for rec in pending:
            if rec.mode == SettlementMode.NATIVE_CRYPTO:
                await self.reconcile_crypto(rec.settlement_id)
                reconciled += 1
            elif rec.mode == SettlementMode.DELEGATED_CARD:
                await self.reconcile_delegated(rec.settlement_id)
                reconciled += 1
        return reconciled
