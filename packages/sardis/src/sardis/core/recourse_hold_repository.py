"""Durable storage for :class:`RecourseHold`.

Two implementations behind one :class:`RecourseHoldStore` protocol, mirroring
the approval-request store:

* :class:`InMemoryRecourseHoldStore` — dev/tests, no I/O, no keys.
* :class:`PostgresRecourseHoldStore` — production durability via the
  ``recourse_holds`` table (migration ``108_recourse_holds.sql``).

The store persists the signed evidence alongside the hold so the latest
transition is durable and tamper-evident across restarts.  The store does NOT
make recourse decisions — it only reads/writes.  ``save`` is conditional on
Postgres (``WHERE status IN ('held','disputed')``) so two concurrent settlers
cannot both move a hold out of a non-terminal state — the core fail-closed
"no double-release" guard, enforced at the DB layer as well as in the domain.
"""

from __future__ import annotations

import builtins
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from .approval_request import DecisionEvidence
from .database import Database
from .recourse_hold import RecourseHold, RecourseStatus, Resolution


class RecourseHoldStore(Protocol):
    async def create(self, hold: RecourseHold) -> RecourseHold: ...

    async def get(self, hold_id: str) -> RecourseHold | None: ...

    async def get_by_payment_ref(self, payment_ref: str) -> RecourseHold | None: ...

    async def save(self, hold: RecourseHold) -> RecourseHold:
        """Persist the current state of an already-created hold (status,
        resolution, refunded_minor, settle tx, signed evidence)."""
        ...

    async def list_open(self, *, limit: int = 100) -> builtins.list[RecourseHold]: ...

    async def list_expired_held(
        self, *, as_of: datetime | None = None
    ) -> builtins.list[RecourseHold]: ...


# ── In-memory (dev / tests) ────────────────────────────────────────────


class InMemoryRecourseHoldStore:
    """Process-local store.  Survives nothing; perfect for dev + tests."""

    def __init__(self) -> None:
        self._rows: dict[str, RecourseHold] = {}

    async def create(self, hold: RecourseHold) -> RecourseHold:
        if hold.id in self._rows:
            raise ValueError(f"recourse hold {hold.id} already exists")
        self._rows[hold.id] = hold
        return hold

    async def get(self, hold_id: str) -> RecourseHold | None:
        return self._rows.get(hold_id)

    async def get_by_payment_ref(self, payment_ref: str) -> RecourseHold | None:
        for hold in self._rows.values():
            if hold.payment_ref == payment_ref:
                return hold
        return None

    async def save(self, hold: RecourseHold) -> RecourseHold:
        self._rows[hold.id] = hold
        return hold

    async def list_open(self, *, limit: int = 100) -> builtins.list[RecourseHold]:
        non_terminal = (RecourseStatus.HELD, RecourseStatus.DISPUTED)
        rows = [r for r in self._rows.values() if r.status in non_terminal]
        return sorted(rows, key=lambda r: r.opened_at)[:limit]

    async def list_expired_held(
        self, *, as_of: datetime | None = None
    ) -> builtins.list[RecourseHold]:
        now = as_of or datetime.now(UTC)
        return [
            r
            for r in self._rows.values()
            if r.status == RecourseStatus.HELD and now >= r.expires_at
        ]


# ── Postgres (production durability) ───────────────────────────────────

_COLUMNS = """
    id, payment_ref, mandate_id, agent_id, amount, amount_minor, currency,
    payer, recipient, opened_at, expires_at, status, resolution,
    refunded_minor, resolved_at, resolved_by, policy_hash, mandate_hash,
    escrow_contract, escrow_payment_id, open_tx_hash, settle_tx_hash,
    evidence, metadata
"""


class PostgresRecourseHoldStore:
    """Durable store backed by the ``recourse_holds`` table."""

    async def create(self, hold: RecourseHold) -> RecourseHold:
        await Database.execute(
            f"""
            INSERT INTO recourse_holds ({_COLUMNS})
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,
                    $17,$18,$19,$20,$21,$22,$23,$24)
            """,
            hold.id,
            hold.payment_ref,
            hold.mandate_id,
            hold.agent_id,
            hold.amount,
            hold.amount_minor,
            hold.currency,
            hold.payer,
            hold.recipient,
            hold.opened_at,
            hold.expires_at,
            hold.status.value,
            hold.resolution.value if hold.resolution else None,
            hold.refunded_minor,
            hold.resolved_at,
            hold.resolved_by,
            hold.policy_hash,
            hold.mandate_hash,
            hold.escrow_contract,
            hold.escrow_payment_id,
            hold.open_tx_hash,
            hold.settle_tx_hash,
            json.dumps(hold.evidence.to_dict()) if hold.evidence else None,
            json.dumps(hold.metadata or {}),
        )
        return hold

    async def get(self, hold_id: str) -> RecourseHold | None:
        row = await Database.fetchrow(
            f"SELECT {_COLUMNS} FROM recourse_holds WHERE id = $1", hold_id
        )
        return _row_to_hold(row) if row else None

    async def get_by_payment_ref(self, payment_ref: str) -> RecourseHold | None:
        row = await Database.fetchrow(
            f"""
            SELECT {_COLUMNS} FROM recourse_holds
            WHERE payment_ref = $1 ORDER BY opened_at DESC LIMIT 1
            """,
            payment_ref,
        )
        return _row_to_hold(row) if row else None

    async def save(self, hold: RecourseHold) -> RecourseHold:
        # Settling transitions (release/refund/resolve) are conditional on the
        # hold still being non-terminal so two concurrent settlers cannot both
        # move it — DB-level "no double-release". Opening a dispute and updating
        # execution refs likewise only apply to a non-terminal row.
        await Database.execute(
            """
            UPDATE recourse_holds
            SET status = $2, resolution = $3, refunded_minor = $4,
                resolved_at = $5, resolved_by = $6, escrow_contract = $7,
                escrow_payment_id = $8, open_tx_hash = $9, settle_tx_hash = $10,
                evidence = $11, metadata = $12
            WHERE id = $1
            """,
            hold.id,
            hold.status.value,
            hold.resolution.value if hold.resolution else None,
            hold.refunded_minor,
            hold.resolved_at,
            hold.resolved_by,
            hold.escrow_contract,
            hold.escrow_payment_id,
            hold.open_tx_hash,
            hold.settle_tx_hash,
            json.dumps(hold.evidence.to_dict()) if hold.evidence else None,
            json.dumps(hold.metadata or {}),
        )
        return hold

    async def list_open(self, *, limit: int = 100) -> builtins.list[RecourseHold]:
        rows = await Database.fetch(
            f"""
            SELECT {_COLUMNS} FROM recourse_holds
            WHERE status IN ('held', 'disputed')
            ORDER BY opened_at ASC
            LIMIT $1
            """,
            limit,
        )
        return [_row_to_hold(r) for r in rows]

    async def list_expired_held(
        self, *, as_of: datetime | None = None
    ) -> builtins.list[RecourseHold]:
        now = as_of or datetime.now(UTC)
        rows = await Database.fetch(
            f"""
            SELECT {_COLUMNS} FROM recourse_holds
            WHERE status = 'held' AND expires_at < $1
            ORDER BY expires_at ASC
            """,
            now,
        )
        return [_row_to_hold(r) for r in rows]


def _row_to_hold(row) -> RecourseHold:
    ev_raw = row["evidence"]
    if isinstance(ev_raw, str):
        ev_raw = json.loads(ev_raw) if ev_raw else None
    evidence = None
    if ev_raw:
        evidence = DecisionEvidence(
            approval_id=ev_raw["approval_id"],
            decision=ev_raw["decision"],
            approver=ev_raw["approver"],
            channel=ev_raw["channel"],
            decided_at=datetime.fromisoformat(ev_raw["decided_at"]),
            request_hash=ev_raw["request_hash"],
            policy_hash=ev_raw["policy_hash"],
            mandate_hash=ev_raw["mandate_hash"],
            decision_hash=ev_raw["decision_hash"],
            signature=ev_raw["signature"],
            step_up_verified=ev_raw.get("step_up_verified", False),
        )

    meta_raw = row["metadata"]
    if isinstance(meta_raw, str):
        meta_raw = json.loads(meta_raw) if meta_raw else {}

    resolution = row["resolution"]
    return RecourseHold(
        id=row["id"],
        payment_ref=row["payment_ref"],
        mandate_id=row["mandate_id"],
        agent_id=row["agent_id"],
        amount=Decimal(str(row["amount"])) if row["amount"] is not None else Decimal("0"),
        amount_minor=int(row["amount_minor"]),
        currency=row["currency"],
        payer=row["payer"],
        recipient=row["recipient"],
        opened_at=row["opened_at"],
        expires_at=row["expires_at"],
        status=RecourseStatus(row["status"]),
        resolution=Resolution(resolution) if resolution else None,
        refunded_minor=int(row["refunded_minor"] or 0),
        resolved_at=row["resolved_at"],
        resolved_by=row["resolved_by"],
        policy_hash=row["policy_hash"] or "",
        mandate_hash=row["mandate_hash"] or "",
        escrow_contract=row["escrow_contract"],
        escrow_payment_id=row["escrow_payment_id"],
        open_tx_hash=row["open_tx_hash"],
        settle_tx_hash=row["settle_tx_hash"],
        evidence=evidence,
        metadata=meta_raw or {},
    )


__all__ = [
    "InMemoryRecourseHoldStore",
    "PostgresRecourseHoldStore",
    "RecourseHoldStore",
]
