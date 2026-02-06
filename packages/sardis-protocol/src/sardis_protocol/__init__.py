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
    TAP_PROTOCOL_VERSION,
    TAP_SUPPORTED_VERSIONS,
    TapSignatureInput,
    TapVerificationResult,
    parse_signature_input,
    parse_signature_header,
    build_signature_base,
    build_object_signature_base,
    validate_tap_headers,
    validate_agentic_consumer_object,
    validate_agentic_payment_container,
    validate_tap_version,
)
from .tap_keys import (
    select_jwk_by_kid,
    verify_signature_with_jwk,
)

# x402 protocol
try:
    from .x402 import (
        X402Challenge,
        X402ChallengeResponse,
        X402PaymentPayload,
        X402VerificationResult,
        X402HeaderBuilder,
        generate_challenge,
        serialize_challenge_header,
        parse_challenge_header,
        verify_payment_payload,
        validate_x402_version,
        X402_PAYMENT_SIGNATURE_HEADER,
        X402_PAYMENT_RESPONSE_HEADER,
        X402_PAYMENT_REQUIRED_HEADER,
    )
except ImportError:
    pass

# x402 ERC-3009 authorization
try:
    from .x402_erc3009 import (
        ERC3009Authorization,
        build_transfer_authorization,
        validate_authorization_timing,
        encode_authorization_params,
    )
except ImportError:
    pass

# x402 settlement
try:
    from .x402_settlement import (
        X402Settlement,
        X402Settler,
        X402SettlementStatus,
        X402SettlementStore,
        InMemorySettlementStore,
    )
except ImportError:
    pass

# Protocol reason codes
try:
    from .reason_codes import (
        ProtocolReasonCode,
        ReasonCodeMapping,
        REASON_CODE_TABLE,
        get_reason,
        map_exception_to_reason,
        map_legacy_reason_to_code,
    )
except ImportError:
    pass

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
    "TAP_PROTOCOL_VERSION",
    "TAP_SUPPORTED_VERSIONS",
    "TapSignatureInput",
    "TapVerificationResult",
    "parse_signature_input",
    "parse_signature_header",
    "build_signature_base",
    "build_object_signature_base",
    "validate_tap_headers",
    "validate_agentic_consumer_object",
    "validate_agentic_payment_container",
    "validate_tap_version",
    "select_jwk_by_kid",
    "verify_signature_with_jwk",
    # x402 protocol
    "X402Challenge",
    "X402ChallengeResponse",
    "X402PaymentPayload",
    "X402VerificationResult",
    "X402HeaderBuilder",
    "generate_challenge",
    "serialize_challenge_header",
    "parse_challenge_header",
    "verify_payment_payload",
    "validate_x402_version",
    "X402_PAYMENT_SIGNATURE_HEADER",
    "X402_PAYMENT_RESPONSE_HEADER",
    "X402_PAYMENT_REQUIRED_HEADER",
    # x402 ERC-3009
    "ERC3009Authorization",
    "build_transfer_authorization",
    "validate_authorization_timing",
    "encode_authorization_params",
    # x402 settlement
    "X402Settlement",
    "X402Settler",
    "X402SettlementStatus",
    "X402SettlementStore",
    "InMemorySettlementStore",
    # Protocol reason codes
    "ProtocolReasonCode",
    "ReasonCodeMapping",
    "REASON_CODE_TABLE",
    "get_reason",
    "map_exception_to_reason",
    "map_legacy_reason_to_code",
]
