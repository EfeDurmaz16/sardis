"""Middleware for Sardis API."""
from .rate_limit import RateLimitMiddleware, RateLimitConfig
from .logging import (
    StructuredLoggingMiddleware,
    JSONFormatter,
    setup_logging,
    get_correlation_id,
    request_id_var,
)
from .auth import (
    APIKeyManager,
    APIKey,
    AuthContext,
    get_api_key,
    require_api_key,
    require_scope,
    set_api_key_manager,
    get_api_key_manager,
)
from .exceptions import (
    ExceptionHandlerMiddleware,
    register_exception_handlers,
    create_error_response,
)

__all__ = [
    "RateLimitMiddleware",
    "RateLimitConfig",
    "StructuredLoggingMiddleware",
    "JSONFormatter",
    "setup_logging",
    "get_correlation_id",
    "request_id_var",
    "APIKeyManager",
    "APIKey",
    "AuthContext",
    "get_api_key",
    "require_api_key",
    "require_scope",
    "set_api_key_manager",
    "get_api_key_manager",
    "ExceptionHandlerMiddleware",
    "register_exception_handlers",
    "create_error_response",
]
