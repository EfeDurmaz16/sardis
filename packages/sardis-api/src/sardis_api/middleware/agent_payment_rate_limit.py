"""Agent-level sliding-window limiter for payment execution endpoints."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Deque
from uuid import uuid4

from fastapi import HTTPException, status

from sardis_api.routers.metrics import record_agent_payment_rate_limit

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentPaymentRateLimitConfig:
    enabled: bool = True
    max_requests: int = 30
    window_seconds: int = 60

    @classmethod
    def from_settings(cls, settings: Any | None) -> "AgentPaymentRateLimitConfig":
        def _setting(name: str, default: Any) -> Any:
            if settings is not None and hasattr(settings, name):
                return getattr(settings, name)
            env_name = f"SARDIS_{name.upper()}"
            raw = os.getenv(env_name)
            if raw is None:
                return default
            if isinstance(default, bool):
                return raw.strip().lower() in {"1", "true", "yes", "on"}
            if isinstance(default, int):
                try:
                    return int(raw)
                except ValueError:
                    return default
            return raw

        max_requests = max(1, int(_setting("agent_payment_rate_limit_max_requests", 30)))
        window_seconds = max(1, int(_setting("agent_payment_rate_limit_window_seconds", 60)))
        enabled = bool(_setting("agent_payment_rate_limit_enabled", True))
        return cls(enabled=enabled, max_requests=max_requests, window_seconds=window_seconds)


@dataclass(slots=True)
class AgentPaymentRateLimitResult:
    allowed: bool
    current_count: int
    remaining: int
    retry_after_seconds: int = 0


class InMemoryAgentSlidingWindowLimiter:
    """Process-local sliding-window limiter."""

    def __init__(self, config: AgentPaymentRateLimitConfig):
        self._config = config
        self._events: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check_and_record(self, agent_id: str) -> AgentPaymentRateLimitResult:
        now = time.monotonic()
        cutoff = now - self._config.window_seconds
        async with self._lock:
            bucket = self._events[agent_id]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self._config.max_requests:
                retry_after = max(1, int((bucket[0] + self._config.window_seconds) - now))
                return AgentPaymentRateLimitResult(
                    allowed=False,
                    current_count=len(bucket),
                    remaining=0,
                    retry_after_seconds=retry_after,
                )

            bucket.append(now)
            current = len(bucket)
            return AgentPaymentRateLimitResult(
                allowed=True,
                current_count=current,
                remaining=max(0, self._config.max_requests - current),
                retry_after_seconds=0,
            )


class RedisAgentSlidingWindowLimiter:
    """Redis-backed sliding-window limiter for multi-instance deployments."""

    KEY_PREFIX = "sardis:rl:payments:agent"

    def __init__(self, config: AgentPaymentRateLimitConfig, redis_url: str):
        self._config = config
        self._redis_url = redis_url
        self._redis = None
        self._fallback = InMemoryAgentSlidingWindowLimiter(config)

    async def _client(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis.asyncio as redis  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001
            logger.warning("redis_async_unavailable; falling back to in-memory limiter: %s", exc)
            return None
        self._redis = redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def check_and_record(self, agent_id: str) -> AgentPaymentRateLimitResult:
        client = await self._client()
        if client is None:
            return await self._fallback.check_and_record(agent_id)

        now = time.time()
        cutoff = now - self._config.window_seconds
        key = f"{self.KEY_PREFIX}:{agent_id}"
        member = f"{now:.6f}:{uuid4().hex}"
        try:
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            pipe.zadd(key, {member: now})
            pipe.expire(key, self._config.window_seconds + 5)
            results = await pipe.execute()
            current = int(results[1]) + 1
            if current > self._config.max_requests:
                await client.zrem(key, member)
                oldest = await client.zrange(key, 0, 0, withscores=True)
                retry_after = 1
                if oldest:
                    oldest_ts = float(oldest[0][1])
                    retry_after = max(1, int((oldest_ts + self._config.window_seconds) - now))
                return AgentPaymentRateLimitResult(
                    allowed=False,
                    current_count=self._config.max_requests,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )
            return AgentPaymentRateLimitResult(
                allowed=True,
                current_count=current,
                remaining=max(0, self._config.max_requests - current),
                retry_after_seconds=0,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("redis_limiter_error; falling back to in-memory limiter: %s", exc)
            return await self._fallback.check_and_record(agent_id)


_limiter = None
_limiter_signature: tuple[Any, ...] | None = None


def get_agent_payment_rate_limiter(settings: Any | None = None):
    """Return singleton limiter configured from current settings/env."""
    global _limiter, _limiter_signature
    cfg = AgentPaymentRateLimitConfig.from_settings(settings)
    redis_url = ""
    if settings is not None and hasattr(settings, "redis_url"):
        redis_url = str(getattr(settings, "redis_url") or "")
    if not redis_url:
        redis_url = os.getenv("SARDIS_REDIS_URL") or os.getenv("REDIS_URL") or os.getenv("UPSTASH_REDIS_URL") or ""
    signature = (cfg.enabled, cfg.max_requests, cfg.window_seconds, bool(redis_url))
    if _limiter is not None and _limiter_signature == signature:
        return _limiter
    if redis_url:
        _limiter = RedisAgentSlidingWindowLimiter(cfg, redis_url)
    else:
        _limiter = InMemoryAgentSlidingWindowLimiter(cfg)
    _limiter_signature = signature
    return _limiter


async def enforce_agent_payment_rate_limit(
    *,
    agent_id: str,
    operation: str,
    settings: Any | None = None,
) -> AgentPaymentRateLimitResult:
    """Enforce agent-level limiter and raise HTTP 429 on breach."""
    cfg = AgentPaymentRateLimitConfig.from_settings(settings)
    if not cfg.enabled:
        return AgentPaymentRateLimitResult(
            allowed=True,
            current_count=0,
            remaining=cfg.max_requests,
            retry_after_seconds=0,
        )

    limiter = get_agent_payment_rate_limiter(settings)
    result = await limiter.check_and_record(str(agent_id))
    record_agent_payment_rate_limit(operation=operation, allowed=result.allowed)
    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "agent_rate_limit_exceeded",
                "agent_id": str(agent_id),
                "operation": operation,
                "limit": cfg.max_requests,
                "window_seconds": cfg.window_seconds,
                "retry_after_seconds": result.retry_after_seconds,
            },
            headers={"Retry-After": str(result.retry_after_seconds)},
        )
    return result

