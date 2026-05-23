"""Webhook replay protection helpers (cache-backed).

Design:
- Verify provider signature first (fail closed).
- Use a short distributed lock to prevent concurrent double-processing.
- Mark the event as processed only AFTER the handler succeeds.
"""
from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from fastapi import HTTPException, Request, status

T = TypeVar("T")
logger = logging.getLogger(__name__)


def _hash_body(body: bytes | None) -> str:
    if not body:
        return ""
    return hashlib.sha256(body).hexdigest()


async def run_with_replay_protection(
    *,
    request: Request,
    provider: str,
    event_id: str,
    body: bytes | None = None,
    ttl_seconds: int = 24 * 60 * 60,
    lock_ttl_seconds: int = 30,
    response_on_duplicate: Any = None,
    require_replay_protection: bool = True,
    fn: Callable[[], Awaitable[T]],
) -> Any:
    """
    Execute `fn()` at most once per (provider, event_id).

    Fail-closed: if no ``cache_service`` is configured on ``app.state``, the
    handler is REJECTED with HTTP 503 ``webhook_replay_cache_unavailable`` --
    we refuse to process state-changing webhooks without replay protection,
    because that previously meant a captured webhook could be replayed
    indefinitely. Callers that intentionally accept this risk (e.g., a purely
    read-only debug route) MUST opt out by passing
    ``require_replay_protection=False`` explicitly.

    A missing or blank ``event_id`` is treated the same way: without a stable
    dedupe key we cannot enforce single-delivery, so we reject.

    For genuine duplicates (same provider/event_id) we return HTTP 200 so the
    provider stops retrying the same event.

    See ~/project-directions/sardis-sdk-security-model.md §4 (Webhook event_id).
    """
    cache = getattr(request.app.state, "cache_service", None)
    if cache is None:
        if require_replay_protection:
            logger.error(
                "Webhook handler invoked without cache_service; rejecting to "
                "preserve replay protection. provider=%s event_id=%s",
                provider, event_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="webhook_replay_cache_unavailable",
            )
        return await fn()

    provider = (provider or "unknown").strip().lower()
    event_id = (event_id or "").strip()
    if not event_id:
        if require_replay_protection:
            logger.warning(
                "Webhook handler invoked without event_id; rejecting because "
                "replay protection requires a stable dedupe key. provider=%s",
                provider,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="webhook_event_id_required",
            )
        return await fn()

    record_key = f"sardis:webhook:{provider}:{event_id}:processed"
    lock_resource = f"webhook:{provider}:{event_id}"
    body_hash = _hash_body(body)

    existing_raw = await cache.get(record_key)
    if existing_raw:
        if body_hash and existing_raw != body_hash:
            # Do not process: event id reused with different body (suspicious).
            # Return 200 to avoid endless provider retries, but surface via logs elsewhere.
            logger.warning("Webhook event id reused with different body provider=%s event_id=%s", provider, event_id)
            raise HTTPException(status_code=status.HTTP_200_OK, detail="webhook_duplicate_body_mismatch")
        if response_on_duplicate is not None:
            return response_on_duplicate  # type: ignore[return-value]
        raise HTTPException(status_code=status.HTTP_200_OK, detail="webhook_duplicate")

    owner = await cache.acquire_lock(lock_resource, ttl_seconds=lock_ttl_seconds)
    if not owner:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="webhook_in_progress")

    try:
        # Re-check under lock to prevent race.
        existing_raw = await cache.get(record_key)
        if existing_raw:
            if body_hash and existing_raw != body_hash:
                logger.warning("Webhook event id reused with different body provider=%s event_id=%s", provider, event_id)
                raise HTTPException(status_code=status.HTTP_200_OK, detail="webhook_duplicate_body_mismatch")
            if response_on_duplicate is not None:
                return response_on_duplicate  # type: ignore[return-value]
            raise HTTPException(status_code=status.HTTP_200_OK, detail="webhook_duplicate")

        result = await fn()
        await cache.set(record_key, body_hash or str(int(time.time())), ttl=ttl_seconds)
        return result  # type: ignore[return-value]
    finally:
        await cache.release_lock(lock_resource, owner)
