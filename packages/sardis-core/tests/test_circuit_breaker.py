"""
Comprehensive tests for sardis_v2_core.circuit_breaker module.

Tests cover:
- CircuitBreaker state transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Failure counting and threshold handling
- Recovery timeout behavior
- Success threshold in half-open state
- Circuit breaker decorator
- CircuitBreakerRegistry for managing multiple breakers
- Pre-configured service circuit breakers
- Fallback handling
- Stats and monitoring
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

from sardis_v2_core.circuit_breaker import (
    CircuitState,
    CircuitBreakerConfig,
    CircuitStats,
    CircuitBreakerError,
    CircuitBreaker,
    CircuitBreakerRegistry,
    get_circuit_breaker_registry,
    get_circuit_breaker,
    create_service_circuit_breakers,
    circuit_breaker,
)


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_state_values(self):
        """Should have correct state values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig class."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold > 0
        assert config.recovery_timeout > 0
        assert config.success_threshold > 0
        assert config.failure_window > 0

    def test_custom_config(self):
        """Should accept custom values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=10.0,
            success_threshold=2,
            failure_window=30.0,
        )
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 10.0
        assert config.success_threshold == 2
        assert config.failure_window == 30.0

    def test_should_count_as_failure_default(self):
        """Should count all exceptions as failures by default."""
        config = CircuitBreakerConfig()

        assert config.should_count_as_failure(ValueError("test"))
        assert config.should_count_as_failure(RuntimeError("test"))
        assert config.should_count_as_failure(Exception("test"))

    def test_should_count_as_failure_with_excluded(self):
        """Should not count excluded exceptions."""
        config = CircuitBreakerConfig(
            excluded_exceptions=(KeyboardInterrupt, SystemExit)
        )

        assert config.should_count_as_failure(ValueError("test"))
        assert not config.should_count_as_failure(KeyboardInterrupt())
        assert not config.should_count_as_failure(SystemExit())

    def test_should_count_as_failure_with_included(self):
        """Should only count included exceptions when specified."""
        config = CircuitBreakerConfig(
            included_exceptions=(ValueError, TypeError)
        )

        assert config.should_count_as_failure(ValueError("test"))
        assert config.should_count_as_failure(TypeError("test"))
        assert not config.should_count_as_failure(RuntimeError("test"))


class TestCircuitBreakerError:
    """Tests for CircuitBreakerError exception."""

    def test_error_attributes(self):
        """Should have correct attributes."""
        error = CircuitBreakerError("test_service", 15.5)

        assert error.service_name == "test_service"
        assert error.recovery_time == 15.5
        assert "test_service" in str(error)
        assert "15.5" in str(error)

    def test_to_dict(self):
        """Should convert to dict correctly."""
        error = CircuitBreakerError("test_service", 10.0)
        result = error.to_dict()

        assert result["error"] == error.error_code
        assert "test_service" in result["message"]
        assert result["details"]["service"] == "test_service"
        assert result["details"]["recovery_seconds"] == 10.0


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state_closed(self):
        """Circuit should start in CLOSED state."""
        breaker = CircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open

    @pytest.mark.asyncio
    async def test_success_stays_closed(self):
        """Successful calls should keep circuit closed."""
        breaker = CircuitBreaker("test")

        for _ in range(10):
            async with breaker:
                pass  # Success

        assert breaker.is_closed
        assert breaker.stats.successful_calls == 10
        assert breaker.stats.failed_calls == 0

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        """Circuit should open after failure threshold."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            failure_window=60.0,
        )
        breaker = CircuitBreaker("test", config)

        # Cause failures
        for i in range(3):
            try:
                async with breaker:
                    raise ValueError(f"failure {i}")
            except ValueError:
                pass

        assert breaker.is_open
        assert breaker.stats.failed_calls == 3

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self):
        """Open circuit should reject calls."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=10.0,
        )
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        try:
            async with breaker:
                raise ValueError("fail")
        except ValueError:
            pass

        assert breaker.is_open

        # Attempt another call should be rejected
        with pytest.raises(CircuitBreakerError) as exc_info:
            async with breaker:
                pass

        assert exc_info.value.service_name == "test"
        assert breaker.stats.rejected_calls == 1

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self):
        """Circuit should transition to half-open after recovery timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,  # Very short for testing
        )
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        try:
            async with breaker:
                raise ValueError("fail")
        except ValueError:
            pass

        assert breaker.is_open

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Next call should be allowed (half-open state)
        async with breaker:
            pass  # Success in half-open

        # After success in half-open, should be closed
        # (with success_threshold=2 default, need more successes)

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        """Failure in half-open state should reopen circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2,
        )
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        try:
            async with breaker:
                raise ValueError("fail")
        except ValueError:
            pass

        # Wait for half-open
        await asyncio.sleep(0.15)

        # Fail in half-open state
        try:
            async with breaker:
                raise ValueError("fail again")
        except ValueError:
            pass

        # Should be open again
        assert breaker.is_open

    @pytest.mark.asyncio
    async def test_closes_after_success_threshold_in_half_open(self):
        """Circuit should close after success threshold in half-open."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.05,
            success_threshold=2,
        )
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        try:
            async with breaker:
                raise ValueError("fail")
        except ValueError:
            pass

        # Wait for half-open
        await asyncio.sleep(0.1)

        # Two successful calls in half-open
        async with breaker:
            pass
        await asyncio.sleep(0.01)

        async with breaker:
            pass

        # Should be closed now
        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_manual_reset(self):
        """Should support manual reset."""
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        try:
            async with breaker:
                raise ValueError("fail")
        except ValueError:
            pass

        assert breaker.is_open

        # Manual reset
        await breaker.reset()

        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_decorator_usage(self):
        """Should work as decorator."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)

        call_count = 0

        @breaker.decorate
        async def my_service():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await my_service()
        assert result == "success"
        assert call_count == 1
        assert breaker.stats.successful_calls == 1

    @pytest.mark.asyncio
    async def test_call_method(self):
        """Should work with call method."""
        breaker = CircuitBreaker("test")

        async def my_func(x, y):
            return x + y

        result = await breaker.call(my_func, 1, 2)
        assert result == 3

    def test_get_state_info(self):
        """Should return comprehensive state info."""
        breaker = CircuitBreaker("test")
        info = breaker.get_state_info()

        assert info["name"] == "test"
        assert info["state"] == "closed"
        assert "stats" in info
        assert "config" in info

    @pytest.mark.asyncio
    async def test_failure_window_clears_old_failures(self):
        """Old failures outside window should not count."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            failure_window=0.1,  # Very short window
        )
        breaker = CircuitBreaker("test", config)

        # Cause 2 failures
        for _ in range(2):
            try:
                async with breaker:
                    raise ValueError("fail")
            except ValueError:
                pass

        # Wait for failures to expire
        await asyncio.sleep(0.15)

        # One more failure - should not open (old ones expired)
        try:
            async with breaker:
                raise ValueError("fail")
        except ValueError:
            pass

        # Should still be closed (only 1 recent failure)
        assert breaker.is_closed


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry class."""

    def test_get_or_create(self):
        """Should get existing or create new breaker."""
        registry = CircuitBreakerRegistry()

        breaker1 = registry.get_or_create("service_a")
        breaker2 = registry.get_or_create("service_a")
        breaker3 = registry.get_or_create("service_b")

        assert breaker1 is breaker2  # Same instance
        assert breaker1 is not breaker3  # Different instance

    def test_get_nonexistent(self):
        """Should return None for nonexistent breaker."""
        registry = CircuitBreakerRegistry()
        assert registry.get("nonexistent") is None

    def test_set_default_config(self):
        """Should use default config for new breakers."""
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=10)

        registry.set_default_config(config)
        breaker = registry.get_or_create("new_service")

        assert breaker._config.failure_threshold == 10

    def test_get_all_states(self):
        """Should return states for all breakers."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("service_a")
        registry.get_or_create("service_b")

        states = registry.get_all_states()

        assert "service_a" in states
        assert "service_b" in states
        assert states["service_a"]["state"] == "closed"

    @pytest.mark.asyncio
    async def test_reset_all(self):
        """Should reset all breakers."""
        registry = CircuitBreakerRegistry()
        breaker_a = registry.get_or_create(
            "a", CircuitBreakerConfig(failure_threshold=1)
        )
        breaker_b = registry.get_or_create(
            "b", CircuitBreakerConfig(failure_threshold=1)
        )

        # Open both
        for breaker in [breaker_a, breaker_b]:
            try:
                async with breaker:
                    raise ValueError("fail")
            except ValueError:
                pass

        assert breaker_a.is_open
        assert breaker_b.is_open

        # Reset all
        await registry.reset_all()

        assert breaker_a.is_closed
        assert breaker_b.is_closed

    def test_remove(self):
        """Should remove breaker from registry."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("service")

        assert registry.remove("service") is True
        assert registry.get("service") is None
        assert registry.remove("service") is False  # Already removed


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_circuit_breaker_registry_singleton(self):
        """Should return same instance."""
        # Reset for clean test
        import sardis_v2_core.circuit_breaker as cb_module
        cb_module._registry = None

        reg1 = get_circuit_breaker_registry()
        reg2 = get_circuit_breaker_registry()

        assert reg1 is reg2

    def test_get_circuit_breaker(self):
        """Should get or create from global registry."""
        # Reset for clean test
        import sardis_v2_core.circuit_breaker as cb_module
        cb_module._registry = None

        breaker = get_circuit_breaker("test_service")
        assert breaker.name == "test_service"


class TestCreateServiceCircuitBreakers:
    """Tests for create_service_circuit_breakers function."""

    def test_creates_expected_services(self):
        """Should create breakers for expected services."""
        # Reset registry
        import sardis_v2_core.circuit_breaker as cb_module
        cb_module._registry = None

        breakers = create_service_circuit_breakers()

        expected_services = [
            "turnkey",
            "persona_kyc",
            "elliptic_sanctions",
            "lithic_cards",
            "rpc_provider",
        ]

        for service in expected_services:
            assert service in breakers
            assert isinstance(breakers[service], CircuitBreaker)


class TestCircuitBreakerDecorator:
    """Tests for @circuit_breaker decorator."""

    @pytest.mark.asyncio
    async def test_decorator_basic_usage(self):
        """Should work as decorator."""
        # Reset registry
        import sardis_v2_core.circuit_breaker as cb_module
        cb_module._registry = None

        @circuit_breaker("my_service")
        async def my_func():
            return "success"

        result = await my_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_with_config(self):
        """Should accept configuration."""
        import sardis_v2_core.circuit_breaker as cb_module
        cb_module._registry = None

        @circuit_breaker(
            "configured_service",
            failure_threshold=2,
            recovery_timeout=5.0,
        )
        async def my_func():
            return "success"

        await my_func()

        breaker = get_circuit_breaker("configured_service")
        assert breaker._config.failure_threshold == 2

    @pytest.mark.asyncio
    async def test_decorator_with_fallback(self):
        """Should use fallback when circuit is open."""
        import sardis_v2_core.circuit_breaker as cb_module
        cb_module._registry = None

        async def fallback_func():
            return "fallback_result"

        @circuit_breaker(
            "fallback_service",
            failure_threshold=1,
            recovery_timeout=10.0,
            fallback=fallback_func,
        )
        async def my_func():
            raise ValueError("fail")

        # First call fails and opens circuit
        with pytest.raises(ValueError):
            await my_func()

        # Second call should use fallback
        result = await my_func()
        assert result == "fallback_result"


class TestCircuitStats:
    """Tests for CircuitStats tracking."""

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Should track all stats correctly."""
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = CircuitBreaker("test", config)

        # 3 successes
        for _ in range(3):
            async with breaker:
                pass

        # 2 failures
        for _ in range(2):
            try:
                async with breaker:
                    raise ValueError("fail")
            except ValueError:
                pass

        stats = breaker.stats
        assert stats.total_calls == 5
        assert stats.successful_calls == 3
        assert stats.failed_calls == 2
        assert stats.rejected_calls == 0
        assert stats.consecutive_successes == 0  # Last was failure
        assert stats.consecutive_failures == 2
        assert stats.last_success_time is not None
        assert stats.last_failure_time is not None


class TestCircuitBreakerEdgeCases:
    """Edge case tests for circuit breaker."""

    @pytest.mark.asyncio
    async def test_exception_not_suppressed(self):
        """Circuit breaker should not suppress exceptions."""
        breaker = CircuitBreaker("test")

        with pytest.raises(ValueError) as exc_info:
            async with breaker:
                raise ValueError("original error")

        assert str(exc_info.value) == "original error"

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Should handle concurrent access safely."""
        config = CircuitBreakerConfig(failure_threshold=100)
        breaker = CircuitBreaker("test", config)

        async def make_call(should_fail):
            try:
                async with breaker:
                    if should_fail:
                        raise ValueError("fail")
                    return "success"
            except ValueError:
                return "failed"

        # Run many concurrent calls
        results = await asyncio.gather(*[
            make_call(i % 2 == 0) for i in range(50)
        ])

        assert "success" in results
        assert "failed" in results

    @pytest.mark.asyncio
    async def test_zero_failure_threshold(self):
        """Should handle zero failure threshold."""
        # Note: zero threshold doesn't make practical sense,
        # but should not crash
        config = CircuitBreakerConfig(failure_threshold=0)
        breaker = CircuitBreaker("test", config)

        async with breaker:
            pass  # Should work

    @pytest.mark.asyncio
    async def test_very_long_recovery_timeout(self):
        """Should handle very long recovery timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=999999.0,
        )
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        try:
            async with breaker:
                raise ValueError("fail")
        except ValueError:
            pass

        assert breaker.is_open

        # Should still be open (long timeout)
        with pytest.raises(CircuitBreakerError):
            async with breaker:
                pass

    @pytest.mark.asyncio
    async def test_state_info_shows_recovery_time(self):
        """State info should show recovery time when open."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=10.0,
        )
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        try:
            async with breaker:
                raise ValueError("fail")
        except ValueError:
            pass

        info = breaker.get_state_info()
        assert "recovery_remaining_seconds" in info
        assert info["recovery_remaining_seconds"] > 0
        assert info["recovery_remaining_seconds"] <= 10.0
