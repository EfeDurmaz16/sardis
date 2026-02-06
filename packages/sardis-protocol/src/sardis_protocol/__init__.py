"""Protocol adapters for AP2/TAP/x402 compliance."""

from .schemas import (
    IngestMandateRequest,
    MandateExecutionResponse,
    AP2PaymentExecuteRequest,
    AP2PaymentExecuteResponse,
    X402PaymentExecuteRequest,
    X402PaymentExecuteResponse,
)
from .verifier import MandateVerifier, VerificationResult, MandateChainVerification
from .storage import MandateArchive, SqliteReplayCache, ReplayCache
from .payment_methods import (
    PaymentMethod,
    PaymentMethodConfig,
    X402PaymentType,
    X402PaymentRequest,
    X402PaymentResponse,
    get_default_payment_methods,
    parse_payment_method_from_mandate,
)
from .rate_limiter import (
    AgentRateLimiter,
    RedisAgentRateLimiter,
    RateLimitConfig,
    RateLimitResult,
    get_rate_limiter,
    create_rate_limiter,
)
from .tap import (
    TAP_ALLOWED_TAGS,
    TAP_MAX_TIME_WINDOW_SECONDS,
    TAP_ALLOWED_MESSAGE_ALGS,
    TAP_ALLOWED_OBJECT_ALGS,
    TapSignatureInput,
    TapVerificationResult,
    parse_signature_input,
    parse_signature_header,
    build_signature_base,
    build_object_signature_base,
    validate_tap_headers,
    validate_agentic_consumer_object,
    validate_agentic_payment_container,
)
from .tap_keys import (
    select_jwk_by_kid,
    verify_signature_with_jwk,
)

__all__ = [
    # Schemas
    "IngestMandateRequest",
    "MandateExecutionResponse",
    "AP2PaymentExecuteRequest",
    "AP2PaymentExecuteResponse",
    "X402PaymentExecuteRequest",
    "X402PaymentExecuteResponse",
    # Verification
    "MandateVerifier",
    "VerificationResult",
    "MandateChainVerification",
    # Storage
    "MandateArchive",
    "SqliteReplayCache",
    "ReplayCache",
    # Payment Methods (multi-payment support)
    "PaymentMethod",
    "PaymentMethodConfig",
    "X402PaymentType",
    "X402PaymentRequest",
    "X402PaymentResponse",
    "get_default_payment_methods",
    "parse_payment_method_from_mandate",
    # Rate Limiting
    "AgentRateLimiter",
    "RedisAgentRateLimiter",
    "RateLimitConfig",
    "RateLimitResult",
    "get_rate_limiter",
    "create_rate_limiter",
    # TAP helpers
    "TAP_ALLOWED_TAGS",
    "TAP_MAX_TIME_WINDOW_SECONDS",
    "TAP_ALLOWED_MESSAGE_ALGS",
    "TAP_ALLOWED_OBJECT_ALGS",
    "TapSignatureInput",
    "TapVerificationResult",
    "parse_signature_input",
    "parse_signature_header",
    "build_signature_base",
    "build_object_signature_base",
    "validate_tap_headers",
    "validate_agentic_consumer_object",
    "validate_agentic_payment_container",
    "select_jwk_by_kid",
    "verify_signature_with_jwk",
]
