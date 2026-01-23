"""UCP mandate models for Universal Commerce Protocol.

UCP mandates provide a structured commerce layer that maps to AP2 mandates:
- UCPCartMandate -> AP2 CartMandate (merchant's offer)
- UCPCheckoutMandate -> AP2 IntentMandate (user authorization)
- UCPPaymentMandate -> AP2 PaymentMandate (payment instruction)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


class UCPCurrency(str, Enum):
    """Supported currencies in UCP."""

    USD = "USD"
    EUR = "EUR"
    USDC = "USDC"
    USDT = "USDT"
    PYUSD = "PYUSD"
    EURC = "EURC"


class UCPDiscountType(str, Enum):
    """Type of discount applied."""

    PERCENTAGE = "percentage"
    FIXED = "fixed"
    COUPON = "coupon"


@dataclass(slots=True)
class UCPLineItem:
    """A single item in a UCP cart.

    Represents a product or service being purchased with all relevant metadata.
    """

    item_id: str
    name: str
    description: str
    quantity: int
    unit_price_minor: int  # Price in minor units (cents)
    currency: UCPCurrency = UCPCurrency.USD

    # Optional fields
    sku: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Tax handling
    taxable: bool = True
    tax_rate: Optional[Decimal] = None  # As decimal (e.g., 0.08 for 8%)

    @property
    def total_minor(self) -> int:
        """Calculate line item total in minor units."""
        return self.unit_price_minor * self.quantity

    @property
    def tax_amount_minor(self) -> int:
        """Calculate tax amount in minor units."""
        if not self.taxable or self.tax_rate is None:
            return 0
        return int(self.total_minor * self.tax_rate)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "item_id": self.item_id,
            "name": self.name,
            "description": self.description,
            "quantity": self.quantity,
            "unit_price_minor": self.unit_price_minor,
            "currency": self.currency.value,
            "sku": self.sku,
            "category": self.category,
            "image_url": self.image_url,
            "metadata": self.metadata,
            "taxable": self.taxable,
            "tax_rate": str(self.tax_rate) if self.tax_rate else None,
        }


@dataclass(slots=True)
class UCPDiscount:
    """A discount applied to a UCP cart."""

    discount_id: str
    name: str
    discount_type: UCPDiscountType
    value: Decimal  # Percentage (0-100) or fixed amount in minor units
    code: Optional[str] = None  # Coupon code if applicable
    applied_to: Optional[List[str]] = None  # Line item IDs (None = entire cart)
    min_purchase_minor: int = 0  # Minimum purchase amount for discount

    def calculate_discount_minor(self, subtotal_minor: int) -> int:
        """Calculate the discount amount in minor units."""
        if subtotal_minor < self.min_purchase_minor:
            return 0

        if self.discount_type == UCPDiscountType.PERCENTAGE:
            return int(subtotal_minor * (self.value / Decimal("100")))
        elif self.discount_type == UCPDiscountType.FIXED:
            return min(int(self.value), subtotal_minor)
        elif self.discount_type == UCPDiscountType.COUPON:
            return min(int(self.value), subtotal_minor)
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "discount_id": self.discount_id,
            "name": self.name,
            "discount_type": self.discount_type.value,
            "value": str(self.value),
            "code": self.code,
            "applied_to": self.applied_to,
            "min_purchase_minor": self.min_purchase_minor,
        }


@dataclass(slots=True)
class UCPCartMandate:
    """UCP Cart Mandate - represents a merchant's offer.

    Maps to AP2 CartMandate. Contains the line items, pricing, and
    merchant information for a shopping cart.
    """

    mandate_id: str
    merchant_id: str
    merchant_name: str
    merchant_domain: str

    # Cart contents
    line_items: List[UCPLineItem]
    currency: UCPCurrency

    # Pricing
    subtotal_minor: int
    taxes_minor: int
    shipping_minor: int = 0
    discounts: List[UCPDiscount] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: int = field(default_factory=lambda: int(time.time()) + 3600)  # 1 hour
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_discount_minor(self) -> int:
        """Calculate total discount amount."""
        return sum(d.calculate_discount_minor(self.subtotal_minor) for d in self.discounts)

    @property
    def total_minor(self) -> int:
        """Calculate the total cart amount in minor units."""
        return self.subtotal_minor + self.taxes_minor + self.shipping_minor - self.total_discount_minor

    def is_expired(self) -> bool:
        """Check if the cart mandate has expired."""
        return self.expires_at <= int(time.time())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mandate_id": self.mandate_id,
            "mandate_type": "cart",
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "merchant_domain": self.merchant_domain,
            "line_items": [item.to_dict() for item in self.line_items],
            "currency": self.currency.value,
            "subtotal_minor": self.subtotal_minor,
            "taxes_minor": self.taxes_minor,
            "shipping_minor": self.shipping_minor,
            "discounts": [d.to_dict() for d in self.discounts],
            "total_minor": self.total_minor,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class UCPCheckoutMandate:
    """UCP Checkout Mandate - user's authorization to proceed with checkout.

    Maps to AP2 IntentMandate. Represents the user/agent's consent to
    proceed with a specific cart at a specific price.
    """

    mandate_id: str
    cart_mandate_id: str  # Reference to the UCPCartMandate
    subject: str  # User/Agent identifier
    issuer: str  # Platform issuing the mandate

    # Authorization details
    authorized_amount_minor: int
    currency: UCPCurrency
    scope: List[str] = field(default_factory=lambda: ["checkout", "payment"])

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: int = field(default_factory=lambda: int(time.time()) + 900)  # 15 minutes
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex)

    # Signature proof (for verification)
    proof_type: Literal["DataIntegrityProof"] = "DataIntegrityProof"
    proof_value: Optional[str] = None
    verification_method: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the checkout mandate has expired."""
        return self.expires_at <= int(time.time())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mandate_id": self.mandate_id,
            "mandate_type": "checkout",
            "cart_mandate_id": self.cart_mandate_id,
            "subject": self.subject,
            "issuer": self.issuer,
            "authorized_amount_minor": self.authorized_amount_minor,
            "currency": self.currency.value,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "proof_type": self.proof_type,
            "proof_value": self.proof_value,
            "verification_method": self.verification_method,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class UCPPaymentMandate:
    """UCP Payment Mandate - instruction to execute payment.

    Maps to AP2 PaymentMandate. Contains the blockchain-specific details
    for executing the payment.
    """

    mandate_id: str
    checkout_mandate_id: str  # Reference to the UCPCheckoutMandate
    subject: str  # Payer identifier
    issuer: str  # Platform issuing the mandate

    # Payment details
    chain: str  # Blockchain network (e.g., "base", "polygon")
    token: str  # Token symbol (e.g., "USDC", "USDT")
    amount_minor: int  # Amount in minor units
    destination: str  # Recipient address

    # Verification
    audit_hash: str  # Hash linking cart -> checkout -> payment
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex)

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: int = field(default_factory=lambda: int(time.time()) + 300)  # 5 minutes

    # Signature proof (for verification)
    proof_type: Literal["DataIntegrityProof"] = "DataIntegrityProof"
    proof_value: Optional[str] = None
    verification_method: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the payment mandate has expired."""
        return self.expires_at <= int(time.time())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mandate_id": self.mandate_id,
            "mandate_type": "payment",
            "checkout_mandate_id": self.checkout_mandate_id,
            "subject": self.subject,
            "issuer": self.issuer,
            "chain": self.chain,
            "token": self.token,
            "amount_minor": self.amount_minor,
            "destination": self.destination,
            "audit_hash": self.audit_hash,
            "nonce": self.nonce,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at,
            "proof_type": self.proof_type,
            "proof_value": self.proof_value,
            "verification_method": self.verification_method,
            "metadata": self.metadata,
        }


__all__ = [
    "UCPCurrency",
    "UCPDiscountType",
    "UCPLineItem",
    "UCPDiscount",
    "UCPCartMandate",
    "UCPCheckoutMandate",
    "UCPPaymentMandate",
]
