"""Redis-backed replay cache for mandate deduplication.

Fail-closed: if Redis is unreachable the mandate is treated as replayed
(returns False from check_and_store) to prevent double-execution.
"""
from __future__ import annotations

import logging
import time

from .storage import ReplayCache

logger = logging.getLogger(__name__)


class RedisReplayCache(ReplayCache):
    """Redis-backed replay cache for mandate deduplication. Fail-closed.

    Implements the same ``check_and_store`` interface as the in-memory
    :class:`ReplayCache` so that :class:`MandateVerifier` can accept either
    implementation transparently.

    Args:
        redis_client: A synchronous ``redis.Redis`` instance (or compatible).
        ttl_seconds: Default TTL applied to each key (default 24 hours).
    """

    def __init__(self, redis_client: object, ttl_seconds: int = 86_400):
        # We don't need the parent's in-memory dict, but calling super keeps
        # the type hierarchy clean (isinstance checks, stats skeleton, etc.).
        super().__init__(default_ttl_seconds=ttl_seconds)
        self._redis = redis_client
        self._ttl = ttl_seconds

    # ---- key helpers ----

    @staticmethod
    def _key(mandate_id: str) -> str:
        return f"sardis:replay:{mandate_id}"

    # ---- public interface (matches ReplayCache) ----

    def check_and_store(self, mandate_id: str, expires_at: int) -> bool:
        """Check whether *mandate_id* has already been seen.

        Returns ``True`` if the mandate is **new** (safe to execute) and
        ``False`` if it is a **duplicate** (must reject).

        On Redis errors the method returns ``False`` (fail-closed) so that
        a mandate can never slip through due to an infrastructure outage.
        """
        key = self._key(mandate_id)
        now = int(time.time())

        # Compute a sensible TTL: honour the mandate's own expiry when it is
        # in the future; otherwise fall back to the configured default.
        if expires_at > now:
            ttl = expires_at - now
        else:
            ttl = self._ttl

        try:
            # SET NX — atomic "set if not exists".  Returns True when the key
            # was created (mandate is new), None/False when it already existed.
            was_set = self._redis.set(key, "1", nx=True, ex=ttl)
            if was_set:
                return True  # new mandate
            return False  # duplicate
        except Exception:
            logger.exception(
                "Redis error during replay check for %s — fail-closed (treating as duplicate)",
                mandate_id,
            )
            return False  # fail-closed

    def cleanup(self, now: int | None = None) -> int:
        """No-op — Redis TTL handles expiration automatically."""
        return 0

    def stats(self) -> dict:
        """Minimal stats; scanning Redis keys is expensive, so we keep it
        lightweight and only report what the base class tracks."""
        return {
            "backend": "redis",
            "ttl_seconds": self._ttl,
        }

    def clear(self) -> None:
        """Delete all replay-cache keys (use with caution)."""
        try:
            cursor: int = 0
            while True:
                cursor, keys = self._redis.scan(cursor, match="sardis:replay:*", count=500)
                if keys:
                    self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            logger.exception("Redis error during replay cache clear")
