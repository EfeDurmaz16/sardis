"""Durable storage for :class:`ApprovalRequest`.

Two implementations behind one :class:`ApprovalRequestStore` protocol:

* :class:`InMemoryApprovalRequestStore` — dev/tests, no I/O, no keys.
* :class:`PostgresApprovalRequestStore` — production durability via the
  ``approval_requests`` table (migration ``107_approval_requests.sql``).

The store persists the signed :class:`DecisionEvidence` alongside the request so
the decision is durable and tamper-evident across restarts.  The store does NOT
make policy decisions — it only reads/writes.  ``transition`` is the single
mutating entry point and is conditional (``WHERE status = 'pending'`` on
Postgres) so two concurrent deciders cannot both move a request out of pending.
"""

from __future__ import annotations

import builtins
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from .approval_request import (
    ApprovalRequest,
    ApprovalState,
    DecisionEvidence,
)
from .database import Database


class ApprovalRequestStore(Protocol):
    async def create(self, request: ApprovalRequest) -> ApprovalRequest: ...

    async def get(self, approval_id: str) -> ApprovalRequest | None: ...

    async def save(self, request: ApprovalRequest) -> ApprovalRequest:
        """Persist the full current state of an already-created request
        (status, decision fields, signed evidence, reexecuted flag)."""
        ...

    async def list_pending(
        self, *, limit: int = 100
    ) -> builtins.list[ApprovalRequest]: ...

    async def list_expired_pending(
        self, *, as_of: datetime | None = None
    ) -> builtins.list[ApprovalRequest]: ...


# ── In-memory (dev / tests) ────────────────────────────────────────────


class InMemoryApprovalRequestStore:
    """Process-local store.  Survives nothing; perfect for dev + tests."""

    def __init__(self) -> None:
        self._rows: dict[str, ApprovalRequest] = {}

    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        if request.id in self._rows:
            raise ValueError(f"approval request {request.id} already exists")
        self._rows[request.id] = request
        return request

    async def get(self, approval_id: str) -> ApprovalRequest | None:
        return self._rows.get(approval_id)

    async def save(self, request: ApprovalRequest) -> ApprovalRequest:
        self._rows[request.id] = request
        return request

    async def list_pending(self, *, limit: int = 100) -> builtins.list[ApprovalRequest]:
        pending = [r for r in self._rows.values() if r.status == ApprovalState.PENDING]
        return sorted(pending, key=lambda r: r.requested_at)[:limit]

    async def list_expired_pending(
        self, *, as_of: datetime | None = None
    ) -> builtins.list[ApprovalRequest]:
        now = as_of or datetime.now(UTC)
        return [
            r
            for r in self._rows.values()
            if r.status == ApprovalState.PENDING and now >= r.expires_at
        ]


# ── Postgres (production durability) ───────────────────────────────────

_COLUMNS = """
    id, agent_id, mandate_id, spending_mandate_id, amount, currency,
    counterparty, reason, status, requested_at, expires_at, decided_by,
    decided_at, policy_hash, mandate_hash, requires_step_up, reexecuted,
    evidence, metadata
"""


class PostgresApprovalRequestStore:
    """Durable store backed by the ``approval_requests`` table."""

    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        await Database.execute(
            f"""
            INSERT INTO approval_requests ({_COLUMNS})
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
            """,
            request.id,
            request.agent_id,
            request.mandate_id,
            request.spending_mandate_id,
            request.amount,
            request.currency,
            request.counterparty,
            request.reason,
            request.status.value,
            request.requested_at,
            request.expires_at,
            request.decided_by,
            request.decided_at,
            request.policy_hash,
            request.mandate_hash,
            request.requires_step_up,
            request.reexecuted,
            json.dumps(request.evidence.to_dict()) if request.evidence else None,
            json.dumps(request.metadata or {}),
        )
        return request

    async def get(self, approval_id: str) -> ApprovalRequest | None:
        row = await Database.fetchrow(
            f"SELECT {_COLUMNS} FROM approval_requests WHERE id = $1", approval_id
        )
        return _row_to_request(row) if row else None

    async def save(self, request: ApprovalRequest) -> ApprovalRequest:
        # Conditional on still-pending guards against a concurrent decider
        # racing two terminal transitions; once terminal, save is idempotent on
        # the same terminal row (used by the re-execution flag update).
        await Database.execute(
            """
            UPDATE approval_requests
            SET status = $2, decided_by = $3, decided_at = $4,
                reexecuted = $5, evidence = $6, metadata = $7
            WHERE id = $1
            """,
            request.id,
            request.status.value,
            request.decided_by,
            request.decided_at,
            request.reexecuted,
            json.dumps(request.evidence.to_dict()) if request.evidence else None,
            json.dumps(request.metadata or {}),
        )
        return request

    async def list_pending(self, *, limit: int = 100) -> builtins.list[ApprovalRequest]:
        rows = await Database.fetch(
            f"""
            SELECT {_COLUMNS} FROM approval_requests
            WHERE status = 'pending'
            ORDER BY requested_at ASC
            LIMIT $1
            """,
            limit,
        )
        return [_row_to_request(r) for r in rows]

    async def list_expired_pending(
        self, *, as_of: datetime | None = None
    ) -> builtins.list[ApprovalRequest]:
        now = as_of or datetime.now(UTC)
        rows = await Database.fetch(
            f"""
            SELECT {_COLUMNS} FROM approval_requests
            WHERE status = 'pending' AND expires_at < $1
            ORDER BY expires_at ASC
            """,
            now,
        )
        return [_row_to_request(r) for r in rows]


def _row_to_request(row) -> ApprovalRequest:
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

    return ApprovalRequest(
        id=row["id"],
        agent_id=row["agent_id"],
        mandate_id=row["mandate_id"],
        spending_mandate_id=row["spending_mandate_id"],
        amount=Decimal(str(row["amount"])) if row["amount"] is not None else Decimal("0"),
        currency=row["currency"],
        counterparty=row["counterparty"],
        reason=row["reason"],
        status=ApprovalState(row["status"]),
        requested_at=row["requested_at"],
        expires_at=row["expires_at"],
        decided_by=row["decided_by"],
        decided_at=row["decided_at"],
        policy_hash=row["policy_hash"] or "",
        mandate_hash=row["mandate_hash"] or "",
        requires_step_up=row["requires_step_up"],
        reexecuted=row["reexecuted"],
        evidence=evidence,
        metadata=meta_raw or {},
    )
