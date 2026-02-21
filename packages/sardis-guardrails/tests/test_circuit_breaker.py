"""Unit tests for circuit breaker pattern."""

import asyncio
import pytest
import time
from sardis_guardrails.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
)


class TestCircuitBreaker:
    """Test circuit breaker state transitions and protection."""

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker(agent_id="agent-123")
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_closed_to_open_after_threshold_failures(self):
        """Test CLOSED -> OPEN transition after failures exceed threshold."""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout=60.0)
        breaker = CircuitBreaker(agent_id="agent-123", config=config)

        async def failing_func():
            raise ValueError("Simulated failure")

        # Trigger failures up to threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Circuit should now be OPEN
        assert breaker.state == CircuitState.OPEN

        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker.call(failing_func)

        assert "Circuit breaker open" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self):
        """Test OPEN -> HALF_OPEN transition after reset timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            reset_timeout=0.1,  # Short timeout for testing
        )
        breaker = CircuitBreaker(agent_id="agent-123", config=config)

        async def failing_func():
            raise ValueError("Failure")

        # Trip the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.2)

        # Next call should transition to HALF_OPEN (before executing function)
        # Use a successful function to avoid re-opening
        async def success_func():
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"
        # State should be HALF_OPEN or CLOSED depending on success threshold

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self):
        """Test HALF_OPEN -> CLOSED transition on successful calls."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            reset_timeout=0.1,
            success_threshold=2,
        )
        breaker = CircuitBreaker(agent_id="agent-123", config=config)

        async def failing_func():
            raise ValueError("Failure")

        async def success_func():
            return "success"

        # Trip the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for reset timeout
        await asyncio.sleep(0.2)

        # Make successful calls to reach success threshold
        await breaker.call(success_func)
        await breaker.call(success_func)

        # Should be back to CLOSED
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self):
        """Test HALF_OPEN -> OPEN transition on any failure."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            reset_timeout=0.1,
        )
        breaker = CircuitBreaker(agent_id="agent-123", config=config)

        async def failing_func():
            raise ValueError("Failure")

        # Trip the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for reset timeout
        await asyncio.sleep(0.2)

        # Any failure in half-open should immediately trip circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_decorator_pattern(self):
        """Test circuit breaker decorator pattern."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(agent_id="agent-123", config=config)

        @breaker.protected
        async def protected_func(value: int) -> int:
            if value < 0:
                raise ValueError("Negative value")
            return value * 2

        # Successful calls
        result = await protected_func(5)
        assert result == 10

        # Trigger failures
        for _ in range(2):
            with pytest.raises(ValueError):
                await protected_func(-1)

        # Circuit should be open
        assert breaker.state == CircuitState.OPEN

        # Next call should be blocked
        with pytest.raises(CircuitBreakerError):
            await protected_func(5)

    @pytest.mark.asyncio
    async def test_success_resets_failure_count_in_closed_state(self):
        """Test that successful calls reset failure count in CLOSED state."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(agent_id="agent-123", config=config)

        async def failing_func():
            raise ValueError("Failure")

        async def success_func():
            return "success"

        # Partial failures
        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        # Success should reset count
        await breaker.call(success_func)

        stats = await breaker.get_stats()
        assert stats.failure_count == 0

        # Should still be in CLOSED state
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_manual_reset(self):
        """Test manual circuit breaker reset."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(agent_id="agent-123", config=config)

        async def failing_func():
            raise ValueError("Failure")

        # Trip the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Manual reset
        await breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        stats = await breaker.get_stats()
        assert stats.failure_count == 0

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test statistics retrieval."""
        breaker = CircuitBreaker(agent_id="agent-123")

        async def success_func():
            return "ok"

        await breaker.call(success_func)

        stats = await breaker.get_stats()
        assert stats.state == CircuitState.CLOSED
        assert stats.total_calls == 1
        assert stats.total_failures == 0

    @pytest.mark.asyncio
    async def test_non_async_function(self):
        """Test circuit breaker with non-async functions."""
        breaker = CircuitBreaker(agent_id="agent-123")

        def sync_func(x: int) -> int:
            if x < 0:
                raise ValueError("Negative")
            return x * 2

        result = await breaker.call(sync_func, 5)
        assert result == 10

        with pytest.raises(ValueError):
            await breaker.call(sync_func, -1)

    @pytest.mark.asyncio
    async def test_half_open_max_calls_limit(self):
        """Test HALF_OPEN state enforces max calls limit."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            reset_timeout=0.1,
            half_open_max_calls=2,
            success_threshold=3,  # More than max calls
        )
        breaker = CircuitBreaker(agent_id="agent-123", config=config)

        async def failing_func():
            raise ValueError("Failure")

        async def success_func():
            return "ok"

        # Trip circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.2)

        # First call transitions to HALF_OPEN
        await breaker.call(success_func)

        # Second call in HALF_OPEN
        await breaker.call(success_func)

        # Third call should exceed max_calls
        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker.call(success_func)

        assert "Max test calls exceeded" in str(exc_info.value)
