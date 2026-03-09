"""Execution side-effect queue for durable post-payment operations.

Instead of performing ledger appends, webhooks, and spend recording inline
(where failure leaves state inconsistent), callers queue side effects that
a background worker processes with retry semantics.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExecutionSideEffect:
    """A deferred side effect to execute after payment completes."""
    tx_id: str
    effect_type: str  # 'ledger_append', 'webhook', 'spend_record', 'alert'
    payload: dict[str, Any] = field(default_factory=dict)
    max_attempts: int = 5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def queue_side_effect(effect: ExecutionSideEffect) -> int | None:
    """Insert a side effect into the database queue.

    Returns the row ID on success, None if DB is unavailable.
    """
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO execution_side_effects (tx_id, effect_type, payload, max_attempts)
                VALUES ($1, $2, $3::jsonb, $4)
                RETURNING id
                """,
                effect.tx_id,
                effect.effect_type,
                json.dumps(effect.payload),
                effect.max_attempts,
            )
            return row["id"] if row else None
    except Exception as e:
        logger.error("Failed to queue side effect (tx=%s, type=%s): %s", effect.tx_id, effect.effect_type, e)
        return None


async def fetch_pending_effects(batch_size: int = 20) -> list[dict[str, Any]]:
    """Fetch and lock pending side effects for processing.

    Uses FOR UPDATE SKIP LOCKED to support concurrent workers.
    """
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, tx_id, effect_type, payload, attempt_count, max_attempts
                FROM execution_side_effects
                WHERE status IN ('pending', 'failed')
                  AND attempt_count < max_attempts
                  AND next_retry_at <= now()
                ORDER BY id
                LIMIT $1
                FOR UPDATE SKIP LOCKED
                """,
                batch_size,
            )
            # Mark as processing
            if rows:
                ids = [r["id"] for r in rows]
                await conn.execute(
                    """
                    UPDATE execution_side_effects
                    SET status = 'processing', attempt_count = attempt_count + 1
                    WHERE id = ANY($1::bigint[])
                    """,
                    ids,
                )
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error("Failed to fetch pending side effects: %s", e)
        return []


async def mark_completed(effect_id: int) -> None:
    """Mark a side effect as successfully processed."""
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE execution_side_effects
                SET status = 'completed', processed_at = now()
                WHERE id = $1
                """,
                effect_id,
            )
    except Exception as e:
        logger.error("Failed to mark effect %d completed: %s", effect_id, e)


async def mark_failed(effect_id: int, error: str) -> None:
    """Mark a side effect as failed with exponential backoff retry."""
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE execution_side_effects
                SET status = 'failed',
                    last_error = $2,
                    next_retry_at = now() + (interval '1 second' * power(2, attempt_count))
                WHERE id = $1
                """,
                effect_id,
                error[:1000],
            )
    except Exception as e:
        logger.error("Failed to mark effect %d failed: %s", effect_id, e)
