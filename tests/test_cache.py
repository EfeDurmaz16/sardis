"""Unit tests for CacheService."""
from __future__ import annotations

import asyncio
import pytest
from decimal import Decimal

from sardis_v2_core.cache import (
    CacheService,
    CacheMetrics,
    InMemoryCache,
    RedisCache,
)


class TestCacheMetrics:
    """Test CacheMetrics class."""

    def test_initial_state(self):
        """Test metrics start at zero."""
        metrics = CacheMetrics()
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.sets == 0
        assert metrics.deletes == 0
        assert metrics.errors == 0
        assert metrics.hit_rate == 0.0
        assert metrics.miss_rate == 0.0
        assert metrics.avg_latency_ms == 0.0

    def test_record_hit(self):
        """Test recording cache hits."""
        metrics = CacheMetrics()
        metrics.record_hit(5.5)
        metrics.record_hit(3.2)

        assert metrics.hits == 2
        assert metrics.misses == 0
        assert metrics.operation_count == 2
        assert metrics.avg_latency_ms == pytest.approx(4.35, rel=0.01)

    def test_record_miss(self):
        """Test recording cache misses."""
        metrics = CacheMetrics()
        metrics.record_miss(2.0)
        metrics.record_miss(4.0)

        assert metrics.hits == 0
        assert metrics.misses == 2
        assert metrics.avg_latency_ms == pytest.approx(3.0, rel=0.01)

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        metrics = CacheMetrics()
        metrics.record_hit(1.0)
        metrics.record_hit(1.0)
        metrics.record_hit(1.0)
        metrics.record_miss(1.0)

        assert metrics.hit_rate == pytest.approx(0.75, rel=0.01)
        assert metrics.miss_rate == pytest.approx(0.25, rel=0.01)

    def test_record_operations(self):
        """Test recording set/delete operations."""
        metrics = CacheMetrics()
        metrics.record_set(2.0)
        metrics.record_set(3.0)
        metrics.record_delete(1.5)

        assert metrics.sets == 2
        assert metrics.deletes == 1
        assert metrics.operation_count == 3
        assert metrics.avg_latency_ms == pytest.approx(2.16, rel=0.01)

    def test_record_errors(self):
        """Test recording errors."""
        metrics = CacheMetrics()
        metrics.record_error()
        metrics.record_error()

        assert metrics.errors == 2

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = CacheMetrics()
        metrics.record_hit(5.0)
        metrics.record_miss(3.0)
        metrics.record_set(2.0)

        result = metrics.to_dict()

        assert result["hits"] == 1
        assert result["misses"] == 1
        assert result["sets"] == 1
        assert result["hit_rate"] == 0.5
        assert result["miss_rate"] == 0.5
        assert result["total_operations"] == 3
        assert "avg_latency_ms" in result

    def test_reset(self):
        """Test resetting metrics."""
        metrics = CacheMetrics()
        metrics.record_hit(5.0)
        metrics.record_miss(3.0)
        metrics.record_error()

        metrics.reset()

        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.errors == 0
        assert metrics.operation_count == 0


class TestInMemoryCache:
    """Test InMemoryCache backend."""

    @pytest.mark.asyncio
    async def test_get_set(self):
        """Test basic get/set operations."""
        cache = InMemoryCache()

        # Set value
        assert await cache.set("key1", "value1")

        # Get value
        result = await cache.get("key1")
        assert result == "value1"

        # Get non-existent key
        result = await cache.get("key2")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(self):
        """Test set with TTL expiration."""
        cache = InMemoryCache()

        # Set with 1 second TTL
        await cache.set("key1", "value1", ttl=1)

        # Should exist immediately
        result = await cache.get("key1")
        assert result == "value1"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete operation."""
        cache = InMemoryCache()

        await cache.set("key1", "value1")
        assert await cache.delete("key1")

        result = await cache.get("key1")
        assert result is None

        # Delete non-existent key
        assert not await cache.delete("key2")

    @pytest.mark.asyncio
    async def test_exists(self):
        """Test exists check."""
        cache = InMemoryCache()

        await cache.set("key1", "value1")
        assert await cache.exists("key1")
        assert not await cache.exists("key2")

    @pytest.mark.asyncio
    async def test_incr(self):
        """Test increment operation."""
        cache = InMemoryCache()

        # Increment non-existent key
        result = await cache.incr("counter")
        assert result == 1

        # Increment existing key
        result = await cache.incr("counter")
        assert result == 2

        # Increment by custom amount
        result = await cache.incr("counter", amount=5)
        assert result == 7

    @pytest.mark.asyncio
    async def test_expire(self):
        """Test setting TTL on existing key."""
        cache = InMemoryCache()

        await cache.set("key1", "value1")
        assert await cache.expire("key1", ttl=1)

        # Should exist immediately
        assert await cache.exists("key1")

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        assert not await cache.exists("key1")

    @pytest.mark.asyncio
    async def test_acquire_lock(self):
        """Test distributed lock acquisition."""
        cache = InMemoryCache()

        # Acquire lock
        assert await cache.acquire_lock("resource1", ttl=10, owner="owner1")

        # Try to acquire again - should fail
        assert not await cache.acquire_lock("resource1", ttl=10, owner="owner2")

    @pytest.mark.asyncio
    async def test_release_lock(self):
        """Test distributed lock release."""
        cache = InMemoryCache()

        # Acquire and release
        await cache.acquire_lock("resource1", ttl=10, owner="owner1")
        assert await cache.release_lock("resource1", owner="owner1")

        # Should be able to acquire again
        assert await cache.acquire_lock("resource1", ttl=10, owner="owner2")

    @pytest.mark.asyncio
    async def test_release_lock_wrong_owner(self):
        """Test releasing lock with wrong owner."""
        cache = InMemoryCache()

        await cache.acquire_lock("resource1", ttl=10, owner="owner1")

        # Try to release with wrong owner
        assert not await cache.release_lock("resource1", owner="owner2")

        # Original owner can still release
        assert await cache.release_lock("resource1", owner="owner1")

    @pytest.mark.asyncio
    async def test_extend_lock(self):
        """Test extending lock TTL."""
        cache = InMemoryCache()

        await cache.acquire_lock("resource1", ttl=1, owner="owner1")

        # Extend lock
        assert await cache.extend_lock("resource1", ttl=10, owner="owner1")

        # Wait for original TTL
        await asyncio.sleep(1.1)

        # Lock should still be held (extended)
        assert not await cache.acquire_lock("resource1", ttl=10, owner="owner2")

    @pytest.mark.asyncio
    async def test_extend_lock_wrong_owner(self):
        """Test extending lock with wrong owner."""
        cache = InMemoryCache()

        await cache.acquire_lock("resource1", ttl=10, owner="owner1")

        # Try to extend with wrong owner
        assert not await cache.extend_lock("resource1", ttl=20, owner="owner2")


class TestCacheService:
    """Test CacheService high-level operations."""

    @pytest.mark.asyncio
    async def test_create_in_memory(self):
        """Test creating cache service with in-memory backend."""
        cache = CacheService.create()
        assert cache is not None
        assert cache._backend is not None

    @pytest.mark.asyncio
    async def test_balance_operations(self):
        """Test balance caching operations."""
        cache = CacheService.create()
        wallet_id = "wallet_123"
        token = "USDC"
        balance = Decimal("1000.50")

        # Set balance
        assert await cache.set_balance(wallet_id, token, balance)

        # Get balance
        result = await cache.get_balance(wallet_id, token)
        assert result == balance

        # Invalidate balance
        assert await cache.invalidate_balance(wallet_id, token)

        # Should be gone
        result = await cache.get_balance(wallet_id, token)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_wallet_balances(self):
        """Test invalidating all balances for a wallet."""
        cache = CacheService.create()
        wallet_id = "wallet_123"

        # Set multiple balances
        await cache.set_balance(wallet_id, "USDC", Decimal("100"))
        await cache.set_balance(wallet_id, "USDT", Decimal("200"))
        await cache.set_balance(wallet_id, "PYUSD", Decimal("300"))

        # Invalidate all
        count = await cache.invalidate_wallet_balances(wallet_id)
        assert count >= 3

    @pytest.mark.asyncio
    async def test_balance_generation_blocks_stale_writes_after_invalidation(self):
        """Old-generation writes should never be returned after invalidation."""
        cache = CacheService.create()
        wallet_id = "wallet_321"
        token = "USDC"

        await cache.set_balance(wallet_id, token, Decimal("100"))
        old_version = await cache._get_balance_version(wallet_id)
        old_key = cache._balance_key(wallet_id, token, old_version)
        assert await cache._backend.get(old_key) == "100"

        await cache.invalidate_wallet_balances(wallet_id)
        assert await cache.get_balance(wallet_id, token) is None

        # Simulate a stale concurrent writer still writing old-generation data.
        await cache._backend.set(old_key, "999", ttl=60)
        assert await cache.get_balance(wallet_id, token) is None

        await cache.set_balance(wallet_id, token, Decimal("123"))
        assert await cache.get_balance(wallet_id, token) == Decimal("123")

    @pytest.mark.asyncio
    async def test_wallet_operations(self):
        """Test wallet data caching."""
        cache = CacheService.create()
        wallet_id = "wallet_123"
        wallet_data = {
            "id": wallet_id,
            "address": "0x1234...",
            "agent_id": "agent_456",
        }

        # Set wallet
        assert await cache.set_wallet(wallet_id, wallet_data)

        # Get wallet
        result = await cache.get_wallet(wallet_id)
        assert result == wallet_data

        # Invalidate wallet
        assert await cache.invalidate_wallet(wallet_id)

        # Should be gone
        result = await cache.get_wallet(wallet_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_agent_operations(self):
        """Test agent data caching."""
        cache = CacheService.create()
        agent_id = "agent_123"
        agent_data = {
            "id": agent_id,
            "name": "Test Agent",
            "wallet_id": "wallet_456",
        }

        # Set agent
        assert await cache.set_agent(agent_id, agent_data)

        # Get agent
        result = await cache.get_agent(agent_id)
        assert result == agent_data

        # Invalidate agent
        assert await cache.invalidate_agent(agent_id)

        # Should be gone
        result = await cache.get_agent(agent_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        cache = CacheService.create()
        identifier = "user_123"
        limit = 5
        window = 60

        # First 5 requests should be allowed
        for i in range(5):
            allowed, count = await cache.check_rate_limit(identifier, limit, window)
            assert allowed
            assert count == i + 1

        # 6th request should be denied
        allowed, count = await cache.check_rate_limit(identifier, limit, window)
        assert not allowed
        assert count == 6

    @pytest.mark.asyncio
    async def test_get_rate_limit_remaining(self):
        """Test getting remaining rate limit."""
        cache = CacheService.create()
        identifier = "user_123"
        limit = 10

        # Initially should have full limit
        remaining = await cache.get_rate_limit_remaining(identifier, limit)
        assert remaining == 10

        # After one request
        await cache.check_rate_limit(identifier, limit, 60)
        remaining = await cache.get_rate_limit_remaining(identifier, limit)
        assert remaining == 9

    @pytest.mark.asyncio
    async def test_distributed_lock(self):
        """Test distributed lock operations."""
        cache = CacheService.create()
        resource = "transfer_wallet_123"

        # Acquire lock
        owner = await cache.acquire_lock(resource, ttl_seconds=10)
        assert owner is not None

        # Try to acquire again - should fail
        owner2 = await cache.acquire_lock(resource, ttl_seconds=10)
        assert owner2 is None

        # Release lock
        assert await cache.release_lock(resource, owner)

        # Should be able to acquire again
        owner3 = await cache.acquire_lock(resource, ttl_seconds=10)
        assert owner3 is not None

    @pytest.mark.asyncio
    async def test_lock_context_manager(self):
        """Test lock context manager."""
        cache = CacheService.create()
        resource = "transfer_wallet_123"

        # Use context manager
        async with cache.lock(resource, ttl_seconds=10) as lock_id:
            assert lock_id is not None

            # Try to acquire in parallel - should fail
            owner2 = await cache.acquire_lock(resource, ttl_seconds=10)
            assert owner2 is None

        # After context exit, should be released
        owner3 = await cache.acquire_lock(resource, ttl_seconds=10)
        assert owner3 is not None

    @pytest.mark.asyncio
    async def test_lock_context_manager_timeout(self):
        """Test lock context manager timeout."""
        cache = CacheService.create()
        resource = "transfer_wallet_123"

        # Acquire lock
        owner = await cache.acquire_lock(resource, ttl_seconds=30)

        # Try to acquire with context manager - should timeout
        with pytest.raises(TimeoutError):
            async with cache.lock(resource, ttl_seconds=10, max_retries=3, retry_delay=0.1):
                pass

    @pytest.mark.asyncio
    async def test_metrics_enabled(self):
        """Test that metrics are collected when enabled."""
        cache = CacheService.create(enable_metrics=True)
        wallet_id = "wallet_123"
        token = "USDC"

        # Perform operations
        await cache.set_balance(wallet_id, token, Decimal("100"))
        await cache.get_balance(wallet_id, token)
        await cache.get_balance(wallet_id, "USDT")  # miss

        # Check metrics
        metrics = cache.get_metrics()
        assert metrics is not None
        assert metrics["hits"] >= 1
        assert metrics["misses"] >= 1
        assert metrics["sets"] >= 1
        assert metrics["total_operations"] >= 3

    @pytest.mark.asyncio
    async def test_metrics_disabled(self):
        """Test that metrics are not collected when disabled."""
        cache = CacheService.create(enable_metrics=False)
        wallet_id = "wallet_123"

        await cache.set_balance(wallet_id, "USDC", Decimal("100"))

        # Metrics should be None
        metrics = cache.get_metrics()
        assert metrics is None

    @pytest.mark.asyncio
    async def test_reset_metrics(self):
        """Test resetting metrics."""
        cache = CacheService.create(enable_metrics=True)
        wallet_id = "wallet_123"

        await cache.set_balance(wallet_id, "USDC", Decimal("100"))
        await cache.get_balance(wallet_id, "USDC")

        # Check metrics exist
        metrics = cache.get_metrics()
        assert metrics["total_operations"] > 0

        # Reset
        cache.reset_metrics()

        # Should be zero
        metrics = cache.get_metrics()
        assert metrics["total_operations"] == 0

    @pytest.mark.asyncio
    async def test_key_prefixing(self):
        """Test that cache keys are properly prefixed."""
        cache = CacheService.create()

        # Internal method test
        key = cache._key("balance", "wallet_123", "USDC")
        assert key == "sardis:balance:wallet_123:USDC"

        key = cache._key("wallet", "wallet_123")
        assert key == "sardis:wallet:wallet_123"
