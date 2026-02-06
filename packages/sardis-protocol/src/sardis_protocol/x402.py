"""x402 HTTP 402 Payment Required protocol implementation.

Implements:
- Challenge generation (server -> client, 402 response)
- Payment payload construction and verification (client -> server)
- v2 standardized headers (PAYMENT-SIGNATURE, PAYMENT-RESPONSE)

Reference: https://www.x402.org/
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


# v2 header constants
X402_PAYMENT_SIGNATURE_HEADER = "PAYMENT-SIGNATURE"
X402_PAYMENT_RESPONSE_HEADER = "PAYMENT-RESPONSE"
X402_PAYMENT_REQUIRED_HEADER = "PaymentRequired"

X402_VERSION_1 = "1.0"
X402_VERSION_2 = "2.0"
X402_SUPPORTED_VERSIONS = [X402_VERSION_1, X402_VERSION_2]


@dataclass(slots=True)
class X402Challenge:
    """Server-generated payment challenge (HTTP 402 response body)."""
    payment_id: str
    resource_uri: str
    amount: str  # Amount in smallest unit (string for precision)
    currency: str
    payee_address: str
    network: str  # e.g., "base", "polygon"
    token_address: str  # Contract address of payment token
    expires_at: int  # Unix timestamp
    nonce: str  # Unique per challenge


@dataclass(slots=True)
class X402ChallengeResponse:
    """Wraps the 402 response with header content."""
    challenge: X402Challenge
    http_status: int = 402
    header_value: str = ""  # Serialized for PaymentRequired header

    def __post_init__(self):
        if not self.header_value:
            self.header_value = serialize_challenge_header(self.challenge)


@dataclass(slots=True)
class X402PaymentPayload:
    """Client-constructed payment payload."""
    payment_id: str
    payer_address: str
    amount: str
    nonce: str  # Must match challenge nonce
    signature: str  # Cryptographic signature over canonical payload
    authorization: dict = field(default_factory=dict)  # ERC-3009 fields


@dataclass(slots=True)
class X402VerificationResult:
    """Result of payment payload verification."""
    accepted: bool
    reason: str | None = None
    payload: X402PaymentPayload | None = None


def generate_challenge(
    resource_uri: str,
    amount: str,
    currency: str,
    payee_address: str,
    network: str = "base",
    token_address: str = "",
    ttl_seconds: int = 300,
) -> X402ChallengeResponse:
    """Generate a 402 payment challenge."""
    challenge = X402Challenge(
        payment_id=f"x402_{uuid.uuid4().hex}",
        resource_uri=resource_uri,
        amount=amount,
        currency=currency,
        payee_address=payee_address,
        network=network,
        token_address=token_address,
        expires_at=int(time.time()) + ttl_seconds,
        nonce=uuid.uuid4().hex,
    )
    return X402ChallengeResponse(challenge=challenge)


def serialize_challenge_header(challenge: X402Challenge) -> str:
    """Serialize challenge for the PaymentRequired header (base64-encoded JSON)."""
    data = {
        "payment_id": challenge.payment_id,
        "resource_uri": challenge.resource_uri,
        "amount": challenge.amount,
        "currency": challenge.currency,
        "payee_address": challenge.payee_address,
        "network": challenge.network,
        "token_address": challenge.token_address,
        "expires_at": challenge.expires_at,
        "nonce": challenge.nonce,
    }
    return base64.b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()


def parse_challenge_header(header_value: str) -> X402Challenge:
    """Parse a PaymentRequired header value back to X402Challenge."""
    try:
        data = json.loads(base64.b64decode(header_value))
    except Exception as exc:
        raise ValueError(f"invalid_challenge_header: {exc}") from exc
    return X402Challenge(**data)


def _build_canonical_payload(challenge: X402Challenge, payer_address: str) -> str:
    """Build canonical payload for signature verification."""
    parts = [
        challenge.payment_id,
        payer_address,
        challenge.amount,
        challenge.nonce,
        challenge.payee_address,
        challenge.network,
    ]
    return "|".join(parts)


def verify_payment_payload(
    payload: X402PaymentPayload,
    challenge: X402Challenge,
    *,
    now: int | None = None,
    verify_signature_fn: Callable | None = None,
) -> X402VerificationResult:
    """Verify a payment payload against its challenge."""
    current = now if now is not None else int(time.time())

    # Check expiration
    if challenge.expires_at <= current:
        return X402VerificationResult(False, "x402_challenge_expired")

    # Check nonce match
    if payload.nonce != challenge.nonce:
        return X402VerificationResult(False, "x402_nonce_mismatch")

    # Check amount match
    if payload.amount != challenge.amount:
        return X402VerificationResult(False, "x402_amount_mismatch")

    # Check payment_id match
    if payload.payment_id != challenge.payment_id:
        return X402VerificationResult(False, "x402_payment_id_mismatch")

    # Verify signature if callback provided
    if verify_signature_fn is not None:
        canonical = _build_canonical_payload(challenge, payload.payer_address)
        try:
            verified = bool(verify_signature_fn(canonical.encode(), payload.signature, payload.payer_address))
        except Exception:
            verified = False
        if not verified:
            return X402VerificationResult(False, "x402_signature_invalid")

    return X402VerificationResult(True, payload=payload)


# --- v2 Header Utilities ---

class X402HeaderBuilder:
    """Constructs x402 v2 standardized headers."""

    @staticmethod
    def build_payment_required_header(challenge: X402Challenge) -> dict[str, str]:
        """Build headers for 402 response."""
        return {
            X402_PAYMENT_REQUIRED_HEADER: serialize_challenge_header(challenge),
            "Content-Type": "application/json",
        }

    @staticmethod
    def build_payment_signature_header(payload: X402PaymentPayload) -> dict[str, str]:
        """Build headers for payment request."""
        data = {
            "payment_id": payload.payment_id,
            "payer_address": payload.payer_address,
            "amount": payload.amount,
            "nonce": payload.nonce,
            "signature": payload.signature,
        }
        if payload.authorization:
            data["authorization"] = payload.authorization
        encoded = base64.b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()
        return {X402_PAYMENT_SIGNATURE_HEADER: encoded}

    @staticmethod
    def build_payment_response_header(settlement_data: dict) -> dict[str, str]:
        """Build headers for settlement response."""
        encoded = base64.b64encode(json.dumps(settlement_data, separators=(",", ":")).encode()).decode()
        return {X402_PAYMENT_RESPONSE_HEADER: encoded}

    @staticmethod
    def parse_payment_signature_header(header_value: str) -> X402PaymentPayload:
        """Parse PAYMENT-SIGNATURE header to X402PaymentPayload."""
        try:
            data = json.loads(base64.b64decode(header_value))
        except Exception as exc:
            raise ValueError(f"invalid_payment_signature_header: {exc}") from exc
        return X402PaymentPayload(
            payment_id=data["payment_id"],
            payer_address=data["payer_address"],
            amount=data["amount"],
            nonce=data["nonce"],
            signature=data["signature"],
            authorization=data.get("authorization", {}),
        )


def validate_x402_version(version: str) -> tuple[bool, str | None]:
    """Validate an x402 protocol version."""
    if not version:
        return True, None
    if version in X402_SUPPORTED_VERSIONS:
        return True, None
    return False, f"x402_version_unsupported:{version}"


__all__ = [
    "X402_PAYMENT_SIGNATURE_HEADER",
    "X402_PAYMENT_RESPONSE_HEADER",
    "X402_PAYMENT_REQUIRED_HEADER",
    "X402_VERSION_1",
    "X402_VERSION_2",
    "X402_SUPPORTED_VERSIONS",
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
]
