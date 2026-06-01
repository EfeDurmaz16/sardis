"""Canonical x402 v1 wire format (de)serialization.

Implements the EXACT structures from the x402 Foundation v1 specification so
Sardis can interoperate with real x402 clients/facilitators (CDP, Stripe,
x402-fetch, etc.). This module is pure (de)serialization + validation — it
performs NO signature recovery and NO money movement; the EIP-3009/EIP-712
crypto stays in ``x402_erc3009.py`` and is invoked by the facilitator route.

Primary sources (fetched 2026-06):
- Core spec: github.com/x402-foundation/x402 ``specs/x402-specification-v1.md``
  §5 (PaymentRequirements / PaymentPayload / SettlementResponse), §7
  (facilitator /verify /settle /supported), §9 (error codes).
- HTTP transport: ``specs/transports-v1/http.md`` (X-PAYMENT /
  X-PAYMENT-RESPONSE base64 headers, 402 JSON body).
- exact-EVM scheme: ``specs/schemes/exact/scheme_exact_evm.md``.
- Network ids / chainIds: ``python/legacy/src/x402/chains.py`` (NETWORK_TO_ID)
  and ``go/mechanisms/evm/v1/network.go`` (NetworkChainIDs).

Canonical wire structures:
- 402 body ``PaymentRequirementsResponse`` = ``{x402Version, error, accepts:[PaymentRequirements]}``.
- ``X-PAYMENT`` request header = base64(JSON ``PaymentPayload``) =
  ``{x402Version, scheme, network, payload:{signature, authorization{from,to,value,validAfter,validBefore,nonce}}}``.
- ``X-PAYMENT-RESPONSE`` response header = base64(JSON ``SettlementResponse``) =
  ``{success, transaction, network, payer, errorReason?}``.
- Facilitator ``/verify`` & ``/settle`` request = ``{x402Version, paymentPayload, paymentRequirements}``.

Standard base64 (not url-safe) is used per the spec's published header
examples (decode round-trips verified against the spec golden vector).
"""
from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

X402_VERSION = 1
EXACT_SCHEME = "exact"

# Canonical HTTP transport header names (v1).
X_PAYMENT_HEADER = "X-PAYMENT"
X_PAYMENT_RESPONSE_HEADER = "X-PAYMENT-RESPONSE"


# ---------------------------------------------------------------------------
# Canonical error / reason codes (spec §9). Used verbatim on the wire as
# ``invalidReason`` (/verify) and ``errorReason`` (/settle, X-PAYMENT-RESPONSE).
# ---------------------------------------------------------------------------

class X402ErrorCode(str, Enum):
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INVALID_VALID_AFTER = "invalid_exact_evm_payload_authorization_valid_after"
    INVALID_VALID_BEFORE = "invalid_exact_evm_payload_authorization_valid_before"
    INVALID_VALUE = "invalid_exact_evm_payload_authorization_value"
    INVALID_SIGNATURE = "invalid_exact_evm_payload_signature"
    RECIPIENT_MISMATCH = "invalid_exact_evm_payload_recipient_mismatch"
    INVALID_NETWORK = "invalid_network"
    INVALID_PAYLOAD = "invalid_payload"
    INVALID_PAYMENT_REQUIREMENTS = "invalid_payment_requirements"
    INVALID_SCHEME = "invalid_scheme"
    UNSUPPORTED_SCHEME = "unsupported_scheme"
    INVALID_X402_VERSION = "invalid_x402_version"
    INVALID_TRANSACTION_STATE = "invalid_transaction_state"
    UNEXPECTED_VERIFY_ERROR = "unexpected_verify_error"
    UNEXPECTED_SETTLE_ERROR = "unexpected_settle_error"


# Map internal x402_erc3009 verify reasons -> canonical invalidReason codes.
# The internal reasons remain for logging; the wire carries the canonical code.
_INTERNAL_REASON_TO_CANONICAL: dict[str, X402ErrorCode] = {
    "authorization_not_yet_valid": X402ErrorCode.INVALID_VALID_AFTER,
    "authorization_expired": X402ErrorCode.INVALID_VALID_BEFORE,
    "valid_after_must_be_before_valid_before": X402ErrorCode.INVALID_VALID_BEFORE,
    "signer_mismatch_authorization_from": X402ErrorCode.INVALID_SIGNATURE,
    "signer_mismatch_payer_address": X402ErrorCode.INVALID_SIGNATURE,
    "signature_not_hex": X402ErrorCode.INVALID_SIGNATURE,
    "eth_account_not_installed": X402ErrorCode.UNEXPECTED_VERIFY_ERROR,
}


def canonical_invalid_reason(internal_reason: str | None) -> X402ErrorCode:
    """Translate an internal verify reason string to a canonical error code.

    Fail-closed: an unknown / missing reason maps to ``invalid_exact_evm_payload_signature``
    only when it is clearly signature-shaped, otherwise ``invalid_payload``.
    Recognized prefixes (``signature_bad_length:``, ``recovery_failed:``,
    ``unsupported_network_for_eip3009:``) are mapped explicitly.
    """
    if internal_reason is None:
        return X402ErrorCode.INVALID_PAYLOAD
    if internal_reason in _INTERNAL_REASON_TO_CANONICAL:
        return _INTERNAL_REASON_TO_CANONICAL[internal_reason]
    if internal_reason.startswith("signature_bad_length:") or internal_reason.startswith(
        "recovery_failed:"
    ):
        return X402ErrorCode.INVALID_SIGNATURE
    if internal_reason.startswith("unsupported_network_for_eip3009:"):
        return X402ErrorCode.INVALID_NETWORK
    return X402ErrorCode.INVALID_PAYLOAD


class X402WireError(ValueError):
    """Raised when a canonical x402 wire structure is malformed.

    Carries a canonical ``code`` so the route can surface it verbatim.
    """

    def __init__(self, code: X402ErrorCode, detail: str = "") -> None:
        self.code = code
        super().__init__(f"{code.value}{(': ' + detail) if detail else ''}")


# ---------------------------------------------------------------------------
# Network identifier mapping: canonical x402 network id <-> Sardis network id
# <-> chainId. Sourced from x402 chains.py / network.go and cross-checked
# against the EIP-712 domains in x402_erc3009.py (chainId must match the domain
# Sardis signs against — a mismatch would bind a signature to the wrong chain).
# Fail-closed: unknown network -> invalid_network.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _NetworkEntry:
    canonical: str  # x402 v1 wire id (hyphenated)
    sardis: str     # Sardis internal id (used to resolve EIP-712 domain)
    chain_id: int


# Only networks for which Sardis has a verified EIP-712 USDC domain
# (x402_erc3009._USDC_EIP712_DOMAINS) are listed. canonical/chainId values are
# the x402-Foundation-defined ones; base/base-sepolia/ethereum/polygon are in
# the canonical v1 network set, arbitrum/optimism are Sardis-supported chains
# carried with their standard hyphenated ids + chainIds.
_NETWORKS: tuple[_NetworkEntry, ...] = (
    _NetworkEntry("base", "base", 8453),
    _NetworkEntry("base-sepolia", "base_sepolia", 84532),
    _NetworkEntry("ethereum", "ethereum", 1),
    _NetworkEntry("polygon", "polygon", 137),
    _NetworkEntry("arbitrum", "arbitrum", 42161),
    _NetworkEntry("optimism", "optimism", 10),
)

_CANONICAL_TO_ENTRY: dict[str, _NetworkEntry] = {e.canonical: e for e in _NETWORKS}
_SARDIS_TO_ENTRY: dict[str, _NetworkEntry] = {e.sardis: e for e in _NETWORKS}


def canonical_network_to_sardis(network: str) -> str:
    """Map a canonical x402 network id (e.g. ``base-sepolia``) to the Sardis id.

    Raises:
        X402WireError(invalid_network): if the network is unknown / unsupported.
    """
    entry = _CANONICAL_TO_ENTRY.get((network or "").strip())
    if entry is None:
        raise X402WireError(X402ErrorCode.INVALID_NETWORK, network or "<empty>")
    return entry.sardis


def sardis_network_to_canonical(network: str) -> str:
    """Map a Sardis network id (e.g. ``base_sepolia``) to the canonical x402 id."""
    entry = _SARDIS_TO_ENTRY.get((network or "").strip())
    if entry is None:
        raise X402WireError(X402ErrorCode.INVALID_NETWORK, network or "<empty>")
    return entry.canonical


def canonical_network_chain_id(network: str) -> int:
    """Return the chainId for a canonical x402 network id (fail-closed)."""
    entry = _CANONICAL_TO_ENTRY.get((network or "").strip())
    if entry is None:
        raise X402WireError(X402ErrorCode.INVALID_NETWORK, network or "<empty>")
    return entry.chain_id


def supported_canonical_networks() -> list[str]:
    """All canonical network ids Sardis can verify (stable order)."""
    return [e.canonical for e in _NETWORKS]


# ---------------------------------------------------------------------------
# Canonical dataclasses (spec §5)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PaymentRequirements:
    """A single entry in the 402 ``accepts`` array (spec §5.1.2)."""

    scheme: str
    network: str
    max_amount_required: str
    asset: str
    pay_to: str
    resource: str
    description: str
    max_timeout_seconds: int
    mime_type: str | None = None
    output_schema: Any | None = None
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "scheme": self.scheme,
            "network": self.network,
            "maxAmountRequired": self.max_amount_required,
            "asset": self.asset,
            "payTo": self.pay_to,
            "resource": self.resource,
            "description": self.description,
            "maxTimeoutSeconds": self.max_timeout_seconds,
        }
        # Optional fields: emit even when None for mimeType/outputSchema to mirror
        # the spec example (which shows outputSchema: null), but omit extra when None.
        d["mimeType"] = self.mime_type
        d["outputSchema"] = self.output_schema
        if self.extra is not None:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PaymentRequirements:
        if not isinstance(data, dict):
            raise X402WireError(X402ErrorCode.INVALID_PAYMENT_REQUIREMENTS, "not an object")
        try:
            return cls(
                scheme=str(data["scheme"]),
                network=str(data["network"]),
                max_amount_required=str(data["maxAmountRequired"]),
                asset=str(data["asset"]),
                pay_to=str(data["payTo"]),
                resource=str(data["resource"]),
                description=str(data["description"]),
                max_timeout_seconds=int(data["maxTimeoutSeconds"]),
                mime_type=data.get("mimeType"),
                output_schema=data.get("outputSchema"),
                extra=data.get("extra"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise X402WireError(
                X402ErrorCode.INVALID_PAYMENT_REQUIREMENTS, str(exc)
            ) from exc


@dataclass(slots=True)
class ExactEvmAuthorization:
    """EIP-3009 TransferWithAuthorization fields (spec §5.2.2 Authorization)."""

    from_: str
    to: str
    value: str
    valid_after: str
    valid_before: str
    nonce: str

    def to_dict(self) -> dict[str, str]:
        return {
            "from": self.from_,
            "to": self.to,
            "value": self.value,
            "validAfter": self.valid_after,
            "validBefore": self.valid_before,
            "nonce": self.nonce,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExactEvmAuthorization:
        if not isinstance(data, dict):
            raise X402WireError(X402ErrorCode.INVALID_PAYLOAD, "authorization not an object")
        try:
            return cls(
                from_=str(data["from"]),
                to=str(data["to"]),
                value=str(data["value"]),
                valid_after=str(data["validAfter"]),
                valid_before=str(data["validBefore"]),
                nonce=str(data["nonce"]),
            )
        except (KeyError, TypeError) as exc:
            raise X402WireError(X402ErrorCode.INVALID_PAYLOAD, f"authorization: {exc}") from exc


@dataclass(slots=True)
class PaymentPayload:
    """Canonical ``X-PAYMENT`` payload (spec §5.2)."""

    scheme: str
    network: str
    signature: str
    authorization: ExactEvmAuthorization
    x402_version: int = X402_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "x402Version": self.x402_version,
            "scheme": self.scheme,
            "network": self.network,
            "payload": {
                "signature": self.signature,
                "authorization": self.authorization.to_dict(),
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PaymentPayload:
        if not isinstance(data, dict):
            raise X402WireError(X402ErrorCode.INVALID_PAYLOAD, "not an object")
        version = data.get("x402Version")
        if version != X402_VERSION:
            raise X402WireError(X402ErrorCode.INVALID_X402_VERSION, str(version))
        scheme = data.get("scheme")
        if scheme != EXACT_SCHEME:
            # Unknown scheme is unsupported (fail-closed) — only "exact" is implemented.
            raise X402WireError(X402ErrorCode.UNSUPPORTED_SCHEME, str(scheme))
        inner = data.get("payload")
        if not isinstance(inner, dict):
            raise X402WireError(X402ErrorCode.INVALID_PAYLOAD, "missing payload object")
        signature = inner.get("signature")
        if not isinstance(signature, str) or not signature:
            raise X402WireError(X402ErrorCode.INVALID_PAYLOAD, "missing signature")
        auth = ExactEvmAuthorization.from_dict(inner.get("authorization", {}))
        return cls(
            scheme=scheme,
            network=str(data["network"]),
            signature=signature,
            authorization=auth,
            x402_version=version,
        )


@dataclass(slots=True)
class SettlementResponse:
    """Canonical ``X-PAYMENT-RESPONSE`` payload (spec §5.3)."""

    success: bool
    transaction: str
    network: str
    payer: str
    error_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "success": self.success,
            "transaction": self.transaction,
            "network": self.network,
            "payer": self.payer,
        }
        if not self.success and self.error_reason is not None:
            d["errorReason"] = self.error_reason
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SettlementResponse:
        if not isinstance(data, dict):
            raise X402WireError(X402ErrorCode.INVALID_PAYLOAD, "not an object")
        return cls(
            success=bool(data["success"]),
            transaction=str(data.get("transaction", "")),
            network=str(data["network"]),
            payer=str(data["payer"]),
            error_reason=data.get("errorReason"),
        )


@dataclass(slots=True)
class PaymentRequirementsResponse:
    """Canonical HTTP 402 JSON body (spec §5.1)."""

    error: str
    accepts: list[PaymentRequirements] = field(default_factory=list)
    x402_version: int = X402_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "x402Version": self.x402_version,
            "error": self.error,
            "accepts": [a.to_dict() for a in self.accepts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PaymentRequirementsResponse:
        if not isinstance(data, dict):
            raise X402WireError(X402ErrorCode.INVALID_PAYMENT_REQUIREMENTS, "not an object")
        accepts_raw = data.get("accepts", [])
        if not isinstance(accepts_raw, list):
            raise X402WireError(X402ErrorCode.INVALID_PAYMENT_REQUIREMENTS, "accepts not a list")
        return cls(
            error=str(data.get("error", "")),
            accepts=[PaymentRequirements.from_dict(a) for a in accepts_raw],
            x402_version=int(data.get("x402Version", X402_VERSION)),
        )


# ---------------------------------------------------------------------------
# base64 header (de)serialization (spec transports-v1/http.md)
# ---------------------------------------------------------------------------

def _b64encode_json(obj: dict[str, Any]) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _b64decode_json(value: str, *, code: X402ErrorCode) -> dict[str, Any]:
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise X402WireError(code, f"base64: {exc}") from exc
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise X402WireError(code, f"json: {exc}") from exc
    if not isinstance(data, dict):
        raise X402WireError(code, "not a JSON object")
    return data


def encode_x_payment_header(payload: PaymentPayload) -> str:
    """Serialize a PaymentPayload to the ``X-PAYMENT`` header value."""
    return _b64encode_json(payload.to_dict())


def decode_x_payment_header(header_value: str) -> PaymentPayload:
    """Parse an ``X-PAYMENT`` header value into a PaymentPayload (fail-closed)."""
    data = _b64decode_json(header_value, code=X402ErrorCode.INVALID_PAYLOAD)
    return PaymentPayload.from_dict(data)


def encode_x_payment_response_header(settlement: SettlementResponse) -> str:
    """Serialize a SettlementResponse to the ``X-PAYMENT-RESPONSE`` header value."""
    return _b64encode_json(settlement.to_dict())


def decode_x_payment_response_header(header_value: str) -> SettlementResponse:
    """Parse an ``X-PAYMENT-RESPONSE`` header value into a SettlementResponse."""
    data = _b64decode_json(header_value, code=X402ErrorCode.INVALID_PAYLOAD)
    return SettlementResponse.from_dict(data)


def build_402_body(
    accepts: list[PaymentRequirements],
    error: str = "X-PAYMENT header is required",
) -> dict[str, Any]:
    """Build the canonical HTTP 402 JSON response body."""
    return PaymentRequirementsResponse(error=error, accepts=accepts).to_dict()


def parse_402_body(data: dict[str, Any]) -> PaymentRequirementsResponse:
    """Parse a canonical HTTP 402 JSON response body."""
    return PaymentRequirementsResponse.from_dict(data)


def supported_kinds() -> list[dict[str, Any]]:
    """The ``kinds`` list for ``GET /supported`` (spec §7.3)."""
    return [
        {"x402Version": X402_VERSION, "scheme": EXACT_SCHEME, "network": net}
        for net in supported_canonical_networks()
    ]


__all__ = [
    "X402_VERSION",
    "EXACT_SCHEME",
    "X_PAYMENT_HEADER",
    "X_PAYMENT_RESPONSE_HEADER",
    "X402ErrorCode",
    "X402WireError",
    "canonical_invalid_reason",
    "PaymentRequirements",
    "ExactEvmAuthorization",
    "PaymentPayload",
    "SettlementResponse",
    "PaymentRequirementsResponse",
    "canonical_network_to_sardis",
    "sardis_network_to_canonical",
    "canonical_network_chain_id",
    "supported_canonical_networks",
    "encode_x_payment_header",
    "decode_x_payment_header",
    "encode_x_payment_response_header",
    "decode_x_payment_response_header",
    "build_402_body",
    "parse_402_body",
    "supported_kinds",
]
