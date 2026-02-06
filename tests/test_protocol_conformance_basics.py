"""Protocol baseline/negative tests for AP2 and multi-rail method parsing."""
from __future__ import annotations

import pytest
import time

from sardis_protocol.payment_methods import PaymentMethod, parse_payment_method_from_mandate
from sardis_protocol.verifier import MandateVerifier
from sardis_v2_core import load_settings

pytestmark = [pytest.mark.protocol_conformance, pytest.mark.ap2]


def _proof() -> dict[str, str]:
    return {
        "type": "DataIntegrityProof",
        "verification_method": "did:key:ed25519:ZmFrZQ==",
        "created": str(int(time.time())),
        "proof_purpose": "assertionMethod",
        "proof_value": "dGVzdA==",
    }


def _base(mandate_id: str, mandate_type: str, purpose: str) -> dict:
    return {
        "mandate_id": mandate_id,
        "mandate_type": mandate_type,
        "issuer": "agent:test",
        "subject": "agent:test",
        "expires_at": int(time.time()) + 3600,
        "nonce": "nonce-protocol",
        "proof": _proof(),
        "domain": "example.com",
        "purpose": purpose,
    }


def _bundle() -> dict:
    return {
        "intent": {
            **_base("intent-proto", "intent", "intent"),
            "scope": ["payment"],
            "requested_amount": 1000,
        },
        "cart": {
            **_base("cart-proto", "cart", "cart"),
            "line_items": [{"id": "item-1", "price_minor": 1000}],
            "merchant_domain": "merchant.example",
            "currency": "USD",
            "subtotal_minor": 1000,
            "taxes_minor": 0,
        },
        "payment": {
            **_base("payment-proto", "payment", "checkout"),
            "chain": "base",
            "token": "USDC",
            "amount_minor": 1000,
            "destination": "0x1234567890123456789012345678901234567890",
            "audit_hash": "audit-hash",
            "merchant_domain": "merchant.example",
        },
    }


def test_ap2_rejects_missing_payment_merchant_domain():
    verifier = MandateVerifier(settings=load_settings())
    payload = _bundle()
    payload["payment"].pop("merchant_domain", None)

    result = verifier.verify_chain(type("Bundle", (), payload)())

    assert result.accepted is False
    assert result.reason == "payment_missing_merchant_domain"


def test_ap2_rejects_merchant_domain_mismatch():
    verifier = MandateVerifier(settings=load_settings())
    payload = _bundle()
    payload["payment"]["merchant_domain"] = "another-merchant.example"

    result = verifier.verify_chain(type("Bundle", (), payload)())

    assert result.accepted is False
    assert result.reason == "merchant_domain_mismatch"


def test_ap2_rejects_malformed_payload_missing_proof():
    verifier = MandateVerifier(settings=load_settings())
    payload = _bundle()
    payload["cart"].pop("proof", None)

    result = verifier.verify_chain(type("Bundle", (), payload)())

    assert result.accepted is False
    assert str(result.reason).startswith("invalid_payload:")


def test_payment_method_parser_detects_x402_and_card_paths():
    assert parse_payment_method_from_mandate({"protocol": "x402"}) == PaymentMethod.X402
    assert parse_payment_method_from_mandate(
        {"payment_details": {"virtual_card_id": "card_123"}}
    ) == PaymentMethod.VIRTUAL_CARD
    assert parse_payment_method_from_mandate(
        {"payment_details": {"bank_account": "ach_1"}}
    ) == PaymentMethod.BANK_TRANSFER
    assert parse_payment_method_from_mandate({}) == PaymentMethod.STABLECOIN
