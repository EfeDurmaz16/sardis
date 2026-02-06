"""AP2 Security Lock behavior tests.

Verifies that the AP2 verification pipeline enforces fail-closed semantics:
- Missing any mandate in the chain causes immediate rejection
- Partial verification never proceeds
- Error reasons are specific and actionable
- Production mode requires identity registry
"""
from __future__ import annotations

import os
import time
import pytest
from unittest.mock import patch

from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import IntentMandate, CartMandate, PaymentMandate, VCProof
from sardis_protocol.verifier import MandateVerifier, VerificationError
from sardis_protocol.schemas import AP2PaymentExecuteRequest

pytestmark = [pytest.mark.protocol_conformance, pytest.mark.ap2]


def create_valid_proof() -> dict:
    """Create a valid proof dictionary."""
    return {
        "type": "DataIntegrityProof",
        "verification_method": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK#ed25519:abcdef0123456789",
        "proof_value": "dGVzdF9zaWduYXR1cmVfdmFsaWQ=",
        "proof_purpose": "assertionMethod",
        "created": "2026-02-06T00:00:00Z",
    }


def create_valid_intent_dict(mandate_id: str = "intent_001") -> dict:
    """Create a valid intent mandate dictionary."""
    return {
        "mandate_id": mandate_id,
        "mandate_type": "intent",
        "purpose": "intent",
        "issuer": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
        "subject": "agent-001",
        "expires_at": int(time.time()) + 3600,
        "nonce": f"nonce_{mandate_id}",
        "domain": "example.com",
        "scope": ["shopping"],
        "requested_amount": 10000,
        "proof": create_valid_proof(),
    }


def create_valid_cart_dict(mandate_id: str = "cart_001") -> dict:
    """Create a valid cart mandate dictionary."""
    return {
        "mandate_id": mandate_id,
        "mandate_type": "cart",
        "purpose": "cart",
        "issuer": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
        "subject": "agent-001",
        "expires_at": int(time.time()) + 3600,
        "nonce": f"nonce_{mandate_id}",
        "domain": "example.com",
        "merchant_domain": "shop.example.com",
        "line_items": [
            {
                "item_id": "item1",
                "name": "Widget",
                "quantity": 1,
                "price_minor": 5000,
            }
        ],
        "subtotal_minor": 5000,
        "taxes_minor": 500,
        "currency": "USD",
        "proof": create_valid_proof(),
    }


def create_valid_payment_dict(mandate_id: str = "payment_001") -> dict:
    """Create a valid payment mandate dictionary."""
    return {
        "mandate_id": mandate_id,
        "mandate_type": "payment",
        "purpose": "checkout",
        "issuer": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
        "subject": "agent-001",
        "expires_at": int(time.time()) + 3600,
        "nonce": f"nonce_{mandate_id}",
        "domain": "example.com",
        "merchant_domain": "shop.example.com",
        "amount_minor": 5500,
        "token": "USDC",
        "chain": "base",
        "destination": "0x1234567890123456789012345678901234567890",
        "audit_hash": "abc123",
        "ai_agent_presence": True,
        "transaction_modality": "human_not_present",
        "proof": create_valid_proof(),
    }


class TestSecurityLockBehavior:
    def test_missing_intent_fails_entire_chain(self):
        """Missing intent mandate must fail the entire chain, not partial success."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        bundle = AP2PaymentExecuteRequest(
            intent={},
            cart=create_valid_cart_dict(),
            payment=create_valid_payment_dict(),
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason is not None
        assert "invalid_payload" in result.reason
        assert result.chain is None

    def test_missing_cart_fails_entire_chain(self):
        """Missing cart mandate must fail the entire chain."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        bundle = AP2PaymentExecuteRequest(
            intent=create_valid_intent_dict(),
            cart={},
            payment=create_valid_payment_dict(),
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason is not None
        assert "invalid_payload" in result.reason
        assert result.chain is None

    def test_missing_payment_fails_entire_chain(self):
        """Missing payment mandate must fail the entire chain."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        bundle = AP2PaymentExecuteRequest(
            intent=create_valid_intent_dict(),
            cart=create_valid_cart_dict(),
            payment={},
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason is not None
        assert "invalid_payload" in result.reason
        assert result.chain is None

    def test_partial_verification_never_proceeds(self):
        """If intent passes but cart fails, payment should never be checked."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        # Create a cart with wrong type (will fail type check before signature verification)
        invalid_cart = create_valid_cart_dict()
        invalid_cart["mandate_type"] = "intent"  # Wrong type

        bundle = AP2PaymentExecuteRequest(
            intent=create_valid_intent_dict(),
            cart=invalid_cart,
            payment=create_valid_payment_dict(),
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason == "cart_invalid_type"
        assert result.chain is None
        # The test verifies that the failure happens at cart type check,
        # before reaching payment verification

    def test_error_reasons_identify_specific_mandate(self):
        """Each failure reason must identify which mandate and what went wrong."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        # Test 1: Intent type error
        invalid_intent = create_valid_intent_dict()
        invalid_intent["mandate_type"] = "payment"

        bundle = AP2PaymentExecuteRequest(
            intent=invalid_intent,
            cart=create_valid_cart_dict(),
            payment=create_valid_payment_dict(),
        )

        result = verifier.verify_chain(bundle)
        assert result.accepted is False
        assert "intent" in result.reason
        assert result.reason == "intent_invalid_type"

        # Test 2: Cart type error
        invalid_cart = create_valid_cart_dict()
        invalid_cart["mandate_type"] = "payment"

        bundle = AP2PaymentExecuteRequest(
            intent=create_valid_intent_dict(),
            cart=invalid_cart,
            payment=create_valid_payment_dict(),
        )

        result = verifier.verify_chain(bundle)
        assert result.accepted is False
        assert "cart" in result.reason
        assert result.reason == "cart_invalid_type"

        # Test 3: Payment type error
        invalid_payment = create_valid_payment_dict()
        invalid_payment["purpose"] = "intent"

        bundle = AP2PaymentExecuteRequest(
            intent=create_valid_intent_dict(),
            cart=create_valid_cart_dict(),
            payment=invalid_payment,
        )

        result = verifier.verify_chain(bundle)
        assert result.accepted is False
        assert "payment" in result.reason
        assert result.reason == "payment_invalid_type"

    def test_production_mode_requires_identity_registry(self):
        """In production mode (SARDIS_ENVIRONMENT=production), missing identity registry raises VerificationError."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings, identity_registry=None)

        bundle = AP2PaymentExecuteRequest(
            intent=create_valid_intent_dict(),
            cart=create_valid_cart_dict(),
            payment=create_valid_payment_dict(),
        )

        # Patch environment to simulate production
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "production"}):
            # The verify_chain will call verify() which calls _identity_from_proof()
            # In production without identity registry, it should raise VerificationError
            with pytest.raises(VerificationError, match="Identity registry required in production"):
                verifier.verify_chain(bundle)

    def test_fail_closed_on_malformed_proof(self):
        """Malformed proof data must cause rejection, not silent pass."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        # Test with malformed proof_value (not valid base64)
        malformed_intent = create_valid_intent_dict()
        malformed_intent["proof"]["proof_value"] = "not!valid!base64!@#$"

        bundle = AP2PaymentExecuteRequest(
            intent=malformed_intent,
            cart=create_valid_cart_dict(),
            payment=create_valid_payment_dict(),
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason is not None
        # Should fail with signature_malformed or signature_invalid
        assert "signature" in result.reason or "intent" in result.reason
        assert result.chain is None

    def test_missing_proof_field_fails_closed(self):
        """Missing proof field must cause immediate rejection."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        # Test with missing proof entirely
        intent_no_proof = create_valid_intent_dict()
        del intent_no_proof["proof"]

        bundle = AP2PaymentExecuteRequest(
            intent=intent_no_proof,
            cart=create_valid_cart_dict(),
            payment=create_valid_payment_dict(),
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason is not None
        assert "invalid_payload" in result.reason
        assert result.chain is None

    def test_expired_mandate_fails_closed(self):
        """Expired mandate must fail the entire chain."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        # Create expired intent
        expired_intent = create_valid_intent_dict()
        expired_intent["expires_at"] = int(time.time()) - 3600  # 1 hour ago

        bundle = AP2PaymentExecuteRequest(
            intent=expired_intent,
            cart=create_valid_cart_dict(),
            payment=create_valid_payment_dict(),
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason == "mandate_expired"
        assert result.chain is None

    def test_domain_not_authorized_fails_closed(self):
        """Domain not in allowed_domains must fail."""
        settings = SardisSettings(allowed_domains=["trusted.com"])  # Different domain
        verifier = MandateVerifier(settings=settings)

        bundle = AP2PaymentExecuteRequest(
            intent=create_valid_intent_dict(),  # Has domain="example.com"
            cart=create_valid_cart_dict(),
            payment=create_valid_payment_dict(),
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason is not None
        # Will fail at domain check for one of the mandates
        assert "domain" in result.reason or "intent" in result.reason
        assert result.chain is None

    def test_subject_mismatch_fails_closed(self):
        """Different subjects across mandates must fail."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        intent = create_valid_intent_dict()
        cart = create_valid_cart_dict()
        payment = create_valid_payment_dict()

        # Change subject on cart
        cart["subject"] = "agent-002"

        bundle = AP2PaymentExecuteRequest(
            intent=intent,
            cart=cart,
            payment=payment,
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason == "subject_mismatch"
        assert result.chain is None

    def test_amount_exceeds_cart_total_fails_closed(self):
        """Payment amount exceeding cart total must fail."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        intent = create_valid_intent_dict()
        cart = create_valid_cart_dict()
        payment = create_valid_payment_dict()

        # Set payment amount higher than cart total
        payment["amount_minor"] = 10000  # Cart total is 5500

        bundle = AP2PaymentExecuteRequest(
            intent=intent,
            cart=cart,
            payment=payment,
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason == "payment_exceeds_cart_total"
        assert result.chain is None

    def test_missing_merchant_domain_fails_closed(self):
        """Missing merchant_domain in payment must fail."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        intent = create_valid_intent_dict()
        cart = create_valid_cart_dict()
        payment = create_valid_payment_dict()

        # Remove merchant_domain
        payment["merchant_domain"] = None

        bundle = AP2PaymentExecuteRequest(
            intent=intent,
            cart=cart,
            payment=payment,
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason == "payment_missing_merchant_domain"
        assert result.chain is None

    def test_merchant_domain_mismatch_fails_closed(self):
        """Mismatched merchant_domain between cart and payment must fail."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        intent = create_valid_intent_dict()
        cart = create_valid_cart_dict()
        payment = create_valid_payment_dict()

        # Change payment merchant_domain
        payment["merchant_domain"] = "different.example.com"

        bundle = AP2PaymentExecuteRequest(
            intent=intent,
            cart=cart,
            payment=payment,
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason == "merchant_domain_mismatch"
        assert result.chain is None

    def test_missing_agent_presence_fails_closed(self):
        """Payment with ai_agent_presence=False must fail."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        intent = create_valid_intent_dict()
        cart = create_valid_cart_dict()
        payment = create_valid_payment_dict()

        # Set agent presence to False
        payment["ai_agent_presence"] = False

        bundle = AP2PaymentExecuteRequest(
            intent=intent,
            cart=cart,
            payment=payment,
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason == "payment_agent_presence_required"
        assert result.chain is None

    def test_invalid_modality_fails_closed(self):
        """Invalid transaction_modality must fail."""
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings=settings)

        intent = create_valid_intent_dict()
        cart = create_valid_cart_dict()
        payment = create_valid_payment_dict()

        # Set invalid modality
        payment["transaction_modality"] = "invalid_modality"

        bundle = AP2PaymentExecuteRequest(
            intent=intent,
            cart=cart,
            payment=payment,
        )

        result = verifier.verify_chain(bundle)

        assert result.accepted is False
        assert result.reason == "payment_invalid_modality"
        assert result.chain is None
