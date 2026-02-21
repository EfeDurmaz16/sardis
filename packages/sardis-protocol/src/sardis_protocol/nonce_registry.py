"""Time-bound nonce generation and validation for AP2 transactions.

Provides cryptographically secure nonces with built-in expiration and one-time use
semantics to prevent replay attacks.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class NonceConfig:
    """Configuration for nonce registry."""
    default_expiry_seconds: int = 300  # 5 minutes
    hash_algorithm: str = "sha256"
    random_bytes: int = 16


class NonceRegistry:
    """Time-bound nonce generation and validation for AP2 transactions.

    Generates unique nonces with format: {timestamp}:{agent_id_hash}:{random_bytes}
    Validates nonce freshness and prevents reuse.
    """

    def __init__(self, config: NonceConfig | None = None):
        """Initialize nonce registry.

        Args:
            config: Optional nonce configuration
        """
        self.config = config or NonceConfig()
        self._consumed_nonces: set[str] = set()
        self._cleanup_threshold = 10000  # Cleanup after 10k nonces

    def generate_nonce(self, agent_id: str, mandate_hash: str) -> str:
        """Generate unique time-bound nonce for AP2 transaction.

        Args:
            agent_id: Agent identifier
            mandate_hash: Associated mandate hash for additional entropy

        Returns:
            Nonce string in format: {timestamp}:{agent_id_hash}:{random_bytes}
        """
        timestamp = int(time.time())

        # Hash agent_id for privacy
        hasher = hashlib.new(self.config.hash_algorithm)
        hasher.update(f"{agent_id}:{mandate_hash}".encode())
        agent_hash = hasher.hexdigest()[:16]

        # Generate cryptographically secure random bytes
        random_hex = secrets.token_hex(self.config.random_bytes)

        return f"{timestamp}:{agent_hash}:{random_hex}"

    def validate_nonce(self, nonce: str, max_age_seconds: int | None = None) -> bool:
        """Verify nonce is valid and not expired.

        Args:
            nonce: Nonce string to validate
            max_age_seconds: Maximum age in seconds (uses default_expiry if None)

        Returns:
            True if nonce is valid and not expired, False otherwise
        """
        try:
            parts = nonce.split(":")
            if len(parts) != 3:
                return False

            timestamp_str, agent_hash, random_hex = parts

            # Validate timestamp is numeric
            try:
                timestamp = int(timestamp_str)
            except ValueError:
                return False

            # Validate agent_hash format (16 hex chars)
            if len(agent_hash) != 16 or not all(c in "0123456789abcdef" for c in agent_hash):
                return False

            # Validate random_hex format
            expected_len = self.config.random_bytes * 2  # hex encoding doubles length
            if len(random_hex) != expected_len or not all(c in "0123456789abcdef" for c in random_hex):
                return False

            # Check expiration
            max_age = max_age_seconds or self.config.default_expiry_seconds
            now = int(time.time())
            age = now - timestamp

            if age < 0:
                # Nonce from the future - clock skew or manipulation
                return False

            if age > max_age:
                # Nonce expired
                return False

            return True

        except (ValueError, IndexError):
            return False

    def consume_nonce(self, nonce: str, max_age_seconds: int | None = None) -> bool:
        """Consume a nonce with one-time use semantics.

        Args:
            nonce: Nonce string to consume
            max_age_seconds: Maximum age in seconds (uses default_expiry if None)

        Returns:
            True if nonce was valid and consumed, False if invalid or already consumed
        """
        # First validate the nonce
        if not self.validate_nonce(nonce, max_age_seconds):
            return False

        # Check if already consumed
        if nonce in self._consumed_nonces:
            return False

        # Mark as consumed
        self._consumed_nonces.add(nonce)

        # Periodic cleanup to prevent unbounded growth
        if len(self._consumed_nonces) >= self._cleanup_threshold:
            self._cleanup_expired_nonces(max_age_seconds)

        return True

    def _cleanup_expired_nonces(self, max_age_seconds: int | None = None) -> int:
        """Remove expired nonces from consumed set.

        Args:
            max_age_seconds: Maximum age for valid nonces

        Returns:
            Number of nonces cleaned up
        """
        max_age = max_age_seconds or self.config.default_expiry_seconds
        now = int(time.time())
        cutoff = now - max_age

        # Filter out expired nonces
        expired = {
            nonce
            for nonce in self._consumed_nonces
            if self._extract_timestamp(nonce) is not None
            and self._extract_timestamp(nonce) < cutoff  # type: ignore
        }

        self._consumed_nonces -= expired
        return len(expired)

    def _extract_timestamp(self, nonce: str) -> int | None:
        """Extract timestamp from nonce string.

        Args:
            nonce: Nonce string

        Returns:
            Timestamp as int, or None if invalid format
        """
        try:
            parts = nonce.split(":")
            if len(parts) >= 1:
                return int(parts[0])
        except (ValueError, IndexError):
            pass
        return None

    def get_stats(self) -> dict:
        """Get nonce registry statistics.

        Returns:
            Dictionary with registry metrics
        """
        now = int(time.time())
        max_age = self.config.default_expiry_seconds

        active = sum(
            1
            for nonce in self._consumed_nonces
            if self._extract_timestamp(nonce) is not None
            and (now - self._extract_timestamp(nonce)) <= max_age  # type: ignore
        )

        return {
            "total_consumed": len(self._consumed_nonces),
            "active_nonces": active,
            "expired_nonces": len(self._consumed_nonces) - active,
            "cleanup_threshold": self._cleanup_threshold,
            "default_expiry": self.config.default_expiry_seconds,
        }

    def clear(self) -> None:
        """Clear all consumed nonces."""
        self._consumed_nonces.clear()


class RedisNonceRegistry(NonceRegistry):
    """Redis-backed nonce registry for distributed deployments.

    Uses Redis sets with TTL for automatic cleanup and distributed coordination.
    """

    def __init__(self, redis_url: str, config: NonceConfig | None = None):
        """Initialize Redis-backed nonce registry.

        Args:
            redis_url: Redis connection URL
            config: Optional nonce configuration
        """
        super().__init__(config)
        self.redis_url = redis_url
        self._redis = None
        self._namespace = "sardis:nonce:"

    async def _get_redis(self):
        """Lazy initialization of Redis connection."""
        if self._redis is None:
            import redis.asyncio as redis
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    def _make_key(self, nonce: str) -> str:
        """Generate namespaced Redis key for nonce."""
        return f"{self._namespace}{nonce}"

    async def consume_nonce_async(self, nonce: str, max_age_seconds: int | None = None) -> bool:
        """Consume a nonce with one-time use semantics (async Redis version).

        Args:
            nonce: Nonce string to consume
            max_age_seconds: Maximum age in seconds (uses default_expiry if None)

        Returns:
            True if nonce was valid and consumed, False if invalid or already consumed
        """
        # First validate the nonce
        if not self.validate_nonce(nonce, max_age_seconds):
            return False

        redis = await self._get_redis()
        key = self._make_key(nonce)
        max_age = max_age_seconds or self.config.default_expiry_seconds

        # Atomic set-if-not-exists with TTL
        # Returns True if key was set (new), False if key already existed
        was_set = await redis.set(key, "1", nx=True, ex=max_age)

        return bool(was_set)

    async def is_consumed_async(self, nonce: str) -> bool:
        """Check if nonce has been consumed (async Redis version).

        Args:
            nonce: Nonce string to check

        Returns:
            True if nonce exists in Redis (already consumed), False otherwise
        """
        redis = await self._get_redis()
        key = self._make_key(nonce)
        exists = await redis.exists(key)
        return bool(exists)

    async def get_stats_async(self) -> dict:
        """Get nonce registry statistics (async Redis version).

        Returns:
            Dictionary with registry metrics
        """
        redis = await self._get_redis()

        # Count keys matching our namespace
        pattern = f"{self._namespace}*"
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
            "namespace": self._namespace,
            "default_expiry": self.config.default_expiry_seconds,
        }

    async def clear_async(self) -> None:
        """Clear all consumed nonces (async Redis version)."""
        redis = await self._get_redis()

        # Delete all keys matching our namespace
        pattern = f"{self._namespace}*"
        cursor = 0

        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=1000)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.close()


__all__ = [
    "NonceConfig",
    "NonceRegistry",
    "RedisNonceRegistry",
]
