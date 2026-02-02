"""Persistent spending policy state store with atomic enforcement.

Ensures spending limits are enforced atomically in the database,
preventing races in multi-instance deployments.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


class SpendingPolicyStore:
    """Database-backed spending policy state with atomic limit enforcement.

    All spend recording and limit checks are performed in a single SQL
    transaction using row-level locking (SELECT ... FOR UPDATE) to prevent
    races between concurrent workers.
    """

    def __init__(self, dsn: Optional[str] = None):
        self._dsn = dsn or os.getenv("DATABASE_URL", "")
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
        return self._pool

    async def record_spend_atomic(
        self,
        agent_id: str,
        amount: Decimal,
        currency: str = "USDC",
    ) -> tuple[bool, str]:
        """Atomically check limits and record a spend.

        Returns (success, reason). If success is False, no state is modified.
        This method uses SELECT FOR UPDATE to prevent concurrent over-spending.
        """
        if amount <= 0:
            return False, "amount_must_be_positive"

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Lock the policy row for this agent
                policy = await conn.fetchrow(
                    """
                    SELECT id, limit_per_tx, limit_total, spent_total
                    FROM spending_policies
                    WHERE agent_id = $1::uuid
                    FOR UPDATE
                    """,
                    agent_id,
                )

                if not policy:
                    return False, "no_policy_found"

                limit_per_tx = Decimal(str(policy["limit_per_tx"]))
                limit_total = Decimal(str(policy["limit_total"]))
                spent_total = Decimal(str(policy["spent_total"]))

                # Per-transaction limit
                if amount > limit_per_tx:
                    return False, "per_transaction_limit"

                # Lifetime total limit
                if spent_total + amount > limit_total:
                    return False, "total_limit_exceeded"

                # Check time window limits (with row locking)
                windows = await conn.fetch(
                    """
                    SELECT id, window_type, limit_amount, current_spent, window_start
                    FROM time_window_limits
                    WHERE policy_id = $1
                    FOR UPDATE
                    """,
                    policy["id"],
                )

                now = datetime.now(timezone.utc)
                for window in windows:
                    window_type = window["window_type"]
                    limit_amount = Decimal(str(window["limit_amount"]))
                    current_spent = Decimal(str(window["current_spent"]))
                    window_start = window["window_start"]

                    # Determine window duration
                    if window_type == "daily":
                        duration = timedelta(days=1)
                    elif window_type == "weekly":
                        duration = timedelta(weeks=1)
                    elif window_type == "monthly":
                        duration = timedelta(days=30)
                    else:
                        continue

                    # Reset window if expired
                    if now >= window_start + duration:
                        current_spent = Decimal("0")
                        await conn.execute(
                            """
                            UPDATE time_window_limits
                            SET current_spent = 0, window_start = $1
                            WHERE id = $2
                            """,
                            now,
                            window["id"],
                        )

                    # Check window limit
                    if current_spent + amount > limit_amount:
                        return False, f"{window_type}_limit_exceeded"

                # All checks passed — record the spend atomically
                await conn.execute(
                    """
                    UPDATE spending_policies
                    SET spent_total = spent_total + $1, updated_at = NOW()
                    WHERE id = $2
                    """,
                    float(amount),
                    policy["id"],
                )

                # Update all time windows
                for window in windows:
                    await conn.execute(
                        """
                        UPDATE time_window_limits
                        SET current_spent = current_spent + $1
                        WHERE id = $2
                        """,
                        float(amount),
                        window["id"],
                    )

                logger.info(
                    "Spend recorded atomically",
                    extra={
                        "agent_id": agent_id,
                        "amount": str(amount),
                        "new_spent_total": str(spent_total + amount),
                    },
                )
                return True, "OK"

    async def get_remaining(self, agent_id: str) -> Optional[dict]:
        """Get remaining spend capacity for an agent."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            policy = await conn.fetchrow(
                """
                SELECT limit_total, spent_total, limit_per_tx
                FROM spending_policies
                WHERE agent_id = $1::uuid
                """,
                agent_id,
            )
            if not policy:
                return None

            remaining_total = Decimal(str(policy["limit_total"])) - Decimal(str(policy["spent_total"]))

            windows = await conn.fetch(
                """
                SELECT window_type, limit_amount, current_spent, window_start
                FROM time_window_limits
                WHERE policy_id = (SELECT id FROM spending_policies WHERE agent_id = $1::uuid)
                """,
                agent_id,
            )

            result = {
                "remaining_total": max(Decimal("0"), remaining_total),
                "limit_per_tx": Decimal(str(policy["limit_per_tx"])),
            }
            for w in windows:
                remaining = Decimal(str(w["limit_amount"])) - Decimal(str(w["current_spent"]))
                result[f"remaining_{w['window_type']}"] = max(Decimal("0"), remaining)

            return result

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None
