"""Tests for RedisReplayCache (D3) and rate-limiter Redis enforcement (D4)."""
from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest
from sardis_protocol.rate_limiter import get_rate_limiter
from sardis_protocol.replay_cache_redis import RedisReplayCache

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_redis() -> MagicMock:
    """Return a mock that quacks like ``redis.Redis``."""
    mock = MagicMock()
    # By default, .set(nx=True) returns True (key was new)
    mock.set.return_value = True
    return mock


def _reset_global_rate_limiter():
    """Reset the module-level global so each test starts fresh."""
    import sardis_protocol.rate_limiter as rl_mod
    rl_mod._rate_limiter = None


# ---------------------------------------------------------------------------
# D3 — RedisReplayCache
# ---------------------------------------------------------------------------


class TestRedisReplayCacheSeenReturnsFalseForNew:
    """First call to check_and_store for a new mandate returns True (accepted)."""

    def test_new_mandate_returns_true(self):
        redis = _make_fake_redis()
        cache = RedisReplayCache(redis_client=redis, ttl_seconds=3600)

        expires = int(time.time()) + 3600
        result = cache.check_and_store("mandate_new_1", expires)

        assert result is True
        redis.set.assert_called_once()


class TestRedisReplayCacheSeenReturnsTrueForDuplicate:
    """Second call for the same mandate returns False (rejected as duplicate)."""

    def test_duplicate_mandate_returns_false(self):
        redis = _make_fake_redis()
        # Simulate key already existing (NX returns None)
        redis.set.return_value = None
        cache = RedisReplayCache(redis_client=redis, ttl_seconds=3600)

        expires = int(time.time()) + 3600
        result = cache.check_and_store("mandate_dup_1", expires)

        assert result is False


class TestRedisReplayCacheUsesCorrectKeyPrefix:
    """Redis key must use the ``sardis:replay:`` prefix."""

    def test_key_pattern(self):
        redis = _make_fake_redis()
        cache = RedisReplayCache(redis_client=redis, ttl_seconds=300)

        mandate_id = "mnd_abc123"
        expires = int(time.time()) + 600
        cache.check_and_store(mandate_id, expires)

        call_args = redis.set.call_args
        key_used = call_args[0][0] if call_args[0] else call_args[1].get("name")
        assert key_used == f"sardis:replay:{mandate_id}"


class TestRedisReplayCacheFailClosed:
    """On Redis error, check_and_store returns False (fail-closed)."""

    def test_redis_error_returns_false(self):
        redis = _make_fake_redis()
        redis.set.side_effect = ConnectionError("Redis down")
        cache = RedisReplayCache(redis_client=redis, ttl_seconds=3600)

        expires = int(time.time()) + 3600
        result = cache.check_and_store("mandate_err_1", expires)

        assert result is False


class TestRedisReplayCacheInheritance:
    """RedisReplayCache is a drop-in replacement for ReplayCache."""

    def test_is_subclass(self):
        from sardis_protocol.storage import ReplayCache
        assert issubclass(RedisReplayCache, ReplayCache)


# ---------------------------------------------------------------------------
# D4 — Rate limiter enforcement
# ---------------------------------------------------------------------------


class TestRateLimiterRequiresRedisInNonDev:
    """get_rate_limiter must raise RuntimeError in non-dev environments
    when redis_url is not provided."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        _reset_global_rate_limiter()
        yield
        _reset_global_rate_limiter()

    @pytest.mark.parametrize("env_value", ["sandbox", "staging", "production", "prod"])
    def test_raises_in_non_dev(self, env_value):
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": env_value}):
            with pytest.raises(RuntimeError, match="Redis URL required"):
                get_rate_limiter(redis_url=None)

    def test_raises_when_env_is_prod(self):
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "prod"}):
            with pytest.raises(RuntimeError, match="Redis URL required"):
                get_rate_limiter(redis_url=None)


class TestRateLimiterAllowsMemoryInDev:
    """get_rate_limiter must NOT raise when environment is dev-like."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        _reset_global_rate_limiter()
        yield
        _reset_global_rate_limiter()

    @pytest.mark.parametrize("env_value", ["dev", "development", "local"])
    def test_no_error_in_dev(self, env_value):
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": env_value}):
            limiter = get_rate_limiter(redis_url=None)
            assert limiter is not None

    def test_default_env_is_dev(self):
        """When SARDIS_ENVIRONMENT is not set, default is 'dev' — no error."""
        env = os.environ.copy()
        env.pop("SARDIS_ENVIRONMENT", None)
        with patch.dict(os.environ, env, clear=True):
            limiter = get_rate_limiter(redis_url=None)
            assert limiter is not None
