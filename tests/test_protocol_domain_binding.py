"""Unit tests for AP2 domain binding semantics (identity domain vs merchant domain)."""

from __future__ import annotations

import time

from sardis_protocol.schemas import AP2PaymentExecuteRequest
from sardis_protocol.verifier import MandateVerifier, VerificationResult
from sardis_v2_core import SardisSettings


def _proof() -> dict:
    return {
        "type": "DataIntegrityProof",
        "verification_method": "ed25519:" + ("00" * 32),
        "created": "2026-01-01T00:00:00Z",
        "proof_purpose": "assertionMethod",
        "proof_value": "cHJvb2Y=",
    }


def _bundle(*, payment_overrides: dict | None = None, cart_overrides: dict | None = None) -> AP2PaymentExecuteRequest:
    now = int(time.time())
    intent = {
        "mandate_id": "mnd_intent",
        "mandate_type": "intent",
        "issuer": "did:web:sardis.network",
        "subject": "agent_1",
        "expires_at": now + 300,
        "nonce": "n1",
        "proof": _proof(),
        "domain": "sardis.network",
        "purpose": "intent",
        "scope": ["checkout"],
        "requested_amount": 10_000,
    }
    cart = {
        "mandate_id": "mnd_cart",
        "mandate_type": "cart",
        "issuer": "did:web:sardis.network",
        "subject": "agent_1",
        "expires_at": now + 300,
        "nonce": "n2",
        "proof": _proof(),
        "domain": "sardis.network",
        "purpose": "cart",
        "line_items": [{"sku": "x", "qty": 1, "price_minor": 10_000}],
        "merchant_domain": "merchant.example",
        "currency": "USD",
        "subtotal_minor": 10_000,
        "taxes_minor": 0,
    }
    if cart_overrides:
        cart.update(cart_overrides)
    payment = {
        "mandate_id": "mnd_payment",
        "mandate_type": "payment",
        "issuer": "did:web:sardis.network",
        "subject": "agent_1",
        "expires_at": now + 300,
        "nonce": "n3",
        "proof": _proof(),
        "domain": "sardis.network",
        "purpose": "checkout",
        "chain": "base_sepolia",
        "token": "USDC",
        "amount_minor": 10_000,
        "destination": "0x0000000000000000000000000000000000000000",
        "audit_hash": "hash",
        "merchant_domain": "merchant.example",
    }
    if payment_overrides:
        payment.update(payment_overrides)
    return AP2PaymentExecuteRequest(intent=intent, cart=cart, payment=payment)


def test_verify_chain_requires_payment_merchant_domain():
    settings = SardisSettings(environment="dev")
    verifier = MandateVerifier(settings=settings)
    verifier.verify = lambda mandate: VerificationResult(True)  # type: ignore[assignment]

    result = verifier.verify_chain(_bundle(payment_overrides={"merchant_domain": None}))
    assert result.accepted is False
    assert result.reason == "payment_missing_merchant_domain"


def test_verify_chain_rejects_merchant_domain_mismatch():
    settings = SardisSettings(environment="dev")
    verifier = MandateVerifier(settings=settings)
    verifier.verify = lambda mandate: VerificationResult(True)  # type: ignore[assignment]

    result = verifier.verify_chain(_bundle(payment_overrides={"merchant_domain": "evil.example"}))
    assert result.accepted is False
    assert result.reason == "merchant_domain_mismatch"


def test_verify_chain_accepts_when_domains_match():
    settings = SardisSettings(environment="dev")
    verifier = MandateVerifier(settings=settings)
    verifier.verify = lambda mandate: VerificationResult(True)  # type: ignore[assignment]

    result = verifier.verify_chain(_bundle())
    assert result.accepted is True
    assert result.chain is not None


def test_verify_chain_rejects_missing_agent_presence_signal():
    settings = SardisSettings(environment="dev")
    verifier = MandateVerifier(settings=settings)
    verifier.verify = lambda mandate: VerificationResult(True)  # type: ignore[assignment]

    result = verifier.verify_chain(_bundle(payment_overrides={"ai_agent_presence": False}))
    assert result.accepted is False
    assert result.reason == "payment_agent_presence_required"


def test_verify_chain_rejects_invalid_modality_signal():
    settings = SardisSettings(environment="dev")
    verifier = MandateVerifier(settings=settings)
    verifier.verify = lambda mandate: VerificationResult(True)  # type: ignore[assignment]

    result = verifier.verify_chain(_bundle(payment_overrides={"transaction_modality": "invalid"}))
    assert result.accepted is False
    assert result.reason == "payment_invalid_modality"
