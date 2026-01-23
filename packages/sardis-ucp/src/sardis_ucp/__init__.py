"""Universal Commerce Protocol (UCP) integration for Sardis.

UCP enables structured commerce between agents and merchants, providing:
- Checkout sessions with cart management
- Order lifecycle management
- Fulfillment tracking
- Payment mandate translation (AP2 <-> UCP)

This package bridges UCP's commerce primitives with Sardis's payment infrastructure.
"""

from .models.mandates import (
    UCPCurrency,
    UCPDiscountType,
    UCPCartMandate,
    UCPCheckoutMandate,
    UCPPaymentMandate,
    UCPLineItem,
    UCPDiscount,
)
from .models.profiles import (
    UCPCapabilityType,
    UCPBusinessProfile,
    UCPPlatformProfile,
    UCPCapability,
    UCPPaymentCapability,
    UCPEndpoints,
)
from .models.orders import (
    UCPOrder,
    UCPOrderStatus,
    UCPFulfillment,
    UCPFulfillmentStatus,
    UCPFulfillmentEvent,
    UCPShippingAddress,
)
from .capabilities.checkout import (
    UCPCheckoutCapability,
    CheckoutSession,
    CheckoutSessionStatus,
    CheckoutResult,
    CheckoutError,
    CheckoutSessionExpiredError,
    CheckoutSessionNotFoundError,
    InvalidCheckoutOperationError,
)

__all__ = [
    # Mandates
    "UCPCurrency",
    "UCPDiscountType",
    "UCPCartMandate",
    "UCPCheckoutMandate",
    "UCPPaymentMandate",
    "UCPLineItem",
    "UCPDiscount",
    # Profiles
    "UCPCapabilityType",
    "UCPBusinessProfile",
    "UCPPlatformProfile",
    "UCPCapability",
    "UCPPaymentCapability",
    "UCPEndpoints",
    # Orders
    "UCPOrder",
    "UCPOrderStatus",
    "UCPFulfillment",
    "UCPFulfillmentStatus",
    "UCPFulfillmentEvent",
    "UCPShippingAddress",
    # Checkout
    "UCPCheckoutCapability",
    "CheckoutSession",
    "CheckoutSessionStatus",
    "CheckoutResult",
    "CheckoutError",
    "CheckoutSessionExpiredError",
    "CheckoutSessionNotFoundError",
    "InvalidCheckoutOperationError",
]
