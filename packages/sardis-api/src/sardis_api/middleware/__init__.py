"""Middleware for Sardis API.

Production-grade middleware components:
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- Request body size limits
- API versioning headers
- Request ID tracking
- Rate limiting
- Structured logging
- Exception handling (RFC 7807)
- Webhook signature verification
"""
from .rate_limit import RateLimitMiddleware, RateLimitConfig
from .logging import (
    StructuredLoggingMiddleware,
    JSONFormatter,
    setup_logging,
    get_correlation_id,
    request_id_var,
    request_start_time_var,
    LoggingConfig,
    SENSITIVE_HEADERS,
    SENSITIVE_PARAMS,
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
    create_validation_error_response,
    RFC7807Error,
    ERROR_TYPE_BASE,
)
from .security import (
    SecurityConfig,
    SecurityHeadersMiddleware,
    RequestBodyLimitMiddleware,
    RequestIdMiddleware,
    WebhookSignatureVerifier,
    verify_webhook_signature,
    API_VERSION,
    SECURITY_HEADERS_PERMISSIVE,
    SECURITY_HEADERS_STRICT,
)

__all__ = [
    # Rate limiting
    "RateLimitMiddleware",
    "RateLimitConfig",
    # Logging
    "StructuredLoggingMiddleware",
    "JSONFormatter",
    "setup_logging",
    "get_correlation_id",
    "request_id_var",
    "request_start_time_var",
    "LoggingConfig",
    "SENSITIVE_HEADERS",
    "SENSITIVE_PARAMS",
    # Auth
    "APIKeyManager",
    "APIKey",
    "AuthContext",
    "get_api_key",
    "require_api_key",
    "require_scope",
    "set_api_key_manager",
    "get_api_key_manager",
    # Exceptions (RFC 7807)
    "ExceptionHandlerMiddleware",
    "register_exception_handlers",
    "create_error_response",
    "create_validation_error_response",
    "RFC7807Error",
    "ERROR_TYPE_BASE",
    # Security
    "SecurityConfig",
    "SecurityHeadersMiddleware",
    "RequestBodyLimitMiddleware",
    "RequestIdMiddleware",
    "WebhookSignatureVerifier",
    "verify_webhook_signature",
    "API_VERSION",
    "SECURITY_HEADERS_PERMISSIVE",
    "SECURITY_HEADERS_STRICT",
]
