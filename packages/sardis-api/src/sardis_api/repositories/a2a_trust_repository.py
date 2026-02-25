"""Repository for A2A trust relations (org-scoped sender -> recipient graph)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional
import os
import uuid


class A2ATrustRepository:
    """Persisted trust relation store with in-memory fallback for dev/tests."""

    def __init__(self, pool=None, dsn: str | None = None):
        self._pool = pool
        self._dsn = dsn or os.getenv("DATABASE_URL", "")
        self._table_ready = False
        self._relations_mem: dict[str, set[tuple[str, str]]] = defaultdict(set)

    def _use_postgres(self) -> bool:
        if self._pool is not None:
            return True
        return self._dsn.startswith(("postgresql://", "postgres://"))

    async def _get_pool(self):
        if self._pool is None:
            if not self._use_postgres():
                return None
            import asyncpg

            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
        return self._pool

    async def _ensure_table(self) -> None:
        if self._table_ready or not self._use_postgres():
            return
        pool = await self._get_pool()
        if pool is None:
            return
        environment = (os.getenv("SARDIS_ENVIRONMENT", "dev") or "dev").strip().lower()
        async with pool.acquire() as conn:
            if environment in {"prod", "production"}:
                exists = await conn.fetchval(
                    """
                    SELECT EXISTS(
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_name = 'a2a_trust_relations'
                    )
                    """
                )
                if not exists:
                    raise RuntimeError(
                        "a2a_trust_relations table not found in production; "
                        "run database migrations before starting the API"
                    )
            else:
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS a2a_trust_relations (
                        id UUID PRIMARY KEY,
                        organization_id TEXT NOT NULL,
                        sender_agent_id TEXT NOT NULL,
                        recipient_agent_id TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE (organization_id, sender_agent_id, recipient_agent_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_a2a_trust_org_sender
                      ON a2a_trust_relations(organization_id, sender_agent_id);
                    CREATE INDEX IF NOT EXISTS idx_a2a_trust_org_recipient
                      ON a2a_trust_relations(organization_id, recipient_agent_id);
                    """
                )
        self._table_ready = True

    @staticmethod
    def _normalize(value: str) -> str:
        return (value or "").strip()

    async def upsert_relation(
        self,
        *,
        organization_id: str,
        sender_agent_id: str,
        recipient_agent_id: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        org_id = self._normalize(organization_id)
        sender = self._normalize(sender_agent_id)
        recipient = self._normalize(recipient_agent_id)
        if not org_id:
            raise ValueError("organization_id_required")
        if not sender or not recipient:
            raise ValueError("sender_and_recipient_required")

        meta = metadata or {}
        now = datetime.now(timezone.utc).isoformat()
        if not self._use_postgres():
            self._relations_mem[org_id].add((sender, recipient))
            return {
                "organization_id": org_id,
                "sender_agent_id": sender,
                "recipient_agent_id": recipient,
                "metadata": meta,
                "updated_at": now,
            }

        await self._ensure_table()
        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("a2a_trust_repository_pool_unavailable")
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO a2a_trust_relations (
                    id, organization_id, sender_agent_id, recipient_agent_id, metadata
                ) VALUES ($1::uuid, $2, $3, $4, $5::jsonb)
                ON CONFLICT (organization_id, sender_agent_id, recipient_agent_id)
                DO UPDATE SET
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                RETURNING organization_id, sender_agent_id, recipient_agent_id, metadata, updated_at
                """,
                str(uuid.uuid4()),
                org_id,
                sender,
                recipient,
                meta,
            )
        return dict(row)

    async def delete_relation(
        self,
        *,
        organization_id: str,
        sender_agent_id: str,
        recipient_agent_id: str,
    ) -> bool:
        org_id = self._normalize(organization_id)
        sender = self._normalize(sender_agent_id)
        recipient = self._normalize(recipient_agent_id)
        if not org_id or not sender or not recipient:
            return False

        if not self._use_postgres():
            key = (sender, recipient)
            if key not in self._relations_mem.get(org_id, set()):
                return False
            self._relations_mem[org_id].discard(key)
            return True

        await self._ensure_table()
        pool = await self._get_pool()
        if pool is None:
            return False
        async with pool.acquire() as conn:
            deleted = await conn.execute(
                """
                DELETE FROM a2a_trust_relations
                WHERE organization_id = $1 AND sender_agent_id = $2 AND recipient_agent_id = $3
                """,
                org_id,
                sender,
                recipient,
            )
        return str(deleted).startswith("DELETE 1")

    async def get_trust_table(self, organization_id: str) -> dict[str, set[str]]:
        org_id = self._normalize(organization_id)
        if not org_id:
            return {}
        if not self._use_postgres():
            out: dict[str, set[str]] = defaultdict(set)
            for sender, recipient in self._relations_mem.get(org_id, set()):
                out[sender].add(recipient)
            return dict(out)

        await self._ensure_table()
        pool = await self._get_pool()
        if pool is None:
            return {}
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT sender_agent_id, recipient_agent_id
                FROM a2a_trust_relations
                WHERE organization_id = $1
                ORDER BY sender_agent_id ASC, recipient_agent_id ASC
                """,
                org_id,
            )
        out: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            out[str(row["sender_agent_id"])].add(str(row["recipient_agent_id"]))
        return dict(out)
