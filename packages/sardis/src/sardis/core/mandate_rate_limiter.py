"""Per-mandate rate limiter — limits payment frequency per mandate.

Enforces a maximum number of payments per time window for each mandate.
Uses Redis when available, falls back to in-memory for dev.

Usage:
    limiter = MandateRateLimiter(redis_url="redis://localhost:6379")

    allowed, info = await limiter.check(
        mandate_id="mandate_xxx",
        max_requests=10,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(429, f"Mandate rate limit: {info}")
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("sardis.mandate_rate_limiter")


@dataclass(frozen=True)
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    current: int
    limit: int
    window_seconds: int
    remaining: int
    retry_after: float | None = None


class MandateRateLimiter:
    """Per-mandate payment rate limiter.

    Tracks payment count per mandate using a sliding window.
    Redis-backed for production, in-memory for dev/test.
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        self._memory: dict[str, list[float]] = {}

    async def check(
        self,
        mandate_id: str,
        max_requests: int = 10,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        """Check if a payment is within the mandate's rate limit.

        Returns RateLimitResult with allowed status and remaining quota.
        """
        if self._redis:
            return await self._check_redis(mandate_id, max_requests, window_seconds)
        return self._check_memory(mandate_id, max_requests, window_seconds)

    async def record(self, mandate_id: str, window_seconds: int = 60) -> None:
        """Record a payment against the mandate's rate limit window."""
        if self._redis:
            await self._record_redis(mandate_id, window_seconds)
        else:
            self._record_memory(mandate_id)

    def _check_memory(
        self, mandate_id: str, max_requests: int, window_seconds: int
    ) -> RateLimitResult:
        """In-memory sliding window check (dev/test only)."""
        now = time.time()
        key = f"mandate_rate:{mandate_id}"
        timestamps = self._memory.get(key, [])

        # Remove expired entries
        cutoff = now - window_seconds
        timestamps = [t for t in timestamps if t > cutoff]
        self._memory[key] = timestamps

        current = len(timestamps)
        allowed = current < max_requests
        remaining = max(0, max_requests - current)

        retry_after = None
        if not allowed and timestamps:
            retry_after = timestamps[0] + window_seconds - now

        return RateLimitResult(
            allowed=allowed,
            current=current,
            limit=max_requests,
            window_seconds=window_seconds,
            remaining=remaining,
            retry_after=retry_after,
        )

    def _record_memory(self, mandate_id: str) -> None:
        key = f"mandate_rate:{mandate_id}"
        if key not in self._memory:
            self._memory[key] = []
        self._memory[key].append(time.time())

    async def _check_redis(
        self, mandate_id: str, max_requests: int, window_seconds: int
    ) -> RateLimitResult:
        """Redis sliding window check."""
        key = f"sardis:mandate_rate:{mandate_id}"
        now = time.time()
        cutoff = now - window_seconds

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zcard(key)
        pipe.execute()

        results = await pipe
        current = results[1]
        allowed = current < max_requests
        remaining = max(0, max_requests - current)

        return RateLimitResult(
            allowed=allowed,
            current=current,
            limit=max_requests,
            window_seconds=window_seconds,
            remaining=remaining,
        )

    async def _record_redis(self, mandate_id: str, window_seconds: int = 60) -> None:
        key = f"sardis:mandate_rate:{mandate_id}"
        now = time.time()
        pipe = self._redis.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds + 10)  # TTL slightly longer than window
        await pipe.execute()
