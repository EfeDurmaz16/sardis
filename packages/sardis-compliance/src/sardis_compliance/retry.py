"""
Comprehensive retry logic for external API calls.

Provides production-grade retry mechanisms with:
- Exponential backoff with jitter
- Circuit breaker pattern
- Rate limiting
- Request deduplication
- Detailed logging and metrics
"""
from __future__ import annotations

import asyncio
import functools
import hashlib
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, Set, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class RetryStrategy(str, Enum):
    """Retry backoff strategies."""
    FIXED = "fixed"  # Fixed delay between retries
    LINEAR = "linear"  # Linear increase in delay
    EXPONENTIAL = "exponential"  # Exponential increase with jitter
    FIBONACCI = "fibonacci"  # Fibonacci sequence delays


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter_factor: float = 0.1  # Random jitter as fraction of delay
    backoff_multiplier: float = 2.0  # For exponential backoff
    retryable_exceptions: tuple = (Exception,)  # Which exceptions to retry
    retryable_status_codes: Set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})
    timeout_seconds: float = 30.0  # Per-request timeout


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes to close from half-open
    timeout_seconds: float = 60.0  # Time before trying again after open
    half_open_max_calls: int = 3  # Max calls in half-open state


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    wait_for_token: bool = True  # Wait if no tokens available


@dataclass
class RetryResult(Generic[T]):
    """Result of a retried operation."""
    success: bool
    value: Optional[T] = None
    error: Optional[Exception] = None
    attempts: int = 0
    total_time_seconds: float = 0.0
    final_delay_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "error": str(self.error) if self.error else None,
            "attempts": self.attempts,
            "total_time_seconds": self.total_time_seconds,
            "final_delay_seconds": self.final_delay_seconds,
        }


class RetryDelayCalculator:
    """Calculates retry delays based on strategy."""

    def __init__(self, config: RetryConfig):
        self._config = config
        self._fibonacci_cache = [0, 1]

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number."""
        if self._config.strategy == RetryStrategy.FIXED:
            base_delay = self._config.initial_delay_seconds

        elif self._config.strategy == RetryStrategy.LINEAR:
            base_delay = self._config.initial_delay_seconds * (attempt + 1)

        elif self._config.strategy == RetryStrategy.EXPONENTIAL:
            base_delay = self._config.initial_delay_seconds * (
                self._config.backoff_multiplier ** attempt
            )

        elif self._config.strategy == RetryStrategy.FIBONACCI:
            base_delay = self._config.initial_delay_seconds * self._fibonacci(attempt)

        else:
            base_delay = self._config.initial_delay_seconds

        # Apply jitter
        jitter = base_delay * self._config.jitter_factor * random.uniform(-1, 1)
        delay = base_delay + jitter

        # Cap at max delay
        return min(delay, self._config.max_delay_seconds)

    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number with caching."""
        while len(self._fibonacci_cache) <= n:
            self._fibonacci_cache.append(
                self._fibonacci_cache[-1] + self._fibonacci_cache[-2]
            )
        return self._fibonacci_cache[n]


class CircuitBreaker:
    """
    Circuit breaker implementation.

    Prevents cascading failures by opening the circuit after
    repeated failures, allowing time for recovery.
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            self._check_state_transition()
            return self._state

    @property
    def is_available(self) -> bool:
        """Check if circuit allows requests."""
        state = self.state
        return state != CircuitState.OPEN

    def _check_state_transition(self) -> None:
        """Check and perform state transitions."""
        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
                if elapsed >= self._config.timeout_seconds:
                    logger.info(f"Circuit breaker {self._name}: OPEN -> HALF_OPEN")
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._config.success_threshold:
                    logger.info(f"Circuit breaker {self._name}: HALF_OPEN -> CLOSED")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now(timezone.utc)

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker {self._name}: HALF_OPEN -> OPEN (failure during recovery)")
                self._state = CircuitState.OPEN
                self._half_open_calls = 0

            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self._config.failure_threshold:
                    logger.warning(
                        f"Circuit breaker {self._name}: CLOSED -> OPEN "
                        f"(threshold {self._config.failure_threshold} reached)"
                    )
                    self._state = CircuitState.OPEN

    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                return False

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self._config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self._name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None,
        }


class RateLimiter:
    """
    Token bucket rate limiter.

    Controls request rate to prevent overwhelming external services.
    """

    def __init__(
        self,
        name: str,
        config: Optional[RateLimitConfig] = None,
    ):
        self._name = name
        self._config = config or RateLimitConfig()
        self._tokens = float(self._config.burst_size)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * self._config.requests_per_second
        self._tokens = min(self._config.burst_size, self._tokens + new_tokens)
        self._last_refill = now

    def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True

            return False

    async def acquire_async(self, tokens: int = 1) -> bool:
        """
        Asynchronously acquire tokens, waiting if configured.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired
        """
        while True:
            if self.acquire(tokens):
                return True

            if not self._config.wait_for_token:
                return False

            # Wait for tokens to refill
            wait_time = tokens / self._config.requests_per_second
            await asyncio.sleep(wait_time)

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        with self._lock:
            self._refill()
            return {
                "name": self._name,
                "available_tokens": self._tokens,
                "burst_size": self._config.burst_size,
                "requests_per_second": self._config.requests_per_second,
            }


class RequestDeduplicator:
    """
    Prevents duplicate concurrent requests.

    When multiple identical requests are made concurrently,
    only one actually executes and others wait for its result.
    """

    def __init__(self, ttl_seconds: float = 60.0):
        self._ttl_seconds = ttl_seconds
        self._pending: Dict[str, asyncio.Future] = {}
        self._results: Dict[str, tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()

    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Create a unique key for a request."""
        data = f"{func_name}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(data.encode()).hexdigest()

    async def dedupe(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute function with deduplication.

        If an identical request is already in progress, wait for its result.
        """
        key = self._make_key(func.__name__, args, kwargs)

        async with self._lock:
            # Check for cached result
            if key in self._results:
                result, cached_at = self._results[key]
                age = (datetime.now(timezone.utc) - cached_at).total_seconds()
                if age < self._ttl_seconds:
                    logger.debug(f"Request dedupe: returning cached result for {func.__name__}")
                    return result

            # Check for pending request
            if key in self._pending:
                logger.debug(f"Request dedupe: waiting for pending request {func.__name__}")
                return await self._pending[key]

            # Create new pending future
            future = asyncio.get_event_loop().create_future()
            self._pending[key] = future

        try:
            # Execute the request
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Cache result
            async with self._lock:
                self._results[key] = (result, datetime.now(timezone.utc))
                future.set_result(result)
                del self._pending[key]

            return result

        except Exception as e:
            async with self._lock:
                future.set_exception(e)
                del self._pending[key]
            raise


class RetryableClient:
    """
    A wrapper that adds retry, circuit breaker, and rate limiting to async operations.

    Usage:
        client = RetryableClient("my_service")

        @client.with_retry
        async def fetch_data(url: str):
            async with httpx.AsyncClient() as http:
                return await http.get(url)
    """

    def __init__(
        self,
        name: str,
        retry_config: Optional[RetryConfig] = None,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        rate_config: Optional[RateLimitConfig] = None,
        enable_dedup: bool = True,
    ):
        """
        Initialize retryable client.

        Args:
            name: Service name for logging and metrics
            retry_config: Retry configuration
            circuit_config: Circuit breaker configuration
            rate_config: Rate limiter configuration
            enable_dedup: Enable request deduplication
        """
        self._name = name
        self._retry_config = retry_config or RetryConfig()
        self._delay_calculator = RetryDelayCalculator(self._retry_config)
        self._circuit_breaker = CircuitBreaker(name, circuit_config)
        self._rate_limiter = RateLimiter(name, rate_config)
        self._deduplicator = RequestDeduplicator() if enable_dedup else None

        # Metrics
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._retried_requests = 0

    async def execute(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs,
    ) -> RetryResult:
        """
        Execute function with retry, circuit breaker, and rate limiting.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            RetryResult with operation outcome
        """
        start_time = time.monotonic()
        self._total_requests += 1

        # Check circuit breaker
        if not self._circuit_breaker.allow_request():
            logger.warning(f"Circuit breaker open for {self._name}")
            return RetryResult(
                success=False,
                error=Exception("Circuit breaker open"),
                attempts=0,
            )

        # Rate limiting
        if not await self._rate_limiter.acquire_async():
            logger.warning(f"Rate limit exceeded for {self._name}")
            return RetryResult(
                success=False,
                error=Exception("Rate limit exceeded"),
                attempts=0,
            )

        # Deduplication
        if self._deduplicator:
            try:
                result = await self._deduplicator.dedupe(
                    self._execute_with_retry, func, *args, **kwargs
                )
                return result
            except Exception as e:
                return RetryResult(
                    success=False,
                    error=e,
                    attempts=1,
                    total_time_seconds=time.monotonic() - start_time,
                )

        return await self._execute_with_retry(func, *args, **kwargs)

    async def _execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs,
    ) -> RetryResult:
        """Execute with retry logic."""
        start_time = time.monotonic()
        last_exception = None
        last_delay = 0.0

        for attempt in range(self._retry_config.max_retries + 1):
            try:
                # Execute with timeout
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self._retry_config.timeout_seconds,
                    )
                else:
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, functools.partial(func, *args, **kwargs)),
                        timeout=self._retry_config.timeout_seconds,
                    )

                # Success
                self._circuit_breaker.record_success()
                self._successful_requests += 1

                return RetryResult(
                    success=True,
                    value=result,
                    attempts=attempt + 1,
                    total_time_seconds=time.monotonic() - start_time,
                    final_delay_seconds=last_delay,
                )

            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(
                    f"{self._name}: Request timeout (attempt {attempt + 1}/{self._retry_config.max_retries + 1})"
                )

            except self._retry_config.retryable_exceptions as e:
                last_exception = e
                logger.warning(
                    f"{self._name}: Retryable error (attempt {attempt + 1}): {e}"
                )

            except Exception as e:
                # Non-retryable exception
                self._circuit_breaker.record_failure()
                self._failed_requests += 1
                return RetryResult(
                    success=False,
                    error=e,
                    attempts=attempt + 1,
                    total_time_seconds=time.monotonic() - start_time,
                )

            # Calculate delay and wait before retry
            if attempt < self._retry_config.max_retries:
                last_delay = self._delay_calculator.calculate_delay(attempt)
                self._retried_requests += 1
                logger.info(f"{self._name}: Retrying in {last_delay:.2f}s")
                await asyncio.sleep(last_delay)

        # All retries exhausted
        self._circuit_breaker.record_failure()
        self._failed_requests += 1

        return RetryResult(
            success=False,
            error=last_exception,
            attempts=self._retry_config.max_retries + 1,
            total_time_seconds=time.monotonic() - start_time,
            final_delay_seconds=last_delay,
        )

    def with_retry(self, func: Callable) -> Callable:
        """
        Decorator to add retry behavior to a function.

        Usage:
            @client.with_retry
            async def my_function():
                ...
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await self.execute(func, *args, **kwargs)
            if result.success:
                return result.value
            raise result.error

        return wrapper

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "name": self._name,
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "failed_requests": self._failed_requests,
            "retried_requests": self._retried_requests,
            "success_rate": (
                self._successful_requests / self._total_requests * 100
                if self._total_requests > 0 else 0
            ),
            "circuit_breaker": self._circuit_breaker.get_stats(),
            "rate_limiter": self._rate_limiter.get_stats(),
        }


def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator factory for adding retry to functions.

    Usage:
        @retry(max_retries=5, strategy=RetryStrategy.EXPONENTIAL)
        async def my_api_call():
            ...
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay_seconds=initial_delay,
        max_delay_seconds=max_delay,
        strategy=strategy,
        retryable_exceptions=retryable_exceptions,
    )

    delay_calculator = RetryDelayCalculator(config)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)

                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        delay = delay_calculator.calculate_delay(attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{config.max_retries} for {func.__name__}: {e}. "
                            f"Waiting {delay:.2f}s"
                        )
                        await asyncio.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


def create_retryable_client(
    name: str,
    retry_config: Optional[RetryConfig] = None,
    circuit_config: Optional[CircuitBreakerConfig] = None,
    rate_config: Optional[RateLimitConfig] = None,
) -> RetryableClient:
    """Factory function to create a RetryableClient."""
    return RetryableClient(
        name=name,
        retry_config=retry_config,
        circuit_config=circuit_config,
        rate_config=rate_config,
    )
