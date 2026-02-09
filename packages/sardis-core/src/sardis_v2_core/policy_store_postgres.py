"""PostgreSQL-backed policy store.

Stores SpendingPolicy JSON in `agents.spending_policy` (JSONB).
This keeps the demo/production API behavior identical.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from .policy_store import AsyncPolicyStore
from .spending_policy import SpendingPolicy, create_default_policy
from .spending_policy_json import spending_policy_from_json, spending_policy_to_json


class PostgresPolicyStore(AsyncPolicyStore):
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

    async def fetch_policy(self, agent_id: str) -> Optional[SpendingPolicy]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT spending_policy FROM agents WHERE external_id = $1",
                agent_id,
            )
            if not row:
                return None
            data = row["spending_policy"]
            if not isinstance(data, dict):
                return None
            return spending_policy_from_json(data)

    async def set_policy(self, agent_id: str, policy: SpendingPolicy) -> None:
        import json as _json
        pool = await self._get_pool()
        payload = spending_policy_to_json(policy)
        async with pool.acquire() as conn:
            # Ensure agent exists (minimal upsert).
            await conn.execute(
                """
                INSERT INTO agents (external_id, name)
                VALUES ($1, $1)
                ON CONFLICT (external_id) DO NOTHING
                """,
                agent_id,
            )
            await conn.execute(
                "UPDATE agents SET spending_policy = $2::jsonb, updated_at = NOW() WHERE external_id = $1",
                agent_id,
                _json.dumps(payload),
            )

    async def delete_policy(self, agent_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            res = await conn.execute(
                "UPDATE agents SET spending_policy = NULL, updated_at = NOW() WHERE external_id = $1",
                agent_id,
            )
            return "UPDATE 1" in res

    async def record_spend(self, agent_id: str, amount: Decimal) -> SpendingPolicy:
        """
        Atomically update spend state inside agents.spending_policy (JSONB).

        Uses row-level locking to prevent concurrent lost updates.
        """
        import json as _json
        if amount <= 0:
            raise ValueError("amount_must_be_positive")

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Ensure agent exists (minimal upsert).
                await conn.execute(
                    """
                    INSERT INTO agents (external_id, name)
                    VALUES ($1, $1)
                    ON CONFLICT (external_id) DO NOTHING
                    """,
                    agent_id,
                )

                row = await conn.fetchrow(
                    "SELECT spending_policy FROM agents WHERE external_id = $1 FOR UPDATE",
                    agent_id,
                )
                data = row["spending_policy"] if row else None
                policy = spending_policy_from_json(data) if isinstance(data, dict) else create_default_policy(agent_id)

                for window in (policy.daily_limit, policy.weekly_limit, policy.monthly_limit):
                    if window is None:
                        continue
                    window.reset_if_expired()
                    window.record_spend(amount)

                policy.spent_total += amount
                policy.updated_at = datetime.now(timezone.utc)

                payload = spending_policy_to_json(policy)
                await conn.execute(
                    "UPDATE agents SET spending_policy = $2::jsonb, updated_at = NOW() WHERE external_id = $1",
                    agent_id,
                    _json.dumps(payload),
                )
                return policy

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
