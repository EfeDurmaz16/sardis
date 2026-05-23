"""Policy version store — immutable audit trail for every policy change.

Every call to set_policy() creates a new version record with:
- Auto-incremented version number per agent
- SHA-256 hash of the canonical policy JSON
- Parent link forming a version chain
- Attribution (created_by) for audit

Usage:
    store = PolicyVersionStore()
    version = await store.create_version(pool, "agent_1", policy_dict, "max $500/day", "did:fides:abc")
    latest = await store.get_latest(pool, "agent_1")
    diff = await store.diff_versions(pool, "agent_1", 1, 2)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _nanoid(prefix: str = "pvr") -> str:
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def compute_policy_hash(policy_json: dict[str, Any]) -> str:
    """SHA-256 of canonical (sorted-keys, no-whitespace) JSON."""
    canonical = json.dumps(policy_json, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class PolicyVersion:
    """Immutable record of a single policy state."""
    id: str
    agent_id: str
    version: int
    policy_json: dict[str, Any]
    policy_text: str | None
    created_at: datetime
    created_by: str | None
    parent_version_id: str | None
    hash: str


class PolicyVersionStore:
    """CRUD for the policy_versions table."""

    async def create_version(
        self,
        pool: Any,
        agent_id: str,
        policy_json: dict[str, Any],
        policy_text: str | None = None,
        created_by: str | None = None,
        _max_retries: int = 3,
    ) -> PolicyVersion:
        """Create a new policy version, auto-incrementing from the latest.

        Uses a transaction with SELECT ... FOR UPDATE to prevent race conditions
        on concurrent version creation. Retries on unique constraint violation.
        """
        version_id = _nanoid()
        policy_hash = compute_policy_hash(policy_json)
        now = datetime.now(UTC)

        for attempt in range(_max_retries):
            try:
                async with pool.acquire() as conn, conn.transaction():
                    # Lock the latest version row to serialize concurrent writes
                    row = await conn.fetchrow(
                        "SELECT id, version FROM policy_versions "
                        "WHERE agent_id = $1 ORDER BY version DESC LIMIT 1 "
                        "FOR UPDATE",
                        agent_id,
                    )
                    if row:
                        next_version = row["version"] + 1
                        parent_id = row["id"]
                    else:
                        next_version = 1
                        parent_id = None

                    await conn.execute(
                        """
                            INSERT INTO policy_versions
                                (id, agent_id, version, policy_json, policy_text,
                                 created_at, created_by, parent_version_id, hash)
                            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)
                            """,
                        version_id,
                        agent_id,
                        next_version,
                        json.dumps(policy_json),
                        policy_text,
                        now,
                        created_by,
                        parent_id,
                        policy_hash,
                    )

                return PolicyVersion(
                    id=version_id,
                    agent_id=agent_id,
                    version=next_version,
                    policy_json=policy_json,
                    policy_text=policy_text,
                    created_at=now,
                    created_by=created_by,
                    parent_version_id=parent_id,
                    hash=policy_hash,
                )
            except Exception as e:
                # Retry on unique constraint violation (concurrent write)
                if "unique" in str(e).lower() and attempt < _max_retries - 1:
                    version_id = _nanoid()  # new ID for retry
                    continue
                raise

    async def get_version(
        self,
        pool: Any,
        agent_id: str,
        version: int,
    ) -> PolicyVersion | None:
        """Fetch a specific version."""
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM policy_versions WHERE agent_id = $1 AND version = $2",
                agent_id,
                version,
            )
        return self._row_to_version(row) if row else None

    async def get_latest(
        self,
        pool: Any,
        agent_id: str,
    ) -> PolicyVersion | None:
        """Fetch the most recent version for an agent."""
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM policy_versions "
                "WHERE agent_id = $1 ORDER BY version DESC LIMIT 1",
                agent_id,
            )
        return self._row_to_version(row) if row else None

    async def list_versions(
        self,
        pool: Any,
        agent_id: str,
        limit: int = 20,
    ) -> list[PolicyVersion]:
        """List versions for an agent, newest first."""
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM policy_versions "
                "WHERE agent_id = $1 ORDER BY version DESC LIMIT $2",
                agent_id,
                limit,
            )
        return [self._row_to_version(r) for r in rows]

    async def diff_versions(
        self,
        pool: Any,
        agent_id: str,
        v1: int,
        v2: int,
    ) -> dict[str, Any]:
        """Compute a JSON diff between two versions."""
        ver1 = await self.get_version(pool, agent_id, v1)
        ver2 = await self.get_version(pool, agent_id, v2)
        if ver1 is None or ver2 is None:
            raise ValueError(f"Version not found: v{v1 if ver1 is None else v2}")

        added: dict[str, Any] = {}
        removed: dict[str, Any] = {}
        changed: dict[str, Any] = {}

        all_keys = set(ver1.policy_json.keys()) | set(ver2.policy_json.keys())
        for key in sorted(all_keys):
            val1 = ver1.policy_json.get(key)
            val2 = ver2.policy_json.get(key)
            if val1 is None and val2 is not None:
                added[key] = val2
            elif val1 is not None and val2 is None:
                removed[key] = val1
            elif val1 != val2:
                changed[key] = {"from": val1, "to": val2}

        return {
            "agent_id": agent_id,
            "from_version": v1,
            "to_version": v2,
            "added": added,
            "removed": removed,
            "changed": changed,
        }

    @staticmethod
    def _row_to_version(row: Any) -> PolicyVersion:
        policy_json = row["policy_json"]
        if isinstance(policy_json, str):
            policy_json = json.loads(policy_json)
        return PolicyVersion(
            id=row["id"],
            agent_id=row["agent_id"],
            version=row["version"],
            policy_json=policy_json,
            policy_text=row["policy_text"],
            created_at=row["created_at"],
            created_by=row["created_by"],
            parent_version_id=row["parent_version_id"],
            hash=row["hash"],
        )
