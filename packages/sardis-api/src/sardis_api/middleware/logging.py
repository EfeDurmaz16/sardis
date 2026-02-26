"""Structured logging middleware with correlation IDs for request tracing.

Provides production-grade logging with:
- Request/response correlation IDs
- Request timing and metrics
- Structured JSON logging for production
- Security-aware logging (no sensitive data)
- Configurable log levels per path
"""
from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for request correlation ID
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Context variable for request start time (for nested timing)
request_start_time_var: ContextVar[Optional[float]] = ContextVar("request_start_time", default=None)

logger = logging.getLogger("sardis.api")

# Headers that should never be logged (security)
SENSITIVE_HEADERS = frozenset({
    "authorization",
    "x-api-key",
    "cookie",
    "set-cookie",
    "x-auth-token",
    "x-csrf-token",
})

# Query parameters that should be masked (security)
SENSITIVE_PARAMS = frozenset({
    "token",
    "api_key",
    "apikey",
    "secret",
    "password",
    "key",
})


@dataclass
class LoggingConfig:
    """Configuration for structured logging middleware."""

    # Paths to exclude from logging entirely
    exclude_paths: List[str] = field(default_factory=lambda: [
        "/health",
        "/",
        "/api/v2/docs",
        "/api/v2/openapi.json",
    ])

    # Paths to log at DEBUG level only
    debug_paths: List[str] = field(default_factory=lambda: [
        "/api/v2/health",
    ])

    # Log request body for these content types (up to max_body_log_size)
    log_body_content_types: Set[str] = field(default_factory=lambda: {
        "application/json",
    })

    # Maximum body size to log (bytes)
    max_body_log_size: int = 1024

    # Include response headers in logs
    log_response_headers: bool = False

    # Slow request threshold (ms) - logs warning if exceeded
    slow_request_threshold_ms: float = 1000.0


class CorrelationIdFilter(logging.Filter):
    """Logging filter that adds correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = request_id_var.get() or "-"
        return True


def mask_sensitive_value(value: str) -> str:
    """Mask a sensitive value, showing only first/last characters."""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def filter_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Filter out sensitive headers from logging."""
    return {
        k: (mask_sensitive_value(v) if k.lower() in SENSITIVE_HEADERS else v)
        for k, v in headers.items()
    }


def filter_query_params(query_string: str) -> str:
    """Filter out sensitive query parameters from logging."""
    if not query_string:
        return ""

    params = []
    for param in query_string.split("&"):
        if "=" in param:
            key, value = param.split("=", 1)
            if key.lower() in SENSITIVE_PARAMS:
                params.append(f"{key}=***")
            else:
                params.append(param)
        else:
            params.append(param)
    return "&".join(params)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured logging with correlation IDs.

    Features:
    - Generates unique correlation ID for each request
    - Accepts X-Request-ID header for distributed tracing
    - Logs request/response with timing
    - Adds correlation ID to response headers
    - Security-aware: filters sensitive headers and params
    - Slow request warnings
    - Configurable per-path log levels
    """

    def __init__(
        self,
        app,
        exclude_paths: list[str] | None = None,
        config: LoggingConfig | None = None,
    ):
        super().__init__(app)
        self.config = config or LoggingConfig()
        if exclude_paths:
            self.config.exclude_paths = exclude_paths

    @staticmethod
    def _is_payment_endpoint(path: str) -> bool:
        return (
            "/pay" in path
            or "/payments" in path
            or "/checkout" in path
            or "/cards" in path
        )

    @staticmethod
    def _infer_payment_rail(path: str) -> str:
        p = (path or "").lower()
        if "onchain" in p or "/wallets/" in p:
            return "onchain"
        if "cards" in p or "stripe" in p or "treasury" in p:
            return "fiat"
        return "unknown"

    def _record_metrics(self, *, method: str, path: str, status_code: int, duration_ms: float) -> None:
        try:
            from sardis_api.routers.metrics import (
                record_http_request,
                record_payment_execution_latency,
            )

            duration_seconds = max(duration_ms / 1000.0, 0.0)
            record_http_request(method=method, endpoint=path, status=status_code, duration=duration_seconds)
            if self._is_payment_endpoint(path):
                outcome = "success" if status_code < 400 else "error"
                record_payment_execution_latency(
                    rail=self._infer_payment_rail(path),
                    outcome=outcome,
                    duration_seconds=duration_seconds,
                )
        except Exception:
            # Metrics failures should never impact request processing.
            logger.debug("metrics_recording_failed", exc_info=True)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if request.url.path in self.config.exclude_paths:
            return await call_next(request)

        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:16]}"
        request_id_var.set(correlation_id)

        # Store in request state for access by handlers
        request.state.request_id = correlation_id

        # Extract request info
        method = request.method
        path = request.url.path
        query = filter_query_params(request.url.query)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")[:100]

        # Determine log level based on path
        is_debug_path = path in self.config.debug_paths
        log_level = logging.DEBUG if is_debug_path else logging.INFO

        # Build request context for logging
        request_context = {
            "event": "request_start",
            "correlation_id": correlation_id,
            "method": method,
            "path": path,
            "query": query if query else None,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "content_length": request.headers.get("content-length"),
            "content_type": request.headers.get("content-type"),
        }

        # Remove None values
        request_context = {k: v for k, v in request_context.items() if v is not None}

        # Log request start
        logger.log(log_level, "Request started", extra=request_context)

        # Process request with timing
        start_time = time.perf_counter()
        request_start_time_var.set(start_time)

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Build response context
            response_context = {
                "event": "request_complete",
                "correlation_id": correlation_id,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }

            # Add response content length if available
            content_length = response.headers.get("content-length")
            if content_length:
                response_context["response_size"] = int(content_length)

            # Log at appropriate level based on status and duration
            if response.status_code >= 500:
                logger.error("Request completed with server error", extra=response_context)
            elif response.status_code >= 400:
                logger.warning("Request completed with client error", extra=response_context)
            elif duration_ms > self.config.slow_request_threshold_ms:
                response_context["slow_request"] = True
                logger.warning("Slow request completed", extra=response_context)
            else:
                logger.log(log_level, "Request completed", extra=response_context)

            self._record_metrics(
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Add correlation ID to response headers
            response.headers["X-Request-ID"] = correlation_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log error
            logger.error(
                "Request failed",
                extra={
                    "event": "request_error",
                    "correlation_id": correlation_id,
                    "method": method,
                    "path": path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": round(duration_ms, 2),
                },
                exc_info=True,
            )
            self._record_metrics(
                method=method,
                path=path,
                status_code=500,
                duration_ms=duration_ms,
            )
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, considering proxy headers."""
        # Check X-Forwarded-For first (for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP (nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        return request.client.host if request.client else "unknown"


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }

        # Add extra fields
        if hasattr(record, "event"):
            log_data["event"] = record.event
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "client_ip"):
            log_data["client_ip"] = record.client_ip
        if hasattr(record, "error"):
            log_data["error"] = record.error
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(json_format: bool = True, level: str = "INFO"):
    """
    Configure structured logging for the application.
    
    Args:
        json_format: Use JSON format (for production) or human-readable (for dev)
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))

    # Add correlation ID filter
    console_handler.addFilter(CorrelationIdFilter())

    # Set formatter
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s"
            )
        )

    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_correlation_id() -> Optional[str]:
    """Get the current request's correlation ID."""
    return request_id_var.get()
