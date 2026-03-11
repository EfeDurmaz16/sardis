"""Protocol adapters for AP2/TAP/x402 compliance."""

import contextlib

from .mandate_cache import (
    InMemoryMandateCache,
    MandateCache,
    MandateCacheConfig,
)
from .nonce_registry import (
    NonceConfig,
    NonceRegistry,
    RedisNonceRegistry,
)
from .payment_methods import (
    PaymentMethod,
    PaymentMethodConfig,
    X402PaymentRequest,
    X402PaymentResponse,
    X402PaymentType,
    get_default_payment_methods,
    parse_payment_method_from_mandate,
)
from .rate_limiter import (
    AgentRateLimiter,
    RateLimitConfig,
    RateLimitResult,
    RedisAgentRateLimiter,
    create_rate_limiter,
    get_rate_limiter,
)
from .replay_cache_redis import RedisReplayCache
from .schemas import (
    AP2PaymentExecuteRequest,
    AP2PaymentExecuteResponse,
    IngestMandateRequest,
    MandateExecutionResponse,
    X402PaymentExecuteRequest,
    X402PaymentExecuteResponse,
)
from .storage import MandateArchive, ReplayCache, SqliteReplayCache
from .tap import (
    TAP_ALLOWED_MESSAGE_ALGS,
    TAP_ALLOWED_OBJECT_ALGS,
    TAP_ALLOWED_TAGS,
    TAP_MAX_TIME_WINDOW_SECONDS,
    TAP_PROTOCOL_VERSION,
    TAP_SUPPORTED_VERSIONS,
    TapSignatureInput,
    TapVerificationResult,
    build_object_signature_base,
    build_signature_base,
    parse_signature_header,
    parse_signature_input,
    validate_agentic_consumer_object,
    validate_agentic_payment_container,
    validate_tap_headers,
    validate_tap_version,
)
from .tap_keys import (
    select_jwk_by_kid,
    verify_signature_with_jwk,
)
from .verifier import MandateChainVerification, MandateVerifier, VerificationResult

# x402 protocol
with contextlib.suppress(ImportError):
    from .x402 import (
        X402_PAYMENT_REQUIRED_HEADER,
        X402_PAYMENT_RESPONSE_HEADER,
        X402_PAYMENT_SIGNATURE_HEADER,
        X402Challenge,
        X402ChallengeResponse,
        X402HeaderBuilder,
        X402PaymentPayload,
        X402VerificationResult,
        generate_challenge,
        parse_challenge_header,
        serialize_challenge_header,
        validate_x402_version,
        verify_payment_payload,
    )

# x402 ERC-3009 authorization
with contextlib.suppress(ImportError):
    from .x402_erc3009 import (
        ERC3009Authorization,
        build_transfer_authorization,
        encode_authorization_params,
        validate_authorization_timing,
    )

# x402 settlement
with contextlib.suppress(ImportError):
    from .x402_settlement import (
        InMemorySettlementStore,
        X402Settlement,
        X402SettlementStatus,
        X402SettlementStore,
        X402Settler,
    )

# ERC-8128: Signed HTTP Requests
with contextlib.suppress(ImportError):
    from .erc8128 import (
        ERC8128SignatureInput,
        ERC8128VerificationResult,
        build_keyid,
        build_signature_base as erc8128_build_signature_base,
        compute_content_digest,
        parse_signature_input as erc8128_parse_signature_input,
        sign_request as erc8128_sign_request,
        verify_request as erc8128_verify_request,
    )

# ERC-8021: Transaction Attribution
with contextlib.suppress(ImportError):
    from .erc8021 import (
        AttributionData,
        append_attribution,
        decode_attribution,
        encode_attribution,
        has_attribution,
        sardis_attribution,
        strip_attribution,
    )

# ERC-8126: ZK Risk Scoring
with contextlib.suppress(ImportError):
    from .erc8126 import (
        AgentVerification,
        RiskBand,
        VerificationResult as ERC8126VerificationResult,
        VerificationStatus as ERC8126VerificationStatus,
        VerificationType,
        ZKProofCommitment,
        compute_composite_score,
        create_proof_commitment,
        evaluate_etv,
        evaluate_scv,
        evaluate_wav,
        evaluate_wv,
        risk_score_to_normalized,
        score_to_risk_band,
        verify_agent,
    )

# Protocol reason codes
with contextlib.suppress(ImportError):
    from .reason_codes import (
        REASON_CODE_TABLE,
        ProtocolReasonCode,
        ReasonCodeMapping,
        get_reason,
        map_exception_to_reason,
        map_legacy_reason_to_code,
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
    "RedisReplayCache",
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
    # Mandate Cache (AP2 replay protection)
    "MandateCacheConfig",
    "MandateCache",
    "InMemoryMandateCache",
    # Nonce Registry (time-bound nonces)
    "NonceConfig",
    "NonceRegistry",
    "RedisNonceRegistry",
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
    # ERC-8128: Signed HTTP Requests
    "ERC8128SignatureInput",
    "ERC8128VerificationResult",
    "build_keyid",
    "compute_content_digest",
    "erc8128_build_signature_base",
    "erc8128_parse_signature_input",
    "erc8128_sign_request",
    "erc8128_verify_request",
    # ERC-8021: Transaction Attribution
    "AttributionData",
    "encode_attribution",
    "decode_attribution",
    "append_attribution",
    "strip_attribution",
    "has_attribution",
    "sardis_attribution",
    # ERC-8126: ZK Risk Scoring
    "AgentVerification",
    "RiskBand",
    "ERC8126VerificationResult",
    "ERC8126VerificationStatus",
    "VerificationType",
    "ZKProofCommitment",
    "compute_composite_score",
    "create_proof_commitment",
    "evaluate_etv",
    "evaluate_scv",
    "evaluate_wav",
    "evaluate_wv",
    "risk_score_to_normalized",
    "score_to_risk_band",
    "verify_agent",
    # Protocol reason codes
    "ProtocolReasonCode",
    "ReasonCodeMapping",
    "REASON_CODE_TABLE",
    "get_reason",
    "map_exception_to_reason",
    "map_legacy_reason_to_code",
]
