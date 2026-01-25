"""
Logging utilities for Sardis Core with sensitive data masking.

This module provides logging utilities that automatically mask sensitive
data like passwords, API keys, and tokens from log messages.

Usage:
    from sardis_v2_core.logging import (
        get_logger,
        mask_sensitive_data,
        log_request,
        log_response,
    )

    logger = get_logger(__name__)

    # Automatic masking in structured logs
    logger.info("Processing payment", extra=mask_sensitive_data({
        "amount": 100,
        "api_key": "sk_live_xxx",  # Will be masked
    }))

    # Request/response logging
    log_request(logger, "POST", "/payments", headers, body)
    log_response(logger, 200, response_body, duration_ms)
"""
from __future__ import annotations

import copy
import json
import logging
import re
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterator,
    Optional,
    ParamSpec,
    Sequence,
    TypeVar,
    Union,
)

from .constants import LoggingConfig

T = TypeVar("T")
P = ParamSpec("P")


# =============================================================================
# Sensitive Data Masking
# =============================================================================

def mask_value(value: str, show_chars: int = 4) -> str:
    """Mask a sensitive value, optionally showing first/last characters.

    Args:
        value: The value to mask
        show_chars: Number of characters to show at start and end

    Returns:
        Masked string
    """
    if not value or len(value) <= show_chars * 2:
        return LoggingConfig.MASK_PATTERN

    return f"{value[:show_chars]}...{value[-show_chars:]}"


def is_sensitive_key(key: str) -> bool:
    """Check if a key name indicates sensitive data.

    Args:
        key: The key name to check

    Returns:
        True if the key likely contains sensitive data
    """
    key_lower = key.lower().replace("-", "_")
    return key_lower in LoggingConfig.SENSITIVE_FIELDS or any(
        sensitive in key_lower
        for sensitive in ("secret", "password", "token", "key", "credential", "auth")
    )


def mask_sensitive_data(
    data: Any,
    additional_fields: Optional[Sequence[str]] = None,
    mask_pattern: str = LoggingConfig.MASK_PATTERN,
    _depth: int = 0,
    _max_depth: int = 10,
) -> Any:
    """Recursively mask sensitive data in a data structure.

    Args:
        data: The data structure to mask (dict, list, or scalar)
        additional_fields: Additional field names to mask
        mask_pattern: Pattern to replace sensitive values with
        _depth: Current recursion depth (internal)
        _max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        Copy of data with sensitive values masked
    """
    if _depth > _max_depth:
        return data

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if is_sensitive_key(key):
                result[key] = mask_pattern
            elif additional_fields and key in additional_fields:
                result[key] = mask_pattern
            else:
                result[key] = mask_sensitive_data(
                    value,
                    additional_fields,
                    mask_pattern,
                    _depth + 1,
                    _max_depth,
                )
        return result

    elif isinstance(data, (list, tuple)):
        return type(data)(
            mask_sensitive_data(
                item,
                additional_fields,
                mask_pattern,
                _depth + 1,
                _max_depth,
            )
            for item in data
        )

    elif isinstance(data, str):
        # Check for inline sensitive patterns
        return _mask_inline_patterns(data)

    return data


def _mask_inline_patterns(text: str) -> str:
    """Mask common sensitive patterns in text.

    Handles patterns like:
    - API keys: sk_live_xxxxx, pk_test_xxxxx
    - Bearer tokens: Bearer xxxxx
    - Basic auth: Basic xxxxx
    - URLs with credentials: https://user:pass@host

    Args:
        text: The text to check for sensitive patterns

    Returns:
        Text with sensitive patterns masked
    """
    if len(text) > LoggingConfig.MAX_LOG_MESSAGE_LENGTH:
        text = text[: LoggingConfig.MAX_LOG_MESSAGE_LENGTH] + "...[truncated]"

    # Mask common API key patterns
    patterns = [
        # API keys with prefixes
        (r'\b(sk_live_|sk_test_|pk_live_|pk_test_)[a-zA-Z0-9]+\b', r'\1***'),
        (r'\b(api_key[=:])\s*["\']?([^"\'\s]+)["\']?', r'\1***'),
        # Bearer tokens
        (r'(Bearer\s+)[a-zA-Z0-9._-]+', r'\1***'),
        # Basic auth
        (r'(Basic\s+)[a-zA-Z0-9+/=]+', r'\1***'),
        # URLs with credentials
        (r'(https?://)[^:]+:[^@]+@', r'\1***:***@'),
        # JWT tokens (simplified)
        (r'\beyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b', '***JWT***'),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


def mask_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Mask sensitive HTTP headers.

    Args:
        headers: HTTP headers dictionary

    Returns:
        Headers with sensitive values masked
    """
    sensitive_headers = {
        "authorization",
        "x-api-key",
        "x-auth-token",
        "cookie",
        "set-cookie",
        "x-sardis-signature",
    }

    result = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if key_lower in sensitive_headers:
            result[key] = LoggingConfig.MASK_PATTERN
        else:
            result[key] = value
    return result


# =============================================================================
# Structured Logging
# =============================================================================

@dataclass
class RequestContext:
    """Context for a single request/operation.

    Attributes:
        request_id: Unique identifier for this request
        operation: Name of the operation being performed
        started_at: When the operation started
        user_id: Optional user/agent identifier
        wallet_id: Optional wallet identifier
        extra: Additional context data
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: str = ""
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    user_id: Optional[str] = None
    wallet_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        delta = datetime.now(timezone.utc) - self.started_at
        return delta.total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        result = {
            "request_id": self.request_id,
            "operation": self.operation,
            "elapsed_ms": self.elapsed_ms(),
        }
        if self.user_id:
            result["user_id"] = self.user_id
        if self.wallet_id:
            result["wallet_id"] = self.wallet_id
        if self.extra:
            result.update(mask_sensitive_data(self.extra))
        return result


class StructuredLogger:
    """Logger wrapper that adds structured context and masking.

    Usage:
        logger = StructuredLogger(__name__)
        logger.info("Processing payment", amount=100, wallet_id="wallet_xxx")

        # With context
        with logger.context(operation="process_payment", user_id="user_123"):
            logger.info("Starting payment")
            # ... do work ...
            logger.info("Payment complete")
    """

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
    ) -> None:
        """Initialize structured logger.

        Args:
            name: Logger name (typically __name__)
            level: Default logging level
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._context_stack: list[RequestContext] = []

    @property
    def current_context(self) -> Optional[RequestContext]:
        """Get the current request context."""
        return self._context_stack[-1] if self._context_stack else None

    @contextmanager
    def context(
        self,
        operation: str,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        **extra: Any,
    ) -> Iterator[RequestContext]:
        """Create a logging context for an operation.

        Args:
            operation: Name of the operation
            request_id: Optional request ID (generated if not provided)
            user_id: Optional user identifier
            wallet_id: Optional wallet identifier
            **extra: Additional context data

        Yields:
            RequestContext for the operation
        """
        ctx = RequestContext(
            request_id=request_id or str(uuid.uuid4()),
            operation=operation,
            user_id=user_id,
            wallet_id=wallet_id,
            extra=extra,
        )
        self._context_stack.append(ctx)

        try:
            self.debug(f"Starting {operation}")
            yield ctx
            self.debug(f"Completed {operation}", elapsed_ms=ctx.elapsed_ms())
        except Exception as e:
            self.error(
                f"Failed {operation}: {type(e).__name__}",
                elapsed_ms=ctx.elapsed_ms(),
                error=str(e),
            )
            raise
        finally:
            self._context_stack.pop()

    def _build_extra(self, **kwargs: Any) -> Dict[str, Any]:
        """Build extra data for log record."""
        extra = mask_sensitive_data(kwargs)

        if self.current_context:
            extra.update(self.current_context.to_dict())

        return extra

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._logger.debug(message, extra={"data": self._build_extra(**kwargs)})

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._logger.info(message, extra={"data": self._build_extra(**kwargs)})

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._logger.warning(message, extra={"data": self._build_extra(**kwargs)})

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._logger.error(message, extra={"data": self._build_extra(**kwargs)})

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._logger.exception(message, extra={"data": self._build_extra(**kwargs)})

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._logger.critical(message, extra={"data": self._build_extra(**kwargs)})


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


# =============================================================================
# Request/Response Logging
# =============================================================================

def log_request(
    logger: Union[logging.Logger, StructuredLogger],
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Any] = None,
    request_id: Optional[str] = None,
) -> None:
    """Log an outgoing HTTP request.

    Args:
        logger: Logger to use
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        headers: Optional request headers (sensitive values masked)
        body: Optional request body (sensitive values masked)
        request_id: Optional request ID for correlation
    """
    log_data = {
        "direction": "request",
        "method": method,
        "url": _mask_inline_patterns(url),
    }

    if request_id:
        log_data["request_id"] = request_id

    if headers:
        log_data["headers"] = mask_headers(headers)

    if body is not None:
        masked_body = mask_sensitive_data(body)
        # Truncate large bodies
        body_str = json.dumps(masked_body, default=str)
        if len(body_str) > LoggingConfig.MAX_RESPONSE_BODY_LOG_LENGTH:
            body_str = body_str[: LoggingConfig.MAX_RESPONSE_BODY_LOG_LENGTH] + "..."
        log_data["body"] = body_str

    if isinstance(logger, StructuredLogger):
        logger.debug(f"HTTP {method} {url}", **log_data)
    else:
        logger.debug(f"HTTP {method} {url}", extra={"data": log_data})


def log_response(
    logger: Union[logging.Logger, StructuredLogger],
    status_code: int,
    body: Optional[Any] = None,
    duration_ms: Optional[float] = None,
    request_id: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Log an HTTP response.

    Args:
        logger: Logger to use
        status_code: HTTP status code
        body: Optional response body (sensitive values masked)
        duration_ms: Request duration in milliseconds
        request_id: Optional request ID for correlation
        error: Optional error message
    """
    log_data: Dict[str, Any] = {
        "direction": "response",
        "status_code": status_code,
    }

    if request_id:
        log_data["request_id"] = request_id

    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms

    if error:
        log_data["error"] = error

    if body is not None:
        masked_body = mask_sensitive_data(body)
        body_str = json.dumps(masked_body, default=str)
        if len(body_str) > LoggingConfig.MAX_RESPONSE_BODY_LOG_LENGTH:
            body_str = body_str[: LoggingConfig.MAX_RESPONSE_BODY_LOG_LENGTH] + "..."
        log_data["body"] = body_str

    level = logging.DEBUG if status_code < 400 else logging.WARNING

    message = f"HTTP {status_code}"
    if duration_ms is not None:
        message += f" ({duration_ms:.0f}ms)"

    if isinstance(logger, StructuredLogger):
        if level == logging.WARNING:
            logger.warning(message, **log_data)
        else:
            logger.debug(message, **log_data)
    else:
        logger.log(level, message, extra={"data": log_data})


# =============================================================================
# Logging Decorators
# =============================================================================

def log_operation(
    operation_name: Optional[str] = None,
    logger: Optional[StructuredLogger] = None,
    log_args: bool = True,
    log_result: bool = False,
    log_exceptions: bool = True,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator to log async function calls.

    Args:
        operation_name: Name for the operation (defaults to function name)
        logger: Logger to use (defaults to function's module)
        log_args: Whether to log function arguments
        log_result: Whether to log the return value
        log_exceptions: Whether to log exceptions

    Returns:
        Decorator function
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        op_name = operation_name or func.__name__

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time = time.time()

            extra: Dict[str, Any] = {"function": func.__name__}

            if log_args:
                # Mask arguments
                extra["args"] = mask_sensitive_data(
                    {f"arg{i}": arg for i, arg in enumerate(args)}
                )
                extra["kwargs"] = mask_sensitive_data(kwargs)

            logger.info(f"Starting {op_name}", **extra)

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                result_extra = {"duration_ms": duration_ms}
                if log_result:
                    result_extra["result"] = mask_sensitive_data(result)

                logger.info(f"Completed {op_name}", **result_extra)
                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                if log_exceptions:
                    logger.error(
                        f"Failed {op_name}: {type(e).__name__}",
                        duration_ms=duration_ms,
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )
                raise

        return wrapper

    return decorator


def log_operation_sync(
    operation_name: Optional[str] = None,
    logger: Optional[StructuredLogger] = None,
    log_args: bool = True,
    log_result: bool = False,
    log_exceptions: bool = True,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to log synchronous function calls.

    Same as log_operation but for sync functions.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        op_name = operation_name or func.__name__

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time = time.time()

            extra: Dict[str, Any] = {"function": func.__name__}

            if log_args:
                extra["args"] = mask_sensitive_data(
                    {f"arg{i}": arg for i, arg in enumerate(args)}
                )
                extra["kwargs"] = mask_sensitive_data(kwargs)

            logger.info(f"Starting {op_name}", **extra)

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                result_extra = {"duration_ms": duration_ms}
                if log_result:
                    result_extra["result"] = mask_sensitive_data(result)

                logger.info(f"Completed {op_name}", **result_extra)
                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                if log_exceptions:
                    logger.error(
                        f"Failed {op_name}: {type(e).__name__}",
                        duration_ms=duration_ms,
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )
                raise

        return wrapper

    return decorator


# =============================================================================
# JSON Formatter for Production
# =============================================================================

class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging.

    Formats log records as JSON for easy parsing by log aggregators.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra data if present
        if hasattr(record, "data") and record.data:
            log_data["data"] = record.data

        return json.dumps(log_data, default=str)


def configure_logging(
    level: int = logging.INFO,
    json_format: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """Configure logging for the application.

    Args:
        level: Logging level
        json_format: Whether to use JSON formatting
        log_file: Optional file path for logging
    """
    handlers: list[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    if json_format:
        console_handler.setFormatter(JsonFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )

    handlers.append(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(JsonFormatter())  # Always JSON for files
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,
    )


__all__ = [
    # Core functions
    "mask_sensitive_data",
    "mask_value",
    "mask_headers",
    "is_sensitive_key",
    # Logging
    "get_logger",
    "StructuredLogger",
    "RequestContext",
    "log_request",
    "log_response",
    # Decorators
    "log_operation",
    "log_operation_sync",
    # Configuration
    "configure_logging",
    "JsonFormatter",
]
