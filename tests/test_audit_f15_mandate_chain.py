"""Test MandateChain __post_init__ validation."""
import time
import pytest

from sardis_v2_core.mandates import IntentMandate, CartMandate, PaymentMandate, MandateChain, VCProof


def create_test_proof():
    """Helper to create a test VCProof."""
    return VCProof(
        proof_type="Ed25519Signature2020",
        verification_method="did:key:ed25519:test",
        proof_purpose="assertionMethod",
        created=str(int(time.time())),
        proof_value="test-signature"
    )


def test_mandate_chain_valid():
    """Valid mandate chain should be created successfully."""
    agent_id = "agent:test@example.com"
    expires_at = int(time.time()) + 3600

    intent = IntentMandate(
        mandate_id="intent-1",
        mandate_type="intent",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at,
        domain="example.com",
        purpose="intent",
        nonce="nonce1",
        scope=["payments"],
        requested_amount=2000000,
        proof=create_test_proof()
    )

    cart = CartMandate(
        mandate_id="cart-1",
        mandate_type="cart",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at + 100,  # Cart expires after intent
        domain="example.com",
        purpose="cart",
        nonce="nonce2",
        line_items=[{"item_id": "1", "name": "Item", "quantity": 1, "price_minor": 1000}],
        merchant_domain="merchant.com",
        currency="USD",
        subtotal_minor=1000,
        taxes_minor=100,
        proof=create_test_proof()
    )

    payment = PaymentMandate(
        mandate_id="payment-1",
        mandate_type="payment",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at + 200,  # Payment expires after cart
        domain="example.com",
        purpose="checkout",
        nonce="nonce3",
        chain="base",
        token="USDC",
        amount_minor=1100,  # Within cart total (1000 + 100)
        destination="0x1234567890123456789012345678901234567890",
        audit_hash="test-hash",
        merchant_domain="merchant.com",
        proof=create_test_proof()
    )

    # Should create successfully
    chain = MandateChain(intent=intent, cart=cart, payment=payment)
    assert chain.intent == intent
    assert chain.cart == cart
    assert chain.payment == payment


def test_mandate_chain_mismatched_agent_ids():
    """Chain with different agent_ids should fail."""
    expires_at = int(time.time()) + 3600

    intent = IntentMandate(
        mandate_id="intent-1",
        mandate_type="intent",
        subject="agent:alice@example.com",
        issuer="agent:alice@example.com",
        expires_at=expires_at,
        domain="example.com",
        purpose="intent",
        nonce="nonce1",
        scope=["payments"],
        requested_amount=2000000,
        proof=create_test_proof()
    )

    cart = CartMandate(
        mandate_id="cart-1",
        mandate_type="cart",
        subject="agent:bob@example.com",  # Different agent!
        issuer="agent:bob@example.com",
        expires_at=expires_at + 100,
        domain="example.com",
        purpose="cart",
        nonce="nonce2",
        line_items=[{"item_id": "1", "name": "Item", "quantity": 1, "price_minor": 1000}],
        merchant_domain="merchant.com",
        currency="USD",
        subtotal_minor=1000,
        taxes_minor=0,
        proof=create_test_proof()
    )

    payment = PaymentMandate(
        mandate_id="payment-1",
        mandate_type="payment",
        subject="agent:alice@example.com",
        issuer="agent:alice@example.com",
        expires_at=expires_at + 200,
        domain="example.com",
        purpose="checkout",
        nonce="nonce3",
        chain="base",
        token="USDC",
        amount_minor=1000,
        destination="0x1234567890123456789012345678901234567890",
        audit_hash="test-hash",
        merchant_domain="merchant.com",
        proof=create_test_proof()
    )

    # Should fail due to agent_id mismatch
    with pytest.raises(ValueError, match="All mandates must reference the same agent_id"):
        MandateChain(intent=intent, cart=cart, payment=payment)


def test_mandate_chain_payment_exceeds_cart_total():
    """Chain where payment exceeds cart total should fail."""
    agent_id = "agent:test@example.com"
    expires_at = int(time.time()) + 3600

    intent = IntentMandate(
        mandate_id="intent-1",
        mandate_type="intent",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at,
        domain="example.com",
        purpose="intent",
        nonce="nonce1",
        scope=["payments"],
        requested_amount=10000000,
        proof=create_test_proof()
    )

    cart = CartMandate(
        mandate_id="cart-1",
        mandate_type="cart",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at + 100,
        domain="example.com",
        purpose="cart",
        nonce="nonce2",
        line_items=[{"item_id": "1", "name": "Item", "quantity": 1, "price_minor": 1000}],
        merchant_domain="merchant.com",
        currency="USD",
        subtotal_minor=1000,
        taxes_minor=100,
        proof=create_test_proof()
    )

    payment = PaymentMandate(
        mandate_id="payment-1",
        mandate_type="payment",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at + 200,
        domain="example.com",
        purpose="checkout",
        nonce="nonce3",
        chain="base",
        token="USDC",
        amount_minor=2000,  # Exceeds cart total of 1100!
        destination="0x1234567890123456789012345678901234567890",
        audit_hash="test-hash",
        merchant_domain="merchant.com",
        proof=create_test_proof()
    )

    # Should fail due to payment > cart total
    with pytest.raises(ValueError, match="Payment amount .* exceeds cart total"):
        MandateChain(intent=intent, cart=cart, payment=payment)


def test_mandate_chain_payment_exceeds_intent_amount():
    """Chain where payment exceeds intent requested_amount should fail."""
    agent_id = "agent:test@example.com"
    expires_at = int(time.time()) + 3600

    intent = IntentMandate(
        mandate_id="intent-1",
        mandate_type="intent",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at,
        domain="example.com",
        purpose="intent",
        nonce="nonce1",
        scope=["payments"],
        requested_amount=500,  # Intent only allows up to 500
        proof=create_test_proof()
    )

    cart = CartMandate(
        mandate_id="cart-1",
        mandate_type="cart",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at + 100,
        domain="example.com",
        purpose="cart",
        nonce="nonce2",
        line_items=[{"item_id": "1", "name": "Item", "quantity": 1, "price_minor": 900}],
        merchant_domain="merchant.com",
        currency="USD",
        subtotal_minor=900,
        taxes_minor=100,
        proof=create_test_proof()
    )

    payment = PaymentMandate(
        mandate_id="payment-1",
        mandate_type="payment",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at + 200,
        domain="example.com",
        purpose="checkout",
        nonce="nonce3",
        chain="base",
        token="USDC",
        amount_minor=1000,  # Within cart total but exceeds intent!
        destination="0x1234567890123456789012345678901234567890",
        audit_hash="test-hash",
        merchant_domain="merchant.com",
        proof=create_test_proof()
    )

    # Should fail due to payment > intent requested_amount
    with pytest.raises(ValueError, match="Payment amount .* exceeds intent requested amount"):
        MandateChain(intent=intent, cart=cart, payment=payment)


def test_mandate_chain_timestamps_out_of_order():
    """Chain with timestamps not in order (intent <= cart <= payment) should fail."""
    agent_id = "agent:test@example.com"
    base_time = int(time.time()) + 3600

    intent = IntentMandate(
        mandate_id="intent-1",
        mandate_type="intent",
        subject=agent_id,
        issuer=agent_id,
        expires_at=base_time + 1000,  # Intent expires LAST
        domain="example.com",
        purpose="intent",
        nonce="nonce1",
        scope=["payments"],
        requested_amount=2000000,
        proof=create_test_proof()
    )

    cart = CartMandate(
        mandate_id="cart-1",
        mandate_type="cart",
        subject=agent_id,
        issuer=agent_id,
        expires_at=base_time + 500,  # Cart in middle
        domain="example.com",
        purpose="cart",
        nonce="nonce2",
        line_items=[{"item_id": "1", "name": "Item", "quantity": 1, "price_minor": 1000}],
        merchant_domain="merchant.com",
        currency="USD",
        subtotal_minor=1000,
        taxes_minor=0,
        proof=create_test_proof()
    )

    payment = PaymentMandate(
        mandate_id="payment-1",
        mandate_type="payment",
        subject=agent_id,
        issuer=agent_id,
        expires_at=base_time,  # Payment expires FIRST - wrong order!
        domain="example.com",
        purpose="checkout",
        nonce="nonce3",
        chain="base",
        token="USDC",
        amount_minor=1000,
        destination="0x1234567890123456789012345678901234567890",
        audit_hash="test-hash",
        merchant_domain="merchant.com",
        proof=create_test_proof()
    )

    # Should fail due to incorrect timestamp ordering
    with pytest.raises(ValueError, match="Mandate expiration timestamps must be ordered"):
        MandateChain(intent=intent, cart=cart, payment=payment)


def test_mandate_chain_intent_without_requested_amount():
    """Chain where intent has no requested_amount should not validate against it."""
    agent_id = "agent:test@example.com"
    expires_at = int(time.time()) + 3600

    intent = IntentMandate(
        mandate_id="intent-1",
        mandate_type="intent",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at,
        domain="example.com",
        purpose="intent",
        nonce="nonce1",
        scope=["payments"],
        requested_amount=None,  # No amount limit in intent
        proof=create_test_proof()
    )

    cart = CartMandate(
        mandate_id="cart-1",
        mandate_type="cart",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at + 100,
        domain="example.com",
        purpose="cart",
        nonce="nonce2",
        line_items=[{"item_id": "1", "name": "Item", "quantity": 1, "price_minor": 1000000}],
        merchant_domain="merchant.com",
        currency="USD",
        subtotal_minor=1000000,
        taxes_minor=0,
        proof=create_test_proof()
    )

    payment = PaymentMandate(
        mandate_id="payment-1",
        mandate_type="payment",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at + 200,
        domain="example.com",
        purpose="checkout",
        nonce="nonce3",
        chain="base",
        token="USDC",
        amount_minor=1000000,  # Large amount, but no intent limit
        destination="0x1234567890123456789012345678901234567890",
        audit_hash="test-hash",
        merchant_domain="merchant.com",
        proof=create_test_proof()
    )

    # Should succeed - no intent amount limit to validate against
    chain = MandateChain(intent=intent, cart=cart, payment=payment)
    assert chain is not None
