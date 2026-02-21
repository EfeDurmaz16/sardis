"""Redis-based AP2 mandate caching with consume-once semantics for replay protection.

This module provides:
- Atomic consume-once mandate verification using Redis SETNX
- In-memory fallback for development/testing
- TTL-based expiration for automatic cleanup
- Cache statistics and monitoring
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(slots=True)
class MandateCacheConfig:
    """Configuration for mandate cache."""
    redis_url: str
    default_ttl: int = 3600  # 1 hour default
    max_mandate_size: int = 65536  # 64KB
    namespace_prefix: str = "sardis:mandate:"


class MandateCache:
    """Redis-backed mandate cache with consume-once semantics.

    Uses Redis SETNX for atomic consume-once operations to prevent replay attacks.
    """

    def __init__(self, config: MandateCacheConfig):
        """Initialize Redis-backed mandate cache.

        Args:
            config: Cache configuration with Redis URL and settings
        """
        self.config = config
        self._redis = None
        self._stats_hits = 0
        self._stats_misses = 0

    async def _get_redis(self):
        """Lazy initialization of Redis connection."""
        if self._redis is None:
            import redis.asyncio as redis
            self._redis = await redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    def _make_key(self, mandate_hash: str) -> str:
        """Generate namespaced Redis key for mandate hash."""
        return f"{self.config.namespace_prefix}{mandate_hash}"

    async def consume_mandate(
        self,
        mandate_hash: str,
        mandate_data: dict,
        ttl: int | None = None,
    ) -> bool:
        """Consume a mandate with atomic check-and-set.

        Uses Redis SETNX for atomicity - returns True only if mandate was NEW.

        Args:
            mandate_hash: Unique hash of the mandate
            mandate_data: Mandate payload to store
            ttl: Time-to-live in seconds (uses default_ttl if None)

        Returns:
            True if mandate was consumed (first time seen), False if already consumed
        """
        redis = await self._get_redis()
        key = self._make_key(mandate_hash)
        effective_ttl = ttl or self.config.default_ttl

        # Validate mandate size
        payload = json.dumps(mandate_data)
        if len(payload) > self.config.max_mandate_size:
            raise ValueError(f"mandate_too_large: {len(payload)} > {self.config.max_mandate_size}")

        # Prepare mandate record
        record = {
            "mandate_hash": mandate_hash,
            "consumed_at": int(time.time()),
            "data": mandate_data,
        }
        record_json = json.dumps(record)

        # Atomic set-if-not-exists with TTL
        # Returns True if key was set (new), False if key already existed
        was_set = await redis.set(key, record_json, nx=True, ex=effective_ttl)

        if was_set:
            self._stats_misses += 1  # Cache miss = new mandate
            return True
        else:
            self._stats_hits += 1  # Cache hit = already seen
            return False

    async def is_consumed(self, mandate_hash: str) -> bool:
        """Check if mandate has already been consumed.

        Args:
            mandate_hash: Unique hash of the mandate

        Returns:
            True if mandate exists in cache (already consumed), False otherwise
        """
        redis = await self._get_redis()
        key = self._make_key(mandate_hash)
        exists = await redis.exists(key)
        return bool(exists)

    async def get_mandate(self, mandate_hash: str) -> dict | None:
        """Retrieve mandate data if it exists.

        Args:
            mandate_hash: Unique hash of the mandate

        Returns:
            Mandate data dict if found, None otherwise
        """
        redis = await self._get_redis()
        key = self._make_key(mandate_hash)
        record_json = await redis.get(key)

        if record_json is None:
            return None

        try:
            record = json.loads(record_json)
            return record.get("data")
        except (json.JSONDecodeError, KeyError):
            return None

    async def revoke_mandate(self, mandate_hash: str) -> bool:
        """Explicitly revoke/invalidate a mandate.

        Args:
            mandate_hash: Unique hash of the mandate

        Returns:
            True if mandate was deleted, False if it didn't exist
        """
        redis = await self._get_redis()
        key = self._make_key(mandate_hash)
        deleted = await redis.delete(key)
        return bool(deleted)

    async def cleanup_expired(self) -> int:
        """Manual cleanup of expired entries.

        Note: Redis TTL handles most cleanup automatically.
        This method is primarily for monitoring/stats.

        Returns:
            Number of entries cleaned up (always 0 for Redis, handled by TTL)
        """
        # Redis handles TTL expiration automatically
        # This is a no-op but maintained for interface compatibility
        return 0

    async def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        redis = await self._get_redis()

        # Count keys matching our namespace
        pattern = f"{self.config.namespace_prefix}*"
        cursor = 0
        total_count = 0

        # Use SCAN to avoid blocking on large keyspaces
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=1000)
            total_count += len(keys)
            if cursor == 0:
                break

        return {
            "total_consumed": total_count,
            "cache_hits": self._stats_hits,
            "cache_misses": self._stats_misses,
            "hit_rate": self._stats_hits / max(1, self._stats_hits + self._stats_misses),
            "namespace": self.config.namespace_prefix,
        }

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.close()


class InMemoryMandateCache:
    """In-memory mandate cache fallback for development/testing.

    Provides same interface as MandateCache but uses local dict storage.
    Thread-safe with asyncio.Lock.
    """

    def __init__(self, config: MandateCacheConfig | None = None):
        """Initialize in-memory mandate cache.

        Args:
            config: Optional config (used for compatibility, TTL honored)
        """
        self.config = config or MandateCacheConfig(redis_url="memory://")
        self._cache: dict[str, tuple[dict, int]] = {}  # {hash: (data, expires_at)}
        self._lock = asyncio.Lock()
        self._stats_hits = 0
        self._stats_misses = 0

    async def consume_mandate(
        self,
        mandate_hash: str,
        mandate_data: dict,
        ttl: int | None = None,
    ) -> bool:
        """Consume a mandate with atomic check-and-set.

        Args:
            mandate_hash: Unique hash of the mandate
            mandate_data: Mandate payload to store
            ttl: Time-to-live in seconds

        Returns:
            True if mandate was consumed (first time seen), False if already consumed
        """
        async with self._lock:
            now = int(time.time())
            effective_ttl = ttl or self.config.default_ttl

            # Check if already exists and not expired
            if mandate_hash in self._cache:
                _, expires_at = self._cache[mandate_hash]
                if expires_at > now:
                    self._stats_hits += 1
                    return False

            # Store new mandate
            self._cache[mandate_hash] = (mandate_data, now + effective_ttl)
            self._stats_misses += 1
            return True

    async def is_consumed(self, mandate_hash: str) -> bool:
        """Check if mandate has already been consumed.

        Args:
            mandate_hash: Unique hash of the mandate

        Returns:
            True if mandate exists and not expired, False otherwise
        """
        async with self._lock:
            now = int(time.time())
            if mandate_hash in self._cache:
                _, expires_at = self._cache[mandate_hash]
                return expires_at > now
            return False

    async def get_mandate(self, mandate_hash: str) -> dict | None:
        """Retrieve mandate data if it exists.

        Args:
            mandate_hash: Unique hash of the mandate

        Returns:
            Mandate data dict if found and not expired, None otherwise
        """
        async with self._lock:
            now = int(time.time())
            if mandate_hash in self._cache:
                data, expires_at = self._cache[mandate_hash]
                if expires_at > now:
                    return data
            return None

    async def revoke_mandate(self, mandate_hash: str) -> bool:
        """Explicitly revoke/invalidate a mandate.

        Args:
            mandate_hash: Unique hash of the mandate

        Returns:
            True if mandate was deleted, False if it didn't exist
        """
        async with self._lock:
            if mandate_hash in self._cache:
                del self._cache[mandate_hash]
                return True
            return False

    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of expired entries removed
        """
        async with self._lock:
            now = int(time.time())
            expired = [
                mandate_hash
                for mandate_hash, (_, expires_at) in self._cache.items()
                if expires_at <= now
            ]
            for mandate_hash in expired:
                del self._cache[mandate_hash]
            return len(expired)

    async def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        async with self._lock:
            now = int(time.time())
            active = sum(
                1 for _, expires_at in self._cache.values()
                if expires_at > now
            )
            expired = len(self._cache) - active

            return {
                "total_consumed": len(self._cache),
                "active_entries": active,
                "expired_entries": expired,
                "cache_hits": self._stats_hits,
                "cache_misses": self._stats_misses,
                "hit_rate": self._stats_hits / max(1, self._stats_hits + self._stats_misses),
                "namespace": "memory",
            }

    async def close(self) -> None:
        """Close cache (no-op for in-memory)."""
        pass


__all__ = [
    "MandateCacheConfig",
    "MandateCache",
    "InMemoryMandateCache",
]
