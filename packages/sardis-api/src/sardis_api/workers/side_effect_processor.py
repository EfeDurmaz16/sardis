"""Background worker for processing execution side effects.

Polls the execution_side_effects table and processes pending items
with retry semantics and exponential backoff.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sardis_v2_core.execution_queue import (
    fetch_pending_effects,
    mark_completed,
    mark_failed,
)

logger = logging.getLogger("sardis.worker.side_effects")


async def _process_ledger_append(payload: dict[str, Any]) -> None:
    """Process a deferred ledger append."""
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ledger_entries (
                    entry_id, wallet_id, entry_type, amount, currency,
                    chain, chain_tx_hash, status, metadata, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, now())
                ON CONFLICT (entry_id) DO NOTHING
                """,
                payload.get("entry_id"),
                payload.get("wallet_id"),
                payload.get("entry_type", "payment"),
                payload.get("amount"),
                payload.get("currency"),
                payload.get("chain"),
                payload.get("tx_hash"),
                payload.get("status", "completed"),
                json.dumps(payload.get("metadata", {})),
            )
    except Exception as e:
        raise RuntimeError(f"Ledger append failed: {e}") from e


async def _process_webhook(payload: dict[str, Any]) -> None:
    """Process a deferred webhook delivery."""
    try:
        import aiohttp

        url = payload.get("url")
        if not url:
            return

        body = payload.get("body", {})
        headers = payload.get("headers", {})
        headers.setdefault("Content-Type", "application/json")

        async with aiohttp.ClientSession() as session, session.post(
            url,
            json=body,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"Webhook returned {resp.status}")
    except ImportError:
        raise RuntimeError("aiohttp not installed")


async def _process_spend_record(payload: dict[str, Any]) -> None:
    """Process a deferred spend record update."""
    # Spend recording is best-effort and already handled by the cap engine
    logger.info("Spend record processed for tx=%s", payload.get("tx_id"))


# Effect type -> handler mapping
_HANDLERS = {
    "ledger_append": _process_ledger_append,
    "webhook": _process_webhook,
    "spend_record": _process_spend_record,
}


async def process_batch(batch_size: int = 20) -> int:
    """Fetch and process a batch of pending side effects.

    Returns the number of effects processed.
    """
    effects = await fetch_pending_effects(batch_size)
    if not effects:
        return 0

    processed = 0
    for effect in effects:
        effect_id = effect["id"]
        effect_type = effect["effect_type"]
        payload = effect["payload"] if isinstance(effect["payload"], dict) else json.loads(effect["payload"])

        handler = _HANDLERS.get(effect_type)
        if handler is None:
            logger.warning("Unknown side effect type: %s (id=%d)", effect_type, effect_id)
            await mark_failed(effect_id, f"Unknown effect type: {effect_type}")
            continue

        try:
            await handler(payload)
            await mark_completed(effect_id)
            processed += 1
        except Exception as e:
            logger.warning("Side effect %d (%s) failed: %s", effect_id, effect_type, e)
            await mark_failed(effect_id, str(e))

    return processed


async def run_worker(poll_interval: float = 2.0, batch_size: int = 20) -> None:
    """Run the side effect processor as a continuous background loop.

    Args:
        poll_interval: Seconds between polls when no work found.
        batch_size: Max effects to process per batch.
    """
    logger.info("Side effect worker started (interval=%.1fs, batch=%d)", poll_interval, batch_size)
    while True:
        try:
            processed = await process_batch(batch_size)
            if processed:
                logger.info("Processed %d side effects", processed)
                # If we had work, immediately check for more
                continue
        except Exception as e:
            logger.exception("Side effect worker error: %s", e)

        await asyncio.sleep(poll_interval)
