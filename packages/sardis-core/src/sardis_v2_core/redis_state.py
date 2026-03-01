"""
Redis-backed state store with in-memory fallback.

Provides a unified interface for shared state that works across
multiple process instances via Redis, with graceful fallback to
in-memory storage when Redis is unavailable (dev mode).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Lazy Redis import to avoid hard dependency
_redis_client = None
_fallback_mode = False


async def _get_redis():
    """Get or create async Redis client."""
    global _redis_client, _fallback_mode
    if _fallback_mode:
        return None
    if _redis_client is not None:
        return _redis_client

    redis_url = os.getenv("SARDIS_REDIS_URL") or os.getenv("UPSTASH_REDIS_URL")
    if not redis_url:
        logger.info("No SARDIS_REDIS_URL set, using in-memory fallback")
        _fallback_mode = True
        return None

    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(redis_url, decode_responses=True)
        await _redis_client.ping()
        logger.info("Connected to Redis for state storage")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}), using in-memory fallback")
        _fallback_mode = True
        return None


class RedisStateStore:
    """
    Redis-backed state store with in-memory fallback.

    Usage:
        store = RedisStateStore(namespace="drift_detector")
        await store.set("agent:123", {"score": 0.5}, ttl=3600)
        data = await store.get("agent:123")
    """

    def __init__(self, namespace: str):
        self._namespace = namespace
        self._memory: dict[str, Any] = {}
        self._memory_lists: dict[str, list] = {}

    def _key(self, key: str) -> str:
        return f"sardis:{self._namespace}:{key}"

    async def get(self, key: str) -> Optional[dict]:
        """Get a value by key. Returns None if not found."""
        r = await _get_redis()
        if r is not None:
            try:
                raw = await r.get(self._key(key))
                if raw is None:
                    return None
                return json.loads(raw)
            except Exception as e:
                logger.warning(f"Redis get failed for {key}: {e}")
        return self._memory.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value with optional TTL in seconds."""
        r = await _get_redis()
        if r is not None:
            try:
                raw = json.dumps(value, default=str)
                if ttl:
                    await r.setex(self._key(key), ttl, raw)
                else:
                    await r.set(self._key(key), raw)
                return
            except Exception as e:
                logger.warning(f"Redis set failed for {key}: {e}")
        self._memory[key] = value

    async def delete(self, key: str) -> None:
        """Delete a key."""
        r = await _get_redis()
        if r is not None:
            try:
                await r.delete(self._key(key))
                return
            except Exception as e:
                logger.warning(f"Redis delete failed for {key}: {e}")
        self._memory.pop(key, None)

    async def get_list(self, key: str) -> list:
        """Get a list by key."""
        r = await _get_redis()
        if r is not None:
            try:
                raw_items = await r.lrange(self._key(key), 0, -1)
                return [json.loads(item) for item in raw_items]
            except Exception as e:
                logger.warning(f"Redis get_list failed for {key}: {e}")
        return self._memory_lists.get(key, [])

    async def append_list(self, key: str, value: Any, max_len: Optional[int] = None, ttl: Optional[int] = None) -> None:
        """Append to a list with optional max length and TTL."""
        r = await _get_redis()
        if r is not None:
            try:
                rkey = self._key(key)
                raw = json.dumps(value, default=str)
                await r.rpush(rkey, raw)
                if max_len:
                    await r.ltrim(rkey, -max_len, -1)
                if ttl:
                    await r.expire(rkey, ttl)
                return
            except Exception as e:
                logger.warning(f"Redis append_list failed for {key}: {e}")
        if key not in self._memory_lists:
            self._memory_lists[key] = []
        self._memory_lists[key].append(value)
        if max_len and len(self._memory_lists[key]) > max_len:
            self._memory_lists[key] = self._memory_lists[key][-max_len:]

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        r = await _get_redis()
        if r is not None:
            try:
                return bool(await r.exists(self._key(key)))
            except Exception as e:
                logger.warning(f"Redis exists failed for {key}: {e}")
        return key in self._memory or key in self._memory_lists

    async def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching pattern."""
        r = await _get_redis()
        if r is not None:
            try:
                full_pattern = self._key(pattern)
                raw_keys = await r.keys(full_pattern)
                prefix = self._key("")
                return [k.removeprefix(prefix) for k in raw_keys]
            except Exception as e:
                logger.warning(f"Redis keys failed for {pattern}: {e}")
        return list(self._memory.keys()) + list(self._memory_lists.keys())
