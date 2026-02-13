from __future__ import annotations

import pytest

from sardis_api.middleware.rate_limit import InMemoryRateLimiter, RateLimitConfig, create_rate_limiter


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
