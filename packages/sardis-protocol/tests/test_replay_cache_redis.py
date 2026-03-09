"""Tests for RedisReplayCache (D3) and rate-limiter Redis enforcement (D4).

NOTE: These tests are duplicated at tests/test_replay_cache_redis.py (root)
where the conftest.py adds all package source dirs to sys.path. Run from the
root test suite with: ``uv run pytest tests/test_replay_cache_redis.py -v``
"""
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
    mock = MagicMock()
    mock.set.return_value = True
    return mock


def _reset_global_rate_limiter():
    import sardis_protocol.rate_limiter as rl_mod
    rl_mod._rate_limiter = None


# ---------------------------------------------------------------------------
# D3 — RedisReplayCache
# ---------------------------------------------------------------------------


class TestRedisReplayCacheSeenReturnsFalseForNew:
    def test_new_mandate_returns_true(self):
        redis = _make_fake_redis()
        cache = RedisReplayCache(redis_client=redis, ttl_seconds=3600)
        assert cache.check_and_store("m1", int(time.time()) + 3600) is True


class TestRedisReplayCacheSeenReturnsTrueForDuplicate:
    def test_duplicate_mandate_returns_false(self):
        redis = _make_fake_redis()
        redis.set.return_value = None
        cache = RedisReplayCache(redis_client=redis, ttl_seconds=3600)
        assert cache.check_and_store("m1", int(time.time()) + 3600) is False


class TestRedisReplayCacheUsesCorrectKeyPrefix:
    def test_key_pattern(self):
        redis = _make_fake_redis()
        cache = RedisReplayCache(redis_client=redis, ttl_seconds=300)
        cache.check_and_store("mnd_abc123", int(time.time()) + 600)
        key_used = redis.set.call_args[0][0]
        assert key_used == "sardis:replay:mnd_abc123"


class TestRedisReplayCacheFailClosed:
    def test_redis_error_returns_false(self):
        redis = _make_fake_redis()
        redis.set.side_effect = ConnectionError("Redis down")
        cache = RedisReplayCache(redis_client=redis, ttl_seconds=3600)
        assert cache.check_and_store("m1", int(time.time()) + 3600) is False


# ---------------------------------------------------------------------------
# D4 — Rate limiter enforcement
# ---------------------------------------------------------------------------


class TestRateLimiterRequiresRedisInNonDev:
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


class TestRateLimiterAllowsMemoryInDev:
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
