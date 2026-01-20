"""Unit tests for mandate models and verification."""
from __future__ import annotations

import time
import pytest
from sardis_v2_core.mandates import (
    IntentMandate,
    CartMandate,
    PaymentMandate,
    MandateChain,
    VCProof,
)


def create_vc_proof(method: str = "did:key:z6Mk...#key-1") -> VCProof:
    """Create a test VCProof."""
    return VCProof(
        verification_method=method,
        created="2025-12-08T00:00:00Z",
        proof_value="test_signature_value",
    )


class TestMandateExpiration:
    """Tests for mandate expiration logic."""

    def test_mandate_not_expired(self):
        """Test that a mandate with future expiration is not expired."""
        future_time = int(time.time()) + 3600  # 1 hour from now
        proof = create_vc_proof()
        
        mandate = IntentMandate(
            mandate_id="test_intent_001",
            mandate_type="intent",
            issuer="test_issuer",
            subject="test_subject",
            expires_at=future_time,
            nonce="nonce_001",
            proof=proof,
            domain="sardis.network",
            purpose="intent",
            scope=["payments"],
        )
        
        assert mandate.is_expired() is False

    def test_mandate_expired(self):
        """Test that a mandate with past expiration is expired."""
        past_time = int(time.time()) - 100  # 100 seconds ago
        proof = create_vc_proof()
        
        mandate = IntentMandate(
            mandate_id="test_intent_002",
            mandate_type="intent",
            issuer="test_issuer",
            subject="test_subject",
            expires_at=past_time,
            nonce="nonce_002",
            proof=proof,
            domain="sardis.network",
            purpose="intent",
            scope=["payments"],
        )
        
        assert mandate.is_expired() is True

    def test_mandate_expired_at_exact_time(self):
        """Test that a mandate expired at current time is considered expired."""
        now = int(time.time())
        proof = create_vc_proof()
        
        mandate = PaymentMandate(
            mandate_id="test_payment_001",
            mandate_type="payment",
            issuer="test_issuer",
            subject="test_wallet",
            expires_at=now,
            nonce="nonce_003",
            proof=proof,
            domain="sardis.network",
            purpose="checkout",
            chain="base_sepolia",
            token="USDC",
            amount_minor=10000,
            destination="0x1234567890123456789012345678901234567890",
            audit_hash="abc123",
        )
        
        assert mandate.is_expired() is True


class TestIntentMandate:
    """Tests for IntentMandate model."""

    def test_intent_mandate_creation(self):
        """Test creating an IntentMandate."""
        proof = create_vc_proof()
        
        mandate = IntentMandate(
            mandate_id="intent_001",
            mandate_type="intent",
            issuer="user_123",
            subject="agent_456",
            expires_at=int(time.time()) + 300,
            nonce="unique_nonce",
            proof=proof,
            domain="sardis.network",
            purpose="intent",
            scope=["payments", "shopping"],
            requested_amount=50000,  # $500.00
        )
        
        assert mandate.mandate_id == "intent_001"
        assert mandate.mandate_type == "intent"
        assert mandate.scope == ["payments", "shopping"]
        assert mandate.requested_amount == 50000

    def test_intent_mandate_default_scope(self):
        """Test IntentMandate with default empty scope."""
        proof = create_vc_proof()
        
        mandate = IntentMandate(
            mandate_id="intent_002",
            mandate_type="intent",
            issuer="user_123",
            subject="agent_456",
            expires_at=int(time.time()) + 300,
            nonce="nonce_2",
            proof=proof,
            domain="sardis.network",
            purpose="browsing",
        )
        
        assert mandate.scope == []
        assert mandate.requested_amount is None


class TestCartMandate:
    """Tests for CartMandate model."""

    def test_cart_mandate_creation(self):
        """Test creating a CartMandate."""
        proof = create_vc_proof()
        
        line_items = [
            {"sku": "PROD001", "quantity": 2, "price_minor": 1500},
            {"sku": "PROD002", "quantity": 1, "price_minor": 2000},
        ]
        
        mandate = CartMandate(
            mandate_id="cart_001",
            mandate_type="cart",
            issuer="merchant.example.com",
            subject="agent_456",
            expires_at=int(time.time()) + 300,
            nonce="cart_nonce",
            proof=proof,
            domain="merchant.example.com",
            purpose="cart",
            line_items=line_items,
            merchant_domain="merchant.example.com",
            currency="USD",
            subtotal_minor=5000,
            taxes_minor=500,
        )
        
        assert mandate.mandate_id == "cart_001"
        assert len(mandate.line_items) == 2
        assert mandate.subtotal_minor == 5000
        assert mandate.taxes_minor == 500


class TestPaymentMandate:
    """Tests for PaymentMandate model."""

    def test_payment_mandate_creation(self):
        """Test creating a PaymentMandate."""
        proof = create_vc_proof()
        
        mandate = PaymentMandate(
            mandate_id="payment_001",
            mandate_type="payment",
            issuer="agent_456",
            subject="wallet_789",
            expires_at=int(time.time()) + 300,
            nonce="payment_nonce",
            proof=proof,
            domain="sardis.network",
            purpose="checkout",
            chain="base_sepolia",
            token="USDC",
            amount_minor=5500,  # $55.00
            destination="0xRecipientAddress12345678901234567890",
            audit_hash="sha256:abc123def456",
        )
        
        assert mandate.mandate_id == "payment_001"
        assert mandate.chain == "base_sepolia"
        assert mandate.token == "USDC"
        assert mandate.amount_minor == 5500

    def test_payment_mandate_various_tokens(self):
        """Test PaymentMandate with various stablecoin tokens."""
        proof = create_vc_proof()
        
        for token in ["USDC", "USDT", "PYUSD", "EURC"]:
            mandate = PaymentMandate(
                mandate_id=f"payment_{token}",
                mandate_type="payment",
                issuer="agent",
                subject="wallet",
                expires_at=int(time.time()) + 300,
                nonce=f"nonce_{token}",
                proof=proof,
                domain="sardis.network",
                purpose="checkout",
                chain="base",
                token=token,
                amount_minor=10000,
                destination="0x1234567890123456789012345678901234567890",
                audit_hash="hash",
            )
            assert mandate.token == token


class TestMandateChain:
    """Tests for MandateChain model."""

    def test_mandate_chain_creation(self):
        """Test creating a complete MandateChain."""
        proof = create_vc_proof()
        expires = int(time.time()) + 300
        
        intent = IntentMandate(
            mandate_id="intent_chain",
            mandate_type="intent",
            issuer="user_123",
            subject="agent_456",
            expires_at=expires,
            nonce="nonce_1",
            proof=proof,
            domain="sardis.network",
            purpose="intent",
            scope=["payments"],
            requested_amount=10000,
        )
        
        cart = CartMandate(
            mandate_id="cart_chain",
            mandate_type="cart",
            issuer="merchant.com",
            subject="agent_456",
            expires_at=expires,
            nonce="nonce_2",
            proof=proof,
            domain="merchant.com",
            purpose="cart",
            line_items=[{"sku": "ITEM1", "quantity": 1, "price_minor": 10000}],
            merchant_domain="merchant.com",
            currency="USD",
            subtotal_minor=10000,
            taxes_minor=0,
        )
        
        payment = PaymentMandate(
            mandate_id="payment_chain",
            mandate_type="payment",
            issuer="agent_456",
            subject="wallet_789",
            expires_at=expires,
            nonce="nonce_3",
            proof=proof,
            domain="sardis.network",
            purpose="checkout",
            chain="base_sepolia",
            token="USDC",
            amount_minor=10000,
            destination="0xMerchantAddress1234567890123456789012",
            audit_hash="chain_hash",
        )
        
        chain = MandateChain(
            intent=intent,
            cart=cart,
            payment=payment,
        )
        
        assert chain.intent.mandate_id == "intent_chain"
        assert chain.cart.mandate_id == "cart_chain"
        assert chain.payment.mandate_id == "payment_chain"
        assert chain.payment.amount_minor == 10000


class TestVCProof:
    """Tests for VCProof model."""

    def test_vc_proof_creation(self):
        """Test creating a VCProof."""
        proof = VCProof(
            verification_method="did:key:z6MkhaXgBZDvotDkL5LY7QWXXXX#key-1",
            created="2025-12-08T12:00:00Z",
            proof_purpose="assertionMethod",
            proof_value="base64EncodedSignatureValue",
        )
        
        assert proof.type == "DataIntegrityProof"
        assert "did:key" in proof.verification_method
        assert proof.proof_purpose == "assertionMethod"

    def test_vc_proof_default_values(self):
        """Test VCProof default values."""
        proof = VCProof(
            verification_method="did:example:123#key-1",
            created="2025-12-08T00:00:00Z",
            proof_value="signature",
        )
        
        assert proof.type == "DataIntegrityProof"
        assert proof.proof_purpose == "assertionMethod"







