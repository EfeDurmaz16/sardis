"""Pydantic models for the Agentic Commerce Protocol (ACP).

EXPERIMENTAL / PARTIAL — these shapes diverge from the current ACP spec
(targets stale 2026-01-30; current is 2026-04-17) and are NOT a conformance
claim. See docs/productization/research/PROTOCOL_STRATEGY.md (ACP).

Sketches the data shapes toward the ACP OpenAPI specification. Covers checkout
sessions, delegate payment, webhook events, and SPT integration.

Reference: https://docs.stripe.com/agentic-commerce/protocol
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# ACP version
# ---------------------------------------------------------------------------

ACP_API_VERSION = "2026-01-30"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ACPCheckoutStatus(str, Enum):
    open = "open"
    completed = "completed"
    canceled = "canceled"
    expired = "expired"


class ACPPaymentStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"


class ACPFulfillmentType(str, Enum):
    shipping = "shipping"
    pickup = "pickup"
    digital = "digital"


class ACPOrderStatus(str, Enum):
    created = "created"
    confirmed = "confirmed"
    shipped = "shipped"
    fulfilled = "fulfilled"
    canceled = "canceled"


class ACPWebhookEventType(str, Enum):
    order_create = "order_create"
    order_update = "order_update"


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class ACPAddress(BaseModel):
    name: str | None = None
    line_one: str | None = None
    line_two: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None


class ACPBuyerInformation(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: ACPAddress | None = None


class ACPLineItemRequest(BaseModel):
    """Line item in a create/update request."""
    id: str = Field(..., description="Product / SKU identifier")
    quantity: int = Field(..., ge=1)
    price: Decimal | None = Field(None, description="Optional price override")
    name: str | None = Field(None, description="Optional display name")


class ACPLineItem(BaseModel):
    """Resolved line item in a checkout response."""
    id: str
    name: str = ""
    description: str = ""
    image_url: str | None = None
    quantity: int = 1
    unit_price: Decimal = Decimal("0")
    currency: str = "usd"
    total: Decimal = Decimal("0")


class ACPTotals(BaseModel):
    subtotal: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    shipping: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    currency: str = "usd"


class ACPPaymentInfo(BaseModel):
    status: ACPPaymentStatus = ACPPaymentStatus.pending
    methods_supported: list[str] = Field(default_factory=lambda: ["card", "crypto"])
    payment_intent_id: str | None = None
    error: str | None = None


class ACPFulfillment(BaseModel):
    type: ACPFulfillmentType = ACPFulfillmentType.digital
    address: ACPAddress | None = None
    estimated_delivery: str | None = None
    tracking_number: str | None = None
    tracking_url: str | None = None


class ACPAffiliateAttribution(BaseModel):
    touchpoint: str | None = None


# ---------------------------------------------------------------------------
# Checkout session requests
# ---------------------------------------------------------------------------

class ACPCreateCheckoutRequest(BaseModel):
    """Create a new ACP checkout session."""
    items: list[ACPLineItemRequest] = Field(..., min_length=1)
    buyer_information: ACPBuyerInformation | None = None
    fulfillment: ACPFulfillment | None = None
    affiliate_attribution: ACPAffiliateAttribution | None = None
    webhook_url: str | None = Field(
        None,
        description="URL where order lifecycle webhooks will be sent",
    )


class ACPUpdateCheckoutRequest(BaseModel):
    """Update an existing ACP checkout session."""
    items: list[ACPLineItemRequest] | None = None
    buyer_information: ACPBuyerInformation | None = None
    fulfillment: ACPFulfillment | None = None


class ACPCryptoPayment(BaseModel):
    """Crypto payment details for completing checkout via on-chain transfer."""
    tx_hash: str = Field(..., description="On-chain transaction hash")
    chain: str = Field(..., description="Chain name (e.g., base, polygon)")
    token: str = Field(default="USDC", description="Token symbol")


class ACPCompleteCheckoutRequest(BaseModel):
    """Complete an ACP checkout session with payment."""
    payment_method: Literal["delegate_payment", "crypto", "spt"] = Field(
        ...,
        description="Payment method: delegate_payment (card via ACP), crypto (on-chain), or spt (Stripe SPT)",
    )
    delegate_payment_token: str | None = Field(
        None,
        description="Delegate payment token (vt_...) for card payments",
    )
    shared_payment_granted_token: str | None = Field(
        None,
        description="Stripe Shared Payment Token (spt_...) for SPT payments",
    )
    crypto_payment: ACPCryptoPayment | None = Field(
        None,
        description="Crypto payment details for on-chain payments",
    )


# ---------------------------------------------------------------------------
# Checkout session response
# ---------------------------------------------------------------------------

class ACPCheckoutSessionResponse(BaseModel):
    """Full ACP checkout session state returned by all endpoints."""
    id: str = Field(..., description="Checkout session ID (csn_...)")
    status: ACPCheckoutStatus
    items: list[ACPLineItem] = Field(default_factory=list)
    totals: ACPTotals = Field(default_factory=ACPTotals)
    payment: ACPPaymentInfo = Field(default_factory=ACPPaymentInfo)
    fulfillment: ACPFulfillment = Field(default_factory=ACPFulfillment)
    buyer_information: ACPBuyerInformation | None = None
    affiliate_attribution: ACPAffiliateAttribution | None = None
    webhook_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    api_version: str = ACP_API_VERSION


# ---------------------------------------------------------------------------
# Delegate Payment models
# ---------------------------------------------------------------------------

class ACPDelegatePaymentCard(BaseModel):
    """Card details for delegate payment."""
    type: Literal["card"] = "card"
    number: str = Field(..., description="Card number")
    exp_month: int = Field(..., ge=1, le=12)
    exp_year: int = Field(..., ge=2025)
    cvc: str = Field(..., min_length=3, max_length=4)
    name: str | None = None


class ACPDelegateAllowance(BaseModel):
    """Spending allowance constraints for delegate payment."""
    reason: Literal["one_time"] = "one_time"
    max_amount: int = Field(..., gt=0, description="Max amount in smallest currency unit (cents)")
    currency: str = Field(default="usd")
    checkout_session_id: str = Field(..., description="ACP checkout session this allowance is for")
    merchant_id: str | None = None
    expires_at: str | None = Field(None, description="ISO 8601 expiration timestamp")


class ACPRiskSignal(BaseModel):
    """Risk signal from the agent's risk assessment."""
    type: str = Field(..., description="Signal type (e.g., device_fingerprint, ip_reputation)")
    score: float = Field(..., ge=0, le=1)
    action: str = Field(default="allow", description="Recommended action")


class ACPDelegatePaymentRequest(BaseModel):
    """Receive card credentials from an agent, tokenize via Stripe."""
    payment_method: ACPDelegatePaymentCard
    allowance: ACPDelegateAllowance
    billing_address: ACPAddress | None = None
    risk_signals: list[ACPRiskSignal] = Field(default_factory=list)


class ACPDelegatePaymentResponse(BaseModel):
    """Response after tokenizing delegate payment credentials."""
    id: str = Field(..., description="Delegate payment token (vt_...)")
    created: str
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Webhook event models
# ---------------------------------------------------------------------------

class ACPRefund(BaseModel):
    id: str
    amount: Decimal
    currency: str = "usd"
    status: str = "pending"
    reason: str | None = None


class ACPOrderData(BaseModel):
    """Order data sent in webhook events."""
    type: Literal["order"] = "order"
    checkout_session_id: str
    permalink_url: str | None = None
    status: ACPOrderStatus
    refunds: list[ACPRefund] = Field(default_factory=list)


class ACPWebhookEvent(BaseModel):
    """Webhook event sent to the agent's webhook URL."""
    type: ACPWebhookEventType
    data: ACPOrderData
    timestamp: str | None = None
    api_version: str = ACP_API_VERSION
