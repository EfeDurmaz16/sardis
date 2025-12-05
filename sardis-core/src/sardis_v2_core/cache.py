"""Caching layer with Redis/Upstash support and in-memory fallback."""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheBackend(ABC):
    """Abstract cache backend interface."""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value in cache with optional TTL in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        pass

    @abstractmethod
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key."""
        pass


class InMemoryCache(CacheBackend):
    """In-memory cache for development."""

    def __init__(self):
        self._store: Dict[str, tuple[str, Optional[float]]] = {}  # key -> (value, expires_at)
        import time
        self._time = time

    async def get(self, key: str) -> Optional[str]:
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if expires_at and self._time.time() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        expires_at = self._time.time() + ttl if ttl else None
        self._store[key] = (value, expires_at)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None

    async def incr(self, key: str, amount: int = 1) -> int:
        current = await self.get(key)
        new_value = int(current or 0) + amount
        await self.set(key, str(new_value))
        return new_value

    async def expire(self, key: str, ttl: int) -> bool:
        if key not in self._store:
            return False
        value, _ = self._store[key]
        self._store[key] = (value, self._time.time() + ttl)
        return True


class RedisCache(CacheBackend):
    """Redis/Upstash cache backend."""

    def __init__(self, url: str):
        self._url = url
        self._client = None

    async def _get_client(self):
        """Lazy initialization of Redis client."""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(self._url, decode_responses=True)
            except ImportError:
                logger.warning("redis package not installed, falling back to in-memory cache")
                raise
        return self._client

    async def get(self, key: str) -> Optional[str]:
        try:
            client = await self._get_client()
            return await client.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        try:
            client = await self._get_client()
            if ttl:
                await client.setex(key, ttl, value)
            else:
                await client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            result = await client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        try:
            client = await self._get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    async def incr(self, key: str, amount: int = 1) -> int:
        try:
            client = await self._get_client()
            return await client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis incr error: {e}")
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        try:
            client = await self._get_client()
            return await client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


class CacheService:
    """High-level caching service with typed operations."""

    # Cache key prefixes
    PREFIX_BALANCE = "balance"
    PREFIX_WALLET = "wallet"
    PREFIX_AGENT = "agent"
    PREFIX_RATE_LIMIT = "rate"

    # Default TTLs (seconds)
    TTL_BALANCE = 60  # 1 minute
    TTL_WALLET = 300  # 5 minutes
    TTL_AGENT = 300  # 5 minutes
    TTL_RATE_LIMIT = 60  # 1 minute

    def __init__(self, backend: CacheBackend):
        self._backend = backend

    @classmethod
    def create(cls, redis_url: Optional[str] = None) -> "CacheService":
        """Create a cache service with appropriate backend."""
        if redis_url:
            try:
                backend = RedisCache(redis_url)
                logger.info("Using Redis cache backend")
            except Exception:
                backend = InMemoryCache()
                logger.info("Falling back to in-memory cache")
        else:
            backend = InMemoryCache()
            logger.info("Using in-memory cache (no Redis URL provided)")
        return cls(backend)

    def _key(self, prefix: str, *parts: str) -> str:
        """Build a cache key."""
        return f"sardis:{prefix}:{':'.join(parts)}"

    # Balance caching

    async def get_balance(self, wallet_id: str, token: str) -> Optional[Decimal]:
        """Get cached wallet balance."""
        key = self._key(self.PREFIX_BALANCE, wallet_id, token)
        value = await self._backend.get(key)
        if value is not None:
            return Decimal(value)
        return None

    async def set_balance(
        self, wallet_id: str, token: str, balance: Decimal, ttl: Optional[int] = None
    ) -> bool:
        """Cache wallet balance."""
        key = self._key(self.PREFIX_BALANCE, wallet_id, token)
        return await self._backend.set(key, str(balance), ttl or self.TTL_BALANCE)

    async def invalidate_balance(self, wallet_id: str, token: str) -> bool:
        """Invalidate cached balance."""
        key = self._key(self.PREFIX_BALANCE, wallet_id, token)
        return await self._backend.delete(key)

    async def invalidate_wallet_balances(self, wallet_id: str) -> int:
        """Invalidate all balances for a wallet."""
        # For simplicity, we invalidate known tokens
        tokens = ["USDC", "USDT", "PYUSD", "EURC"]
        count = 0
        for token in tokens:
            if await self.invalidate_balance(wallet_id, token):
                count += 1
        return count

    # Wallet caching

    async def get_wallet(self, wallet_id: str) -> Optional[dict]:
        """Get cached wallet data."""
        key = self._key(self.PREFIX_WALLET, wallet_id)
        value = await self._backend.get(key)
        if value:
            return json.loads(value)
        return None

    async def set_wallet(self, wallet_id: str, wallet_data: dict, ttl: Optional[int] = None) -> bool:
        """Cache wallet data."""
        key = self._key(self.PREFIX_WALLET, wallet_id)
        return await self._backend.set(key, json.dumps(wallet_data, default=str), ttl or self.TTL_WALLET)

    async def invalidate_wallet(self, wallet_id: str) -> bool:
        """Invalidate cached wallet."""
        key = self._key(self.PREFIX_WALLET, wallet_id)
        return await self._backend.delete(key)

    # Agent caching

    async def get_agent(self, agent_id: str) -> Optional[dict]:
        """Get cached agent data."""
        key = self._key(self.PREFIX_AGENT, agent_id)
        value = await self._backend.get(key)
        if value:
            return json.loads(value)
        return None

    async def set_agent(self, agent_id: str, agent_data: dict, ttl: Optional[int] = None) -> bool:
        """Cache agent data."""
        key = self._key(self.PREFIX_AGENT, agent_id)
        return await self._backend.set(key, json.dumps(agent_data, default=str), ttl or self.TTL_AGENT)

    async def invalidate_agent(self, agent_id: str) -> bool:
        """Invalidate cached agent."""
        key = self._key(self.PREFIX_AGENT, agent_id)
        return await self._backend.delete(key)

    # Rate limiting helpers

    async def check_rate_limit(
        self, identifier: str, limit: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check rate limit for an identifier.
        
        Returns:
            (allowed, current_count)
        """
        key = self._key(self.PREFIX_RATE_LIMIT, identifier)
        
        # Increment counter
        count = await self._backend.incr(key)
        
        # Set expiry on first request
        if count == 1:
            await self._backend.expire(key, window_seconds)
        
        return count <= limit, count

    async def get_rate_limit_remaining(self, identifier: str, limit: int) -> int:
        """Get remaining requests for rate limit."""
        key = self._key(self.PREFIX_RATE_LIMIT, identifier)
        value = await self._backend.get(key)
        current = int(value) if value else 0
        return max(0, limit - current)


def create_cache_service(redis_url: Optional[str] = None) -> CacheService:
    """Factory function to create cache service."""
    return CacheService.create(redis_url)
