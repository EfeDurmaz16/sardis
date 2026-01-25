"""
Comprehensive tests for sardis_v2_core.retry module.

Tests cover:
- RetryConfig configuration and delay calculation
- Async and sync retry execution
- Retry decorator functionality
- Exponential backoff with jitter
- Non-retryable exception handling
- Retry exhaustion
- RetryContext for manual retry control
- On-retry callbacks
- Pre-configured retry configurations
"""
from __future__ import annotations

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sardis_v2_core.retry import (
    RetryConfig,
    RetryStats,
    RetryExhausted,
    RetryContext,
    retry,
    retry_sync_decorator,
    retry_async,
    retry_sync,
    MPC_RETRY_CONFIG,
    RPC_RETRY_CONFIG,
    DB_RETRY_CONFIG,
    WEBHOOK_RETRY_CONFIG,
)


class TestRetryConfig:
    """Tests for RetryConfig class."""

    def test_default_config(self):
        """Should create config with default values."""
        config = RetryConfig()
        assert config.max_retries >= 0
        assert config.base_delay > 0
        assert config.max_delay > config.base_delay
        assert 0 <= config.jitter <= 1

    def test_custom_config(self):
        """Should accept custom configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=0.1,
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 10.0
        assert config.exponential_base == 2.0
        assert config.jitter == 0.1

    def test_calculate_delay_exponential(self):
        """Should calculate exponential backoff delay."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=100.0,
            jitter=0.0,  # No jitter for predictable tests
        )

        assert config.calculate_delay(0) == 1.0  # 1 * 2^0 = 1
        assert config.calculate_delay(1) == 2.0  # 1 * 2^1 = 2
        assert config.calculate_delay(2) == 4.0  # 1 * 2^2 = 4
        assert config.calculate_delay(3) == 8.0  # 1 * 2^3 = 8

    def test_calculate_delay_capped_at_max(self):
        """Should cap delay at max_delay."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=5.0,
            jitter=0.0,
        )

        # 1 * 2^4 = 16, but should be capped at 5
        assert config.calculate_delay(4) == 5.0
        assert config.calculate_delay(10) == 5.0

    def test_calculate_delay_with_jitter(self):
        """Should add jitter to delay."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=1.0,  # No exponential growth
            max_delay=10.0,
            jitter=0.5,  # 50% jitter
        )

        # With jitter, delay should be between 0.5 and 1.5
        delays = [config.calculate_delay(0) for _ in range(100)]
        assert min(delays) >= 0.5
        assert max(delays) <= 1.5
        # Should have some variation
        assert len(set(delays)) > 1

    def test_should_retry_with_retryable_exception(self):
        """Should retry for retryable exceptions."""
        config = RetryConfig(retryable_exceptions=(ValueError,))

        assert config.should_retry(ValueError("test"))
        assert not config.should_retry(TypeError("test"))

    def test_should_retry_with_non_retryable_exception(self):
        """Should not retry non-retryable exceptions."""
        config = RetryConfig(
            retryable_exceptions=(Exception,),
            non_retryable_exceptions=(KeyboardInterrupt, SystemExit),
        )

        assert config.should_retry(ValueError("test"))
        assert not config.should_retry(KeyboardInterrupt())
        assert not config.should_retry(SystemExit())

    def test_should_retry_with_custom_condition(self):
        """Should use custom retry condition."""
        def custom_condition(exc):
            return "retry" in str(exc)

        config = RetryConfig(retry_condition=custom_condition)

        assert config.should_retry(Exception("please retry"))
        assert not config.should_retry(Exception("do not"))


class TestRetryStats:
    """Tests for RetryStats class."""

    def test_default_stats(self):
        """Should have default values."""
        stats = RetryStats()
        assert stats.attempts == 0
        assert stats.total_delay == 0.0
        assert stats.success is False
        assert stats.last_exception is None


class TestRetryExhausted:
    """Tests for RetryExhausted exception."""

    def test_exception_contains_stats(self):
        """Should contain retry stats."""
        stats = RetryStats(attempts=3, total_delay=5.0)
        original = ValueError("original error")

        exc = RetryExhausted("All retries failed", stats, original)

        assert exc.stats == stats
        assert exc.original_exception == original
        assert "All retries failed" in str(exc)


class TestRetryAsync:
    """Tests for retry_async function."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Should succeed on first attempt without retries."""
        call_count = 0

        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_async(successful_func, config=RetryConfig(max_retries=3))

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Should succeed after retries."""
        call_count = 0

        async def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "success"

        config = RetryConfig(max_retries=5, base_delay=0.01, jitter=0.0)
        result = await retry_async(eventually_succeeds, config=config)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Should raise RetryExhausted when all retries fail."""
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=0.0)

        with pytest.raises(RetryExhausted) as exc_info:
            await retry_async(always_fails, config=config)

        assert call_count == 4  # Initial + 3 retries
        assert exc_info.value.stats.attempts == 4
        assert isinstance(exc_info.value.original_exception, ValueError)

    @pytest.mark.asyncio
    async def test_non_retryable_exception_raised_immediately(self):
        """Should raise non-retryable exceptions immediately."""
        call_count = 0

        async def raises_non_retryable():
            nonlocal call_count
            call_count += 1
            raise KeyboardInterrupt()

        config = RetryConfig(
            max_retries=3,
            non_retryable_exceptions=(KeyboardInterrupt,),
        )

        with pytest.raises(KeyboardInterrupt):
            await retry_async(raises_non_retryable, config=config)

        assert call_count == 1  # Should not retry

    @pytest.mark.asyncio
    async def test_on_retry_callback(self):
        """Should call on_retry callback before each retry."""
        retry_info = []

        def on_retry(attempt, exception, delay):
            retry_info.append((attempt, type(exception).__name__, delay))

        call_count = 0

        async def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("error")
            return "success"

        config = RetryConfig(
            max_retries=5,
            base_delay=0.01,
            jitter=0.0,
            on_retry=on_retry,
        )

        await retry_async(eventually_succeeds, config=config)

        assert len(retry_info) == 2
        assert retry_info[0][0] == 1  # First retry
        assert retry_info[0][1] == "ValueError"
        assert retry_info[1][0] == 2  # Second retry


class TestRetrySync:
    """Tests for retry_sync function."""

    def test_success_on_first_attempt(self):
        """Should succeed on first attempt."""
        call_count = 0

        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = retry_sync(successful_func, config=RetryConfig(max_retries=3))

        assert result == "success"
        assert call_count == 1

    def test_success_after_retries(self):
        """Should succeed after retries."""
        call_count = 0

        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary")
            return "success"

        config = RetryConfig(max_retries=5, base_delay=0.01, jitter=0.0)
        result = retry_sync(eventually_succeeds, config=config)

        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """Should raise RetryExhausted when all retries fail."""
        def always_fails():
            raise ValueError("always fails")

        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=0.0)

        with pytest.raises(RetryExhausted):
            retry_sync(always_fails, config=config)


class TestRetryDecorator:
    """Tests for @retry decorator."""

    @pytest.mark.asyncio
    async def test_decorator_without_arguments(self):
        """Should work as decorator without parentheses."""
        call_count = 0

        @retry
        async def my_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await my_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_decorator_with_arguments(self):
        """Should work as decorator with arguments."""
        call_count = 0

        @retry(max_retries=2, base_delay=0.01, jitter=0.0)
        async def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("retry")
            return "success"

        result = await eventually_succeeds()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_with_config(self):
        """Should accept config object."""
        config = RetryConfig(max_retries=1, base_delay=0.01, jitter=0.0)
        call_count = 0

        @retry(config=config)
        async def my_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("retry")
            return "success"

        result = await my_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Should preserve function name and docstring."""
        @retry
        async def my_documented_func():
            """This is my docstring."""
            return True

        assert my_documented_func.__name__ == "my_documented_func"
        assert "docstring" in my_documented_func.__doc__

    @pytest.mark.asyncio
    async def test_decorator_with_non_retryable_exceptions(self):
        """Should not retry non-retryable exceptions."""
        call_count = 0

        @retry(
            max_retries=3,
            non_retryable_exceptions=(KeyError,),
        )
        async def raises_keyerror():
            nonlocal call_count
            call_count += 1
            raise KeyError("non-retryable")

        with pytest.raises(KeyError):
            await raises_keyerror()

        assert call_count == 1


class TestRetrySyncDecorator:
    """Tests for @retry_sync_decorator."""

    def test_sync_decorator(self):
        """Should work with sync functions."""
        call_count = 0

        @retry_sync_decorator(max_retries=2, base_delay=0.01, jitter=0.0)
        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("retry")
            return "success"

        result = eventually_succeeds()
        assert result == "success"
        assert call_count == 2


class TestRetryContext:
    """Tests for RetryContext context manager."""

    @pytest.mark.asyncio
    async def test_async_retry_context_success(self):
        """Should support manual retry loop with success."""
        call_count = 0

        async with RetryContext(config=RetryConfig(max_retries=3)) as ctx:
            while ctx.should_continue():
                try:
                    call_count += 1
                    if call_count < 3:
                        raise ValueError("retry")
                    ctx.mark_success()
                    break
                except Exception as e:
                    await ctx.handle_exception(e)

        assert ctx.stats.success is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_context_exhausted(self):
        """Should raise RetryExhausted when retries exhausted."""
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=0.0)

        with pytest.raises(RetryExhausted):
            async with RetryContext(config=config) as ctx:
                while ctx.should_continue():
                    try:
                        raise ValueError("always fails")
                    except Exception as e:
                        await ctx.handle_exception(e)

    def test_sync_retry_context(self):
        """Should support sync retry context."""
        call_count = 0
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=0.0)

        with RetryContext(config=config) as ctx:
            while ctx.should_continue():
                try:
                    call_count += 1
                    if call_count < 2:
                        raise ValueError("retry")
                    ctx.mark_success()
                    break
                except Exception as e:
                    ctx.handle_exception_sync(e)

        assert ctx.stats.success is True


class TestPreConfiguredRetryConfigs:
    """Tests for pre-configured retry configurations."""

    def test_mpc_retry_config(self):
        """MPC config should have appropriate settings."""
        assert MPC_RETRY_CONFIG.max_retries > 0
        assert MPC_RETRY_CONFIG.base_delay > 0
        assert MPC_RETRY_CONFIG.jitter >= 0

    def test_rpc_retry_config(self):
        """RPC config should have appropriate settings."""
        assert RPC_RETRY_CONFIG.max_retries > 0
        assert RPC_RETRY_CONFIG.base_delay > 0

    def test_db_retry_config(self):
        """DB config should have appropriate settings."""
        assert DB_RETRY_CONFIG.max_retries > 0
        assert DB_RETRY_CONFIG.base_delay > 0

    def test_webhook_retry_config(self):
        """Webhook config should have appropriate settings."""
        assert WEBHOOK_RETRY_CONFIG.max_retries > 0
        assert WEBHOOK_RETRY_CONFIG.base_delay >= 1.0  # At least 1 second


class TestRetryIntegration:
    """Integration tests for retry functionality."""

    @pytest.mark.asyncio
    async def test_retry_with_varying_exceptions(self):
        """Should handle different exception types."""
        exceptions_raised = []

        async def raises_different_exceptions():
            if len(exceptions_raised) == 0:
                exceptions_raised.append("ValueError")
                raise ValueError("first")
            elif len(exceptions_raised) == 1:
                exceptions_raised.append("RuntimeError")
                raise RuntimeError("second")
            return "success"

        config = RetryConfig(
            max_retries=5,
            base_delay=0.01,
            jitter=0.0,
            retryable_exceptions=(ValueError, RuntimeError),
        )

        result = await retry_async(raises_different_exceptions, config=config)

        assert result == "success"
        assert len(exceptions_raised) == 2

    @pytest.mark.asyncio
    async def test_retry_total_delay_tracking(self):
        """Should track total delay across retries."""
        async def always_fails():
            raise ValueError("fail")

        config = RetryConfig(
            max_retries=3,
            base_delay=0.05,
            exponential_base=1.0,  # No exponential growth
            jitter=0.0,
        )

        try:
            await retry_async(always_fails, config=config)
        except RetryExhausted as e:
            # Should have accumulated ~0.15s total delay (3 retries * 0.05s)
            assert e.stats.total_delay >= 0.14
            assert e.stats.total_delay <= 0.20

    @pytest.mark.asyncio
    async def test_retry_with_arguments_to_function(self):
        """Should pass arguments to retried function."""
        call_args = []

        async def func_with_args(x, y, z=None):
            call_args.append((x, y, z))
            if len(call_args) < 2:
                raise ValueError("retry")
            return x + y

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=0.0)
        result = await retry_async(func_with_args, 1, 2, z=3, config=config)

        assert result == 3
        assert all(args == (1, 2, 3) for args in call_args)

    @pytest.mark.asyncio
    async def test_zero_retries(self):
        """Should work with zero retries (single attempt)."""
        async def fails_once():
            raise ValueError("fail")

        config = RetryConfig(max_retries=0)

        with pytest.raises(RetryExhausted) as exc_info:
            await retry_async(fails_once, config=config)

        assert exc_info.value.stats.attempts == 1


class TestRetryEdgeCases:
    """Edge case tests for retry functionality."""

    @pytest.mark.asyncio
    async def test_retry_with_async_generator_function(self):
        """Should handle functions that return coroutines."""
        async def async_func():
            return await asyncio.sleep(0.001) or "done"

        result = await retry_async(async_func, config=RetryConfig(max_retries=1))
        assert result == "done"

    def test_retry_config_immutable(self):
        """RetryConfig should be immutable (frozen dataclass)."""
        config = RetryConfig()

        with pytest.raises(Exception):  # FrozenInstanceError
            config.max_retries = 10

    @pytest.mark.asyncio
    async def test_retry_handles_base_exception(self):
        """Should handle BaseException subclasses."""
        async def raises_base_exception():
            raise SystemExit(1)

        config = RetryConfig(
            max_retries=1,
            retryable_exceptions=(BaseException,),
        )

        # SystemExit is a BaseException
        with pytest.raises(RetryExhausted):
            await retry_async(raises_base_exception, config=config)

    def test_negative_delay_prevented(self):
        """Calculate delay should never return negative."""
        config = RetryConfig(
            base_delay=0.1,
            jitter=0.9,  # High jitter could theoretically go negative
        )

        # Test many times due to randomness
        for attempt in range(100):
            delay = config.calculate_delay(attempt)
            assert delay >= 0
