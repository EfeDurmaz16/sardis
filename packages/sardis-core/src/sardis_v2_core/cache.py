"""Caching layer with Redis/Upstash support and in-memory fallback."""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, Optional, TypeVar, Generic, AsyncIterator

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheMetrics:
    """Cache performance metrics."""

    # Hit/miss counters
    hits: int = 0
    misses: int = 0

    # Operation counters
    sets: int = 0
    deletes: int = 0

    # Latency tracking (milliseconds)
    total_latency_ms: float = 0.0
    operation_count: int = 0

    # Error tracking
    errors: int = 0

    def record_hit(self, latency_ms: float) -> None:
        """Record a cache hit."""
        self.hits += 1
        self._record_latency(latency_ms)

    def record_miss(self, latency_ms: float) -> None:
        """Record a cache miss."""
        self.misses += 1
        self._record_latency(latency_ms)

    def record_set(self, latency_ms: float) -> None:
        """Record a cache set operation."""
        self.sets += 1
        self._record_latency(latency_ms)

    def record_delete(self, latency_ms: float) -> None:
        """Record a cache delete operation."""
        self.deletes += 1
        self._record_latency(latency_ms)

    def record_error(self) -> None:
        """Record a cache error."""
        self.errors += 1

    def _record_latency(self, latency_ms: float) -> None:
        """Record operation latency."""
        self.total_latency_ms += latency_ms
        self.operation_count += 1

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate (0.0 to 1.0)."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate (0.0 to 1.0)."""
        total = self.hits + self.misses
        return self.misses / total if total > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average operation latency in milliseconds."""
        return self.total_latency_ms / self.operation_count if self.operation_count > 0 else 0.0

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate, 4),
            "miss_rate": round(self.miss_rate, 4),
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "total_operations": self.operation_count,
        }

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.total_latency_ms = 0.0
        self.operation_count = 0
        self.errors = 0


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

    @abstractmethod
    async def acquire_lock(self, key: str, ttl: int, owner: str) -> bool:
        """
        Acquire a distributed lock using SETNX pattern.

        Args:
            key: Lock key name
            ttl: Lock TTL in seconds (auto-release)
            owner: Unique identifier for lock owner

        Returns:
            True if lock acquired, False if already held
        """
        pass

    @abstractmethod
    async def release_lock(self, key: str, owner: str) -> bool:
        """
        Release a distributed lock (only if owner matches).

        Args:
            key: Lock key name
            owner: Unique identifier for lock owner

        Returns:
            True if lock released, False if not held or wrong owner
        """
        pass

    @abstractmethod
    async def extend_lock(self, key: str, ttl: int, owner: str) -> bool:
        """
        Extend a lock's TTL (only if owner matches).

        Args:
            key: Lock key name
            ttl: New TTL in seconds
            owner: Unique identifier for lock owner

        Returns:
            True if extended, False if not held or wrong owner
        """
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

    async def acquire_lock(self, key: str, ttl: int, owner: str) -> bool:
        """Acquire lock using in-memory SETNX simulation."""
        # Check if lock already exists and is not expired
        existing = await self.get(key)
        if existing is not None:
            return False  # Lock already held

        # Set lock with owner as value
        await self.set(key, owner, ttl)
        return True

    async def release_lock(self, key: str, owner: str) -> bool:
        """Release lock only if owner matches."""
        current_owner = await self.get(key)
        if current_owner != owner:
            return False  # Not the owner or lock doesn't exist

        return await self.delete(key)

    async def extend_lock(self, key: str, ttl: int, owner: str) -> bool:
        """Extend lock TTL only if owner matches."""
        current_owner = await self.get(key)
        if current_owner != owner:
            return False  # Not the owner or lock doesn't exist

        return await self.expire(key, ttl)


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

    async def acquire_lock(self, key: str, ttl: int, owner: str) -> bool:
        """Acquire distributed lock using Redis SETNX."""
        try:
            client = await self._get_client()
            # SET key value NX EX ttl - atomic SETNX with expiry
            result = await client.set(key, owner, nx=True, ex=ttl)
            return result is not None and result
        except Exception as e:
            logger.error(f"Redis acquire_lock error: {e}")
            return False

    async def release_lock(self, key: str, owner: str) -> bool:
        """Release lock using Lua script for atomicity (check owner then delete)."""
        try:
            client = await self._get_client()
            # Lua script ensures atomicity: only delete if owner matches
            # Note: Redis eval() executes Lua scripts server-side for atomic operations
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = await client.eval(lua_script, 1, key, owner)
            return result == 1
        except Exception as e:
            logger.error(f"Redis release_lock error: {e}")
            return False

    async def extend_lock(self, key: str, ttl: int, owner: str) -> bool:
        """Extend lock TTL using Lua script (check owner then extend)."""
        try:
            client = await self._get_client()
            # Lua script ensures atomicity: only extend if owner matches
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            result = await client.eval(lua_script, 1, key, owner, ttl)
            return result == 1
        except Exception as e:
            logger.error(f"Redis extend_lock error: {e}")
            return False


class CacheService:
    """High-level caching service with typed operations."""

    # Cache key prefixes
    PREFIX_BALANCE = "balance"
    PREFIX_BALANCE_VERSION = "balance_version"
    PREFIX_WALLET = "wallet"
    PREFIX_AGENT = "agent"
    PREFIX_RATE_LIMIT = "rate"
    PREFIX_AUTH = "auth"

    # Default TTLs (seconds)
    TTL_BALANCE = 60  # 1 minute
    TTL_WALLET = 300  # 5 minutes
    TTL_AGENT = 300  # 5 minutes
    TTL_RATE_LIMIT = 60  # 1 minute

    def __init__(self, backend: CacheBackend, enable_metrics: bool = True):
        self._backend = backend
        self._metrics = CacheMetrics() if enable_metrics else None

    async def get(self, key: str) -> Optional[str]:
        """Get a raw value from cache (for health checks)."""
        start = time.time()
        try:
            result = await self._backend.get(key)
            latency_ms = (time.time() - start) * 1000

            if self._metrics:
                if result is not None:
                    self._metrics.record_hit(latency_ms)
                else:
                    self._metrics.record_miss(latency_ms)

            return result
        except Exception as e:
            if self._metrics:
                self._metrics.record_error()
            raise

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a raw value in cache with optional TTL (seconds)."""
        start = time.time()
        try:
            result = await self._backend.set(key, value, ttl=ttl)
            latency_ms = (time.time() - start) * 1000
            if self._metrics:
                self._metrics.record_set(latency_ms)
            return result
        except Exception:
            if self._metrics:
                self._metrics.record_error()
            raise

    async def delete(self, key: str) -> bool:
        """Delete a raw key from cache."""
        start = time.time()
        try:
            result = await self._backend.delete(key)
            latency_ms = (time.time() - start) * 1000
            if self._metrics:
                self._metrics.record_delete(latency_ms)
            return result
        except Exception:
            if self._metrics:
                self._metrics.record_error()
            raise

    async def exists(self, key: str) -> bool:
        """Check if a raw key exists in cache."""
        start = time.time()
        try:
            result = await self._backend.exists(key)
            latency_ms = (time.time() - start) * 1000
            if self._metrics:
                if result:
                    self._metrics.record_hit(latency_ms)
                else:
                    self._metrics.record_miss(latency_ms)
            return result
        except Exception:
            if self._metrics:
                self._metrics.record_error()
            raise

    @classmethod
    def create(cls, redis_url: Optional[str] = None, enable_metrics: bool = True) -> "CacheService":
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
        return cls(backend, enable_metrics=enable_metrics)

    def _key(self, prefix: str, *parts: str) -> str:
        """Build a cache key."""
        return f"sardis:{prefix}:{':'.join(parts)}"

    async def _get_balance_version(self, wallet_id: str) -> str:
        """Return the cache generation for wallet balances."""
        version_key = self._key(self.PREFIX_BALANCE_VERSION, wallet_id)
        version = await self._backend.get(version_key)
        return version or "0"

    def _balance_key(self, wallet_id: str, token: str, version: str) -> str:
        """Versioned wallet balance cache key."""
        return self._key(self.PREFIX_BALANCE, wallet_id, version, token)

    def _legacy_balance_key(self, wallet_id: str, token: str) -> str:
        """Backward-compatible pre-versioning key."""
        return self._key(self.PREFIX_BALANCE, wallet_id, token)

    # Auth / session security

    async def revoke_jwt_jti(self, jti: str, ttl_seconds: int) -> bool:
        """
        Revoke a JWT by its JTI for the remaining token lifetime.

        This enables logout + server-side revocation for otherwise stateless JWTs.
        """
        ttl_seconds = max(1, int(ttl_seconds))
        key = self._key(self.PREFIX_AUTH, "revoked_jti", jti)
        return await self._backend.set(key, "1", ttl=ttl_seconds)

    async def is_jwt_jti_revoked(self, jti: str) -> bool:
        """Check if a JWT JTI has been revoked."""
        key = self._key(self.PREFIX_AUTH, "revoked_jti", jti)
        return await self._backend.exists(key)

    # Balance caching

    async def get_balance(self, wallet_id: str, token: str) -> Optional[Decimal]:
        """Get cached wallet balance."""
        version = await self._get_balance_version(wallet_id)
        key = self._balance_key(wallet_id, token, version)
        start = time.time()
        try:
            value = await self._backend.get(key)
            latency_ms = (time.time() - start) * 1000

            if self._metrics:
                if value is not None:
                    self._metrics.record_hit(latency_ms)
                else:
                    self._metrics.record_miss(latency_ms)

            if value is not None:
                return Decimal(value)
            # Compatibility fallback for entries written before versioning.
            legacy = await self._backend.get(self._legacy_balance_key(wallet_id, token))
            if legacy is not None:
                return Decimal(legacy)
            return None
        except Exception as e:
            if self._metrics:
                self._metrics.record_error()
            raise

    async def set_balance(
        self, wallet_id: str, token: str, balance: Decimal, ttl: Optional[int] = None
    ) -> bool:
        """Cache wallet balance."""
        version = await self._get_balance_version(wallet_id)
        key = self._balance_key(wallet_id, token, version)
        start = time.time()
        try:
            result = await self._backend.set(key, str(balance), ttl or self.TTL_BALANCE)
            latency_ms = (time.time() - start) * 1000

            if self._metrics:
                self._metrics.record_set(latency_ms)

            return result
        except Exception as e:
            if self._metrics:
                self._metrics.record_error()
            raise

    async def invalidate_balance(self, wallet_id: str, token: str) -> bool:
        """Invalidate cached balance."""
        version = await self._get_balance_version(wallet_id)
        key = self._balance_key(wallet_id, token, version)
        legacy_key = self._legacy_balance_key(wallet_id, token)
        start = time.time()
        try:
            result = await self._backend.delete(key)
            await self._backend.delete(legacy_key)
            latency_ms = (time.time() - start) * 1000

            if self._metrics:
                self._metrics.record_delete(latency_ms)

            return result
        except Exception as e:
            if self._metrics:
                self._metrics.record_error()
            raise

    async def invalidate_wallet_balances(self, wallet_id: str) -> int:
        """Invalidate all balances for a wallet."""
        # Bump generation first so stale writers can no longer affect reads.
        version_key = self._key(self.PREFIX_BALANCE_VERSION, wallet_id)
        new_version = await self._backend.incr(version_key)

        # Best-effort cleanup of previous generation + legacy keys for known tokens.
        old_version = str(max(0, int(new_version) - 1))
        tokens = ["USDC", "USDT", "PYUSD", "EURC"]
        count = 0
        for token in tokens:
            if await self._backend.delete(self._balance_key(wallet_id, token, old_version)):
                count += 1
            if await self._backend.delete(self._legacy_balance_key(wallet_id, token)):
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

    # Distributed locks

    async def acquire_lock(
        self,
        resource: str,
        ttl_seconds: int = 10,
        owner: Optional[str] = None,
    ) -> Optional[str]:
        """
        Acquire a distributed lock on a resource.

        Args:
            resource: Resource identifier to lock
            ttl_seconds: Lock TTL (auto-release after this time)
            owner: Optional owner ID (generated if not provided)

        Returns:
            Lock owner ID if acquired, None if lock already held
        """
        lock_owner = owner or str(uuid.uuid4())
        key = self._key("lock", resource)

        acquired = await self._backend.acquire_lock(key, ttl_seconds, lock_owner)
        return lock_owner if acquired else None

    async def release_lock(self, resource: str, owner: str) -> bool:
        """
        Release a distributed lock.

        Args:
            resource: Resource identifier
            owner: Lock owner ID (from acquire_lock)

        Returns:
            True if released, False if not held or wrong owner
        """
        key = self._key("lock", resource)
        return await self._backend.release_lock(key, owner)

    async def extend_lock(self, resource: str, owner: str, ttl_seconds: int) -> bool:
        """
        Extend a lock's TTL.

        Args:
            resource: Resource identifier
            owner: Lock owner ID
            ttl_seconds: New TTL in seconds

        Returns:
            True if extended, False if not held or wrong owner
        """
        key = self._key("lock", resource)
        return await self._backend.extend_lock(key, ttl_seconds, owner)

    @asynccontextmanager
    async def lock(
        self,
        resource: str,
        ttl_seconds: int = 10,
        retry_delay: float = 0.1,
        max_retries: int = 10,
    ) -> AsyncIterator[str]:
        """
        Context manager for distributed locks with retry logic.

        Usage:
            async with cache.lock("wallet:transfer:wallet_123", ttl_seconds=30) as lock_id:
                # Critical section - only one holder at a time
                await perform_transfer()

        Args:
            resource: Resource to lock
            ttl_seconds: Lock TTL
            retry_delay: Delay between retry attempts (seconds)
            max_retries: Maximum retry attempts

        Raises:
            TimeoutError: If lock cannot be acquired after max_retries
        """
        owner = None
        attempts = 0

        # Try to acquire lock with retries
        while attempts < max_retries:
            owner = await self.acquire_lock(resource, ttl_seconds)
            if owner:
                break

            attempts += 1
            if attempts < max_retries:
                await asyncio.sleep(retry_delay)

        if not owner:
            raise TimeoutError(
                f"Failed to acquire lock on '{resource}' after {max_retries} attempts"
            )

        try:
            yield owner
        finally:
            # Always release lock on exit
            released = await self.release_lock(resource, owner)
            if not released:
                logger.warning(
                    f"Failed to release lock on '{resource}' (owner: {owner[:8]}...)"
                )

    def get_metrics(self) -> Optional[dict]:
        """Get cache performance metrics."""
        if self._metrics:
            return self._metrics.to_dict()
        return None

    def reset_metrics(self) -> None:
        """Reset cache metrics."""
        if self._metrics:
            self._metrics.reset()

    async def close(self):
        """Close cache backend connections."""
        if hasattr(self._backend, "close"):
            await self._backend.close()


def create_cache_service(redis_url: Optional[str] = None) -> CacheService:
    """Factory function to create cache service."""
    return CacheService.create(redis_url)
