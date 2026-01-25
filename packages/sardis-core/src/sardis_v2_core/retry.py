"""
Retry utilities with exponential backoff for Sardis Core.

This module provides decorators and utilities for implementing
retry logic with configurable exponential backoff, jitter,
and circuit breaker integration.

Usage:
    from sardis_v2_core.retry import retry, RetryConfig

    @retry(max_retries=3, base_delay=1.0)
    async def call_external_api():
        ...

    # Or with configuration object
    config = RetryConfig(max_retries=5, base_delay=0.5)

    @retry(config=config)
    async def another_call():
        ...
"""
from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass, field
from typing import (
    Any,
    Awaitable,
    Callable,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    ParamSpec,
    overload,
)

from .constants import RetryConfig as RetryDefaults

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (0 means no retries)
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Maximum jitter factor (0.0-1.0) added to delays
        retryable_exceptions: Tuple of exception types that trigger retries
        non_retryable_exceptions: Tuple of exception types that should not be retried
        on_retry: Optional callback called before each retry
        retry_condition: Optional function to determine if exception should be retried
    """

    max_retries: int = RetryDefaults.DEFAULT_MAX_RETRIES
    base_delay: float = RetryDefaults.DEFAULT_BASE_DELAY
    max_delay: float = RetryDefaults.DEFAULT_MAX_DELAY
    exponential_base: float = RetryDefaults.DEFAULT_EXPONENTIAL_BASE
    jitter: float = RetryDefaults.DEFAULT_JITTER
    retryable_exceptions: tuple[Type[BaseException], ...] = (Exception,)
    non_retryable_exceptions: tuple[Type[BaseException], ...] = ()
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None
    retry_condition: Optional[Callable[[BaseException], bool]] = None

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number.

        Uses exponential backoff with optional jitter.

        Args:
            attempt: The attempt number (0-based)

        Returns:
            Delay in seconds
        """
        # Calculate exponential delay
        delay = self.base_delay * (self.exponential_base ** attempt)

        # Apply maximum cap
        delay = min(delay, self.max_delay)

        # Add jitter
        if self.jitter > 0:
            jitter_range = delay * self.jitter
            delay = delay + random.uniform(-jitter_range, jitter_range)

        return max(0.0, delay)

    def should_retry(self, exception: BaseException) -> bool:
        """Determine if the exception should trigger a retry.

        Args:
            exception: The exception that was raised

        Returns:
            True if the exception should be retried
        """
        # Check non-retryable first (takes precedence)
        if isinstance(exception, self.non_retryable_exceptions):
            return False

        # Check custom retry condition
        if self.retry_condition is not None:
            return self.retry_condition(exception)

        # Check retryable exceptions
        return isinstance(exception, self.retryable_exceptions)


# Pre-configured retry configurations for common use cases
MPC_RETRY_CONFIG = RetryConfig(
    max_retries=RetryDefaults.MPC_MAX_RETRIES,
    base_delay=RetryDefaults.MPC_BASE_DELAY,
    max_delay=RetryDefaults.MPC_MAX_DELAY,
    jitter=0.1,
)

RPC_RETRY_CONFIG = RetryConfig(
    max_retries=RetryDefaults.RPC_MAX_RETRIES,
    base_delay=RetryDefaults.RPC_BASE_DELAY,
    max_delay=RetryDefaults.RPC_MAX_DELAY,
    jitter=0.2,
)

DB_RETRY_CONFIG = RetryConfig(
    max_retries=RetryDefaults.DB_MAX_RETRIES,
    base_delay=RetryDefaults.DB_BASE_DELAY,
    max_delay=RetryDefaults.DB_MAX_DELAY,
    jitter=0.1,
)

WEBHOOK_RETRY_CONFIG = RetryConfig(
    max_retries=RetryDefaults.WEBHOOK_MAX_RETRIES,
    base_delay=1.0,
    max_delay=60.0,
    jitter=0.1,
)


@dataclass
class RetryStats:
    """Statistics about retry execution.

    Attributes:
        attempts: Total number of attempts (including initial)
        total_delay: Total delay time in seconds
        success: Whether the operation eventually succeeded
        last_exception: The last exception if operation failed
    """

    attempts: int = 0
    total_delay: float = 0.0
    success: bool = False
    last_exception: Optional[BaseException] = None


class RetryExhausted(Exception):
    """Raised when all retry attempts have been exhausted.

    Attributes:
        stats: Statistics about the retry attempts
        original_exception: The last exception that was raised
    """

    def __init__(
        self,
        message: str,
        stats: RetryStats,
        original_exception: BaseException,
    ) -> None:
        super().__init__(message)
        self.stats = stats
        self.original_exception = original_exception


async def retry_async(
    func: Callable[P, Awaitable[T]],
    *args: P.args,
    config: Optional[RetryConfig] = None,
    **kwargs: P.kwargs,
) -> T:
    """Execute an async function with retry logic.

    Args:
        func: The async function to execute
        *args: Positional arguments for the function
        config: Retry configuration (uses defaults if None)
        **kwargs: Keyword arguments for the function

    Returns:
        The return value of the function

    Raises:
        RetryExhausted: If all retry attempts fail
    """
    if config is None:
        config = RetryConfig()

    stats = RetryStats()
    last_exception: Optional[BaseException] = None

    for attempt in range(config.max_retries + 1):
        stats.attempts = attempt + 1

        try:
            result = await func(*args, **kwargs)
            stats.success = True
            return result

        except BaseException as e:
            last_exception = e
            stats.last_exception = e

            # Check if we should retry
            if attempt >= config.max_retries:
                break

            if not config.should_retry(e):
                logger.debug(
                    f"Exception {type(e).__name__} is not retryable, "
                    f"raising immediately"
                )
                raise

            # Calculate delay
            delay = config.calculate_delay(attempt)
            stats.total_delay += delay

            # Log retry attempt
            logger.warning(
                f"Retry {attempt + 1}/{config.max_retries} for "
                f"{func.__name__} after {type(e).__name__}: {e}. "
                f"Waiting {delay:.2f}s"
            )

            # Call on_retry callback if provided
            if config.on_retry:
                config.on_retry(attempt + 1, e, delay)

            # Wait before retry
            await asyncio.sleep(delay)

    # All retries exhausted
    raise RetryExhausted(
        f"All {config.max_retries + 1} attempts failed for {func.__name__}",
        stats=stats,
        original_exception=last_exception,
    ) from last_exception


def retry_sync(
    func: Callable[P, T],
    *args: P.args,
    config: Optional[RetryConfig] = None,
    **kwargs: P.kwargs,
) -> T:
    """Execute a synchronous function with retry logic.

    Args:
        func: The function to execute
        *args: Positional arguments for the function
        config: Retry configuration (uses defaults if None)
        **kwargs: Keyword arguments for the function

    Returns:
        The return value of the function

    Raises:
        RetryExhausted: If all retry attempts fail
    """
    if config is None:
        config = RetryConfig()

    stats = RetryStats()
    last_exception: Optional[BaseException] = None

    for attempt in range(config.max_retries + 1):
        stats.attempts = attempt + 1

        try:
            result = func(*args, **kwargs)
            stats.success = True
            return result

        except BaseException as e:
            last_exception = e
            stats.last_exception = e

            # Check if we should retry
            if attempt >= config.max_retries:
                break

            if not config.should_retry(e):
                logger.debug(
                    f"Exception {type(e).__name__} is not retryable, "
                    f"raising immediately"
                )
                raise

            # Calculate delay
            delay = config.calculate_delay(attempt)
            stats.total_delay += delay

            # Log retry attempt
            logger.warning(
                f"Retry {attempt + 1}/{config.max_retries} for "
                f"{func.__name__} after {type(e).__name__}: {e}. "
                f"Waiting {delay:.2f}s"
            )

            # Call on_retry callback if provided
            if config.on_retry:
                config.on_retry(attempt + 1, e, delay)

            # Wait before retry
            time.sleep(delay)

    # All retries exhausted
    raise RetryExhausted(
        f"All {config.max_retries + 1} attempts failed for {func.__name__}",
        stats=stats,
        original_exception=last_exception,
    ) from last_exception


@overload
def retry(
    func: Callable[P, Awaitable[T]],
    /,
) -> Callable[P, Awaitable[T]]:
    ...


@overload
def retry(
    func: None = None,
    /,
    *,
    max_retries: int = ...,
    base_delay: float = ...,
    max_delay: float = ...,
    exponential_base: float = ...,
    jitter: float = ...,
    retryable_exceptions: tuple[Type[BaseException], ...] = ...,
    non_retryable_exceptions: tuple[Type[BaseException], ...] = ...,
    on_retry: Optional[Callable[[int, BaseException, float], None]] = ...,
    config: Optional[RetryConfig] = ...,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    ...


def retry(
    func: Optional[Callable[P, Awaitable[T]]] = None,
    /,
    *,
    max_retries: int = RetryDefaults.DEFAULT_MAX_RETRIES,
    base_delay: float = RetryDefaults.DEFAULT_BASE_DELAY,
    max_delay: float = RetryDefaults.DEFAULT_MAX_DELAY,
    exponential_base: float = RetryDefaults.DEFAULT_EXPONENTIAL_BASE,
    jitter: float = RetryDefaults.DEFAULT_JITTER,
    retryable_exceptions: tuple[Type[BaseException], ...] = (Exception,),
    non_retryable_exceptions: tuple[Type[BaseException], ...] = (),
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
    config: Optional[RetryConfig] = None,
) -> Union[
    Callable[P, Awaitable[T]],
    Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]],
]:
    """Decorator to add retry logic to async functions.

    Can be used with or without arguments:

        @retry
        async def func(): ...

        @retry(max_retries=5)
        async def func(): ...

        @retry(config=my_config)
        async def func(): ...

    Args:
        func: The function to decorate (when used without parentheses)
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Jitter factor for delay randomization
        retryable_exceptions: Exceptions that should trigger retry
        non_retryable_exceptions: Exceptions that should not be retried
        on_retry: Callback function called before each retry
        config: Pre-built RetryConfig (overrides other params)

    Returns:
        Decorated function or decorator
    """

    def decorator(f: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        # Use provided config or build from parameters
        retry_config = config or RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions,
            on_retry=on_retry,
        )

        @functools.wraps(f)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await retry_async(f, *args, config=retry_config, **kwargs)

        return wrapper

    if func is not None:
        return decorator(func)

    return decorator


def retry_sync_decorator(
    func: Optional[Callable[P, T]] = None,
    /,
    *,
    max_retries: int = RetryDefaults.DEFAULT_MAX_RETRIES,
    base_delay: float = RetryDefaults.DEFAULT_BASE_DELAY,
    max_delay: float = RetryDefaults.DEFAULT_MAX_DELAY,
    exponential_base: float = RetryDefaults.DEFAULT_EXPONENTIAL_BASE,
    jitter: float = RetryDefaults.DEFAULT_JITTER,
    retryable_exceptions: tuple[Type[BaseException], ...] = (Exception,),
    non_retryable_exceptions: tuple[Type[BaseException], ...] = (),
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
    config: Optional[RetryConfig] = None,
) -> Union[
    Callable[P, T],
    Callable[[Callable[P, T]], Callable[P, T]],
]:
    """Decorator to add retry logic to synchronous functions.

    Works the same as @retry but for sync functions.
    """

    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        retry_config = config or RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions,
            on_retry=on_retry,
        )

        @functools.wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return retry_sync(f, *args, config=retry_config, **kwargs)

        return wrapper

    if func is not None:
        return decorator(func)

    return decorator


class RetryContext:
    """Context manager for retry logic.

    Useful when you need more control over retry flow:

        async with RetryContext(config=my_config) as ctx:
            while ctx.should_continue():
                try:
                    result = await some_operation()
                    ctx.mark_success()
                    break
                except Exception as e:
                    await ctx.handle_exception(e)
    """

    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        """Initialize retry context.

        Args:
            config: Retry configuration (uses defaults if None)
        """
        self.config = config or RetryConfig()
        self.stats = RetryStats()
        self._attempt = 0
        self._last_exception: Optional[BaseException] = None

    def should_continue(self) -> bool:
        """Check if another attempt should be made.

        Returns:
            True if more attempts are allowed
        """
        return self._attempt <= self.config.max_retries and not self.stats.success

    def mark_success(self) -> None:
        """Mark the current attempt as successful."""
        self.stats.success = True

    async def handle_exception(self, exception: BaseException) -> None:
        """Handle an exception during retry.

        Args:
            exception: The exception that was raised

        Raises:
            The exception if it should not be retried or retries exhausted
        """
        self._last_exception = exception
        self.stats.last_exception = exception

        # Check if we should retry
        if not self.config.should_retry(exception):
            raise exception

        if self._attempt >= self.config.max_retries:
            raise RetryExhausted(
                f"All {self.config.max_retries + 1} attempts failed",
                stats=self.stats,
                original_exception=exception,
            ) from exception

        # Calculate and apply delay
        delay = self.config.calculate_delay(self._attempt)
        self.stats.total_delay += delay

        # Call on_retry callback
        if self.config.on_retry:
            self.config.on_retry(self._attempt + 1, exception, delay)

        await asyncio.sleep(delay)
        self._attempt += 1
        self.stats.attempts = self._attempt + 1

    def handle_exception_sync(self, exception: BaseException) -> None:
        """Synchronous version of handle_exception."""
        self._last_exception = exception
        self.stats.last_exception = exception

        if not self.config.should_retry(exception):
            raise exception

        if self._attempt >= self.config.max_retries:
            raise RetryExhausted(
                f"All {self.config.max_retries + 1} attempts failed",
                stats=self.stats,
                original_exception=exception,
            ) from exception

        delay = self.config.calculate_delay(self._attempt)
        self.stats.total_delay += delay

        if self.config.on_retry:
            self.config.on_retry(self._attempt + 1, exception, delay)

        time.sleep(delay)
        self._attempt += 1
        self.stats.attempts = self._attempt + 1

    async def __aenter__(self) -> "RetryContext":
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit async context."""
        return False

    def __enter__(self) -> "RetryContext":
        """Enter sync context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit sync context."""
        return False


__all__ = [
    "RetryConfig",
    "RetryStats",
    "RetryExhausted",
    "RetryContext",
    "retry",
    "retry_sync_decorator",
    "retry_async",
    "retry_sync",
    "MPC_RETRY_CONFIG",
    "RPC_RETRY_CONFIG",
    "DB_RETRY_CONFIG",
    "WEBHOOK_RETRY_CONFIG",
]
