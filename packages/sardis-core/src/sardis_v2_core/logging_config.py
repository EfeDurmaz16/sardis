"""Structured logging configuration with correlation IDs for request tracing.

This module provides structured JSON logging with:
- Correlation IDs for tracing requests across services
- Contextual fields (user, agent, wallet, transaction)
- Consistent log formatting
- Integration with FastAPI middleware
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

# Context variables for correlation tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
agent_id_var: ContextVar[Optional[str]] = ContextVar("agent_id", default=None)
wallet_id_var: ContextVar[Optional[str]] = ContextVar("wallet_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class CorrelationIDFilter(logging.Filter):
    """Logging filter that adds correlation ID and context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation context to log record."""
        record.correlation_id = correlation_id_var.get()
        record.request_id = request_id_var.get()
        record.agent_id = agent_id_var.get()
        record.wallet_id = wallet_id_var.get()
        record.user_id = user_id_var.get()
        return True


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation context if available
        if hasattr(record, "correlation_id") and record.correlation_id:
            log_data["correlation_id"] = record.correlation_id

        if hasattr(record, "request_id") and record.request_id:
            log_data["request_id"] = record.request_id

        if hasattr(record, "agent_id") and record.agent_id:
            log_data["agent_id"] = record.agent_id

        if hasattr(record, "wallet_id") and record.wallet_id:
            log_data["wallet_id"] = record.wallet_id

        if hasattr(record, "user_id") and record.user_id:
            log_data["user_id"] = record.user_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "correlation_id",
                "request_id",
                "agent_id",
                "wallet_id",
                "user_id",
            ):
                log_data[key] = value

        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON structured logging (True) or simple format (False)
        log_file: Optional file path for logging output
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    if json_format:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - "
            "[%(correlation_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(CorrelationIDFilter())
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(CorrelationIDFilter())
        root_logger.addHandler(file_handler)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return f"cor_{uuid.uuid4().hex[:16]}"


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    request_id_var.set(request_id)


def generate_request_id() -> str:
    """Generate a new request ID."""
    return f"req_{uuid.uuid4().hex[:16]}"


def set_agent_context(agent_id: str) -> None:
    """Set agent ID in logging context."""
    agent_id_var.set(agent_id)


def set_wallet_context(wallet_id: str) -> None:
    """Set wallet ID in logging context."""
    wallet_id_var.set(wallet_id)


def set_user_context(user_id: str) -> None:
    """Set user ID in logging context."""
    user_id_var.set(user_id)


def clear_context() -> None:
    """Clear all context variables."""
    correlation_id_var.set(None)
    request_id_var.set(None)
    agent_id_var.set(None)
    wallet_id_var.set(None)
    user_id_var.set(None)


class LogContext:
    """Context manager for temporary logging context."""

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.correlation_id = correlation_id
        self.request_id = request_id
        self.agent_id = agent_id
        self.wallet_id = wallet_id
        self.user_id = user_id
        self.previous_context = {}

    def __enter__(self) -> "LogContext":
        """Save current context and set new values."""
        self.previous_context = {
            "correlation_id": correlation_id_var.get(),
            "request_id": request_id_var.get(),
            "agent_id": agent_id_var.get(),
            "wallet_id": wallet_id_var.get(),
            "user_id": user_id_var.get(),
        }

        if self.correlation_id:
            correlation_id_var.set(self.correlation_id)
        if self.request_id:
            request_id_var.set(self.request_id)
        if self.agent_id:
            agent_id_var.set(self.agent_id)
        if self.wallet_id:
            wallet_id_var.set(self.wallet_id)
        if self.user_id:
            user_id_var.set(self.user_id)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Restore previous context."""
        correlation_id_var.set(self.previous_context["correlation_id"])
        request_id_var.set(self.previous_context["request_id"])
        agent_id_var.set(self.previous_context["agent_id"])
        wallet_id_var.set(self.previous_context["wallet_id"])
        user_id_var.set(self.previous_context["user_id"])


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with correlation tracking.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Convenience functions for common log patterns
def log_transaction(
    logger: logging.Logger,
    level: str,
    message: str,
    tx_id: Optional[str] = None,
    **kwargs,
) -> None:
    """Log a transaction-related message with context."""
    extra = kwargs.copy()
    if tx_id:
        extra["tx_id"] = tx_id
    getattr(logger, level.lower())(message, extra=extra)


def log_payment(
    logger: logging.Logger,
    level: str,
    message: str,
    mandate_id: Optional[str] = None,
    amount: Optional[str] = None,
    chain: Optional[str] = None,
    **kwargs,
) -> None:
    """Log a payment-related message with context."""
    extra = kwargs.copy()
    if mandate_id:
        extra["mandate_id"] = mandate_id
    if amount:
        extra["amount"] = amount
    if chain:
        extra["chain"] = chain
    getattr(logger, level.lower())(message, extra=extra)


def log_compliance(
    logger: logging.Logger,
    level: str,
    message: str,
    check_type: Optional[str] = None,
    result: Optional[str] = None,
    **kwargs,
) -> None:
    """Log a compliance check with context."""
    extra = kwargs.copy()
    if check_type:
        extra["check_type"] = check_type
    if result:
        extra["result"] = result
    getattr(logger, level.lower())(message, extra=extra)
