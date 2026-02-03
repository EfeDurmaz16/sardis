"""
Sentry error tracking and performance monitoring integration.

This module sets up Sentry for comprehensive error tracking, performance monitoring,
and distributed tracing across the Sardis API.

Features:
- Automatic error capturing and reporting
- Performance transaction tracking
- Request context enrichment
- User context tracking
- Custom tags and breadcrumbs
- Release tracking for deployments
- Environment-based configuration

Reference: https://docs.sentry.io/platforms/python/guides/fastapi/
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from fastapi import Request

logger = logging.getLogger(__name__)


def init_sentry(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
    enable_tracing: bool = True,
) -> None:
    """
    Initialize Sentry SDK for error tracking and performance monitoring.

    Args:
        dsn: Sentry DSN (Data Source Name). If not provided, reads from SENTRY_DSN env var
        environment: Environment name (e.g., "production", "staging", "development")
        release: Release version (e.g., "sardis@1.0.0")
        traces_sample_rate: Percentage of transactions to sample (0.0 to 1.0)
        profiles_sample_rate: Percentage of transactions to profile (0.0 to 1.0)
        enable_tracing: Enable performance monitoring
    """
    # Get DSN from environment if not provided
    if dsn is None:
        dsn = os.getenv("SENTRY_DSN")

    # Skip initialization if no DSN
    if not dsn:
        logger.warning("Sentry DSN not configured. Error tracking disabled.")
        return

    # Get environment from env var if not provided
    if environment is None:
        environment = os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))

    # Get release from env var if not provided
    if release is None:
        release = os.getenv("SENTRY_RELEASE", os.getenv("GIT_COMMIT", "unknown"))

    # Configure logging integration
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors as events
    )

    # Configure integrations
    integrations = [
        FastApiIntegration(transaction_style="url"),
        logging_integration,
        RedisIntegration(),
        SqlalchemyIntegration(),
    ]

    # Initialize Sentry
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=integrations,
        traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
        profiles_sample_rate=profiles_sample_rate if enable_tracing else 0.0,
        send_default_pii=False,  # Don't send PII by default
        attach_stacktrace=True,
        before_send=before_send_event,
        before_breadcrumb=before_breadcrumb,
        # Performance monitoring
        enable_tracing=enable_tracing,
        # Additional options
        debug=environment == "development",
        max_breadcrumbs=50,
        sample_rate=1.0,  # Capture all errors (not sampled)
    )

    logger.info(
        f"Sentry initialized: environment={environment}, release={release}, "
        f"traces_sample_rate={traces_sample_rate}"
    )


def before_send_event(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter and modify events before sending to Sentry.

    This function is called for every event before it's sent.
    Use it to filter out sensitive data, drop certain events, or add custom context.

    Args:
        event: The event dictionary
        hint: Additional context (exception info, etc.)

    Returns:
        Modified event or None to drop the event
    """
    # Drop events from health check endpoints
    if event.get("request", {}).get("url", "").endswith("/health"):
        return None

    # Scrub sensitive data from request headers
    if "request" in event and "headers" in event["request"]:
        sensitive_headers = ["Authorization", "X-API-Key", "Cookie"]
        for header in sensitive_headers:
            if header in event["request"]["headers"]:
                event["request"]["headers"][header] = "[REDACTED]"

    # Add custom tags
    event.setdefault("tags", {})
    event["tags"]["service"] = "sardis-api"

    return event


def before_breadcrumb(crumb: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter and modify breadcrumbs before adding to the event.

    Args:
        crumb: The breadcrumb dictionary
        hint: Additional context

    Returns:
        Modified breadcrumb or None to drop it
    """
    # Drop noisy breadcrumbs
    if crumb.get("category") == "httplib" and crumb.get("data", {}).get("url", "").endswith("/health"):
        return None

    return crumb


def configure_request_context(request: Request) -> None:
    """
    Configure Sentry context for the current request.

    This should be called at the start of request processing to add
    request-specific context to error reports.

    Args:
        request: FastAPI request object
    """
    with sentry_sdk.configure_scope() as scope:
        # Set request context
        scope.set_context("request", {
            "url": str(request.url),
            "method": request.method,
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
        })

        # Set user context if available
        # Note: Only set if user is authenticated
        if hasattr(request.state, "user_id"):
            scope.set_user({
                "id": request.state.user_id,
                # Don't include email or other PII unless explicitly allowed
            })

        # Set tags
        scope.set_tag("endpoint", request.url.path)
        scope.set_tag("method", request.method)


def capture_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    level: str = "error",
) -> Optional[str]:
    """
    Manually capture an exception and send to Sentry.

    Args:
        exception: The exception to capture
        context: Additional context to attach
        tags: Tags to add to the event
        level: Severity level ("fatal", "error", "warning", "info", "debug")

    Returns:
        Event ID if sent successfully, None otherwise
    """
    with sentry_sdk.push_scope() as scope:
        # Set level
        scope.level = level

        # Add context
        if context:
            for key, value in context.items():
                scope.set_context(key, value)

        # Add tags
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        # Capture exception
        event_id = sentry_sdk.capture_exception(exception)
        logger.debug(f"Exception captured in Sentry: event_id={event_id}")
        return event_id


def capture_message(
    message: str,
    level: str = "info",
    tags: Optional[Dict[str, str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Capture a message and send to Sentry.

    Args:
        message: The message to capture
        level: Severity level ("fatal", "error", "warning", "info", "debug")
        tags: Tags to add to the event
        context: Additional context to attach

    Returns:
        Event ID if sent successfully, None otherwise
    """
    with sentry_sdk.push_scope() as scope:
        # Set level
        scope.level = level

        # Add context
        if context:
            for key, value in context.items():
                scope.set_context(key, value)

        # Add tags
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        # Capture message
        event_id = sentry_sdk.capture_message(message, level=level)
        logger.debug(f"Message captured in Sentry: event_id={event_id}")
        return event_id


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Add a breadcrumb to the current scope.

    Breadcrumbs are used to create a trail of events that led to an error.

    Args:
        message: Breadcrumb message
        category: Category (e.g., "auth", "db", "http")
        level: Severity level
        data: Additional data
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )


@asynccontextmanager
async def transaction_context(
    name: str,
    op: str = "function",
    description: Optional[str] = None,
):
    """
    Context manager for creating a Sentry transaction.

    Use this to track performance of specific operations.

    Args:
        name: Transaction name
        op: Operation type (e.g., "http.server", "db.query", "function")
        description: Optional description

    Example:
        async with transaction_context("process_payment", op="payment"):
            # Your code here
            pass
    """
    with sentry_sdk.start_transaction(op=op, name=name, description=description) as transaction:
        try:
            yield transaction
        except Exception as e:
            transaction.set_status("internal_error")
            raise


def start_span(
    op: str,
    description: Optional[str] = None,
):
    """
    Start a span within the current transaction.

    Use this to measure specific operations within a transaction.

    Args:
        op: Operation type (e.g., "db.query", "http.client", "cache.get")
        description: Optional description

    Returns:
        Span context manager

    Example:
        with start_span("db.query", "SELECT users"):
            # Database query here
            pass
    """
    return sentry_sdk.start_span(op=op, description=description)


class SentryMiddleware:
    """
    Custom middleware for enhanced Sentry integration.

    This middleware adds request context and handles exceptions.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Start transaction for this request
        transaction_name = f"{scope['method']} {scope['path']}"
        with sentry_sdk.start_transaction(op="http.server", name=transaction_name):
            # Add breadcrumb for request
            add_breadcrumb(
                message=f"Request: {scope['method']} {scope['path']}",
                category="http",
                level="info",
                data={
                    "method": scope["method"],
                    "path": scope["path"],
                    "query_string": scope.get("query_string", b"").decode(),
                },
            )

            try:
                await self.app(scope, receive, send)
            except Exception as e:
                # Capture exception
                capture_exception(
                    e,
                    context={
                        "request": {
                            "method": scope["method"],
                            "path": scope["path"],
                        }
                    },
                    tags={
                        "endpoint": scope["path"],
                        "method": scope["method"],
                    },
                )
                raise


def get_sentry_trace_id() -> Optional[str]:
    """
    Get the current Sentry trace ID.

    This can be used for logging correlation.

    Returns:
        Trace ID if available, None otherwise
    """
    scope = sentry_sdk.Hub.current.scope
    if scope and scope.transaction:
        return scope.transaction.trace_id
    return None


def set_user_context(
    user_id: str,
    email: Optional[str] = None,
    username: Optional[str] = None,
    **extra_data,
) -> None:
    """
    Set user context for error reports.

    Args:
        user_id: User ID
        email: User email (optional, consider privacy)
        username: Username (optional)
        **extra_data: Additional user data
    """
    user_data = {"id": user_id}

    if email:
        user_data["email"] = email
    if username:
        user_data["username"] = username

    user_data.update(extra_data)

    with sentry_sdk.configure_scope() as scope:
        scope.set_user(user_data)


def clear_user_context() -> None:
    """Clear user context (e.g., after logout)."""
    with sentry_sdk.configure_scope() as scope:
        scope.set_user(None)


def flush_events(timeout: float = 2.0) -> bool:
    """
    Flush pending events to Sentry.

    Useful before shutdown or in serverless environments.

    Args:
        timeout: Maximum time to wait for flush (seconds)

    Returns:
        True if flushed successfully within timeout
    """
    return sentry_sdk.flush(timeout=timeout)
