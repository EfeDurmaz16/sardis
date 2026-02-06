"""UCP Conformance Test Harness.

Tests the complete UCP checkout flow, state machine, AP2 adapter integration,
and security guarantees. All tests run in-memory without external services.
"""

import hashlib
import time
from decimal import Decimal
from typing import Optional

import pytest

from sardis_ucp.adapters.ap2 import (
    AP2CartMandate,
    AP2IntentMandate,
    AP2MandateAdapter,
    AP2PaymentMandate,
    AP2ToUCPResult,
    UCPToAP2Result,
)
from sardis_ucp.capabilities.checkout import (
    CheckoutSession,
    CheckoutSessionStatus,
    InvalidCheckoutOperationError,
    UCPCheckoutCapability,
    CheckoutSessionExpiredError,
    CheckoutSessionNotFoundError,
)
from sardis_ucp.models.mandates import (
    UCPCartMandate,
    UCPCheckoutMandate,
    UCPCurrency,
    UCPDiscount,
    UCPDiscountType,
    UCPLineItem,
    UCPPaymentMandate,
)

pytestmark = [pytest.mark.protocol_conformance, pytest.mark.ucp]


# ============ Fixtures ============


@pytest.fixture
def checkout_capability():
    """Create a UCP checkout capability with in-memory storage."""
    return UCPCheckoutCapability(
        default_tax_rate=Decimal("0.08"),
        session_ttl_seconds=3600,
    )


@pytest.fixture
def adapter():
    """Create an AP2 mandate adapter."""
    return AP2MandateAdapter(platform_domain="sardis.sh")


@pytest.fixture
def sample_line_items():
    """Create sample line items for testing."""
    return [
        UCPLineItem(
            item_id="item_1",
            name="Widget A",
            description="A premium widget",
            quantity=2,
            unit_price_minor=5000,  # $50.00
            currency=UCPCurrency.USD,
            sku="WGT-A-001",
        ),
        UCPLineItem(
            item_id="item_2",
            name="Gadget B",
            description="A deluxe gadget",
            quantity=1,
            unit_price_minor=10000,  # $100.00
            currency=UCPCurrency.USD,
            sku="GDG-B-002",
        ),
    ]


@pytest.fixture
def sample_discount():
    """Create a sample discount for testing."""
    return UCPDiscount(
        discount_id="disc_10pct",
        name="10% Off",
        discount_type=UCPDiscountType.PERCENTAGE,
        value=Decimal("10"),
    )


# ============ Test Cases ============


async def test_end_to_end_ucp_flow(checkout_capability, sample_line_items):
    """Test 1: End-to-end UCP flow - create -> update (add items) -> complete with AP2 mandate generation."""
    # Create checkout session
    session = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_456",
        line_items=sample_line_items[:1],  # Start with 1 item
        currency=UCPCurrency.USD,
        shipping_minor=500,  # $5.00 shipping
    )

    assert session.session_id.startswith("cs_")
    assert session.status == CheckoutSessionStatus.OPEN
    assert len(session.line_items) == 1
    assert session.cart_mandate is not None
    initial_total = session.total_minor

    # Update: add more items
    updated_session = checkout_capability.update_checkout(
        session_id=session.session_id,
        add_items=[sample_line_items[1]],
    )

    assert len(updated_session.line_items) == 2
    assert updated_session.total_minor > initial_total
    assert updated_session.status == CheckoutSessionStatus.OPEN

    # Complete checkout (without payment execution)
    result = await checkout_capability.complete_checkout(
        session_id=session.session_id,
        chain="base",
        token="USDC",
        destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        subject="agent_456",
        issuer="sardis.sh",
        execute_payment=False,
    )

    assert result.success is True
    assert result.payment_mandate is not None
    assert result.payment_mandate.chain == "base"
    assert result.payment_mandate.token == "USDC"
    assert result.payment_mandate.amount_minor == updated_session.total_minor
    assert result.payment_mandate.audit_hash is not None

    # Verify session state after completion
    completed_session = checkout_capability.get_checkout(session.session_id)
    assert completed_session.status == CheckoutSessionStatus.PENDING_PAYMENT
    assert completed_session.checkout_mandate is not None
    assert completed_session.payment_mandate is not None


async def test_escalation_flow(checkout_capability, sample_line_items):
    """Test 2: Escalation flow - create -> escalate -> resolve -> complete."""
    # Create checkout session
    session = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_789",
        line_items=sample_line_items,
        currency=UCPCurrency.USD,
    )

    assert session.status == CheckoutSessionStatus.OPEN

    # Escalate for review
    escalated_session = checkout_capability.escalate_checkout(
        session_id=session.session_id,
        reason="High-value transaction requires approval",
    )

    assert escalated_session.status == CheckoutSessionStatus.REQUIRES_ESCALATION
    assert escalated_session.escalation_reason == "High-value transaction requires approval"
    assert escalated_session.escalation_resolved_at is None

    # Attempt to complete while escalated (should fail)
    with pytest.raises(InvalidCheckoutOperationError) as exc_info:
        await checkout_capability.complete_checkout(
            session_id=session.session_id,
            chain="base",
            token="USDC",
            destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            subject="agent_789",
            issuer="sardis.sh",
            execute_payment=False,
        )
    assert exc_info.value.code == "invalid_operation"

    # Resolve escalation
    resolved_session = checkout_capability.resolve_escalation(session_id=session.session_id)

    assert resolved_session.status == CheckoutSessionStatus.OPEN
    assert resolved_session.escalation_resolved_at is not None

    # Now complete should work
    result = await checkout_capability.complete_checkout(
        session_id=session.session_id,
        chain="base",
        token="USDC",
        destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        subject="agent_789",
        issuer="sardis.sh",
        execute_payment=False,
    )

    assert result.success is True
    assert result.payment_mandate is not None


async def test_cancellation_flow(checkout_capability, sample_line_items):
    """Test 3: Cancellation flow - create -> cancel."""
    # Create checkout session
    session = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_999",
        line_items=sample_line_items,
        currency=UCPCurrency.USD,
    )

    assert session.status == CheckoutSessionStatus.OPEN

    # Cancel the session
    cancelled_session = checkout_capability.cancel_checkout(session_id=session.session_id)

    assert cancelled_session.status == CheckoutSessionStatus.CANCELLED

    # Attempt to update cancelled session (should fail)
    with pytest.raises(InvalidCheckoutOperationError) as exc_info:
        checkout_capability.update_checkout(
            session_id=session.session_id,
            shipping_minor=1000,
        )
    assert exc_info.value.code == "invalid_operation"

    # Attempt to complete cancelled session (should fail)
    with pytest.raises(InvalidCheckoutOperationError):
        await checkout_capability.complete_checkout(
            session_id=session.session_id,
            chain="base",
            token="USDC",
            destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            subject="agent_999",
            issuer="sardis.sh",
            execute_payment=False,
        )


def test_expiration_flow(checkout_capability, sample_line_items):
    """Test 4: Expiration flow - create -> verify expired status after TTL."""
    # Create checkout session with very short TTL
    short_ttl_capability = UCPCheckoutCapability(session_ttl_seconds=1)

    session = short_ttl_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_expiry",
        line_items=sample_line_items,
        currency=UCPCurrency.USD,
    )

    assert session.status == CheckoutSessionStatus.OPEN
    assert not session.is_expired()

    # Wait for expiration
    time.sleep(1.5)

    assert session.is_expired()

    # Attempt to update expired session (should fail)
    with pytest.raises(CheckoutSessionExpiredError) as exc_info:
        short_ttl_capability.update_checkout(
            session_id=session.session_id,
            shipping_minor=1000,
        )
    assert exc_info.value.code == "session_expired"

    # Verify status was updated to EXPIRED
    expired_session = short_ttl_capability.get_checkout(session.session_id)
    assert expired_session.status == CheckoutSessionStatus.EXPIRED


def test_ap2_adapter_round_trip(adapter, sample_line_items):
    """Test 5: AP2 adapter round-trip - UCP -> AP2 -> UCP (data integrity preserved)."""
    # Create UCP mandates
    ucp_cart = UCPCartMandate(
        mandate_id="cart_original",
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        line_items=sample_line_items,
        currency=UCPCurrency.USD,
        subtotal_minor=20000,
        taxes_minor=1600,
        shipping_minor=500,
        expires_at=int(time.time()) + 3600,
    )

    ucp_checkout = UCPCheckoutMandate(
        mandate_id="checkout_original",
        cart_mandate_id=ucp_cart.mandate_id,
        subject="agent_456",
        issuer="sardis.sh",
        authorized_amount_minor=22100,
        currency=UCPCurrency.USD,
        expires_at=int(time.time()) + 900,
    )

    ucp_payment = UCPPaymentMandate(
        mandate_id="payment_original",
        checkout_mandate_id=ucp_checkout.mandate_id,
        subject="agent_456",
        issuer="sardis.sh",
        chain="base",
        token="USDC",
        amount_minor=22100,
        destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        audit_hash="test_hash",
        expires_at=int(time.time()) + 300,
    )

    # Convert UCP -> AP2
    ucp_to_ap2_result = adapter.ucp_to_ap2_chain(ucp_cart, ucp_checkout, ucp_payment)

    assert ucp_to_ap2_result.success is True
    assert ucp_to_ap2_result.security_locked is False
    assert ucp_to_ap2_result.intent_mandate is not None
    assert ucp_to_ap2_result.cart_mandate is not None
    assert ucp_to_ap2_result.payment_mandate is not None

    # Convert AP2 -> UCP
    ap2_to_ucp_result = adapter.ap2_to_ucp_chain(
        intent=ucp_to_ap2_result.intent_mandate,
        cart=ucp_to_ap2_result.cart_mandate,
        payment=ucp_to_ap2_result.payment_mandate,
        merchant_id="merchant_123",
        merchant_name="Test Store",
    )

    assert ap2_to_ucp_result.success is True
    assert ap2_to_ucp_result.security_locked is False
    assert ap2_to_ucp_result.cart_mandate is not None
    assert ap2_to_ucp_result.checkout_mandate is not None
    assert ap2_to_ucp_result.payment_mandate is not None

    # Verify data integrity
    result_cart = ap2_to_ucp_result.cart_mandate
    assert result_cart.merchant_domain == ucp_cart.merchant_domain
    assert result_cart.subtotal_minor == ucp_cart.subtotal_minor
    assert result_cart.taxes_minor == ucp_cart.taxes_minor
    assert len(result_cart.line_items) == len(ucp_cart.line_items)

    result_payment = ap2_to_ucp_result.payment_mandate
    assert result_payment.chain == ucp_payment.chain
    assert result_payment.token == ucp_payment.token
    assert result_payment.amount_minor == ucp_payment.amount_minor


def test_security_lock_partial_mandate_rejection(adapter):
    """Test 6: Security Lock test - verify partial mandate chains are rejected by adapter."""
    # Create a cart mandate with invalid data that will cause conversion failure
    invalid_cart = UCPCartMandate(
        mandate_id="cart_invalid",
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        line_items=[],  # Empty line items - should be valid but shows structure
        currency=UCPCurrency.USD,
        subtotal_minor=0,
        taxes_minor=0,
        shipping_minor=0,
        expires_at=int(time.time()) + 3600,
    )

    checkout = UCPCheckoutMandate(
        mandate_id="checkout_123",
        cart_mandate_id="cart_invalid",
        subject="agent_456",
        issuer="sardis.sh",
        authorized_amount_minor=1000,
        currency=UCPCurrency.USD,
    )

    payment = UCPPaymentMandate(
        mandate_id="payment_123",
        checkout_mandate_id="checkout_123",
        subject="agent_456",
        issuer="sardis.sh",
        chain="base",
        token="USDC",
        amount_minor=1000,
        destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        audit_hash="test",
    )

    # Create a mock verifier that always fails
    class FailingVerifier:
        def verify_chain(self, intent, cart, payment):
            return False, "Chain verification failed"

    adapter_with_verifier = AP2MandateAdapter(verifier=FailingVerifier())

    # Attempt conversion with failing verifier
    result = adapter_with_verifier.ucp_to_ap2_chain(invalid_cart, checkout, payment)

    # Should fail with security lock
    assert result.success is False
    assert result.security_locked is True
    assert result.error_code == "security_lock"
    assert "verification failed" in result.error.lower()

    # Verify no partial mandates are returned
    assert result.intent_mandate is None
    assert result.cart_mandate is None
    assert result.payment_mandate is None


def test_cart_modification(checkout_capability, sample_line_items, sample_discount):
    """Test 7: Cart modification - add items, remove items, add discounts, verify totals."""
    # Create initial session
    session = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_cart",
        line_items=[sample_line_items[0]],
        currency=UCPCurrency.USD,
        tax_rate=Decimal("0.08"),
    )

    initial_total = session.total_minor
    assert len(session.line_items) == 1

    # Add items
    session = checkout_capability.update_checkout(
        session_id=session.session_id,
        add_items=[sample_line_items[1]],
    )

    assert len(session.line_items) == 2
    assert session.total_minor > initial_total

    # Add discount
    session = checkout_capability.update_checkout(
        session_id=session.session_id,
        add_discounts=[sample_discount],
    )

    assert len(session.discounts) == 1
    discounted_total = session.total_minor
    assert discounted_total < initial_total * 2  # Should be less due to discount

    # Remove an item
    session = checkout_capability.update_checkout(
        session_id=session.session_id,
        remove_item_ids=["item_1"],
    )

    assert len(session.line_items) == 1
    assert session.line_items[0].item_id == "item_2"

    # Remove discount
    session = checkout_capability.update_checkout(
        session_id=session.session_id,
        remove_discount_ids=["disc_10pct"],
    )

    assert len(session.discounts) == 0
    # Verify totals are recalculated correctly
    expected_subtotal = 10000  # 1 item at $100
    expected_taxes = int(expected_subtotal * Decimal("0.08"))
    assert session.subtotal_minor == expected_subtotal
    assert session.taxes_minor == expected_taxes


async def test_audit_hash_verification(checkout_capability, adapter, sample_line_items):
    """Test 8: Audit hash verification - verify cart->checkout->payment hash chain integrity."""
    # Create and complete checkout
    session = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_audit",
        line_items=sample_line_items,
        currency=UCPCurrency.USD,
    )

    result = await checkout_capability.complete_checkout(
        session_id=session.session_id,
        chain="base",
        token="USDC",
        destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        subject="agent_audit",
        issuer="sardis.sh",
        execute_payment=False,
    )

    assert result.success is True
    payment_mandate = result.payment_mandate

    # Verify audit hash
    completed_session = checkout_capability.get_checkout(session.session_id)
    is_valid = adapter.verify_audit_hash(
        payment_mandate=payment_mandate,
        cart_mandate_id=completed_session.cart_mandate.mandate_id,
        checkout_mandate_id=completed_session.checkout_mandate.mandate_id,
    )

    assert is_valid is True

    # Tamper with payment mandate and verify it fails
    tampered_payment = UCPPaymentMandate(
        mandate_id=payment_mandate.mandate_id,
        checkout_mandate_id=payment_mandate.checkout_mandate_id,
        subject=payment_mandate.subject,
        issuer=payment_mandate.issuer,
        chain=payment_mandate.chain,
        token=payment_mandate.token,
        amount_minor=payment_mandate.amount_minor + 1000,  # Tampered amount
        destination=payment_mandate.destination,
        audit_hash=payment_mandate.audit_hash,  # Old hash
    )

    is_valid_tampered = adapter.verify_audit_hash(
        payment_mandate=tampered_payment,
        cart_mandate_id=completed_session.cart_mandate.mandate_id,
        checkout_mandate_id=completed_session.checkout_mandate.mandate_id,
    )

    assert is_valid_tampered is False


async def test_state_machine_exhaustive(checkout_capability, sample_line_items):
    """Test 9: State machine exhaustive test - verify all valid transitions succeed and invalid ones raise errors."""
    # Valid transition: OPEN -> PENDING_PAYMENT
    session = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_state",
        line_items=sample_line_items,
        currency=UCPCurrency.USD,
    )

    assert session.status == CheckoutSessionStatus.OPEN

    result = await checkout_capability.complete_checkout(
        session_id=session.session_id,
        chain="base",
        token="USDC",
        destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        subject="agent_state",
        issuer="sardis.sh",
        execute_payment=False,
    )

    session = checkout_capability.get_checkout(session.session_id)
    assert session.status == CheckoutSessionStatus.PENDING_PAYMENT

    # Invalid transition: PENDING_PAYMENT -> update (should fail)
    with pytest.raises(InvalidCheckoutOperationError):
        checkout_capability.update_checkout(
            session_id=session.session_id,
            shipping_minor=1000,
        )

    # Test OPEN -> CANCELLED transition
    session2 = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_state2",
        line_items=sample_line_items,
        currency=UCPCurrency.USD,
    )

    cancelled_session = checkout_capability.cancel_checkout(session_id=session2.session_id)
    assert cancelled_session.status == CheckoutSessionStatus.CANCELLED

    # Invalid: CANCELLED -> CANCELLED (should fail)
    with pytest.raises(InvalidCheckoutOperationError):
        checkout_capability.cancel_checkout(session_id=session2.session_id)

    # Test OPEN -> REQUIRES_ESCALATION transition
    session3 = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_state3",
        line_items=sample_line_items,
        currency=UCPCurrency.USD,
    )

    escalated = checkout_capability.escalate_checkout(
        session_id=session3.session_id,
        reason="Test escalation",
    )
    assert escalated.status == CheckoutSessionStatus.REQUIRES_ESCALATION

    # Valid: REQUIRES_ESCALATION -> OPEN
    resolved = checkout_capability.resolve_escalation(session_id=session3.session_id)
    assert resolved.status == CheckoutSessionStatus.OPEN

    # Invalid: OPEN (already resolved) -> resolve again (should fail)
    with pytest.raises(InvalidCheckoutOperationError):
        checkout_capability.resolve_escalation(session_id=session3.session_id)


async def test_requires_escalation_complete_blocked(checkout_capability, sample_line_items):
    """Test 10: REQUIRES_ESCALATION state - cannot complete session in escalation state."""
    # Create session
    session = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_blocked",
        line_items=sample_line_items,
        currency=UCPCurrency.USD,
    )

    # Escalate
    escalated_session = checkout_capability.escalate_checkout(
        session_id=session.session_id,
        reason="Suspicious transaction pattern",
    )

    assert escalated_session.status == CheckoutSessionStatus.REQUIRES_ESCALATION

    # Attempt to complete while escalated (should fail)
    with pytest.raises(InvalidCheckoutOperationError) as exc_info:
        await checkout_capability.complete_checkout(
            session_id=session.session_id,
            chain="base",
            token="USDC",
            destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            subject="agent_blocked",
            issuer="sardis.sh",
            execute_payment=False,
        )

    assert exc_info.value.code == "invalid_operation"
    assert exc_info.value.details["status"] == CheckoutSessionStatus.REQUIRES_ESCALATION.value

    # Attempt to cancel while escalated (should succeed)
    cancelled = checkout_capability.cancel_checkout(session_id=session.session_id)
    assert cancelled.status == CheckoutSessionStatus.CANCELLED


async def test_empty_cart_completion_fails(checkout_capability):
    """Test 11: Verify empty cart cannot be completed."""
    session = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_empty",
        line_items=[],  # Empty cart
        currency=UCPCurrency.USD,
    )

    result = await checkout_capability.complete_checkout(
        session_id=session.session_id,
        chain="base",
        token="USDC",
        destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        subject="agent_empty",
        issuer="sardis.sh",
        execute_payment=False,
    )

    assert result.success is False
    assert result.error_code == "empty_cart"
    assert "empty" in result.error.lower()


def test_session_not_found_error(checkout_capability):
    """Test 12: Verify proper error handling for non-existent sessions."""
    with pytest.raises(CheckoutSessionNotFoundError) as exc_info:
        checkout_capability.get_checkout("cs_nonexistent")

    assert exc_info.value.code == "session_not_found"

    with pytest.raises(CheckoutSessionNotFoundError):
        checkout_capability.update_checkout(
            session_id="cs_nonexistent",
            shipping_minor=500,
        )

    with pytest.raises(CheckoutSessionNotFoundError):
        checkout_capability.cancel_checkout("cs_nonexistent")


async def test_mandate_chain_linking(checkout_capability, sample_line_items):
    """Test 13: Verify mandate chain properly links cart -> checkout -> payment."""
    session = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_chain",
        line_items=sample_line_items,
        currency=UCPCurrency.USD,
    )

    # Cart mandate created on session creation
    assert session.cart_mandate is not None
    cart_mandate_id = session.cart_mandate.mandate_id

    # Complete to generate checkout and payment mandates
    result = await checkout_capability.complete_checkout(
        session_id=session.session_id,
        chain="base",
        token="USDC",
        destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        subject="agent_chain",
        issuer="sardis.sh",
        execute_payment=False,
    )

    completed_session = checkout_capability.get_checkout(session.session_id)

    # Verify chain linkage
    assert completed_session.cart_mandate is not None
    assert completed_session.checkout_mandate is not None
    assert completed_session.payment_mandate is not None

    # Checkout mandate references cart
    assert completed_session.checkout_mandate.cart_mandate_id == cart_mandate_id

    # Payment mandate references checkout
    assert (
        completed_session.payment_mandate.checkout_mandate_id
        == completed_session.checkout_mandate.mandate_id
    )

    # Audit hash includes cart and checkout mandate IDs
    audit_data = (
        f"{cart_mandate_id}:"
        f"{completed_session.checkout_mandate.mandate_id}:"
        f"{completed_session.payment_mandate.amount_minor}:"
        f"{completed_session.payment_mandate.chain}:"
        f"{completed_session.payment_mandate.token}:"
        f"{completed_session.payment_mandate.destination}"
    )
    expected_hash = hashlib.sha256(audit_data.encode()).hexdigest()

    assert completed_session.payment_mandate.audit_hash == expected_hash


def test_discount_calculation_accuracy(checkout_capability, sample_line_items):
    """Test 14: Verify discount calculations are accurate for percentage and fixed discounts."""
    session = checkout_capability.create_checkout(
        merchant_id="merchant_123",
        merchant_name="Test Store",
        merchant_domain="teststore.com",
        customer_id="agent_discount",
        line_items=sample_line_items,
        currency=UCPCurrency.USD,
        tax_rate=Decimal("0.00"),  # No tax for simpler calculation
    )

    subtotal = session.subtotal_minor  # Should be 20000 (2*5000 + 1*10000)
    assert subtotal == 20000

    # Apply 10% discount
    percentage_discount = UCPDiscount(
        discount_id="disc_10pct",
        name="10% Off",
        discount_type=UCPDiscountType.PERCENTAGE,
        value=Decimal("10"),
    )

    session = checkout_capability.update_checkout(
        session_id=session.session_id,
        add_discounts=[percentage_discount],
    )

    # 10% of 20000 = 2000
    assert session.total_minor == 20000 - 2000

    # Remove percentage discount and add fixed discount
    fixed_discount = UCPDiscount(
        discount_id="disc_fixed",
        name="$50 Off",
        discount_type=UCPDiscountType.FIXED,
        value=Decimal("5000"),  # $50 in minor units
    )

    session = checkout_capability.update_checkout(
        session_id=session.session_id,
        remove_discount_ids=["disc_10pct"],
        add_discounts=[fixed_discount],
    )

    assert session.total_minor == 20000 - 5000

    # Add both discounts
    session = checkout_capability.update_checkout(
        session_id=session.session_id,
        add_discounts=[percentage_discount],
    )

    # Should apply both: 10% (2000) + fixed (5000) = 7000 off
    assert session.total_minor == 20000 - 7000
