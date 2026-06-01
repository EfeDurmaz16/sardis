"""Conformance tests for the canonical x402 v1 wire format.

These verify Sardis's (de)serialization against the EXACT structures published
in the x402 Foundation v1 spec, including a golden vector lifted verbatim from
``specs/transports-v1/http.md``.
"""
from __future__ import annotations

import base64
import json

import pytest

from sardis.protocol.x402_canonical import (
    EXACT_SCHEME,
    X402_VERSION,
    ExactEvmAuthorization,
    PaymentPayload,
    PaymentRequirements,
    PaymentRequirementsResponse,
    SettlementResponse,
    X402ErrorCode,
    X402WireError,
    build_402_body,
    canonical_invalid_reason,
    canonical_network_chain_id,
    canonical_network_to_sardis,
    decode_x_payment_header,
    decode_x_payment_response_header,
    encode_x_payment_header,
    encode_x_payment_response_header,
    parse_402_body,
    sardis_network_to_canonical,
    supported_canonical_networks,
    supported_kinds,
)

# Golden X-PAYMENT header from x402 spec specs/transports-v1/http.md (verbatim).
SPEC_X_PAYMENT = (
    "eyJ4NDAyVmVyc2lvbiI6MSwic2NoZW1lIjoiZXhhY3QiLCJuZXR3b3JrIjoiYmFzZS1zZXBvbGlh"
    "IiwicGF5bG9hZCI6eyJzaWduYXR1cmUiOiIweDJkNmE3NTg4ZDZhY2NhNTA1Y2JmMGQ5YTRhMjI3"
    "ZTBjNTJjNmMzNDAwOGM4ZTg5ODZhMTI4MzI1OTc2NDE3MzYwOGEyY2U2NDk2NjQyZTM3N2Q2ZGE4"
    "ZGJiZjU4MzZlOWJkMTUwOTJmOWVjYWIwNWRlZDNkNjI5M2FmMTQ4YjU3MWMiLCJhdXRob3JpemF0"
    "aW9uIjp7ImZyb20iOiIweDg1N2IwNjUxOUU5MWUzQTU0NTM4NzkxYkRiYjBFMjIzNzNlMzZiNjYi"
    "LCJ0byI6IjB4MjA5NjkzQmM2YWZjMEM1MzI4YkEzNkZhRjAzQzUxNEVGMzEyMjg3QyIsInZhbHVl"
    "IjoiMTAwMDAiLCJ2YWxpZEFmdGVyIjoiMTc0MDY3MjA4OSIsInZhbGlkQmVmb3JlIjoiMTc0MDY3"
    "MjE1NCIsIm5vbmNlIjoiMHhmMzc0NjYxM2MyZDkyMGI1ZmRhYmMwODU2ZjJhZWIyZDRmODhlZTYw"
    "MzdiOGNjNWQwNGE3MWE0NDYyZjEzNDgwIn19fQ=="
)


# --- Golden vector round-trip (spec conformance) ---------------------------

def test_golden_x_payment_decodes_to_spec_fields():
    payload = decode_x_payment_header(SPEC_X_PAYMENT)
    assert payload.x402_version == 1
    assert payload.scheme == "exact"
    assert payload.network == "base-sepolia"
    assert payload.signature.startswith("0x2d6a7588")
    assert payload.authorization.from_ == "0x857b06519E91e3A54538791bDbb0E22373e36b66"
    assert payload.authorization.to == "0x209693Bc6afc0C5328bA36FaF03C514EF312287C"
    assert payload.authorization.value == "10000"
    assert payload.authorization.valid_after == "1740672089"
    assert payload.authorization.valid_before == "1740672154"
    assert payload.authorization.nonce.startswith("0xf3746613")


def test_golden_x_payment_reencodes_to_equivalent_json():
    payload = decode_x_payment_header(SPEC_X_PAYMENT)
    reencoded = encode_x_payment_header(payload)
    # base64 string may differ in field order/whitespace, but the decoded JSON
    # must be structurally identical to the spec's.
    assert json.loads(base64.b64decode(reencoded)) == json.loads(base64.b64decode(SPEC_X_PAYMENT))


def test_payment_payload_roundtrip():
    auth = ExactEvmAuthorization(
        from_="0x" + "1" * 40,
        to="0x" + "2" * 40,
        value="10000",
        valid_after="100",
        valid_before="200",
        nonce="0x" + "ab" * 32,
    )
    payload = PaymentPayload(
        scheme="exact", network="base", signature="0x" + "cd" * 65, authorization=auth
    )
    decoded = decode_x_payment_header(encode_x_payment_header(payload))
    assert decoded.to_dict() == payload.to_dict()


# --- PaymentRequirements / 402 body ----------------------------------------

def test_402_body_matches_spec_shape():
    req = PaymentRequirements(
        scheme="exact",
        network="base-sepolia",
        max_amount_required="10000",
        asset="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        pay_to="0x209693Bc6afc0C5328bA36FaF03C514EF312287C",
        resource="https://api.example.com/premium-data",
        description="Access to premium market data",
        max_timeout_seconds=60,
        mime_type="application/json",
        output_schema=None,
        extra={"name": "USDC", "version": "2"},
    )
    body = build_402_body([req])
    assert body["x402Version"] == 1
    assert body["error"] == "X-PAYMENT header is required"
    a = body["accepts"][0]
    assert set(a) >= {
        "scheme", "network", "maxAmountRequired", "asset", "payTo",
        "resource", "description", "maxTimeoutSeconds",
    }
    assert a["maxAmountRequired"] == "10000"
    assert a["payTo"] == "0x209693Bc6afc0C5328bA36FaF03C514EF312287C"
    assert a["extra"] == {"name": "USDC", "version": "2"}
    # Round-trips back through parse.
    parsed = parse_402_body(body)
    assert isinstance(parsed, PaymentRequirementsResponse)
    assert parsed.accepts[0].max_amount_required == "10000"


def test_payment_requirements_rejects_missing_required_field():
    with pytest.raises(X402WireError) as ei:
        PaymentRequirements.from_dict({"scheme": "exact", "network": "base"})
    assert ei.value.code == X402ErrorCode.INVALID_PAYMENT_REQUIREMENTS


# --- SettlementResponse / X-PAYMENT-RESPONSE -------------------------------

def test_settlement_response_success_roundtrip():
    s = SettlementResponse(
        success=True,
        transaction="0x" + "ef" * 32,
        network="base-sepolia",
        payer="0x857b06519E91e3A54538791bDbb0E22373e36b66",
    )
    header = encode_x_payment_response_header(s)
    decoded = decode_x_payment_response_header(header)
    assert decoded.success is True
    assert decoded.transaction == s.transaction
    assert decoded.payer == s.payer
    # success response omits errorReason per spec.
    assert "errorReason" not in s.to_dict()


def test_settlement_response_failure_carries_error_reason():
    s = SettlementResponse(
        success=False,
        transaction="",
        network="base-sepolia",
        payer="0x857b06519E91e3A54538791bDbb0E22373e36b66",
        error_reason=X402ErrorCode.INSUFFICIENT_FUNDS.value,
    )
    d = s.to_dict()
    assert d["success"] is False
    assert d["transaction"] == ""
    assert d["errorReason"] == "insufficient_funds"


# --- Bad-case rejections (fail-closed) -------------------------------------

def test_decode_rejects_non_base64():
    with pytest.raises(X402WireError) as ei:
        decode_x_payment_header("not valid base64 !!!")
    assert ei.value.code == X402ErrorCode.INVALID_PAYLOAD


def test_decode_rejects_wrong_x402_version():
    bad = base64.b64encode(
        json.dumps({"x402Version": 2, "scheme": "exact", "network": "base", "payload": {}}).encode()
    ).decode()
    with pytest.raises(X402WireError) as ei:
        decode_x_payment_header(bad)
    assert ei.value.code == X402ErrorCode.INVALID_X402_VERSION


def test_decode_rejects_unsupported_scheme():
    bad = base64.b64encode(
        json.dumps(
            {"x402Version": 1, "scheme": "permit2", "network": "base", "payload": {"signature": "0x"}}
        ).encode()
    ).decode()
    with pytest.raises(X402WireError) as ei:
        decode_x_payment_header(bad)
    assert ei.value.code == X402ErrorCode.UNSUPPORTED_SCHEME


def test_decode_rejects_missing_signature():
    bad = base64.b64encode(
        json.dumps(
            {
                "x402Version": 1,
                "scheme": "exact",
                "network": "base",
                "payload": {"authorization": {}},
            }
        ).encode()
    ).decode()
    with pytest.raises(X402WireError) as ei:
        decode_x_payment_header(bad)
    assert ei.value.code == X402ErrorCode.INVALID_PAYLOAD


# --- Network mapping (fail-closed) -----------------------------------------

@pytest.mark.parametrize(
    "canonical,sardis,chain_id",
    [
        ("base", "base", 8453),
        ("base-sepolia", "base_sepolia", 84532),
        ("ethereum", "ethereum", 1),
        ("polygon", "polygon", 137),
    ],
)
def test_network_mapping_roundtrip(canonical, sardis, chain_id):
    assert canonical_network_to_sardis(canonical) == sardis
    assert sardis_network_to_canonical(sardis) == canonical
    assert canonical_network_chain_id(canonical) == chain_id


def test_network_mapping_rejects_unknown():
    with pytest.raises(X402WireError) as ei:
        canonical_network_to_sardis("solana")
    assert ei.value.code == X402ErrorCode.INVALID_NETWORK


def test_network_mapping_rejects_sardis_id_as_canonical():
    # "base_sepolia" (underscore) is the Sardis id, NOT a canonical wire id.
    with pytest.raises(X402WireError) as ei:
        canonical_network_to_sardis("base_sepolia")
    assert ei.value.code == X402ErrorCode.INVALID_NETWORK


def test_supported_networks_and_kinds():
    nets = supported_canonical_networks()
    assert "base" in nets and "base-sepolia" in nets
    kinds = supported_kinds()
    assert all(k["x402Version"] == X402_VERSION and k["scheme"] == EXACT_SCHEME for k in kinds)
    assert {k["network"] for k in kinds} == set(nets)


# --- Reason code translation -----------------------------------------------

@pytest.mark.parametrize(
    "internal,expected",
    [
        ("authorization_not_yet_valid", X402ErrorCode.INVALID_VALID_AFTER),
        ("authorization_expired", X402ErrorCode.INVALID_VALID_BEFORE),
        ("signer_mismatch_authorization_from", X402ErrorCode.INVALID_SIGNATURE),
        ("signer_mismatch_payer_address", X402ErrorCode.INVALID_SIGNATURE),
        ("signature_bad_length:10", X402ErrorCode.INVALID_SIGNATURE),
        ("recovery_failed:boom", X402ErrorCode.INVALID_SIGNATURE),
        ("unsupported_network_for_eip3009:foo", X402ErrorCode.INVALID_NETWORK),
        (None, X402ErrorCode.INVALID_PAYLOAD),
        ("something_unknown", X402ErrorCode.INVALID_PAYLOAD),
    ],
)
def test_canonical_invalid_reason(internal, expected):
    assert canonical_invalid_reason(internal) == expected
