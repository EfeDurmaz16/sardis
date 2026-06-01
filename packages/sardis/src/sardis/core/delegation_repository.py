"""Durable storage for :class:`Delegation` + its signed :class:`DelegationEvidence`.

Two implementations behind one :class:`DelegationStore` protocol, mirroring the
revocation / approval-request / recourse-hold stores:

* :class:`InMemoryDelegationStore` — dev/tests, no I/O, no keys.
* :class:`PostgresDelegationStore` — production durability via the
  ``delegations`` table (migration ``110_delegations.sql``).

The store must answer the two reads chain resolution + revocation propagation
need:

* :meth:`get` — one hop by id.
* :meth:`get_for_delegatee` — the (newest) active delegation a sub-agent holds,
  the entry point for resolving a chain up to the root mandate.
* :meth:`children_of` — the direct child delegations drawn from a given parent
  (mandate id or delegation id), so the Revocation engine can walk a SUBTREE.

Spend recording (:meth:`record_spend`) increments ``spent_total`` on one hop;
the engine calls it for every link in the chain (the delegate's spend decrements
its own + all ancestor delegations).
"""

from __future__ import annotations

import builtins
import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

from .database import Database
from .delegation import (
    Delegation,
    DelegationEvidence,
    DelegationScope,
    DelegationStatus,
    DelegatorKind,
)


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


class DelegationStore(Protocol):
    async def create(self, delegation: Delegation) -> Delegation: ...

    async def get(self, delegation_id: str) -> Delegation | None: ...

    async def save(self, delegation: Delegation) -> Delegation:
        """Persist the full current state (status, spent_total, evidence)."""
        ...

    async def get_for_delegatee(self, delegatee: str) -> Delegation | None:
        """Return the active delegation a sub-agent currently holds (newest)."""
        ...

    async def children_of(
        self, *, parent_kind: str, parent_ref: str
    ) -> builtins.list[Delegation]:
        """Return the direct child delegations drawn from this parent.

        ``parent_kind`` is ``"mandate"`` (children of a root SpendingMandate) or
        ``"delegation"`` (children of another delegation).  Used by the
        Revocation engine to walk a delegation subtree.
        """
        ...

    async def record_spend(self, delegation_id: str, amount: Decimal) -> None:
        """Increment ``spent_total`` on one hop by ``amount`` (token units)."""
        ...


# ── In-memory (dev / tests) ────────────────────────────────────────────


class InMemoryDelegationStore:
    """Process-local store.  Survives nothing; perfect for dev + tests."""

    def __init__(self) -> None:
        self._rows: dict[str, Delegation] = {}

    async def create(self, delegation: Delegation) -> Delegation:
        if delegation.id in self._rows:
            raise ValueError(f"delegation {delegation.id} already exists")
        self._rows[delegation.id] = delegation
        return delegation

    async def get(self, delegation_id: str) -> Delegation | None:
        return self._rows.get(delegation_id)

    async def save(self, delegation: Delegation) -> Delegation:
        self._rows[delegation.id] = delegation
        return delegation

    async def get_for_delegatee(self, delegatee: str) -> Delegation | None:
        matches = [
            d
            for d in self._rows.values()
            if d.delegatee == delegatee and d.status == DelegationStatus.ACTIVE
        ]
        if not matches:
            return None
        # Newest active delegation for this sub-agent.
        return sorted(matches, key=lambda d: d.created_at)[-1]

    async def children_of(
        self, *, parent_kind: str, parent_ref: str
    ) -> builtins.list[Delegation]:
        return [
            d
            for d in self._rows.values()
            if d.delegator_kind.value == parent_kind and d.delegator_ref == parent_ref
        ]

    async def record_spend(self, delegation_id: str, amount: Decimal) -> None:
        row = self._rows.get(delegation_id)
        if row is None:
            return
        row.spent_total = (row.spent_total or Decimal("0")) + Decimal(str(amount))
        if row.amount_cap is not None and row.spent_total >= row.amount_cap:
            row.status = DelegationStatus.EXHAUSTED


# ── Postgres (production durability) ───────────────────────────────────

_COLUMNS = """
    id, org_id, delegator_kind, delegator_ref, delegator_principal, delegatee,
    root_mandate_id, amount_cap, currency, scope, expires_at, valid_from,
    depth, spent_total, status, revoked_at, revoked_by, revocation_reason,
    evidence, metadata, created_at, updated_at
"""


class PostgresDelegationStore:
    """Durable store backed by the ``delegations`` table (migration 110)."""

    async def create(self, delegation: Delegation) -> Delegation:
        await Database.execute(
            f"""
            INSERT INTO delegations ({_COLUMNS})
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,
                    $18,$19,$20,$21,$22)
            """,
            delegation.id,
            delegation.org_id,
            delegation.delegator_kind.value,
            delegation.delegator_ref,
            delegation.delegator_principal,
            delegation.delegatee,
            delegation.root_mandate_id,
            delegation.amount_cap,
            delegation.currency,
            json.dumps(delegation.scope.to_dict()),
            delegation.expires_at,
            delegation.valid_from,
            delegation.depth,
            delegation.spent_total,
            delegation.status.value,
            delegation.revoked_at,
            delegation.revoked_by,
            delegation.revocation_reason,
            json.dumps(delegation.evidence.to_dict()) if delegation.evidence else None,
            json.dumps(delegation.metadata or {}),
            delegation.created_at,
            delegation.updated_at,
        )
        return delegation

    async def get(self, delegation_id: str) -> Delegation | None:
        row = await Database.fetchrow(
            f"SELECT {_COLUMNS} FROM delegations WHERE id = $1", delegation_id
        )
        return _row_to_delegation(row) if row else None

    async def save(self, delegation: Delegation) -> Delegation:
        await Database.execute(
            """
            UPDATE delegations
            SET amount_cap = $2, scope = $3, expires_at = $4, spent_total = $5,
                status = $6, revoked_at = $7, revoked_by = $8,
                revocation_reason = $9, evidence = $10, metadata = $11,
                updated_at = NOW()
            WHERE id = $1
            """,
            delegation.id,
            delegation.amount_cap,
            json.dumps(delegation.scope.to_dict()),
            delegation.expires_at,
            delegation.spent_total,
            delegation.status.value,
            delegation.revoked_at,
            delegation.revoked_by,
            delegation.revocation_reason,
            json.dumps(delegation.evidence.to_dict()) if delegation.evidence else None,
            json.dumps(delegation.metadata or {}),
        )
        return delegation

    async def get_for_delegatee(self, delegatee: str) -> Delegation | None:
        row = await Database.fetchrow(
            f"""
            SELECT {_COLUMNS} FROM delegations
            WHERE delegatee = $1 AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            delegatee,
        )
        return _row_to_delegation(row) if row else None

    async def children_of(
        self, *, parent_kind: str, parent_ref: str
    ) -> builtins.list[Delegation]:
        rows = await Database.fetch(
            f"""
            SELECT {_COLUMNS} FROM delegations
            WHERE delegator_kind = $1 AND delegator_ref = $2
            """,
            parent_kind,
            parent_ref,
        )
        return [_row_to_delegation(r) for r in rows]

    async def record_spend(self, delegation_id: str, amount: Decimal) -> None:
        # Increment + flip to exhausted in one statement so a concurrent read
        # never sees a cap-exceeding spent_total against a still-active row.
        await Database.execute(
            """
            UPDATE delegations
            SET spent_total = COALESCE(spent_total, 0) + $2,
                status = CASE
                    WHEN amount_cap IS NOT NULL
                         AND COALESCE(spent_total, 0) + $2 >= amount_cap
                         AND status = 'active'
                    THEN 'exhausted' ELSE status END,
                updated_at = NOW()
            WHERE id = $1
            """,
            delegation_id,
            Decimal(str(amount)),
        )


def _row_to_delegation(row: Any) -> Delegation:
    data = dict(row)

    scope_raw = data.get("scope")
    if isinstance(scope_raw, str):
        scope_raw = json.loads(scope_raw) if scope_raw else {}
    scope = DelegationScope.from_dict(scope_raw or {})

    ev_raw = data.get("evidence")
    if isinstance(ev_raw, str):
        ev_raw = json.loads(ev_raw) if ev_raw else None
    evidence = DelegationEvidence.from_dict(ev_raw) if ev_raw else None

    meta_raw = data.get("metadata")
    if isinstance(meta_raw, str):
        meta_raw = json.loads(meta_raw) if meta_raw else {}

    status_raw = (data.get("status") or "active").lower()
    try:
        status = DelegationStatus(status_raw)
    except ValueError:
        status = DelegationStatus.ACTIVE

    return Delegation(
        id=data["id"],
        org_id=data.get("org_id") or "",
        delegator_kind=DelegatorKind(data["delegator_kind"]),
        delegator_ref=data["delegator_ref"],
        delegator_principal=data.get("delegator_principal") or "",
        delegatee=data["delegatee"],
        root_mandate_id=data.get("root_mandate_id") or "",
        amount_cap=_to_decimal(data.get("amount_cap")),
        currency=data.get("currency") or "USDC",
        scope=scope,
        expires_at=_as_dt(data.get("expires_at")),
        valid_from=_as_dt(data.get("valid_from")),
        depth=int(data.get("depth") or 1),
        spent_total=_to_decimal(data.get("spent_total")) or Decimal("0"),
        status=status,
        revoked_at=_as_dt(data.get("revoked_at")),
        revoked_by=data.get("revoked_by"),
        revocation_reason=data.get("revocation_reason"),
        evidence=evidence,
        metadata=meta_raw or {},
        created_at=_as_dt(data.get("created_at")),
        updated_at=_as_dt(data.get("updated_at")),
    )


def _as_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


__all__ = [
    "DelegationStore",
    "InMemoryDelegationStore",
    "PostgresDelegationStore",
]
