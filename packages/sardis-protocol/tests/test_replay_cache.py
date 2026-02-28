"""Tests for mandate replay cache and InMemoryMandateCache."""
import asyncio
import time

import pytest

from sardis_protocol.storage import ReplayCache
from sardis_protocol.mandate_cache import InMemoryMandateCache, MandateCacheConfig


# --- ReplayCache ---


class TestReplayCache:
    def test_first_mandate_accepted(self):
        cache = ReplayCache()
        expires = int(time.time()) + 3600
        assert cache.check_and_store("mandate_1", expires) is True

    def test_duplicate_mandate_rejected(self):
        cache = ReplayCache()
        expires = int(time.time()) + 3600
        cache.check_and_store("mandate_1", expires)
        assert cache.check_and_store("mandate_1", expires) is False

    def test_expired_mandate_reusable(self):
        cache = ReplayCache()
        past = int(time.time()) - 10
        # Store with past expiry -- cache uses default TTL for expired values
        cache.check_and_store("mandate_1", past)
        # Manually expire by manipulating the cache
        cache._seen["mandate_1"] = (int(time.time()) - 1, )  # Force expired
        # Actually, the cache stores (expires_at) directly
        cache._seen["mandate_1"] = int(time.time()) - 1
        assert cache.check_and_store("mandate_1", int(time.time()) + 3600) is True

    def test_cleanup_removes_expired(self):
        cache = ReplayCache()
        now = int(time.time())
        cache._seen["old"] = now - 100
        cache._seen["fresh"] = now + 3600
        removed = cache.cleanup(now)
        assert removed == 1
        assert "old" not in cache._seen
        assert "fresh" in cache._seen

    def test_stats(self):
        cache = ReplayCache()
        now = int(time.time())
        cache._seen["active1"] = now + 3600
        cache._seen["expired1"] = now - 100
        stats = cache.stats()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 1
        assert stats["expired_entries"] == 1

    def test_clear(self):
        cache = ReplayCache()
        cache.check_and_store("m1", int(time.time()) + 3600)
        cache.check_and_store("m2", int(time.time()) + 3600)
        cache.clear()
        assert len(cache._seen) == 0

    def test_max_entries_triggers_cleanup(self):
        cache = ReplayCache(max_entries=5)
        now = int(time.time())
        for i in range(5):
            cache._seen[f"m{i}"] = now - 100  # all expired
        # This should trigger cleanup since we're at max
        result = cache.check_and_store("new", now + 3600)
        assert result is True
        # Expired entries should be cleaned
        assert len(cache._seen) == 1


# --- InMemoryMandateCache ---


class TestInMemoryMandateCache:
    @pytest.fixture
    def cache(self):
        config = MandateCacheConfig(redis_url="memory://", default_ttl=60)
        return InMemoryMandateCache(config)

    @pytest.mark.asyncio
    async def test_consume_new_mandate(self, cache):
        result = await cache.consume_mandate("hash1", {"amount": "100"})
        assert result is True

    @pytest.mark.asyncio
    async def test_consume_duplicate_rejected(self, cache):
        await cache.consume_mandate("hash1", {"amount": "100"})
        result = await cache.consume_mandate("hash1", {"amount": "100"})
        assert result is False

    @pytest.mark.asyncio
    async def test_is_consumed(self, cache):
        assert await cache.is_consumed("hash1") is False
        await cache.consume_mandate("hash1", {"amount": "100"})
        assert await cache.is_consumed("hash1") is True

    @pytest.mark.asyncio
    async def test_get_mandate_data(self, cache):
        data = {"amount": "100", "token": "USDC"}
        await cache.consume_mandate("hash1", data)
        retrieved = await cache.get_mandate("hash1")
        assert retrieved == data

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, cache):
        assert await cache.get_mandate("nonexistent") is None

    @pytest.mark.asyncio
    async def test_revoke_mandate(self, cache):
        await cache.consume_mandate("hash1", {"amount": "100"})
        revoked = await cache.revoke_mandate("hash1")
        assert revoked is True
        assert await cache.is_consumed("hash1") is False

    @pytest.mark.asyncio
    async def test_revoke_nonexistent(self, cache):
        revoked = await cache.revoke_mandate("nonexistent")
        assert revoked is False

    @pytest.mark.asyncio
    async def test_expired_mandate_reusable(self, cache):
        # Use very short TTL
        config = MandateCacheConfig(redis_url="memory://", default_ttl=1)
        short_cache = InMemoryMandateCache(config)

        await short_cache.consume_mandate("hash1", {"amount": "100"}, ttl=1)

        # Manually expire it
        short_cache._cache["hash1"] = ({"amount": "100"}, int(time.time()) - 1)

        # Should be reusable now
        result = await short_cache.consume_mandate("hash1", {"amount": "200"})
        assert result is True

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache):
        await cache.consume_mandate("hash1", {"a": 1}, ttl=1)
        cache._cache["hash1"] = ({"a": 1}, int(time.time()) - 1)

        removed = await cache.cleanup_expired()
        assert removed == 1

    @pytest.mark.asyncio
    async def test_stats(self, cache):
        await cache.consume_mandate("hash1", {"a": 1})
        await cache.consume_mandate("hash1", {"a": 1})  # duplicate
        stats = await cache.get_stats()
        assert stats["total_consumed"] == 1
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1

    @pytest.mark.asyncio
    async def test_custom_ttl(self, cache):
        await cache.consume_mandate("hash1", {"a": 1}, ttl=9999)
        assert await cache.is_consumed("hash1") is True
