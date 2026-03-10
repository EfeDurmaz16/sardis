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
from .auth import (
    APIKey,
    APIKeyManager,
    AuthContext,
    get_api_key,
    get_api_key_manager,
    require_api_key,
    require_scope,
    set_api_key_manager,
)
from .exceptions import (
    ERROR_TYPE_BASE,
    ExceptionHandlerMiddleware,
    RFC7807Error,
    create_error_response,
    create_validation_error_response,
    register_exception_handlers,
)
from .logging import (
    SENSITIVE_HEADERS,
    SENSITIVE_PARAMS,
    JSONFormatter,
    LoggingConfig,
    StructuredLoggingMiddleware,
    get_correlation_id,
    request_id_var,
    request_start_time_var,
    setup_logging,
)
from .rate_limit import RateLimitConfig, RateLimitMiddleware
from .security import (
    API_VERSION,
    SECURITY_HEADERS_PERMISSIVE,
    SECURITY_HEADERS_STRICT,
    RequestBodyLimitMiddleware,
    RequestIdMiddleware,
    SecurityConfig,
    SecurityHeadersMiddleware,
    WebhookSignatureVerifier,
    verify_webhook_signature,
)
from .tap import (
    NonceCache,
    TapMiddlewareConfig,
    TapVerificationMiddleware,
)
from .usage_metering import (
    EXEMPT_PREFIXES,
    UsageMeteringMiddleware,
)
from .x402 import (
    X402MiddlewareConfig,
    X402PaymentMiddleware,
    X402PricingRegistry,
    X402PricingRule,
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
    # TAP (Trust Anchor Protocol)
    "TapVerificationMiddleware",
    "TapMiddlewareConfig",
    "NonceCache",
    # x402 Payment Required
    "X402PaymentMiddleware",
    "X402MiddlewareConfig",
    "X402PricingRegistry",
    "X402PricingRule",
    # Usage metering (plan enforcement)
    "UsageMeteringMiddleware",
    "EXEMPT_PREFIXES",
]
