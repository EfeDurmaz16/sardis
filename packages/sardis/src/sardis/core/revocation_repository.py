"""Durable storage for :class:`Revocation` + its signed :class:`RevocationProof`.

Two implementations behind one :class:`RevocationStore` protocol, mirroring the
approval-request / recourse-hold stores:

* :class:`InMemoryRevocationStore` — dev/tests, no I/O, no keys.
* :class:`PostgresRevocationStore` — production durability via the
  ``revocations`` table (migration ``109_revocations.sql``).

The store persists the full target list and the signed proof alongside the
revocation so the kill record is durable and tamper-evident across restarts.

Idempotency is a first-class store concern: a revocation is **keyed by its
target** while in force.  :meth:`get_active_for_target` lets the engine return
the *same* proof for a re-revoke instead of double-propagating.  On Postgres a
partial unique index enforces "at most one active revocation per target" at the
DB layer too, so two concurrent revoke calls cannot both create one.
"""

from __future__ import annotations

import builtins
import json
from typing import Protocol

from .database import Database
from .revocation import (
    PropagationTarget,
    Revocation,
    RevocationProof,
    RevocationStatus,
    RevocationTargetKind,
)


class RevocationStore(Protocol):
    async def create(self, revocation: Revocation) -> Revocation: ...

    async def get(self, revocation_id: str) -> Revocation | None: ...

    async def get_active_for_target(
        self, *, target_kind: str, target_ref: str
    ) -> Revocation | None:
        """Return the existing revocation for this target, if one is in force.

        Used for idempotency: a re-revoke of an already-revoked target returns
        the same signed proof rather than propagating again.
        """
        ...

    async def save(self, revocation: Revocation) -> Revocation:
        """Persist the full current state (status, targets, signed proof)."""
        ...

    async def list_recent(
        self, *, limit: int = 100
    ) -> builtins.list[Revocation]: ...


# ── In-memory (dev / tests) ────────────────────────────────────────────


class InMemoryRevocationStore:
    """Process-local store.  Survives nothing; perfect for dev + tests."""

    def __init__(self) -> None:
        self._rows: dict[str, Revocation] = {}

    async def create(self, revocation: Revocation) -> Revocation:
        if revocation.id in self._rows:
            raise ValueError(f"revocation {revocation.id} already exists")
        self._rows[revocation.id] = revocation
        return revocation

    async def get(self, revocation_id: str) -> Revocation | None:
        return self._rows.get(revocation_id)

    async def get_active_for_target(
        self, *, target_kind: str, target_ref: str
    ) -> Revocation | None:
        # A revocation is terminal-by-construction; "active for target" means
        # one already exists for this (kind, ref).  Newest first.
        matches = [
            r
            for r in self._rows.values()
            if r.target_kind.value == target_kind and r.target_ref == target_ref
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda r: r.requested_at)[-1]

    async def save(self, revocation: Revocation) -> Revocation:
        self._rows[revocation.id] = revocation
        return revocation

    async def list_recent(self, *, limit: int = 100) -> builtins.list[Revocation]:
        rows = sorted(self._rows.values(), key=lambda r: r.requested_at, reverse=True)
        return rows[:limit]


# ── Postgres (production durability) ───────────────────────────────────

_COLUMNS = """
    id, target_kind, target_ref, scope, requested_by, requested_at,
    status, revoked_at, targets, proof, metadata
"""


class PostgresRevocationStore:
    """Durable store backed by the ``revocations`` table."""

    async def create(self, revocation: Revocation) -> Revocation:
        await Database.execute(
            f"""
            INSERT INTO revocations ({_COLUMNS})
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            """,
            revocation.id,
            revocation.target_kind.value,
            revocation.target_ref,
            revocation.scope,
            revocation.requested_by,
            revocation.requested_at,
            revocation.status.value,
            revocation.revoked_at,
            json.dumps([t.to_dict() for t in revocation.targets]),
            json.dumps(revocation.proof.to_dict()) if revocation.proof else None,
            json.dumps(revocation.metadata or {}),
        )
        return revocation

    async def get(self, revocation_id: str) -> Revocation | None:
        row = await Database.fetchrow(
            f"SELECT {_COLUMNS} FROM revocations WHERE id = $1", revocation_id
        )
        return _row_to_revocation(row) if row else None

    async def get_active_for_target(
        self, *, target_kind: str, target_ref: str
    ) -> Revocation | None:
        row = await Database.fetchrow(
            f"""
            SELECT {_COLUMNS} FROM revocations
            WHERE target_kind = $1 AND target_ref = $2
            ORDER BY requested_at DESC
            LIMIT 1
            """,
            target_kind,
            target_ref,
        )
        return _row_to_revocation(row) if row else None

    async def save(self, revocation: Revocation) -> Revocation:
        await Database.execute(
            """
            UPDATE revocations
            SET status = $2, revoked_at = $3, targets = $4, proof = $5,
                metadata = $6
            WHERE id = $1
            """,
            revocation.id,
            revocation.status.value,
            revocation.revoked_at,
            json.dumps([t.to_dict() for t in revocation.targets]),
            json.dumps(revocation.proof.to_dict()) if revocation.proof else None,
            json.dumps(revocation.metadata or {}),
        )
        return revocation

    async def list_recent(self, *, limit: int = 100) -> builtins.list[Revocation]:
        rows = await Database.fetch(
            f"""
            SELECT {_COLUMNS} FROM revocations
            ORDER BY requested_at DESC
            LIMIT $1
            """,
            limit,
        )
        return [_row_to_revocation(r) for r in rows]


def _row_to_revocation(row) -> Revocation:
    targets_raw = row["targets"]
    if isinstance(targets_raw, str):
        targets_raw = json.loads(targets_raw) if targets_raw else []
    targets = [PropagationTarget.from_dict(t) for t in (targets_raw or [])]

    proof_raw = row["proof"]
    if isinstance(proof_raw, str):
        proof_raw = json.loads(proof_raw) if proof_raw else None
    proof = RevocationProof.from_dict(proof_raw) if proof_raw else None

    meta_raw = row["metadata"]
    if isinstance(meta_raw, str):
        meta_raw = json.loads(meta_raw) if meta_raw else {}

    return Revocation(
        id=row["id"],
        target_kind=RevocationTargetKind(row["target_kind"]),
        target_ref=row["target_ref"],
        scope=row["scope"] or "all",
        requested_by=row["requested_by"] or "",
        requested_at=row["requested_at"],
        status=RevocationStatus(row["status"]),
        revoked_at=row["revoked_at"],
        targets=targets,
        proof=proof,
        metadata=meta_raw or {},
    )


__all__ = [
    "InMemoryRevocationStore",
    "PostgresRevocationStore",
    "RevocationStore",
]
