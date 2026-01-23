"""Tests for UCP adapters."""

import time

import pytest

from sardis_ucp.models.mandates import (
    UCPCurrency,
    UCPLineItem,
    UCPCartMandate,
    UCPCheckoutMandate,
    UCPPaymentMandate,
)
from sardis_ucp.adapters.ap2 import (
    AP2MandateAdapter,
    AP2IntentMandate,
    AP2CartMandate,
    AP2PaymentMandate,
    AP2VCProof,
)


@pytest.fixture
def adapter():
    """Create an AP2 adapter for testing."""
    return AP2MandateAdapter(platform_domain="sardis.sh")


@pytest.fixture
def ucp_cart_mandate():
    """Create a sample UCP cart mandate."""
    items = [
        UCPLineItem(
            item_id="item_1",
            name="Widget",
            description="A widget",
            quantity=2,
            unit_price_minor=1000,
            currency=UCPCurrency.USD,
        ),
    ]

    return UCPCartMandate(
        mandate_id="ucp_cart_123",
        merchant_id="merchant_456",
        merchant_name="Test Store",
        merchant_domain="store.test.com",
        line_items=items,
        currency=UCPCurrency.USD,
        subtotal_minor=2000,
        taxes_minor=160,
        expires_at=int(time.time()) + 3600,
        nonce="abc123",
    )


@pytest.fixture
def ucp_checkout_mandate():
    """Create a sample UCP checkout mandate."""
    return UCPCheckoutMandate(
        mandate_id="ucp_checkout_123",
        cart_mandate_id="ucp_cart_456",
        subject="agent_abc",
        issuer="sardis.sh",
        authorized_amount_minor=2160,
        currency=UCPCurrency.USD,
        scope=["checkout", "payment"],
        expires_at=int(time.time()) + 900,
        nonce="def456",
    )


@pytest.fixture
def ucp_payment_mandate():
    """Create a sample UCP payment mandate."""
    return UCPPaymentMandate(
        mandate_id="ucp_payment_123",
        checkout_mandate_id="ucp_checkout_456",
        subject="agent_abc",
        issuer="sardis.sh",
        chain="base",
        token="USDC",
        amount_minor=2160,
        destination="0x1234567890abcdef1234567890abcdef12345678",
        audit_hash="hash123",
        expires_at=int(time.time()) + 300,
        nonce="ghi789",
    )


@pytest.fixture
def ap2_cart_mandate():
    """Create a sample AP2 cart mandate."""
    return AP2CartMandate(
        mandate_id="ap2_cart_123",
        issuer="merchant_456",
        subject="agent_abc",
        expires_at=int(time.time()) + 3600,
        nonce="abc123",
        domain="store.test.com",
        line_items=[
            {
                "item_id": "item_1",
                "name": "Widget",
                "description": "A widget",
                "quantity": 2,
                "unit_price_minor": 1000,
                "currency": "USD",
            }
        ],
        merchant_domain="store.test.com",
        currency="USD",
        subtotal_minor=2000,
        taxes_minor=160,
    )


@pytest.fixture
def ap2_intent_mandate():
    """Create a sample AP2 intent mandate."""
    return AP2IntentMandate(
        mandate_id="ap2_intent_123",
        issuer="sardis.sh",
        subject="agent_abc",
        expires_at=int(time.time()) + 900,
        nonce="def456",
        domain="sardis.sh",
        purpose="checkout",
        scope=["checkout", "payment"],
        requested_amount=2160,
        proof=AP2VCProof(
            verification_method="did:web:sardis.sh#key-1",
            proof_value="signature123",
        ),
    )


@pytest.fixture
def ap2_payment_mandate():
    """Create a sample AP2 payment mandate."""
    return AP2PaymentMandate(
        mandate_id="ap2_payment_123",
        issuer="sardis.sh",
        subject="agent_abc",
        expires_at=int(time.time()) + 300,
        nonce="ghi789",
        domain="sardis.sh",
        chain="base",
        token="USDC",
        amount_minor=2160,
        destination="0x1234567890abcdef1234567890abcdef12345678",
        audit_hash="hash123",
    )


class TestUCPToAP2Conversion:
    """Tests for UCP -> AP2 conversion."""

    def test_ucp_cart_to_ap2(self, adapter, ucp_cart_mandate):
        """Test converting UCP cart mandate to AP2."""
        ap2_cart = adapter.ucp_cart_to_ap2(
            ucp_cart_mandate,
            issuer="merchant_456",
            subject="agent_abc",
        )

        assert ap2_cart.mandate_id == ucp_cart_mandate.mandate_id
        assert ap2_cart.issuer == "merchant_456"
        assert ap2_cart.subject == "agent_abc"
        assert ap2_cart.merchant_domain == ucp_cart_mandate.merchant_domain
        assert ap2_cart.subtotal_minor == ucp_cart_mandate.subtotal_minor
        assert len(ap2_cart.line_items) == 1

    def test_ucp_checkout_to_ap2_intent(self, adapter, ucp_checkout_mandate):
        """Test converting UCP checkout mandate to AP2 intent."""
        ap2_intent = adapter.ucp_checkout_to_ap2_intent(ucp_checkout_mandate)

        assert ap2_intent.mandate_id == ucp_checkout_mandate.mandate_id
        assert ap2_intent.subject == ucp_checkout_mandate.subject
        assert ap2_intent.issuer == ucp_checkout_mandate.issuer
        assert ap2_intent.requested_amount == ucp_checkout_mandate.authorized_amount_minor
        assert ap2_intent.scope == list(ucp_checkout_mandate.scope)

    def test_ucp_payment_to_ap2(self, adapter, ucp_payment_mandate):
        """Test converting UCP payment mandate to AP2."""
        ap2_payment = adapter.ucp_payment_to_ap2(ucp_payment_mandate)

        assert ap2_payment.mandate_id == ucp_payment_mandate.mandate_id
        assert ap2_payment.chain == ucp_payment_mandate.chain
        assert ap2_payment.token == ucp_payment_mandate.token
        assert ap2_payment.amount_minor == ucp_payment_mandate.amount_minor
        assert ap2_payment.destination == ucp_payment_mandate.destination
        assert ap2_payment.audit_hash == ucp_payment_mandate.audit_hash

    def test_ucp_to_ap2_chain(
        self, adapter, ucp_cart_mandate, ucp_checkout_mandate, ucp_payment_mandate
    ):
        """Test converting a complete UCP mandate chain to AP2."""
        result = adapter.ucp_to_ap2_chain(
            cart=ucp_cart_mandate,
            checkout=ucp_checkout_mandate,
            payment=ucp_payment_mandate,
        )

        assert result.success is True
        assert result.cart_mandate is not None
        assert result.intent_mandate is not None
        assert result.payment_mandate is not None


class TestAP2ToUCPConversion:
    """Tests for AP2 -> UCP conversion."""

    def test_ap2_cart_to_ucp(self, adapter, ap2_cart_mandate):
        """Test converting AP2 cart mandate to UCP."""
        ucp_cart = adapter.ap2_cart_to_ucp(
            ap2_cart_mandate,
            merchant_id="merchant_456",
            merchant_name="Test Store",
        )

        assert ucp_cart.mandate_id == ap2_cart_mandate.mandate_id
        assert ucp_cart.merchant_id == "merchant_456"
        assert ucp_cart.merchant_name == "Test Store"
        assert ucp_cart.merchant_domain == ap2_cart_mandate.merchant_domain
        assert len(ucp_cart.line_items) == 1

    def test_ap2_intent_to_ucp_checkout(self, adapter, ap2_intent_mandate):
        """Test converting AP2 intent mandate to UCP checkout."""
        ucp_checkout = adapter.ap2_intent_to_ucp_checkout(
            ap2_intent_mandate,
            cart_mandate_id="cart_123",
        )

        assert ucp_checkout.mandate_id == ap2_intent_mandate.mandate_id
        assert ucp_checkout.cart_mandate_id == "cart_123"
        assert ucp_checkout.subject == ap2_intent_mandate.subject
        assert ucp_checkout.authorized_amount_minor == ap2_intent_mandate.requested_amount

    def test_ap2_payment_to_ucp(self, adapter, ap2_payment_mandate):
        """Test converting AP2 payment mandate to UCP."""
        ucp_payment = adapter.ap2_payment_to_ucp(
            ap2_payment_mandate,
            checkout_mandate_id="checkout_123",
        )

        assert ucp_payment.mandate_id == ap2_payment_mandate.mandate_id
        assert ucp_payment.checkout_mandate_id == "checkout_123"
        assert ucp_payment.chain == ap2_payment_mandate.chain
        assert ucp_payment.token == ap2_payment_mandate.token
        assert ucp_payment.amount_minor == ap2_payment_mandate.amount_minor

    def test_ap2_to_ucp_chain(
        self, adapter, ap2_intent_mandate, ap2_cart_mandate, ap2_payment_mandate
    ):
        """Test converting a complete AP2 mandate chain to UCP."""
        result = adapter.ap2_to_ucp_chain(
            intent=ap2_intent_mandate,
            cart=ap2_cart_mandate,
            payment=ap2_payment_mandate,
            merchant_id="merchant_456",
            merchant_name="Test Store",
        )

        assert result.success is True
        assert result.cart_mandate is not None
        assert result.checkout_mandate is not None
        assert result.payment_mandate is not None


class TestAuditHash:
    """Tests for audit hash utilities."""

    def test_compute_audit_hash(self, adapter):
        """Test computing an audit hash."""
        hash1 = adapter.compute_audit_hash(
            cart_mandate_id="cart_123",
            checkout_mandate_id="checkout_456",
            amount_minor=5000,
            chain="base",
            token="USDC",
            destination="0x1234",
        )

        # Same inputs should produce same hash
        hash2 = adapter.compute_audit_hash(
            cart_mandate_id="cart_123",
            checkout_mandate_id="checkout_456",
            amount_minor=5000,
            chain="base",
            token="USDC",
            destination="0x1234",
        )

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_different_inputs_different_hash(self, adapter):
        """Test that different inputs produce different hashes."""
        hash1 = adapter.compute_audit_hash(
            cart_mandate_id="cart_123",
            checkout_mandate_id="checkout_456",
            amount_minor=5000,
            chain="base",
            token="USDC",
            destination="0x1234",
        )

        hash2 = adapter.compute_audit_hash(
            cart_mandate_id="cart_different",  # Changed
            checkout_mandate_id="checkout_456",
            amount_minor=5000,
            chain="base",
            token="USDC",
            destination="0x1234",
        )

        assert hash1 != hash2

    def test_verify_audit_hash(self, adapter, ucp_payment_mandate):
        """Test verifying an audit hash."""
        # Compute the expected hash
        expected_hash = adapter.compute_audit_hash(
            cart_mandate_id="cart_123",
            checkout_mandate_id="checkout_456",
            amount_minor=ucp_payment_mandate.amount_minor,
            chain=ucp_payment_mandate.chain,
            token=ucp_payment_mandate.token,
            destination=ucp_payment_mandate.destination,
        )

        # Update payment mandate with correct hash
        ucp_payment_mandate.audit_hash = expected_hash

        # Verify
        assert adapter.verify_audit_hash(
            ucp_payment_mandate,
            cart_mandate_id="cart_123",
            checkout_mandate_id="checkout_456",
        ) is True

    def test_verify_audit_hash_mismatch(self, adapter, ucp_payment_mandate):
        """Test that verification fails with wrong hash."""
        ucp_payment_mandate.audit_hash = "wrong_hash"

        assert adapter.verify_audit_hash(
            ucp_payment_mandate,
            cart_mandate_id="cart_123",
            checkout_mandate_id="checkout_456",
        ) is False
