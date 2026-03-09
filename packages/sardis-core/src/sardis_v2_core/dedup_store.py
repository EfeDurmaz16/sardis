"""
Durable deduplication store for mandate execution.

Provides cross-instance duplicate detection to prevent double-payments
when multiple orchestrator instances run behind a load balancer.

Two implementations:
  - RedisDedupStore: production-grade, Redis-backed, with configurable TTL.
  - InMemoryDedupStore: development fallback, process-local only.

Usage:
    store = RedisDedupStore(redis_client, ttl_seconds=86_400)
    existing = await store.check_and_set("mdt_123", result_dict)
    if existing is not None:
        return existing  # duplicate blocked

IMPORTANT: The in-memory store does NOT protect against duplicate mandates
across instances.  Always use RedisDedupStore in production.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)

KEY_PREFIX = "sardis:dedup:"


class DedupStorePort(Protocol):
    """Port for mandate deduplication stores."""

    async def check_and_set(self, mandate_id: str, result: Any) -> Any | None:
        """Return existing result if duplicate, else store and return None."""
        ...

    async def check(self, mandate_id: str) -> Any | None:
        """Return existing result if present, else None (read-only)."""
        ...


class RedisDedupStore:
    """
    Redis-backed mandate deduplication.  Fail-closed.

    Uses a simple GET/SET pattern with a TTL.  The key format is
    ``sardis:dedup:{mandate_id}`` and the value is the JSON-serialised
    payment result.

    Args:
        redis_client: An async Redis client (e.g. ``redis.asyncio.Redis``).
        ttl_seconds: How long to keep dedup entries (default 24 h).
    """

    def __init__(self, redis_client: Any, ttl_seconds: int = 86_400) -> None:
        self._redis = redis_client
        self._ttl = ttl_seconds

    async def check(self, mandate_id: str) -> Any | None:
        """Return existing result if present, else None."""
        key = f"{KEY_PREFIX}{mandate_id}"
        try:
            existing = await self._redis.get(key)
            if existing is not None:
                return json.loads(existing)
            return None
        except Exception:
            # Fail-closed: if Redis is unreachable we cannot confirm uniqueness.
            # Raising lets the caller decide (orchestrator will reject).
            logger.exception("Redis dedup check failed for mandate=%s", mandate_id)
            raise

    async def check_and_set(self, mandate_id: str, result: Any) -> Any | None:
        """Return existing result if duplicate, else store and return None."""
        key = f"{KEY_PREFIX}{mandate_id}"
        try:
            existing = await self._redis.get(key)
            if existing is not None:
                logger.warning("Duplicate mandate detected via Redis: %s", mandate_id)
                return json.loads(existing)
            await self._redis.set(key, json.dumps(result, default=str), ex=self._ttl)
            return None
        except Exception:
            # Fail-closed: if Redis is unreachable we cannot confirm uniqueness.
            logger.exception("Redis dedup check_and_set failed for mandate=%s", mandate_id)
            raise


class InMemoryDedupStore:
    """
    In-memory dedup for development.  NOT suitable for production.

    Process-local dict — duplicates sent to different instances will
    not be caught.
    """

    def __init__(self) -> None:
        import os

        if os.getenv("SARDIS_ENV", "development") == "production":
            logger.critical(
                "InMemoryDedupStore is NOT suitable for production! "
                "Duplicate mandates across instances WILL cause double-payments. "
                "Set dedup_store= to a RedisDedupStore."
            )
        self._store: dict[str, Any] = {}

    async def check(self, mandate_id: str) -> Any | None:
        """Return existing result if present, else None."""
        return self._store.get(mandate_id)

    async def check_and_set(self, mandate_id: str, result: Any) -> Any | None:
        """Return existing result if duplicate, else store and return None."""
        if mandate_id in self._store:
            return self._store[mandate_id]
        self._store[mandate_id] = result
        return None
