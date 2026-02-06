"""Deterministic reason code mapping table for all protocol rejection paths.

This module provides standardized error codes and mappings for TAP, AP2, UCP, and x402
protocol verification failures. Each reason code maps to an HTTP status, human-readable
message, and specification reference.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class ProtocolReasonCode(str, Enum):
    """Protocol-specific rejection reason codes."""

    # TAP (Trust Anchor Protocol) - Identity and signature verification
    TAP_HEADER_MISSING = "tap_header_missing"
    TAP_SIGNATURE_INVALID = "tap_signature_invalid"
    TAP_NONCE_REPLAYED = "tap_nonce_replayed"
    TAP_SIGNATURE_EXPIRED = "tap_signature_expired"
    TAP_ALGORITHM_UNSUPPORTED = "tap_algorithm_unsupported"
    TAP_VERSION_UNSUPPORTED = "tap_version_unsupported"
    TAP_REQUIRED_COMPONENTS_MISSING = "tap_required_components_missing"
    TAP_TAG_INVALID = "tap_tag_invalid"
    TAP_CREATED_NOT_IN_PAST = "tap_created_not_in_past"
    TAP_WINDOW_TOO_LARGE = "tap_window_too_large"
    TAP_LABEL_MISMATCH = "tap_label_mismatch"

    # AP2 (Agent Payment Protocol) - Mandate chain verification
    AP2_INTENT_MISSING = "ap2_intent_missing"
    AP2_CART_MISSING = "ap2_cart_missing"
    AP2_PAYMENT_MISSING = "ap2_payment_missing"
    AP2_SUBJECT_MISMATCH = "ap2_subject_mismatch"
    AP2_MANDATE_EXPIRED = "ap2_mandate_expired"
    AP2_AMOUNT_OVERFLOW = "ap2_amount_overflow"
    AP2_DOMAIN_INVALID = "ap2_domain_invalid"
    AP2_MANDATE_REPLAYED = "ap2_mandate_replayed"
    AP2_AGENT_PRESENCE_MISSING = "ap2_agent_presence_missing"
    AP2_MODALITY_INVALID = "ap2_modality_invalid"
    AP2_SIGNATURE_MALFORMED = "ap2_signature_malformed"
    AP2_SIGNATURE_INVALID = "ap2_signature_invalid"
    AP2_TYPE_PURPOSE_MISMATCH = "ap2_type_purpose_mismatch"
    AP2_SECURITY_LOCK = "ap2_security_lock"
    AP2_VERSION_INVALID = "ap2_version_invalid"
    AP2_IDENTITY_NOT_RESOLVED = "ap2_identity_not_resolved"
    AP2_DOMAIN_NOT_AUTHORIZED = "ap2_domain_not_authorized"
    AP2_RATE_LIMITED = "ap2_rate_limited"
    AP2_PAYMENT_EXCEEDS_CART = "ap2_payment_exceeds_cart"
    AP2_PAYMENT_EXCEEDS_INTENT = "ap2_payment_exceeds_intent"

    # UCP (Universal Checkout Protocol) - Session and escalation management
    UCP_SESSION_NOT_FOUND = "ucp_session_not_found"
    UCP_SESSION_EXPIRED = "ucp_session_expired"
    UCP_ESCALATION_REQUIRED = "ucp_escalation_required"
    UCP_SECURITY_LOCK = "ucp_security_lock"
    UCP_PROFILE_INCOMPATIBLE = "ucp_profile_incompatible"
    UCP_VERSION_UNSUPPORTED = "ucp_version_unsupported"
    UCP_INVALID_OPERATION = "ucp_invalid_operation"
    UCP_EMPTY_CART = "ucp_empty_cart"

    # x402 (Payment Required Protocol) - Micropayment authorization
    X402_CHALLENGE_EXPIRED = "x402_challenge_expired"
    X402_NONCE_MISMATCH = "x402_nonce_mismatch"
    X402_AMOUNT_MISMATCH = "x402_amount_mismatch"
    X402_SIGNATURE_INVALID = "x402_signature_invalid"
    X402_SETTLEMENT_FAILED = "x402_settlement_failed"
    X402_VERSION_UNSUPPORTED = "x402_version_unsupported"
    X402_AUTHORIZATION_TIMING_INVALID = "x402_authorization_timing_invalid"


@dataclass
class ReasonCodeMapping:
    """Maps a reason code to HTTP status, message, and spec reference."""

    code: ProtocolReasonCode
    http_status: int
    human_message: str
    spec_reference: str


# Deterministic mapping table for all protocol rejection paths
REASON_CODE_TABLE: Dict[ProtocolReasonCode, ReasonCodeMapping] = {
    # TAP - Trust Anchor Protocol
    ProtocolReasonCode.TAP_HEADER_MISSING: ReasonCodeMapping(
        code=ProtocolReasonCode.TAP_HEADER_MISSING,
        http_status=400,
        human_message="Required TAP signature headers are missing",
        spec_reference="TAP Merchant Guidance §3.1 - Message Signature Headers",
    ),
    ProtocolReasonCode.TAP_SIGNATURE_INVALID: ReasonCodeMapping(
        code=ProtocolReasonCode.TAP_SIGNATURE_INVALID,
        http_status=401,
        human_message="TAP signature verification failed",
        spec_reference="TAP Merchant Guidance §3.2 - Signature Verification",
    ),
    ProtocolReasonCode.TAP_NONCE_REPLAYED: ReasonCodeMapping(
        code=ProtocolReasonCode.TAP_NONCE_REPLAYED,
        http_status=409,
        human_message="TAP nonce has already been used",
        spec_reference="TAP Merchant Guidance §3.3 - Replay Protection",
    ),
    ProtocolReasonCode.TAP_SIGNATURE_EXPIRED: ReasonCodeMapping(
        code=ProtocolReasonCode.TAP_SIGNATURE_EXPIRED,
        http_status=410,
        human_message="TAP signature has expired",
        spec_reference="TAP Merchant Guidance §3.4 - Temporal Validity",
    ),
    ProtocolReasonCode.TAP_ALGORITHM_UNSUPPORTED: ReasonCodeMapping(
        code=ProtocolReasonCode.TAP_ALGORITHM_UNSUPPORTED,
        http_status=400,
        human_message="TAP signature algorithm is not supported",
        spec_reference="TAP Merchant Guidance §2.2 - Supported Algorithms",
    ),
    ProtocolReasonCode.TAP_VERSION_UNSUPPORTED: ReasonCodeMapping(
        code=ProtocolReasonCode.TAP_VERSION_UNSUPPORTED,
        http_status=400,
        human_message="TAP protocol version is not supported",
        spec_reference="TAP Merchant Guidance §1.3 - Protocol Versioning",
    ),
    ProtocolReasonCode.TAP_REQUIRED_COMPONENTS_MISSING: ReasonCodeMapping(
        code=ProtocolReasonCode.TAP_REQUIRED_COMPONENTS_MISSING,
        http_status=400,
        human_message="Required signature components (@authority, @path) are missing",
        spec_reference="TAP Merchant Guidance §3.1.2 - Required Components",
    ),
    ProtocolReasonCode.TAP_TAG_INVALID: ReasonCodeMapping(
        code=ProtocolReasonCode.TAP_TAG_INVALID,
        http_status=400,
        human_message="TAP signature tag is invalid or not allowed",
        spec_reference="TAP Merchant Guidance §3.1.3 - Tag Semantics",
    ),
    ProtocolReasonCode.TAP_CREATED_NOT_IN_PAST: ReasonCodeMapping(
        code=ProtocolReasonCode.TAP_CREATED_NOT_IN_PAST,
        http_status=422,
        human_message="TAP signature created timestamp must be in the past",
        spec_reference="TAP Merchant Guidance §3.4.1 - Timestamp Validation",
    ),
    ProtocolReasonCode.TAP_WINDOW_TOO_LARGE: ReasonCodeMapping(
        code=ProtocolReasonCode.TAP_WINDOW_TOO_LARGE,
        http_status=422,
        human_message="TAP signature validity window exceeds maximum allowed duration",
        spec_reference="TAP Merchant Guidance §3.4.2 - Window Constraints",
    ),
    ProtocolReasonCode.TAP_LABEL_MISMATCH: ReasonCodeMapping(
        code=ProtocolReasonCode.TAP_LABEL_MISMATCH,
        http_status=400,
        human_message="TAP signature label does not match signature-input label",
        spec_reference="TAP Merchant Guidance §3.1.4 - Label Consistency",
    ),

    # AP2 - Agent Payment Protocol
    ProtocolReasonCode.AP2_INTENT_MISSING: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_INTENT_MISSING,
        http_status=400,
        human_message="Intent mandate is required but not provided",
        spec_reference="AP2 Specification §4.1 - Mandate Chain Structure",
    ),
    ProtocolReasonCode.AP2_CART_MISSING: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_CART_MISSING,
        http_status=400,
        human_message="Cart mandate is required but not provided",
        spec_reference="AP2 Specification §4.2 - Cart Requirements",
    ),
    ProtocolReasonCode.AP2_PAYMENT_MISSING: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_PAYMENT_MISSING,
        http_status=400,
        human_message="Payment mandate is required but not provided",
        spec_reference="AP2 Specification §4.3 - Payment Execution",
    ),
    ProtocolReasonCode.AP2_SUBJECT_MISMATCH: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_SUBJECT_MISMATCH,
        http_status=422,
        human_message="Agent subject must be identical across all mandates in chain",
        spec_reference="AP2 Specification §4.4 - Chain Consistency",
    ),
    ProtocolReasonCode.AP2_MANDATE_EXPIRED: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_MANDATE_EXPIRED,
        http_status=410,
        human_message="One or more mandates in the chain have expired",
        spec_reference="AP2 Specification §5.2 - Temporal Validity",
    ),
    ProtocolReasonCode.AP2_AMOUNT_OVERFLOW: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_AMOUNT_OVERFLOW,
        http_status=422,
        human_message="Payment amount causes arithmetic overflow",
        spec_reference="AP2 Specification §5.3 - Amount Validation",
    ),
    ProtocolReasonCode.AP2_DOMAIN_INVALID: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_DOMAIN_INVALID,
        http_status=400,
        human_message="Mandate domain is malformed or invalid",
        spec_reference="AP2 Specification §5.4 - Domain Requirements",
    ),
    ProtocolReasonCode.AP2_MANDATE_REPLAYED: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_MANDATE_REPLAYED,
        http_status=409,
        human_message="Mandate has already been processed (replay detected)",
        spec_reference="AP2 Specification §6.1 - Replay Protection",
    ),
    ProtocolReasonCode.AP2_AGENT_PRESENCE_MISSING: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_AGENT_PRESENCE_MISSING,
        http_status=422,
        human_message="Payment mandate must declare ai_agent_presence=true",
        spec_reference="AP2 Specification §4.3.2 - Agent Presence Declaration",
    ),
    ProtocolReasonCode.AP2_MODALITY_INVALID: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_MODALITY_INVALID,
        http_status=422,
        human_message="Transaction modality must be human_present or human_not_present",
        spec_reference="AP2 Specification §4.3.3 - Transaction Modality",
    ),
    ProtocolReasonCode.AP2_SIGNATURE_MALFORMED: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_SIGNATURE_MALFORMED,
        http_status=400,
        human_message="Mandate signature is not valid base64 encoding",
        spec_reference="AP2 Specification §5.5 - Signature Format",
    ),
    ProtocolReasonCode.AP2_SIGNATURE_INVALID: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_SIGNATURE_INVALID,
        http_status=401,
        human_message="Mandate signature verification failed",
        spec_reference="AP2 Specification §5.6 - Signature Verification",
    ),
    ProtocolReasonCode.AP2_TYPE_PURPOSE_MISMATCH: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_TYPE_PURPOSE_MISMATCH,
        http_status=422,
        human_message="Mandate type and purpose fields are inconsistent",
        spec_reference="AP2 Specification §4.5 - Type-Purpose Alignment",
    ),
    ProtocolReasonCode.AP2_SECURITY_LOCK: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_SECURITY_LOCK,
        http_status=403,
        human_message="Transaction blocked by security policy",
        spec_reference="AP2 Specification §7.1 - Security Controls",
    ),
    ProtocolReasonCode.AP2_VERSION_INVALID: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_VERSION_INVALID,
        http_status=400,
        human_message="AP2 protocol version is not supported",
        spec_reference="AP2 Specification §1.2 - Protocol Versioning",
    ),
    ProtocolReasonCode.AP2_IDENTITY_NOT_RESOLVED: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_IDENTITY_NOT_RESOLVED,
        http_status=401,
        human_message="Agent identity could not be verified or resolved",
        spec_reference="AP2 Specification §6.2 - Identity Resolution",
    ),
    ProtocolReasonCode.AP2_DOMAIN_NOT_AUTHORIZED: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_DOMAIN_NOT_AUTHORIZED,
        http_status=403,
        human_message="Agent domain is not authorized for transactions",
        spec_reference="AP2 Specification §6.3 - Domain Authorization",
    ),
    ProtocolReasonCode.AP2_RATE_LIMITED: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_RATE_LIMITED,
        http_status=429,
        human_message="Agent has exceeded transaction rate limits",
        spec_reference="AP2 Specification §7.2 - Rate Limiting",
    ),
    ProtocolReasonCode.AP2_PAYMENT_EXCEEDS_CART: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_PAYMENT_EXCEEDS_CART,
        http_status=422,
        human_message="Payment amount exceeds cart total (subtotal + taxes)",
        spec_reference="AP2 Specification §4.6 - Amount Bounds Checking",
    ),
    ProtocolReasonCode.AP2_PAYMENT_EXCEEDS_INTENT: ReasonCodeMapping(
        code=ProtocolReasonCode.AP2_PAYMENT_EXCEEDS_INTENT,
        http_status=422,
        human_message="Payment amount exceeds intent requested amount",
        spec_reference="AP2 Specification §4.7 - Intent Amount Validation",
    ),

    # UCP - Universal Checkout Protocol
    ProtocolReasonCode.UCP_SESSION_NOT_FOUND: ReasonCodeMapping(
        code=ProtocolReasonCode.UCP_SESSION_NOT_FOUND,
        http_status=404,
        human_message="Checkout session does not exist or cannot be found",
        spec_reference="UCP Specification §3.1 - Session Management",
    ),
    ProtocolReasonCode.UCP_SESSION_EXPIRED: ReasonCodeMapping(
        code=ProtocolReasonCode.UCP_SESSION_EXPIRED,
        http_status=410,
        human_message="Checkout session has expired and cannot be resumed",
        spec_reference="UCP Specification §3.2 - Session Expiration",
    ),
    ProtocolReasonCode.UCP_ESCALATION_REQUIRED: ReasonCodeMapping(
        code=ProtocolReasonCode.UCP_ESCALATION_REQUIRED,
        http_status=403,
        human_message="Transaction requires human escalation and approval",
        spec_reference="UCP Specification §4.1 - Escalation Triggers",
    ),
    ProtocolReasonCode.UCP_SECURITY_LOCK: ReasonCodeMapping(
        code=ProtocolReasonCode.UCP_SECURITY_LOCK,
        http_status=403,
        human_message="Checkout session locked due to security policy",
        spec_reference="UCP Specification §5.1 - Security Controls",
    ),
    ProtocolReasonCode.UCP_PROFILE_INCOMPATIBLE: ReasonCodeMapping(
        code=ProtocolReasonCode.UCP_PROFILE_INCOMPATIBLE,
        http_status=422,
        human_message="Agent profile is incompatible with checkout requirements",
        spec_reference="UCP Specification §4.2 - Profile Compatibility",
    ),
    ProtocolReasonCode.UCP_VERSION_UNSUPPORTED: ReasonCodeMapping(
        code=ProtocolReasonCode.UCP_VERSION_UNSUPPORTED,
        http_status=400,
        human_message="UCP protocol version is not supported",
        spec_reference="UCP Specification §1.2 - Protocol Versioning",
    ),
    ProtocolReasonCode.UCP_INVALID_OPERATION: ReasonCodeMapping(
        code=ProtocolReasonCode.UCP_INVALID_OPERATION,
        http_status=400,
        human_message="Operation is not valid for current session state",
        spec_reference="UCP Specification §3.3 - State Transitions",
    ),
    ProtocolReasonCode.UCP_EMPTY_CART: ReasonCodeMapping(
        code=ProtocolReasonCode.UCP_EMPTY_CART,
        http_status=422,
        human_message="Cart is empty and cannot proceed to checkout",
        spec_reference="UCP Specification §4.3 - Cart Validation",
    ),

    # x402 - Payment Required Protocol
    ProtocolReasonCode.X402_CHALLENGE_EXPIRED: ReasonCodeMapping(
        code=ProtocolReasonCode.X402_CHALLENGE_EXPIRED,
        http_status=410,
        human_message="Payment challenge has expired and must be re-issued",
        spec_reference="x402 Specification §3.1 - Challenge Lifetime",
    ),
    ProtocolReasonCode.X402_NONCE_MISMATCH: ReasonCodeMapping(
        code=ProtocolReasonCode.X402_NONCE_MISMATCH,
        http_status=422,
        human_message="Authorization nonce does not match challenge nonce",
        spec_reference="x402 Specification §3.2 - Nonce Binding",
    ),
    ProtocolReasonCode.X402_AMOUNT_MISMATCH: ReasonCodeMapping(
        code=ProtocolReasonCode.X402_AMOUNT_MISMATCH,
        http_status=422,
        human_message="Authorized amount does not match challenge amount",
        spec_reference="x402 Specification §3.3 - Amount Integrity",
    ),
    ProtocolReasonCode.X402_SIGNATURE_INVALID: ReasonCodeMapping(
        code=ProtocolReasonCode.X402_SIGNATURE_INVALID,
        http_status=401,
        human_message="Payment authorization signature is invalid",
        spec_reference="x402 Specification §4.1 - Signature Verification",
    ),
    ProtocolReasonCode.X402_SETTLEMENT_FAILED: ReasonCodeMapping(
        code=ProtocolReasonCode.X402_SETTLEMENT_FAILED,
        http_status=502,
        human_message="Payment settlement failed at payment processor",
        spec_reference="x402 Specification §5.1 - Settlement Handling",
    ),
    ProtocolReasonCode.X402_VERSION_UNSUPPORTED: ReasonCodeMapping(
        code=ProtocolReasonCode.X402_VERSION_UNSUPPORTED,
        http_status=400,
        human_message="x402 protocol version is not supported",
        spec_reference="x402 Specification §1.2 - Protocol Versioning",
    ),
    ProtocolReasonCode.X402_AUTHORIZATION_TIMING_INVALID: ReasonCodeMapping(
        code=ProtocolReasonCode.X402_AUTHORIZATION_TIMING_INVALID,
        http_status=422,
        human_message="Authorization received outside valid timing window",
        spec_reference="x402 Specification §3.4 - Timing Constraints",
    ),
}


def get_reason(code: ProtocolReasonCode) -> ReasonCodeMapping:
    """Get the reason code mapping for a protocol rejection.

    Args:
        code: The protocol reason code to look up

    Returns:
        ReasonCodeMapping with HTTP status, message, and spec reference

    Raises:
        KeyError: If the reason code is not found in the mapping table
    """
    return REASON_CODE_TABLE[code]


def map_legacy_reason_to_code(reason: str) -> ProtocolReasonCode | None:
    """Map legacy string reason codes to the new enum codes.

    This provides backward compatibility with existing verifier.py reason strings.

    Args:
        reason: Legacy string reason from verifier.py

    Returns:
        Corresponding ProtocolReasonCode or None if not mappable
    """
    # Direct mappings from verifier.py
    legacy_map: Dict[str, ProtocolReasonCode] = {
        "mandate_expired": ProtocolReasonCode.AP2_MANDATE_EXPIRED,
        "domain_not_authorized": ProtocolReasonCode.AP2_DOMAIN_NOT_AUTHORIZED,
        "mandate_replayed": ProtocolReasonCode.AP2_MANDATE_REPLAYED,
        "identity_not_resolved": ProtocolReasonCode.AP2_IDENTITY_NOT_RESOLVED,
        "signature_malformed": ProtocolReasonCode.AP2_SIGNATURE_MALFORMED,
        "signature_invalid": ProtocolReasonCode.AP2_SIGNATURE_INVALID,
        "subject_mismatch": ProtocolReasonCode.AP2_SUBJECT_MISMATCH,
        "payment_exceeds_cart_total": ProtocolReasonCode.AP2_PAYMENT_EXCEEDS_CART,
        "payment_exceeds_intent_amount": ProtocolReasonCode.AP2_PAYMENT_EXCEEDS_INTENT,
        "payment_agent_presence_required": ProtocolReasonCode.AP2_AGENT_PRESENCE_MISSING,
        "payment_invalid_modality": ProtocolReasonCode.AP2_MODALITY_INVALID,
        "intent_invalid_type": ProtocolReasonCode.AP2_TYPE_PURPOSE_MISMATCH,
        "cart_invalid_type": ProtocolReasonCode.AP2_TYPE_PURPOSE_MISMATCH,
        "payment_invalid_type": ProtocolReasonCode.AP2_TYPE_PURPOSE_MISMATCH,

        # Rate limiter reasons
        "rate_limit_minute": ProtocolReasonCode.AP2_RATE_LIMITED,
        "rate_limit_hour": ProtocolReasonCode.AP2_RATE_LIMITED,
        "rate_limit_day": ProtocolReasonCode.AP2_RATE_LIMITED,

        # TAP reasons from tap.py
        "tap_signature_input_invalid": ProtocolReasonCode.TAP_HEADER_MISSING,
        "tap_signature_invalid": ProtocolReasonCode.TAP_SIGNATURE_INVALID,
        "tap_signature_label_mismatch": ProtocolReasonCode.TAP_LABEL_MISMATCH,
        "tap_required_components_missing": ProtocolReasonCode.TAP_REQUIRED_COMPONENTS_MISSING,
        "tap_tag_invalid": ProtocolReasonCode.TAP_TAG_INVALID,
        "tap_alg_invalid": ProtocolReasonCode.TAP_ALGORITHM_UNSUPPORTED,
        "tap_created_not_in_past": ProtocolReasonCode.TAP_CREATED_NOT_IN_PAST,
        "tap_expired": ProtocolReasonCode.TAP_SIGNATURE_EXPIRED,
        "tap_window_too_large": ProtocolReasonCode.TAP_WINDOW_TOO_LARGE,
        "tap_nonce_replayed": ProtocolReasonCode.TAP_NONCE_REPLAYED,
        "tap_signature_verification_failed": ProtocolReasonCode.TAP_SIGNATURE_INVALID,
    }

    # Handle prefixed reasons (e.g., "intent_signature_invalid" -> AP2_SIGNATURE_INVALID)
    if reason.startswith("intent_") or reason.startswith("cart_"):
        base_reason = reason.split("_", 1)[1]
        if base_reason in legacy_map:
            return legacy_map[base_reason]

    return legacy_map.get(reason)


def map_exception_to_reason(exc: Exception) -> ProtocolReasonCode | None:
    """Map known exceptions to protocol reason codes.

    Args:
        exc: Exception instance to map

    Returns:
        Corresponding ProtocolReasonCode or None if not mappable
    """
    exc_type = type(exc).__name__
    exc_msg = str(exc).lower()

    # Map by exception type
    if exc_type in ("KeyError", "TypeError", "ValueError"):
        if "signature" in exc_msg:
            return ProtocolReasonCode.AP2_SIGNATURE_MALFORMED
        if "expired" in exc_msg or "expir" in exc_msg:
            return ProtocolReasonCode.AP2_MANDATE_EXPIRED
        if "domain" in exc_msg:
            return ProtocolReasonCode.AP2_DOMAIN_INVALID
        # Default for parsing errors
        return ProtocolReasonCode.AP2_INTENT_MISSING

    # Rate limit exceptions
    if "rate" in exc_msg and "limit" in exc_msg:
        return ProtocolReasonCode.AP2_RATE_LIMITED

    # Identity/auth exceptions
    if "identity" in exc_msg or "auth" in exc_msg:
        return ProtocolReasonCode.AP2_IDENTITY_NOT_RESOLVED

    return None


__all__ = [
    "ProtocolReasonCode",
    "ReasonCodeMapping",
    "REASON_CODE_TABLE",
    "get_reason",
    "map_legacy_reason_to_code",
    "map_exception_to_reason",
]
