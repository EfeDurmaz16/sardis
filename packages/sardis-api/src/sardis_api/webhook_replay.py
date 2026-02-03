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
from typing import Any, Awaitable, Callable, Optional, TypeVar

from fastapi import HTTPException, Request, status

T = TypeVar("T")
logger = logging.getLogger(__name__)


def _hash_body(body: Optional[bytes]) -> str:
    if not body:
        return ""
    return hashlib.sha256(body).hexdigest()


async def run_with_replay_protection(
    *,
    request: Request,
    provider: str,
    event_id: str,
    body: Optional[bytes] = None,
    ttl_seconds: int = 24 * 60 * 60,
    lock_ttl_seconds: int = 30,
    response_on_duplicate: Any = None,
    fn: Callable[[], Awaitable[T]],
) -> Any:
    """
    Execute `fn()` at most once per (provider, event_id).

    If cache isn't configured, this becomes a no-op wrapper.
    For duplicates we return 200 so providers stop retrying the same event.
    """
    cache = getattr(request.app.state, "cache_service", None)
    if cache is None:
        return await fn()

    provider = (provider or "unknown").strip().lower()
    event_id = (event_id or "").strip()
    if not event_id:
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
