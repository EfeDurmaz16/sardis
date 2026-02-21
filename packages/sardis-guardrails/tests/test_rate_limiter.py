"""Unit tests for rate limiter."""

import pytest
import asyncio
from decimal import Decimal
from sardis_guardrails.rate_limiter import (
    RateLimiter,
    RateLimitError,
    TokenBucket,
)


class TestTokenBucket:
    """Test token bucket rate limiting algorithm."""

    def test_initial_tokens_at_capacity(self):
        """Test bucket starts with full capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.available_tokens() == 10

    def test_consume_tokens(self):
        """Test consuming tokens from bucket."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Consume 3 tokens
        success = bucket.consume(3)
        assert success is True
        assert bucket.available_tokens() == 7

        # Consume 7 more
        success = bucket.consume(7)
        assert success is True
        assert bucket.available_tokens() == 0

    def test_consume_more_than_available(self):
        """Test consuming more tokens than available fails."""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)

        # Try to consume more than capacity
        success = bucket.consume(10)
        assert success is False
        assert bucket.available_tokens() == 5  # Unchanged

    def test_token_refill(self):
        """Test tokens refill over time."""
        import time

        bucket = TokenBucket(capacity=10, refill_rate=5.0)  # 5 tokens/second

        # Consume all tokens
        bucket.consume(10)
        assert bucket.available_tokens() == 0

        # Wait 0.4 seconds = 2 tokens should refill
        time.sleep(0.4)
        available = bucket.available_tokens()
        assert available >= 1  # At least 1 token
        assert available <= 3  # At most 3 tokens (accounting for timing variance)

    def test_refill_does_not_exceed_capacity(self):
        """Test refill stops at capacity."""
        import time

        bucket = TokenBucket(capacity=5, refill_rate=10.0)

        # Wait long enough for many refills
        time.sleep(1.0)

        # Should not exceed capacity
        assert bucket.available_tokens() == 5


class TestRateLimiter:
    """Test rate limiter with multiple limits."""

    @pytest.mark.asyncio
    async def test_add_limit(self):
        """Test adding rate limit configuration."""
        limiter = RateLimiter(agent_id="agent-123")

        limiter.add_limit(
            name="per_minute",
            max_transactions=10,
            window_seconds=60.0,
        )

        # Should have limit configured
        assert "per_minute" in limiter._limits

    @pytest.mark.asyncio
    async def test_transaction_count_limit(self):
        """Test transaction count rate limiting."""
        limiter = RateLimiter(agent_id="agent-123")

        limiter.add_limit(
            name="test_limit",
            max_transactions=3,
            window_seconds=60.0,
        )

        # First 3 transactions should succeed
        for _ in range(3):
            await limiter.check_and_record("test_limit", Decimal("100"))

        # 4th should fail
        with pytest.raises(RateLimitError) as exc_info:
            await limiter.check_and_record("test_limit", Decimal("100"))

        assert "Transaction count limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_amount_limit(self):
        """Test total amount rate limiting."""
        limiter = RateLimiter(agent_id="agent-123")

        limiter.add_limit(
            name="amount_limit",
            max_transactions=100,
            window_seconds=60.0,
            max_amount=Decimal("1000.00"),
        )

        # Transactions totaling less than limit should succeed
        await limiter.check_and_record("amount_limit", Decimal("400"))
        await limiter.check_and_record("amount_limit", Decimal("300"))

        # This should exceed amount limit
        with pytest.raises(RateLimitError) as exc_info:
            await limiter.check_and_record("amount_limit", Decimal("400"))

        assert "Amount limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_token_bucket_rate_limiting(self):
        """Test token bucket prevents burst."""
        limiter = RateLimiter(agent_id="agent-123", burst_allowance=1.0)

        limiter.add_limit(
            name="burst_test",
            max_transactions=5,
            window_seconds=10.0,
        )

        # Should allow up to capacity (5 tokens with 1.0 burst allowance)
        for _ in range(5):
            await limiter.check_and_record("burst_test", Decimal("10"))

        # Next should fail due to token bucket exhaustion
        with pytest.raises(RateLimitError) as exc_info:
            await limiter.check_and_record("burst_test", Decimal("10"))

        assert "Transaction rate limit exceeded" in str(exc_info.value)
        assert "Available tokens:" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_burst_allowance(self):
        """Test burst allowance multiplier."""
        limiter = RateLimiter(agent_id="agent-123", burst_allowance=2.0)

        limiter.add_limit(
            name="burst_limit",
            max_transactions=5,
            window_seconds=60.0,
        )

        # With 2.0 burst allowance, capacity is 10 tokens
        # Should allow up to 10 rapid transactions
        for _ in range(10):
            await limiter.check_and_record("burst_limit", Decimal("100"))

        # 11th should fail
        with pytest.raises(RateLimitError):
            await limiter.check_and_record("burst_limit", Decimal("100"))

    @pytest.mark.asyncio
    async def test_sliding_window_cleanup(self):
        """Test old transactions are cleaned from sliding window."""
        limiter = RateLimiter(agent_id="agent-123")

        limiter.add_limit(
            name="window_test",
            max_transactions=2,
            window_seconds=0.2,  # Short window
        )

        # Use up limit
        await limiter.check_and_record("window_test", Decimal("10"))
        await limiter.check_and_record("window_test", Decimal("10"))

        # Should be at limit
        with pytest.raises(RateLimitError):
            await limiter.check_and_record("window_test", Decimal("10"))

        # Wait for window to expire
        await asyncio.sleep(0.3)

        # Should succeed now (old transactions cleaned)
        await limiter.check_and_record("window_test", Decimal("10"))

    @pytest.mark.asyncio
    async def test_get_remaining_capacity(self):
        """Test querying remaining capacity."""
        limiter = RateLimiter(agent_id="agent-123")

        limiter.add_limit(
            name="capacity_test",
            max_transactions=10,
            window_seconds=60.0,
            max_amount=Decimal("1000"),
        )

        # Use some capacity
        await limiter.check_and_record("capacity_test", Decimal("300"))
        await limiter.check_and_record("capacity_test", Decimal("200"))

        capacity = await limiter.get_remaining_capacity("capacity_test")

        assert capacity["remaining_transactions"] == 8
        assert capacity["remaining_amount"] == Decimal("500")

    @pytest.mark.asyncio
    async def test_check_all_limits(self):
        """Test checking all configured limits at once."""
        limiter = RateLimiter(agent_id="agent-123")

        limiter.add_limit(
            name="limit_1",
            max_transactions=5,
            window_seconds=60.0,
        )

        limiter.add_limit(
            name="limit_2",
            max_transactions=3,
            window_seconds=60.0,
        )

        # First 3 should pass both limits
        for _ in range(3):
            await limiter.check_all_limits(Decimal("100"))

        # 4th should fail limit_2
        with pytest.raises(RateLimitError):
            await limiter.check_all_limits(Decimal("100"))

    @pytest.mark.asyncio
    async def test_reset_specific_limit(self):
        """Test resetting a specific limit."""
        limiter = RateLimiter(agent_id="agent-123")

        limiter.add_limit(
            name="reset_test",
            max_transactions=2,
            window_seconds=60.0,
        )

        # Use up limit
        await limiter.check_and_record("reset_test", Decimal("10"))
        await limiter.check_and_record("reset_test", Decimal("10"))

        # Should be at limit
        with pytest.raises(RateLimitError):
            await limiter.check_and_record("reset_test", Decimal("10"))

        # Reset
        await limiter.reset("reset_test")

        # Should work now
        await limiter.check_and_record("reset_test", Decimal("10"))

    @pytest.mark.asyncio
    async def test_reset_all_limits(self):
        """Test resetting all limits."""
        limiter = RateLimiter(agent_id="agent-123")

        limiter.add_limit("limit_1", max_transactions=1, window_seconds=60.0)
        limiter.add_limit("limit_2", max_transactions=1, window_seconds=60.0)

        # Use both limits
        await limiter.check_and_record("limit_1", Decimal("10"))
        await limiter.check_and_record("limit_2", Decimal("10"))

        # Reset all
        await limiter.reset()

        # Both should work again
        await limiter.check_and_record("limit_1", Decimal("10"))
        await limiter.check_and_record("limit_2", Decimal("10"))

    @pytest.mark.asyncio
    async def test_unconfigured_limit_raises_error(self):
        """Test accessing unconfigured limit raises ValueError."""
        limiter = RateLimiter(agent_id="agent-123")

        with pytest.raises(ValueError) as exc_info:
            await limiter.check_and_record("nonexistent", Decimal("10"))

        assert "not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_multiple_agents_independent(self):
        """Test different agents have independent rate limits."""
        limiter1 = RateLimiter(agent_id="agent-1")
        limiter2 = RateLimiter(agent_id="agent-2")

        limiter1.add_limit("limit", max_transactions=1, window_seconds=60.0)
        limiter2.add_limit("limit", max_transactions=1, window_seconds=60.0)

        # Agent 1 uses limit
        await limiter1.check_and_record("limit", Decimal("10"))

        # Agent 2 should still have capacity
        await limiter2.check_and_record("limit", Decimal("10"))

    @pytest.mark.asyncio
    async def test_amount_limit_without_count_limit(self):
        """Test amount limit can trigger before count limit."""
        limiter = RateLimiter(agent_id="agent-123")

        limiter.add_limit(
            name="amount_only",
            max_transactions=100,  # High count limit
            window_seconds=60.0,
            max_amount=Decimal("500"),  # Low amount limit
        )

        # First large transaction
        await limiter.check_and_record("amount_only", Decimal("400"))

        # Second should exceed amount limit (but not count limit)
        with pytest.raises(RateLimitError) as exc_info:
            await limiter.check_and_record("amount_only", Decimal("200"))

        assert "Amount limit exceeded" in str(exc_info.value)
