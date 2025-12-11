"""
Circuit breaker pattern implementation for external service resilience.

Prevents cascading failures by temporarily blocking calls to failing services.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    # Number of failures before opening the circuit
    failure_threshold: int = 5
    
    # Time to wait before attempting recovery (seconds)
    recovery_timeout: float = 30.0
    
    # Number of successful calls in half-open state to close circuit
    success_threshold: int = 2
    
    # Time window for counting failures (seconds)
    failure_window: float = 60.0
    
    # Optional fallback function
    fallback: Optional[Callable[..., Any]] = None
    
    # Whether to count timeouts as failures
    count_timeout_as_failure: bool = True


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
    """Raised when circuit breaker is open."""
    
    def __init__(self, service_name: str, recovery_time: float):
        self.service_name = service_name
        self.recovery_time = recovery_time
        super().__init__(
            f"Circuit breaker open for {service_name}. "
            f"Recovery in {recovery_time:.1f}s"
        )


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
    
    def decorate(self, func: Callable) -> Callable:
        """Decorator to wrap a function with circuit breaker."""
        async def wrapper(*args, **kwargs):
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
    """Create circuit breakers for standard Sardis services."""
    registry = get_circuit_breaker_registry()
    
    services = {
        "turnkey": CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60.0,
            success_threshold=2,
        ),
        "persona_kyc": CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=30.0,
            success_threshold=2,
        ),
        "elliptic_sanctions": CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=30.0,
            success_threshold=2,
        ),
        "lithic_cards": CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=45.0,
            success_threshold=3,
        ),
        "rpc_provider": CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=15.0,
            success_threshold=1,
        ),
    }
    
    return {
        name: registry.get_or_create(name, config)
        for name, config in services.items()
    }



