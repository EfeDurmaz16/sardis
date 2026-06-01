"""Pydantic models for the Agentic Commerce Protocol (ACP).

EXPERIMENTAL / PARTIAL — these shapes diverge from the current ACP spec
(API-Version value 2026-01-16; current spec dir is 2026-04-17) and are NOT a
conformance claim. See docs/productization/research/PROTOCOL_STRATEGY.md (ACP).

PCI POSTURE — Sardis is the **merchant/seller** here, never a PSP.  The merchant
side of the ACP delegated-payment model NEVER receives a raw PAN/CVV/expiry: the
only credential that crosses into Sardis is an **opaque, tokenized** reference
minted by a regulated issuer/PSP (a Stripe Shared Payment Token, or an
issuer-delegated virtual-card reference whose PAN lives in the issuer's PCI
vault — e.g. Crossmint/Rain ``card_id``).  Raw-card intake was removed; any
inbound raw-PAN body is rejected fail-closed (the field does not exist on the
request models, so it 422s; the PSP ``/delegate_payment`` endpoint is gone).

Covers checkout sessions, the tokenized complete shape, webhook events, and SPT.

Reference: https://docs.stripe.com/agentic-commerce/acp
Roles / PAN boundary: https://developers.openai.com/commerce/guides/key-concepts
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# ACP version
# ---------------------------------------------------------------------------

# API-Version header value (current spec version directory is 2026-04-17; the
# header value the ecosystem sends is 2026-01-16).
ACP_API_VERSION = "2026-01-16"


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


# ---------------------------------------------------------------------------
# Tokenized payment data (ACP delegated-payment merchant shape)
# ---------------------------------------------------------------------------
#
# These mirror the ACP merchant ``complete`` ``payment_data`` shape: a handler
# id plus a tokenized instrument.  NO raw PAN/CVV/expiry exists here — only an
# opaque credential token minted by a real issuer/PSP.

#: Tokenized credential kinds Sardis accepts as a merchant.  ``spt`` is a Stripe
#: Shared Payment Token; ``issuer_card`` is an issuer-delegated virtual-card
#: reference (e.g. Crossmint/Rain ``card_id``) whose PAN lives in the issuer's
#: PCI vault.  No kind here carries cardholder data.
ACPCredentialType = Literal["spt", "issuer_card"]


class ACPPaymentCredential(BaseModel):
    """Tokenized payment credential — opaque to Sardis, never a PAN.

    ``token`` is either an SPT (``spt_...``) or an issuer-delegated card
    reference (the issuer/PSP holds the actual card data).
    """
    model_config = {"extra": "forbid"}

    type: ACPCredentialType
    token: str = Field(
        ...,
        min_length=8,
        description="Opaque credential token (e.g. spt_... or an issuer card_id). Never a PAN.",
    )


class ACPPaymentInstrument(BaseModel):
    """Payment instrument carrying only a tokenized credential."""
    model_config = {"extra": "forbid"}

    type: Literal["card", "wallet_token"] = "card"
    credential: ACPPaymentCredential


class ACPPaymentData(BaseModel):
    """ACP merchant ``complete`` payment data — tokenized only.

    Carries a payment-handler id, a tokenized instrument, and (optionally) a
    billing address.  ``extra='forbid'`` guarantees a raw-card field
    (``number``/``cvc``/``exp_*``) is rejected with 422 — fail-closed: Sardis
    can never accept a PAN on this path.
    """
    model_config = {"extra": "forbid"}

    handler_id: str = Field(..., min_length=1, description="Payment handler / PSP id")
    instrument: ACPPaymentInstrument
    billing_address: ACPAddress | None = None


class ACPCompleteCheckoutRequest(BaseModel):
    """Complete an ACP checkout session with payment.

    Exactly one of two PAN-free branches:

    * ``payment_data`` — tokenized issuer-delegated card / SPT (canonical ACP).
    * ``crypto_payment`` — Sardis-native on-chain stablecoin transfer.

    ``extra='forbid'`` rejects legacy raw-card / delegate-token bodies (422):
    the removed ``payment_method`` / ``delegate_payment_token`` /
    ``shared_payment_granted_token`` fields no longer exist, so any client still
    sending them fails closed.
    """
    model_config = {"extra": "forbid"}

    payment_data: ACPPaymentData | None = Field(
        None,
        description="Tokenized payment data (issuer-delegated card or SPT). Never a PAN.",
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
