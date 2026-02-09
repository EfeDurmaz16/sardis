"""PostgreSQL-backed agent repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Any

from .agents import Agent, AgentPolicy, SpendingLimits


class PostgresAgentRepository:
    """PostgreSQL agent repository.

    Maps:
    - Agent.agent_id <-> agents.external_id
    - Agent.owner_id <-> organizations.external_id

    NOTE: The canonical schema stores only a subset of agent fields. We persist
    the remaining fields under `agents.metadata` to avoid losing information.
    """

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return self._pool

    async def _ensure_org(self, conn, owner_id: str) -> str:
        """Ensure an organization row exists and return its UUID."""
        row = await conn.fetchrow(
            "SELECT id FROM organizations WHERE external_id = $1",
            owner_id,
        )
        if row:
            return str(row["id"])
        created = await conn.fetchrow(
            """
            INSERT INTO organizations (external_id, name, settings)
            VALUES ($1, $2, '{}'::jsonb)
            RETURNING id
            """,
            owner_id,
            owner_id,
        )
        return str(created["id"])

    @staticmethod
    def _agent_from_row(row: Any, wallet_external_id: Optional[str]) -> Agent:
        meta = row.get("metadata") if isinstance(row, dict) else row["metadata"]
        if not isinstance(meta, dict):
            meta = {}
        spending_limits = SpendingLimits()
        policy = AgentPolicy()
        try:
            if isinstance(meta.get("spending_limits"), dict):
                spending_limits = SpendingLimits(**meta["spending_limits"])
            if isinstance(meta.get("policy"), dict):
                policy = AgentPolicy(**meta["policy"])
        except Exception:
            # fall back to defaults
            pass

        return Agent(
            agent_id=str(row["external_id"]),
            name=str(row["name"]),
            description=row.get("description"),
            owner_id=str(row.get("organization_external_id") or meta.get("owner_id") or "default"),
            wallet_id=wallet_external_id or meta.get("wallet_id"),
            spending_limits=spending_limits,
            policy=policy,
            api_key_hash=meta.get("api_key_hash"),
            is_active=bool(row.get("is_active", True)),
            metadata=meta,
            created_at=row.get("created_at") or datetime.now(timezone.utc),
            updated_at=row.get("updated_at") or datetime.now(timezone.utc),
        )

    async def create(
        self,
        name: str,
        owner_id: str = "default",
        description: Optional[str] = None,
        spending_limits: Optional[SpendingLimits] = None,
        policy: Optional[AgentPolicy] = None,
        metadata: Optional[dict] = None,
    ) -> Agent:
        pool = await self._get_pool()
        base_meta = dict(metadata or {})
        base_meta["owner_id"] = owner_id
        base_meta["spending_limits"] = (spending_limits or SpendingLimits()).model_dump(mode="json")
        base_meta["policy"] = (policy or AgentPolicy()).model_dump(mode="json")

        async with pool.acquire() as conn:
            async with conn.transaction():
                org_id = await self._ensure_org(conn, owner_id)
                import json as _json
                row = await conn.fetchrow(
                    """
                    INSERT INTO agents (external_id, organization_id, name, description, metadata, is_active)
                    VALUES ($1, $2::uuid, $3, $4, $5::jsonb, TRUE)
                    RETURNING external_id, name, description, is_active, created_at, updated_at, metadata
                    """,
                    f"agent_{__import__('uuid').uuid4().hex[:16]}",
                    org_id,
                    name,
                    description,
                    _json.dumps(base_meta),
                )

                # attach organization_external_id for mapping back to owner_id
                agent = self._agent_from_row(
                    {**dict(row), "organization_external_id": owner_id},
                    wallet_external_id=None,
                )
                return agent

    async def get(self, agent_id: str) -> Optional[Agent]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT a.external_id, a.name, a.description, a.is_active, a.created_at, a.updated_at, a.metadata,
                       o.external_id AS organization_external_id
                FROM agents a
                LEFT JOIN organizations o ON o.id = a.organization_id
                WHERE a.external_id = $1
                """,
                agent_id,
            )
            if not row:
                return None
            wallet_row = await conn.fetchrow(
                """
                SELECT w.external_id
                FROM wallets w
                WHERE w.agent_id = (SELECT id FROM agents WHERE external_id = $1)
                ORDER BY w.created_at DESC
                LIMIT 1
                """,
                agent_id,
            )
            wallet_external_id = str(wallet_row["external_id"]) if wallet_row else None
            return self._agent_from_row(dict(row), wallet_external_id)

    async def list(
        self,
        owner_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Agent]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            where = []
            params: list[Any] = []
            idx = 1
            if owner_id:
                where.append(f"o.external_id = ${idx}")
                params.append(owner_id)
                idx += 1
            if is_active is not None:
                where.append(f"a.is_active = ${idx}")
                params.append(is_active)
                idx += 1

            where_sql = ("WHERE " + " AND ".join(where)) if where else ""
            rows = await conn.fetch(
                f"""
                SELECT a.external_id, a.name, a.description, a.is_active, a.created_at, a.updated_at, a.metadata,
                       o.external_id AS organization_external_id
                FROM agents a
                LEFT JOIN organizations o ON o.id = a.organization_id
                {where_sql}
                ORDER BY a.created_at DESC
                LIMIT ${idx} OFFSET ${idx + 1}
                """,
                *params,
                limit,
                offset,
            )

            agents: list[Agent] = []
            for r in rows:
                agent_id = str(r["external_id"])
                wallet_row = await conn.fetchrow(
                    """
                    SELECT w.external_id
                    FROM wallets w
                    WHERE w.agent_id = (SELECT id FROM agents WHERE external_id = $1)
                    ORDER BY w.created_at DESC
                    LIMIT 1
                    """,
                    agent_id,
                )
                wallet_external_id = str(wallet_row["external_id"]) if wallet_row else None
                agents.append(self._agent_from_row(dict(r), wallet_external_id))
            return agents

    async def update(
        self,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        spending_limits: Optional[SpendingLimits] = None,
        policy: Optional[AgentPolicy] = None,
        is_active: Optional[bool] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[Agent]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            current = await conn.fetchrow(
                """
                SELECT a.external_id, a.name, a.description, a.is_active, a.created_at, a.updated_at, a.metadata,
                       o.external_id AS organization_external_id
                FROM agents a
                LEFT JOIN organizations o ON o.id = a.organization_id
                WHERE a.external_id = $1
                """,
                agent_id,
            )
            if not current:
                return None

            meta = current["metadata"] if isinstance(current["metadata"], dict) else {}
            if not isinstance(meta, dict):
                meta = {}
            if metadata is not None:
                meta.update(metadata)
            if spending_limits is not None:
                meta["spending_limits"] = spending_limits.model_dump(mode="json")
            if policy is not None:
                meta["policy"] = policy.model_dump(mode="json")

            import json as _json
            await conn.execute(
                """
                UPDATE agents
                SET name = COALESCE($2, name),
                    description = COALESCE($3, description),
                    is_active = COALESCE($4, is_active),
                    metadata = $5::jsonb,
                    updated_at = NOW()
                WHERE external_id = $1
                """,
                agent_id,
                name,
                description,
                is_active,
                _json.dumps(meta),
            )
            return await self.get(agent_id)

    async def delete(self, agent_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            res = await conn.execute("DELETE FROM agents WHERE external_id = $1", agent_id)
            return "DELETE 1" in res

    async def bind_wallet(self, agent_id: str, wallet_id: str) -> Optional[Agent]:
        # Wallets own the FK, so binding is a no-op here (WalletRepository creates the relationship).
        # We still store wallet_id in metadata for convenience.
        return await self.update(agent_id, metadata={"wallet_id": wallet_id})

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

