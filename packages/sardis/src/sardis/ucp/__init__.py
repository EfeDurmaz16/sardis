"""Universal Commerce Protocol (UCP) integration for Sardis.

UCP enables structured commerce between agents and merchants, providing:
- Checkout sessions with cart management
- Order lifecycle management
- Fulfillment tracking
- Payment mandate translation (AP2 <-> UCP)

This package bridges UCP's commerce primitives with Sardis's payment infrastructure.
"""

from .capabilities.checkout import (
    CheckoutError,
    CheckoutResult,
    CheckoutSession,
    CheckoutSessionExpiredError,
    CheckoutSessionNotFoundError,
    CheckoutSessionStatus,
    InvalidCheckoutOperationError,
    UCPCheckoutCapability,
)
from .models.mandates import (
    UCPCartMandate,
    UCPCheckoutMandate,
    UCPCurrency,
    UCPDiscount,
    UCPDiscountType,
    UCPLineItem,
    UCPPaymentMandate,
)
from .models.orders import (
    UCPFulfillment,
    UCPFulfillmentEvent,
    UCPFulfillmentStatus,
    UCPOrder,
    UCPOrderStatus,
    UCPShippingAddress,
)
from .models.profiles import (
    UCPBusinessProfile,
    UCPCapability,
    UCPCapabilityType,
    UCPConformanceProfile,
    UCPEndpoints,
    UCPPaymentCapability,
    UCPPlatformProfile,
    UCPSecurityLockMode,
)

# UCP Protocol Version
UCP_PROTOCOL_VERSION = "1.0"
UCP_SUPPORTED_VERSIONS = ["1.0"]


def validate_ucp_version(version: str) -> tuple[bool, str | None]:
    """Validate a UCP protocol version string."""
    if not version:
        return True, None
    if version in UCP_SUPPORTED_VERSIONS:
        return True, None
    major = version.split(".")[0] if "." in version else version
    supported_majors = {v.split(".")[0] for v in UCP_SUPPORTED_VERSIONS}
    if major not in supported_majors:
        return False, f"ucp_version_unsupported:{version}"
    return True, None

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
    "UCPSecurityLockMode",
    "UCPConformanceProfile",
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
    # Version
    "UCP_PROTOCOL_VERSION",
    "UCP_SUPPORTED_VERSIONS",
    "validate_ucp_version",
]
