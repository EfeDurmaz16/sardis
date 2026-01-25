"""
Circuit breaker pattern implementation for external service resilience.

Prevents cascading failures by temporarily blocking calls to failing services.

This module provides:
- CircuitBreaker: Main circuit breaker class for protecting service calls
- CircuitBreakerConfig: Configuration for circuit breaker behavior
- CircuitBreakerRegistry: Global registry for managing circuit breakers
- Pre-configured circuit breakers for common Sardis services

Usage:
    from sardis_v2_core.circuit_breaker import (
        CircuitBreaker,
        CircuitBreakerConfig,
        get_circuit_breaker,
    )

    # Create a circuit breaker
    breaker = CircuitBreaker("my_service")

    # Use as context manager
    async with breaker:
        await make_external_call()

    # Or use as decorator
    @breaker.decorate
    async def make_call():
        ...

    # Or use the global registry
    breaker = get_circuit_breaker("my_service")
"""
from __future__ import annotations

import asyncio
import functools
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Optional,
    ParamSpec,
    Sequence,
    Type,
    TypeVar,
    Union,
)

from .constants import CircuitBreakerDefaults, ErrorCodes

logger = logging.getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker.

    Attributes:
        failure_threshold: Number of failures before opening the circuit.
            Default: 5 (from CircuitBreakerDefaults.FAILURE_THRESHOLD)
        recovery_timeout: Time to wait before attempting recovery in seconds.
            Default: 30.0 (from CircuitBreakerDefaults.RECOVERY_TIMEOUT)
        success_threshold: Number of successful calls in half-open state
            required to close the circuit. Default: 2
        failure_window: Time window for counting failures in seconds.
            Default: 60.0
        fallback: Optional async function to call when circuit is open.
            Should have signature: async def fallback(*args, **kwargs) -> T
        count_timeout_as_failure: Whether timeout exceptions count as failures.
        excluded_exceptions: Exception types that should not count as failures.
        included_exceptions: If set, only these exception types count as failures.
        on_state_change: Optional callback when circuit state changes.
            Signature: (old_state, new_state, breaker_name) -> None
    """

    # Number of failures before opening the circuit
    failure_threshold: int = CircuitBreakerDefaults.FAILURE_THRESHOLD

    # Time to wait before attempting recovery (seconds)
    recovery_timeout: float = CircuitBreakerDefaults.RECOVERY_TIMEOUT

    # Number of successful calls in half-open state to close circuit
    success_threshold: int = CircuitBreakerDefaults.SUCCESS_THRESHOLD

    # Time window for counting failures (seconds)
    failure_window: float = CircuitBreakerDefaults.FAILURE_WINDOW

    # Optional fallback function
    fallback: Optional[Callable[..., Awaitable[Any]]] = None

    # Whether to count timeouts as failures
    count_timeout_as_failure: bool = True

    # Exception types that should NOT count as failures
    excluded_exceptions: tuple[Type[BaseException], ...] = ()

    # If set, ONLY these exception types count as failures
    included_exceptions: Optional[tuple[Type[BaseException], ...]] = None

    # Callback when state changes
    on_state_change: Optional[
        Callable[[CircuitState, CircuitState, str], None]
    ] = None

    def should_count_as_failure(self, exception: BaseException) -> bool:
        """Determine if an exception should count as a failure.

        Args:
            exception: The exception that was raised

        Returns:
            True if the exception should count as a circuit failure
        """
        # Check excluded exceptions first
        if isinstance(exception, self.excluded_exceptions):
            return False

        # If included_exceptions is set, only count those
        if self.included_exceptions is not None:
            return isinstance(exception, self.included_exceptions)

        # By default, all exceptions count as failures
        return True


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0
    current_state: CircuitState = CircuitState.CLOSED
    consecutive_successes: int = 0
    consecutive_failures: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open.

    This exception is raised when a call is attempted while the
    circuit breaker is in the OPEN state.

    Attributes:
        service_name: Name of the service protected by the circuit breaker
        recovery_time: Estimated time until circuit attempts recovery
        error_code: Standardized error code for API responses
    """

    def __init__(self, service_name: str, recovery_time: float) -> None:
        self.service_name = service_name
        self.recovery_time = recovery_time
        self.error_code = ErrorCodes.CIRCUIT_BREAKER_OPEN
        super().__init__(
            f"Circuit breaker open for {service_name}. "
            f"Recovery in {recovery_time:.1f}s"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "error": self.error_code,
            "message": str(self),
            "details": {
                "service": self.service_name,
                "recovery_seconds": self.recovery_time,
            },
        }


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    Usage:
        breaker = CircuitBreaker("payment_service")
        
        async with breaker:
            await make_external_call()
        
        # Or with decorator
        @breaker.decorate
        async def make_call():
            ...
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_times: list = []
        self._last_failure_time: Optional[float] = None
        self._last_state_change: float = time.time()
        self._half_open_successes: int = 0
        self._stats = CircuitStats()
        self._lock = asyncio.Lock()
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN
    
    @property
    def stats(self) -> CircuitStats:
        return self._stats
    
    async def __aenter__(self):
        """Context manager entry - check if call is allowed."""
        await self._before_call()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - record result."""
        if exc_type is None:
            await self._on_success()
        else:
            await self._on_failure(exc_val)
        return False  # Don't suppress exceptions
    
    async def _before_call(self) -> None:
        """Check if the call should be allowed."""
        async with self._lock:
            self._stats.total_calls += 1
            
            if self._state == CircuitState.CLOSED:
                return  # Always allow
            
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                elapsed = time.time() - self._last_state_change
                if elapsed >= self._config.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
                    logger.info(f"Circuit breaker {self._name} transitioning to half-open")
                else:
                    self._stats.rejected_calls += 1
                    remaining = self._config.recovery_timeout - elapsed
                    raise CircuitBreakerError(self._name, remaining)
            
            # Half-open state allows the call through for testing
    
    async def _on_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._stats.successful_calls += 1
            self._stats.last_success_time = time.time()
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self._config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
                    logger.info(f"Circuit breaker {self._name} closed after recovery")
    
    async def _on_failure(self, error: Exception) -> None:
        """Record a failed call."""
        async with self._lock:
            now = time.time()
            
            self._stats.failed_calls += 1
            self._stats.last_failure_time = now
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._failure_times.append(now)
            self._last_failure_time = now
            
            # Clean up old failures outside the window
            window_start = now - self._config.failure_window
            self._failure_times = [t for t in self._failure_times if t >= window_start]
            
            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open state reopens the circuit
                self._transition_to(CircuitState.OPEN)
                self._half_open_successes = 0
                logger.warning(f"Circuit breaker {self._name} reopened after failure in half-open")
            
            elif self._state == CircuitState.CLOSED:
                # Check if we've hit the failure threshold
                if len(self._failure_times) >= self._config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
                    logger.warning(
                        f"Circuit breaker {self._name} opened after "
                        f"{len(self._failure_times)} failures"
                    )
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()
        self._stats.state_changes += 1
        self._stats.current_state = new_state
        
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_successes = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_times.clear()
    
    def decorate(
        self,
        func: Callable[P, Awaitable[T]],
    ) -> Callable[P, Awaitable[T]]:
        """Decorator to wrap an async function with circuit breaker.

        Usage:
            @breaker.decorate
            async def make_api_call():
                ...

        Args:
            func: The async function to wrap

        Returns:
            Wrapped function with circuit breaker protection
        """

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async with self:
                return await func(*args, **kwargs)

        return wrapper
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with circuit breaker protection."""
        async with self:
            return await func(*args, **kwargs)
    
    async def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        async with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._failure_times.clear()
            self._half_open_successes = 0
            logger.info(f"Circuit breaker {self._name} manually reset")
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get detailed state information."""
        now = time.time()
        
        info = {
            "name": self._name,
            "state": self._state.value,
            "stats": {
                "total_calls": self._stats.total_calls,
                "successful_calls": self._stats.successful_calls,
                "failed_calls": self._stats.failed_calls,
                "rejected_calls": self._stats.rejected_calls,
                "consecutive_failures": self._stats.consecutive_failures,
            },
            "config": {
                "failure_threshold": self._config.failure_threshold,
                "recovery_timeout": self._config.recovery_timeout,
                "success_threshold": self._config.success_threshold,
            },
        }
        
        if self._state == CircuitState.OPEN:
            elapsed = now - self._last_state_change
            remaining = max(0, self._config.recovery_timeout - elapsed)
            info["recovery_remaining_seconds"] = remaining
        
        return info


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    
    Provides a central place to create, access, and monitor circuit breakers.
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get an existing circuit breaker or create a new one."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config or self._default_config)
        return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self._breakers.get(name)
    
    def set_default_config(self, config: CircuitBreakerConfig) -> None:
        """Set default configuration for new circuit breakers."""
        self._default_config = config
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get state information for all circuit breakers."""
        return {
            name: breaker.get_state_info()
            for name, breaker in self._breakers.items()
        }
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()
    
    def remove(self, name: str) -> bool:
        """Remove a circuit breaker."""
        if name in self._breakers:
            del self._breakers[name]
            return True
        return False


# Global registry instance
_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> CircuitBreaker:
    """Get or create a circuit breaker from the global registry."""
    return get_circuit_breaker_registry().get_or_create(name, config)


# Pre-configured circuit breakers for common services
def create_service_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Create circuit breakers for standard Sardis services.

    Creates and registers circuit breakers with service-specific
    configurations from constants. These breakers protect external
    service calls from cascading failures.

    Returns:
        Dictionary mapping service names to their circuit breakers

    Services configured:
        - turnkey: MPC signing service (slower recovery, sensitive)
        - persona_kyc: KYC verification service
        - elliptic_sanctions: Sanctions screening service
        - lithic_cards: Card provider service
        - rpc_provider: Blockchain RPC endpoints (fast recovery)
    """
    registry = get_circuit_breaker_registry()

    services = {
        "turnkey": CircuitBreakerConfig(
            failure_threshold=CircuitBreakerDefaults.TURNKEY_FAILURE_THRESHOLD,
            recovery_timeout=CircuitBreakerDefaults.TURNKEY_RECOVERY_TIMEOUT,
            success_threshold=2,
        ),
        "persona_kyc": CircuitBreakerConfig(
            failure_threshold=CircuitBreakerDefaults.PERSONA_FAILURE_THRESHOLD,
            recovery_timeout=CircuitBreakerDefaults.PERSONA_RECOVERY_TIMEOUT,
            success_threshold=2,
        ),
        "elliptic_sanctions": CircuitBreakerConfig(
            failure_threshold=CircuitBreakerDefaults.ELLIPTIC_FAILURE_THRESHOLD,
            recovery_timeout=CircuitBreakerDefaults.ELLIPTIC_RECOVERY_TIMEOUT,
            success_threshold=2,
        ),
        "lithic_cards": CircuitBreakerConfig(
            failure_threshold=CircuitBreakerDefaults.LITHIC_FAILURE_THRESHOLD,
            recovery_timeout=CircuitBreakerDefaults.LITHIC_RECOVERY_TIMEOUT,
            success_threshold=3,
        ),
        "rpc_provider": CircuitBreakerConfig(
            failure_threshold=CircuitBreakerDefaults.RPC_FAILURE_THRESHOLD,
            recovery_timeout=CircuitBreakerDefaults.RPC_RECOVERY_TIMEOUT,
            success_threshold=1,
        ),
    }

    return {
        name: registry.get_or_create(name, config)
        for name, config in services.items()
    }


# =============================================================================
# Convenience decorator
# =============================================================================

def circuit_breaker(
    name: str,
    *,
    failure_threshold: int = CircuitBreakerDefaults.FAILURE_THRESHOLD,
    recovery_timeout: float = CircuitBreakerDefaults.RECOVERY_TIMEOUT,
    success_threshold: int = CircuitBreakerDefaults.SUCCESS_THRESHOLD,
    fallback: Optional[Callable[..., Awaitable[Any]]] = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator to protect an async function with a circuit breaker.

    Usage:
        @circuit_breaker("my_service")
        async def call_external_api():
            ...

        @circuit_breaker(
            "payment_service",
            failure_threshold=3,
            fallback=fallback_handler,
        )
        async def process_payment():
            ...

    Args:
        name: Name for the circuit breaker (used in registry)
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds before attempting recovery
        success_threshold: Successes needed in half-open to close
        fallback: Async function to call when circuit is open

    Returns:
        Decorator function
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            fallback=fallback,
        )
        breaker = get_circuit_breaker(name, config)

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                async with breaker:
                    return await func(*args, **kwargs)
            except CircuitBreakerError:
                if fallback is not None:
                    return await fallback(*args, **kwargs)
                raise

        return wrapper

    return decorator


__all__ = [
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitStats",
    "CircuitBreakerError",
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "get_circuit_breaker_registry",
    "get_circuit_breaker",
    "create_service_circuit_breakers",
    "circuit_breaker",
]






