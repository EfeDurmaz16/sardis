"""Tests for UCP models."""

import time
from decimal import Decimal

import pytest

from sardis_ucp.models.mandates import (
    UCPCurrency,
    UCPDiscountType,
    UCPLineItem,
    UCPDiscount,
    UCPCartMandate,
    UCPCheckoutMandate,
    UCPPaymentMandate,
)
from sardis_ucp.models.profiles import (
    UCPCapabilityType,
    UCPCapability,
    UCPPaymentCapability,
    UCPEndpoints,
    UCPBusinessProfile,
    UCPPlatformProfile,
)
from sardis_ucp.models.orders import (
    UCPOrderStatus,
    UCPFulfillmentStatus,
    UCPShippingAddress,
    UCPFulfillmentEvent,
    UCPFulfillment,
    UCPOrder,
)


class TestUCPLineItem:
    """Tests for UCPLineItem."""

    def test_create_line_item(self):
        """Test creating a line item."""
        item = UCPLineItem(
            item_id="item_1",
            name="Test Product",
            description="A test product",
            quantity=2,
            unit_price_minor=1000,
            currency=UCPCurrency.USD,
        )

        assert item.item_id == "item_1"
        assert item.name == "Test Product"
        assert item.quantity == 2
        assert item.unit_price_minor == 1000

    def test_total_minor_calculation(self):
        """Test line item total calculation."""
        item = UCPLineItem(
            item_id="item_1",
            name="Test",
            description="Test",
            quantity=3,
            unit_price_minor=500,
        )

        assert item.total_minor == 1500  # 3 * 500

    def test_tax_amount_calculation(self):
        """Test line item tax calculation."""
        item = UCPLineItem(
            item_id="item_1",
            name="Test",
            description="Test",
            quantity=2,
            unit_price_minor=1000,
            taxable=True,
            tax_rate=Decimal("0.08"),
        )

        # Total is 2000, tax at 8% = 160
        assert item.tax_amount_minor == 160

    def test_non_taxable_item(self):
        """Test non-taxable line item has zero tax."""
        item = UCPLineItem(
            item_id="item_1",
            name="Test",
            description="Test",
            quantity=2,
            unit_price_minor=1000,
            taxable=False,
            tax_rate=Decimal("0.08"),
        )

        assert item.tax_amount_minor == 0

    def test_to_dict(self):
        """Test line item serialization."""
        item = UCPLineItem(
            item_id="item_1",
            name="Test Product",
            description="A test",
            quantity=1,
            unit_price_minor=999,
            sku="SKU123",
        )

        data = item.to_dict()

        assert data["item_id"] == "item_1"
        assert data["name"] == "Test Product"
        assert data["sku"] == "SKU123"
        assert data["unit_price_minor"] == 999


class TestUCPDiscount:
    """Tests for UCPDiscount."""

    def test_percentage_discount(self):
        """Test percentage discount calculation."""
        discount = UCPDiscount(
            discount_id="disc_1",
            name="10% Off",
            discount_type=UCPDiscountType.PERCENTAGE,
            value=Decimal("10"),
        )

        # 10% of 10000 = 1000
        assert discount.calculate_discount_minor(10000) == 1000

    def test_fixed_discount(self):
        """Test fixed amount discount."""
        discount = UCPDiscount(
            discount_id="disc_1",
            name="$5 Off",
            discount_type=UCPDiscountType.FIXED,
            value=Decimal("500"),
        )

        assert discount.calculate_discount_minor(10000) == 500

    def test_fixed_discount_capped_at_subtotal(self):
        """Test fixed discount doesn't exceed subtotal."""
        discount = UCPDiscount(
            discount_id="disc_1",
            name="$50 Off",
            discount_type=UCPDiscountType.FIXED,
            value=Decimal("5000"),
        )

        # Discount of $50 on $30 subtotal should be capped at $30
        assert discount.calculate_discount_minor(3000) == 3000

    def test_minimum_purchase_requirement(self):
        """Test discount with minimum purchase."""
        discount = UCPDiscount(
            discount_id="disc_1",
            name="$10 Off over $50",
            discount_type=UCPDiscountType.FIXED,
            value=Decimal("1000"),
            min_purchase_minor=5000,
        )

        # Below minimum - no discount
        assert discount.calculate_discount_minor(4000) == 0

        # At minimum - discount applies
        assert discount.calculate_discount_minor(5000) == 1000


class TestUCPCartMandate:
    """Tests for UCPCartMandate."""

    def test_create_cart_mandate(self):
        """Test creating a cart mandate."""
        items = [
            UCPLineItem(
                item_id="item_1",
                name="Product 1",
                description="Desc",
                quantity=2,
                unit_price_minor=1000,
            ),
        ]

        cart = UCPCartMandate(
            mandate_id="cart_123",
            merchant_id="merchant_1",
            merchant_name="Test Merchant",
            merchant_domain="test.com",
            line_items=items,
            currency=UCPCurrency.USD,
            subtotal_minor=2000,
            taxes_minor=160,
        )

        assert cart.mandate_id == "cart_123"
        assert cart.merchant_name == "Test Merchant"
        assert len(cart.line_items) == 1
        assert cart.total_minor == 2160  # subtotal + taxes

    def test_cart_with_discount(self):
        """Test cart total with discount."""
        discount = UCPDiscount(
            discount_id="disc_1",
            name="10% Off",
            discount_type=UCPDiscountType.PERCENTAGE,
            value=Decimal("10"),
        )

        cart = UCPCartMandate(
            mandate_id="cart_123",
            merchant_id="merchant_1",
            merchant_name="Test Merchant",
            merchant_domain="test.com",
            line_items=[],
            currency=UCPCurrency.USD,
            subtotal_minor=10000,
            taxes_minor=800,
            discounts=[discount],
        )

        # Total = 10000 + 800 - 1000 (10% discount) = 9800
        assert cart.total_discount_minor == 1000
        assert cart.total_minor == 9800

    def test_cart_expiration(self):
        """Test cart mandate expiration check."""
        # Create expired cart
        cart = UCPCartMandate(
            mandate_id="cart_123",
            merchant_id="merchant_1",
            merchant_name="Test",
            merchant_domain="test.com",
            line_items=[],
            currency=UCPCurrency.USD,
            subtotal_minor=1000,
            taxes_minor=0,
            expires_at=int(time.time()) - 100,  # Expired 100 seconds ago
        )

        assert cart.is_expired() is True

        # Create valid cart
        valid_cart = UCPCartMandate(
            mandate_id="cart_456",
            merchant_id="merchant_1",
            merchant_name="Test",
            merchant_domain="test.com",
            line_items=[],
            currency=UCPCurrency.USD,
            subtotal_minor=1000,
            taxes_minor=0,
            expires_at=int(time.time()) + 3600,  # Expires in 1 hour
        )

        assert valid_cart.is_expired() is False


class TestUCPCheckoutMandate:
    """Tests for UCPCheckoutMandate."""

    def test_create_checkout_mandate(self):
        """Test creating a checkout mandate."""
        checkout = UCPCheckoutMandate(
            mandate_id="checkout_123",
            cart_mandate_id="cart_456",
            subject="agent_abc",
            issuer="sardis.sh",
            authorized_amount_minor=5000,
            currency=UCPCurrency.USD,
        )

        assert checkout.mandate_id == "checkout_123"
        assert checkout.cart_mandate_id == "cart_456"
        assert checkout.subject == "agent_abc"
        assert checkout.authorized_amount_minor == 5000


class TestUCPPaymentMandate:
    """Tests for UCPPaymentMandate."""

    def test_create_payment_mandate(self):
        """Test creating a payment mandate."""
        payment = UCPPaymentMandate(
            mandate_id="payment_123",
            checkout_mandate_id="checkout_456",
            subject="agent_abc",
            issuer="sardis.sh",
            chain="base",
            token="USDC",
            amount_minor=5000,
            destination="0x1234567890abcdef1234567890abcdef12345678",
            audit_hash="abc123",
        )

        assert payment.mandate_id == "payment_123"
        assert payment.chain == "base"
        assert payment.token == "USDC"
        assert payment.amount_minor == 5000


class TestUCPBusinessProfile:
    """Tests for UCPBusinessProfile."""

    def test_create_business_profile(self):
        """Test creating a business profile."""
        profile = UCPBusinessProfile(
            profile_id="biz_123",
            business_name="Test Store",
            business_domain="store.test.com",
        )

        assert profile.profile_id == "biz_123"
        assert profile.business_name == "Test Store"

    def test_supports_capability(self):
        """Test capability checking."""
        cap = UCPCapability(
            capability_type=UCPCapabilityType.CHECKOUT_CREATE,
            enabled=True,
        )

        profile = UCPBusinessProfile(
            profile_id="biz_123",
            business_name="Test Store",
            business_domain="store.test.com",
            capabilities=[cap],
        )

        assert profile.supports_capability(UCPCapabilityType.CHECKOUT_CREATE) is True
        assert profile.supports_capability(UCPCapabilityType.PAYMENT_REFUND) is False


class TestUCPOrder:
    """Tests for UCPOrder."""

    def test_create_order(self):
        """Test creating an order."""
        order = UCPOrder(
            order_id="ord_123",
            checkout_session_id="cs_456",
            merchant_id="merchant_1",
            customer_id="customer_1",
            total_minor=5000,
        )

        assert order.order_id == "ord_123"
        assert order.status == UCPOrderStatus.PENDING

    def test_confirm_payment(self):
        """Test confirming payment on an order."""
        order = UCPOrder(
            order_id="ord_123",
            checkout_session_id="cs_456",
            merchant_id="merchant_1",
            customer_id="customer_1",
        )

        order.confirm_payment(
            payment_mandate_id="pay_789",
            chain_tx_hash="0xabc123",
        )

        assert order.status == UCPOrderStatus.CONFIRMED
        assert order.payment_mandate_id == "pay_789"
        assert order.chain_tx_hash == "0xabc123"
        assert order.payment_confirmed_at is not None

    def test_cancel_order(self):
        """Test cancelling an order."""
        order = UCPOrder(
            order_id="ord_123",
            checkout_session_id="cs_456",
            merchant_id="merchant_1",
            customer_id="customer_1",
        )

        order.cancel(reason="Customer request")

        assert order.status == UCPOrderStatus.CANCELLED
        assert order.cancelled_at is not None
        assert order.metadata.get("cancellation_reason") == "Customer request"

    def test_refund_order(self):
        """Test refunding an order."""
        order = UCPOrder(
            order_id="ord_123",
            checkout_session_id="cs_456",
            merchant_id="merchant_1",
            customer_id="customer_1",
            total_minor=10000,
        )

        # Partial refund
        order.refund(3000, reason="Damaged item")

        assert order.status == UCPOrderStatus.PARTIALLY_REFUNDED
        assert order.refunded_amount_minor == 3000

        # Full refund
        order.refund(7000, reason="Rest of order")

        assert order.status == UCPOrderStatus.REFUNDED
        assert order.refunded_amount_minor == 10000


class TestUCPFulfillment:
    """Tests for UCPFulfillment."""

    def test_create_fulfillment(self):
        """Test creating a fulfillment."""
        fulfillment = UCPFulfillment(
            fulfillment_id="ful_123",
            order_id="ord_456",
            carrier="UPS",
            tracking_number="1Z999AA10123456784",
        )

        assert fulfillment.fulfillment_id == "ful_123"
        assert fulfillment.status == UCPFulfillmentStatus.PENDING

    def test_add_fulfillment_events(self):
        """Test adding fulfillment events."""
        fulfillment = UCPFulfillment(
            fulfillment_id="ful_123",
            order_id="ord_456",
        )

        # Ship the order
        event = fulfillment.add_event(
            event_id="evt_1",
            status=UCPFulfillmentStatus.SHIPPED,
            location="Warehouse",
            description="Package shipped",
        )

        assert fulfillment.status == UCPFulfillmentStatus.SHIPPED
        assert fulfillment.shipped_at is not None
        assert len(fulfillment.events) == 1

        # Deliver the order
        fulfillment.add_event(
            event_id="evt_2",
            status=UCPFulfillmentStatus.DELIVERED,
            location="Customer address",
        )

        assert fulfillment.status == UCPFulfillmentStatus.DELIVERED
        assert fulfillment.delivered_at is not None
        assert len(fulfillment.events) == 2
