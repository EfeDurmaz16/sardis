from __future__ import annotations

import sys
import types

import pytest
from starlette.requests import Request
from sardis_api.middleware.rate_limit import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RedisRateLimiter,
    create_rate_limiter,
)


def test_rate_limiter_requires_redis_in_production(monkeypatch) -> None:
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "prod")
    monkeypatch.delenv("SARDIS_REDIS_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_URL", raising=False)

    with pytest.raises(RuntimeError, match="Redis is required for production rate limiting"):
        create_rate_limiter(RateLimitConfig())


def test_rate_limiter_falls_back_to_in_memory_in_dev(monkeypatch) -> None:
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")
    monkeypatch.delenv("SARDIS_REDIS_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_URL", raising=False)

    limiter = create_rate_limiter(RateLimitConfig())
    assert isinstance(limiter, InMemoryRateLimiter)


@pytest.mark.asyncio
async def test_redis_rate_limiter_falls_back_when_pipeline_times_out(monkeypatch) -> None:
    class FakePipeline:
        def zremrangebyscore(self, *args, **kwargs):
            return self

        def zcard(self, *args, **kwargs):
            return self

        def zadd(self, *args, **kwargs):
            return self

        def expire(self, *args, **kwargs):
            return self

        async def execute(self):
            raise TimeoutError("redis unavailable")

    class FakeRedisClient:
        def pipeline(self):
            return FakePipeline()

    redis_module = types.ModuleType("redis")
    redis_async_module = types.ModuleType("redis.asyncio")
    redis_async_module.from_url = lambda *args, **kwargs: FakeRedisClient()
    redis_module.asyncio = redis_async_module
    monkeypatch.setitem(sys.modules, "redis", redis_module)
    monkeypatch.setitem(sys.modules, "redis.asyncio", redis_async_module)

    limiter = RedisRateLimiter(RateLimitConfig(), "redis://demo")
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/demo",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
    )
    allowed, headers = await limiter.check_rate_limit(request)

    assert allowed is True
    assert headers["X-RateLimit-Limit"] == "100"
