"""Tests for UCP checkout capability."""

import time
from decimal import Decimal

import pytest

from sardis_ucp.models.mandates import UCPCurrency, UCPLineItem, UCPDiscount, UCPDiscountType
from sardis_ucp.capabilities.checkout import (
    UCPCheckoutCapability,
    CheckoutSession,
    CheckoutSessionStatus,
    CheckoutResult,
    CheckoutSessionNotFoundError,
    CheckoutSessionExpiredError,
    InvalidCheckoutOperationError,
    InMemoryCheckoutSessionStore,
)


@pytest.fixture
def checkout_capability():
    """Create a checkout capability for testing."""
    return UCPCheckoutCapability(
        default_tax_rate=Decimal("0.08"),
        session_ttl_seconds=3600,
    )


@pytest.fixture
def sample_line_items():
    """Create sample line items for testing."""
    return [
        UCPLineItem(
            item_id="item_1",
            name="Widget",
            description="A useful widget",
            quantity=2,
            unit_price_minor=1000,
            currency=UCPCurrency.USD,
        ),
        UCPLineItem(
            item_id="item_2",
            name="Gadget",
            description="A cool gadget",
            quantity=1,
            unit_price_minor=2500,
            currency=UCPCurrency.USD,
        ),
    ]


class TestCheckoutCapability:
    """Tests for UCPCheckoutCapability."""

    def test_create_checkout(self, checkout_capability, sample_line_items):
        """Test creating a checkout session."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        assert session.session_id.startswith("cs_")
        assert session.merchant_name == "Test Store"
        assert session.customer_id == "customer_456"
        assert session.status == CheckoutSessionStatus.OPEN
        assert len(session.line_items) == 2

        # Check totals (2*1000 + 1*2500 = 4500, plus 8% tax = 360)
        assert session.subtotal_minor == 4500
        assert session.taxes_minor == 360
        assert session.total_minor == 4860

    def test_create_checkout_with_shipping(self, checkout_capability, sample_line_items):
        """Test checkout with shipping cost."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
            shipping_minor=500,
        )

        assert session.shipping_minor == 500
        # 4500 subtotal + 360 tax + 500 shipping = 5360
        assert session.total_minor == 5360

    def test_create_checkout_generates_cart_mandate(self, checkout_capability, sample_line_items):
        """Test that create_checkout generates a cart mandate."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        assert session.cart_mandate is not None
        assert session.cart_mandate.mandate_id.startswith("cart_")
        assert session.cart_mandate.merchant_id == "merchant_123"

    def test_get_checkout(self, checkout_capability, sample_line_items):
        """Test getting a checkout session."""
        created = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        retrieved = checkout_capability.get_checkout(created.session_id)

        assert retrieved.session_id == created.session_id
        assert retrieved.merchant_name == "Test Store"

    def test_get_checkout_not_found(self, checkout_capability):
        """Test getting a non-existent checkout session."""
        with pytest.raises(CheckoutSessionNotFoundError) as exc_info:
            checkout_capability.get_checkout("cs_nonexistent")

        assert "cs_nonexistent" in str(exc_info.value)

    def test_update_checkout_add_items(self, checkout_capability, sample_line_items):
        """Test adding items to a checkout session."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        new_item = UCPLineItem(
            item_id="item_3",
            name="Accessory",
            description="An accessory",
            quantity=1,
            unit_price_minor=500,
        )

        updated = checkout_capability.update_checkout(
            session.session_id,
            add_items=[new_item],
        )

        assert len(updated.line_items) == 3
        # New subtotal: 4500 + 500 = 5000
        assert updated.subtotal_minor == 5000

    def test_update_checkout_remove_items(self, checkout_capability, sample_line_items):
        """Test removing items from a checkout session."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        updated = checkout_capability.update_checkout(
            session.session_id,
            remove_item_ids=["item_1"],
        )

        assert len(updated.line_items) == 1
        assert updated.line_items[0].item_id == "item_2"
        # New subtotal: just item_2 = 2500
        assert updated.subtotal_minor == 2500

    def test_update_checkout_add_discount(self, checkout_capability, sample_line_items):
        """Test adding a discount to a checkout session."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        discount = UCPDiscount(
            discount_id="disc_1",
            name="10% Off",
            discount_type=UCPDiscountType.PERCENTAGE,
            value=Decimal("10"),
        )

        updated = checkout_capability.update_checkout(
            session.session_id,
            add_discounts=[discount],
        )

        assert len(updated.discounts) == 1
        # Subtotal: 4500, discount: 450, tax: 360, total: 4410
        assert updated.total_minor == 4410

    def test_update_checkout_shipping(self, checkout_capability, sample_line_items):
        """Test updating shipping cost."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        updated = checkout_capability.update_checkout(
            session.session_id,
            shipping_minor=1000,
        )

        assert updated.shipping_minor == 1000

    def test_cancel_checkout(self, checkout_capability, sample_line_items):
        """Test cancelling a checkout session."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        cancelled = checkout_capability.cancel_checkout(session.session_id)

        assert cancelled.status == CheckoutSessionStatus.CANCELLED

    def test_cancel_completed_checkout_fails(self, checkout_capability, sample_line_items):
        """Test that cancelling a completed checkout fails."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        # Manually set status to completed
        session.status = CheckoutSessionStatus.COMPLETED
        checkout_capability._store.save(session)

        with pytest.raises(InvalidCheckoutOperationError):
            checkout_capability.cancel_checkout(session.session_id)


class TestCheckoutCompletion:
    """Tests for checkout completion."""

    @pytest.mark.asyncio
    async def test_complete_checkout_generates_mandates(self, checkout_capability, sample_line_items):
        """Test that completing checkout generates all mandates."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        result = await checkout_capability.complete_checkout(
            session.session_id,
            chain="base",
            token="USDC",
            destination="0x1234567890abcdef1234567890abcdef12345678",
            subject="agent_abc",
            issuer="sardis.sh",
            execute_payment=False,  # Don't execute, just generate mandates
        )

        assert result.success is True
        assert result.payment_mandate is not None
        assert result.payment_mandate.chain == "base"
        assert result.payment_mandate.token == "USDC"
        assert result.payment_mandate.amount_minor == session.total_minor

    @pytest.mark.asyncio
    async def test_complete_empty_cart_fails(self, checkout_capability):
        """Test that completing an empty cart fails."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=[],  # Empty cart
        )

        result = await checkout_capability.complete_checkout(
            session.session_id,
            chain="base",
            token="USDC",
            destination="0x1234567890abcdef1234567890abcdef12345678",
            subject="agent_abc",
            issuer="sardis.sh",
        )

        assert result.success is False
        assert result.error_code == "empty_cart"

    @pytest.mark.asyncio
    async def test_complete_checkout_updates_status(self, checkout_capability, sample_line_items):
        """Test that completing checkout updates session status."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        await checkout_capability.complete_checkout(
            session.session_id,
            chain="base",
            token="USDC",
            destination="0x1234567890abcdef1234567890abcdef12345678",
            subject="agent_abc",
            issuer="sardis.sh",
            execute_payment=False,
        )

        updated = checkout_capability.get_checkout(session.session_id)
        assert updated.status == CheckoutSessionStatus.PENDING_PAYMENT

    @pytest.mark.asyncio
    async def test_complete_already_completed_fails(self, checkout_capability, sample_line_items):
        """Test that completing an already completed session fails."""
        session = checkout_capability.create_checkout(
            merchant_id="merchant_123",
            merchant_name="Test Store",
            merchant_domain="store.test.com",
            customer_id="customer_456",
            line_items=sample_line_items,
        )

        # Complete once
        await checkout_capability.complete_checkout(
            session.session_id,
            chain="base",
            token="USDC",
            destination="0x1234567890abcdef1234567890abcdef12345678",
            subject="agent_abc",
            issuer="sardis.sh",
            execute_payment=False,
        )

        # Try to complete again
        with pytest.raises(InvalidCheckoutOperationError):
            await checkout_capability.complete_checkout(
                session.session_id,
                chain="base",
                token="USDC",
                destination="0x1234567890abcdef1234567890abcdef12345678",
                subject="agent_abc",
                issuer="sardis.sh",
            )


class TestCheckoutSessionStore:
    """Tests for InMemoryCheckoutSessionStore."""

    def test_save_and_get(self):
        """Test saving and retrieving a session."""
        store = InMemoryCheckoutSessionStore()

        session = CheckoutSession(
            session_id="cs_test",
            merchant_id="merchant_1",
            merchant_name="Test",
            merchant_domain="test.com",
            customer_id="customer_1",
        )

        store.save(session)
        retrieved = store.get("cs_test")

        assert retrieved is not None
        assert retrieved.session_id == "cs_test"

    def test_get_nonexistent(self):
        """Test getting a non-existent session returns None."""
        store = InMemoryCheckoutSessionStore()

        assert store.get("cs_nonexistent") is None

    def test_delete(self):
        """Test deleting a session."""
        store = InMemoryCheckoutSessionStore()

        session = CheckoutSession(
            session_id="cs_test",
            merchant_id="merchant_1",
            merchant_name="Test",
            merchant_domain="test.com",
            customer_id="customer_1",
        )

        store.save(session)
        assert store.delete("cs_test") is True
        assert store.get("cs_test") is None

    def test_delete_nonexistent(self):
        """Test deleting a non-existent session returns False."""
        store = InMemoryCheckoutSessionStore()

        assert store.delete("cs_nonexistent") is False
