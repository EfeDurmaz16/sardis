"""Persistent spending policy state store with atomic enforcement.

Ensures spending limits are enforced atomically in the database,
preventing races in multi-instance deployments.

SECURITY: Without this, a process restart resets all spending limits to zero,
allowing agents to bypass total and daily/weekly/monthly limits.
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
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool

    async def record_spend_atomic(
        self,
        agent_id: str,
        amount: Decimal,
        currency: str = "USDC",
        merchant_id: Optional[str] = None,
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
                window_updates: list[tuple[object, Decimal, datetime]] = []
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

                    # Compute effective spend for this window. If expired, reset in-memory first.
                    if now >= window_start + duration:
                        current_spent = Decimal("0")
                        window_start = now

                    # Check window limit
                    if current_spent + amount > limit_amount:
                        return False, f"{window_type}_limit_exceeded"

                    # Store final value to persist in one batch statement.
                    window_updates.append((window["id"], current_spent + amount, window_start))

                # All checks passed — record the spend atomically
                await conn.execute(
                    """
                    UPDATE spending_policies
                    SET spent_total = spent_total + $1, updated_at = NOW()
                    WHERE id = $2
                    """,
                    amount,
                    policy["id"],
                )

                # Update all windows in one statement to minimize lock hold time.
                if window_updates:
                    window_ids = [w[0] for w in window_updates]
                    window_spent = [w[1] for w in window_updates]
                    window_starts = [w[2] for w in window_updates]
                    await conn.execute(
                        """
                        UPDATE time_window_limits tw
                        SET current_spent = u.current_spent,
                            window_start = u.window_start
                        FROM (
                            SELECT
                                UNNEST($1::uuid[]) AS id,
                                UNNEST($2::numeric[]) AS current_spent,
                                UNNEST($3::timestamptz[]) AS window_start
                        ) AS u
                        WHERE tw.id = u.id
                        """,
                        window_ids,
                        window_spent,
                        window_starts,
                    )

                # Record velocity entry
                await conn.execute(
                    """
                    INSERT INTO spending_velocity (policy_id, tx_timestamp, amount, merchant_id)
                    VALUES ($1, NOW(), $2, $3)
                    """,
                    policy["id"],
                    amount,
                    merchant_id,
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

    async def check_velocity(
        self,
        agent_id: str,
        max_per_minute: int = 5,
        max_per_hour: int = 60,
    ) -> tuple[bool, str]:
        """Check if agent is within velocity limits.

        Prevents rapid-fire small transactions that individually pass
        per-tx limits but collectively represent abuse.
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            policy = await conn.fetchrow(
                "SELECT id FROM spending_policies WHERE agent_id = $1::uuid",
                agent_id,
            )
            if not policy:
                return False, "no_policy_found"

            count_minute = await conn.fetchval(
                """
                SELECT COUNT(*) FROM spending_velocity
                WHERE policy_id = $1 AND tx_timestamp > NOW() - INTERVAL '1 minute'
                """,
                policy["id"],
            )
            if count_minute >= max_per_minute:
                return False, "velocity_limit_per_minute"

            count_hour = await conn.fetchval(
                """
                SELECT COUNT(*) FROM spending_velocity
                WHERE policy_id = $1 AND tx_timestamp > NOW() - INTERVAL '1 hour'
                """,
                policy["id"],
            )
            if count_hour >= max_per_hour:
                return False, "velocity_limit_per_hour"

            return True, "OK"

    async def load_state(self, agent_id: str) -> Optional[dict]:
        """Load current spending state from the database.

        Returns dict with spent_total and per-window current_spent,
        or None if no policy exists for this agent.
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            policy = await conn.fetchrow(
                """
                SELECT id, spent_total, limit_per_tx, limit_total
                FROM spending_policies
                WHERE agent_id = $1::uuid
                """,
                agent_id,
            )
            if not policy:
                return None

            windows = await conn.fetch(
                """
                SELECT window_type, current_spent, limit_amount, window_start
                FROM time_window_limits
                WHERE policy_id = $1
                """,
                policy["id"],
            )

            state = {
                "spent_total": Decimal(str(policy["spent_total"])),
                "limit_per_tx": Decimal(str(policy["limit_per_tx"])),
                "limit_total": Decimal(str(policy["limit_total"])),
                "windows": {},
            }
            for w in windows:
                state["windows"][w["window_type"]] = {
                    "current_spent": Decimal(str(w["current_spent"])),
                    "limit_amount": Decimal(str(w["limit_amount"])),
                    "window_start": w["window_start"],
                }
            return state

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

    async def cleanup_velocity(self, max_age_hours: int = 24) -> int:
        """Remove velocity records older than max_age_hours.

        Call periodically (e.g. via pg_cron or a scheduled task).
        Returns number of deleted records.
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM spending_velocity
                WHERE tx_timestamp < NOW() - ($1 || ' hours')::INTERVAL
                """,
                str(max_age_hours),
            )
            count = int(result.split()[-1]) if result else 0
            if count > 0:
                logger.info(f"Cleaned up {count} velocity records older than {max_age_hours}h")
            return count

    async def close(self):
        # Pool lifecycle managed by Database.close() at app shutdown
        pass
