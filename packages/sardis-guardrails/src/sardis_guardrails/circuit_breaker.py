"""Circuit breaker pattern for payment execution failures.

Automatically trips when failures exceed threshold, preventing cascading failures.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar, ParamSpec

P = ParamSpec("P")
T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    HALF_OPEN = "half_open"  # Testing if service recovered
    OPEN = "open"  # Blocking all requests


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    pass


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Number of failures before tripping
    reset_timeout: float = 60.0  # Seconds before attempting reset (OPEN → HALF_OPEN)
    half_open_max_calls: int = 3  # Max calls to test in half-open state
    success_threshold: int = 2  # Successes needed in half-open to close


@dataclass
class CircuitBreakerStats:
    """Statistics for a circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float | None = None
    last_state_change: float = field(default_factory=time.time)
    total_calls: int = 0
    total_failures: int = 0
    half_open_calls: int = 0


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.

    Tracks failures per agent and automatically trips when threshold is exceeded.
    After a timeout period, enters half-open state to test recovery.

    Example:
        breaker = CircuitBreaker(agent_id="agent-123")

        @breaker.protected
        async def make_payment(amount: Decimal) -> str:
            # Payment logic here
            return transaction_hash

        try:
            tx_hash = await make_payment(Decimal("100.00"))
        except CircuitBreakerError:
            # Circuit is open, reject request
            pass
    """

    def __init__(
        self,
        agent_id: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize circuit breaker for an agent.

        Args:
            agent_id: Unique identifier for the agent
            config: Optional configuration, uses defaults if not provided
        """
        self.agent_id = agent_id
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self.stats.state

    async def call(self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception raised by func
        """
        async with self._lock:
            self.stats.total_calls += 1

            # Check if we should attempt reset
            if self.stats.state == CircuitState.OPEN:
                if await self._should_attempt_reset():
                    await self._transition_to_half_open()
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker open for agent {self.agent_id}. "
                        f"Will retry after {self.config.reset_timeout}s timeout."
                    )

            # Check half-open call limit
            if self.stats.state == CircuitState.HALF_OPEN:
                if self.stats.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerError(
                        f"Circuit breaker half-open for agent {self.agent_id}. "
                        "Max test calls exceeded."
                    )
                self.stats.half_open_calls += 1

        # Execute function outside lock
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            async with self._lock:
                await self._on_success()

            return result

        except Exception as e:
            async with self._lock:
                await self._on_failure()
            raise

    def protected(self, func: Callable[P, T]) -> Callable[P, T]:
        """Decorator to protect a function with circuit breaker.

        Args:
            func: Function to protect

        Returns:
            Wrapped function with circuit breaker protection
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await self.call(func, *args, **kwargs)

        return wrapper

    async def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.stats.last_failure_time is None:
            return False

        time_since_failure = time.time() - self.stats.last_failure_time
        return time_since_failure >= self.config.reset_timeout

    async def _transition_to_half_open(self) -> None:
        """Transition from OPEN to HALF_OPEN state."""
        self.stats.state = CircuitState.HALF_OPEN
        self.stats.last_state_change = time.time()
        self.stats.success_count = 0
        self.stats.failure_count = 0
        self.stats.half_open_calls = 0

    async def _on_success(self) -> None:
        """Handle successful call."""
        if self.stats.state == CircuitState.HALF_OPEN:
            self.stats.success_count += 1

            # Check if we have enough successes to close
            if self.stats.success_count >= self.config.success_threshold:
                self.stats.state = CircuitState.CLOSED
                self.stats.last_state_change = time.time()
                self.stats.failure_count = 0
                self.stats.success_count = 0
                self.stats.half_open_calls = 0

        elif self.stats.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.stats.failure_count = 0

    async def _on_failure(self) -> None:
        """Handle failed call."""
        self.stats.failure_count += 1
        self.stats.total_failures += 1
        self.stats.last_failure_time = time.time()

        if self.stats.state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately trips circuit
            self.stats.state = CircuitState.OPEN
            self.stats.last_state_change = time.time()

        elif self.stats.state == CircuitState.CLOSED:
            # Check if we've exceeded failure threshold
            if self.stats.failure_count >= self.config.failure_threshold:
                self.stats.state = CircuitState.OPEN
                self.stats.last_state_change = time.time()

    async def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        async with self._lock:
            self.stats.state = CircuitState.CLOSED
            self.stats.failure_count = 0
            self.stats.success_count = 0
            self.stats.last_state_change = time.time()

    async def get_stats(self) -> CircuitBreakerStats:
        """Get current statistics.

        Returns:
            Current circuit breaker statistics
        """
        async with self._lock:
            return CircuitBreakerStats(
                state=self.stats.state,
                failure_count=self.stats.failure_count,
                success_count=self.stats.success_count,
                last_failure_time=self.stats.last_failure_time,
                last_state_change=self.stats.last_state_change,
                total_calls=self.stats.total_calls,
                total_failures=self.stats.total_failures,
            )
