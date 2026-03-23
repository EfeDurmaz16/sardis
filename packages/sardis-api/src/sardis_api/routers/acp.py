"""Agentic Commerce Protocol (ACP) checkout endpoints.

Implements Stripe's ACP specification so Sardis can act as a seller
that AI agents can check out from.  An agent discovers our product
catalogue, creates a checkout session, selects fulfillment, and
completes payment using a Shared Payment Token (SPT).

Reference: https://docs.stripe.com/agentic-commerce/protocol
"""
from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(
    prefix="/checkouts",
    dependencies=[Depends(require_principal)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory store  (swap for DB-backed repository in production)
# ---------------------------------------------------------------------------

_checkouts: dict[str, dict[str, Any]] = {}


def _gen_id() -> str:
    return f"checkout_{secrets.token_hex(12)}"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CheckoutStatus(str, Enum):
    not_ready_for_payment = "not_ready_for_payment"
    ready_for_payment = "ready_for_payment"
    in_progress = "in_progress"
    completed = "completed"
    canceled = "canceled"


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class Buyer(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone_number: str | None = None


class Address(BaseModel):
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class LineItemRequest(BaseModel):
    id: str = Field(..., description="Product / SKU identifier")
    quantity: int = Field(..., ge=1)


class LineItem(BaseModel):
    id: str
    description: str = ""
    quantity: int = 1
    unit_amount: Decimal = Decimal("0")
    currency: str = "usd"
    total: Decimal = Decimal("0")


class FulfillmentOption(BaseModel):
    id: str
    label: str
    amount: Decimal = Decimal("0")
    currency: str = "usd"
    estimated_delivery: str | None = None


class Totals(BaseModel):
    subtotal: Decimal = Decimal("0")
    shipping: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    currency: str = "usd"


class PaymentProvider(BaseModel):
    provider: str = "stripe"
    supported_payment_methods: list[str] = Field(
        default_factory=lambda: ["card"],
    )


class CheckoutLink(BaseModel):
    rel: str
    href: str


class Message(BaseModel):
    role: str = "seller"
    content: str = ""


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreateCheckoutRequest(BaseModel):
    items: list[LineItemRequest] = Field(..., min_length=1)
    buyer: Buyer | None = None
    fulfillment_address: Address | None = None


class UpdateCheckoutRequest(BaseModel):
    items: list[LineItemRequest] | None = None
    buyer: Buyer | None = None
    fulfillment_address: Address | None = None
    selected_fulfillment_option: str | None = None


class PaymentData(BaseModel):
    token: str = Field(..., description="Shared Payment Token (spt_xxx)")
    provider: str = Field(default="stripe")
    billing_address: Address | None = None


class CompleteCheckoutRequest(BaseModel):
    payment_data: PaymentData


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------

class CheckoutResponse(BaseModel):
    id: str
    buyer: Buyer | None = None
    payment_provider: PaymentProvider = Field(default_factory=PaymentProvider)
    status: CheckoutStatus
    currency: str = "usd"
    line_items: list[LineItem] = Field(default_factory=list)
    fulfillment_options: list[FulfillmentOption] = Field(default_factory=list)
    totals: Totals = Field(default_factory=Totals)
    messages: list[Message] = Field(default_factory=list)
    links: list[CheckoutLink] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CATALOG: dict[str, dict[str, Any]] = {
    "sardis_pro_monthly": {
        "description": "Sardis Pro — Monthly",
        "unit_amount": Decimal("99.00"),
        "currency": "usd",
    },
    "sardis_enterprise_monthly": {
        "description": "Sardis Enterprise — Monthly",
        "unit_amount": Decimal("499.00"),
        "currency": "usd",
    },
    "sardis_api_credits_1000": {
        "description": "1 000 API Credits",
        "unit_amount": Decimal("10.00"),
        "currency": "usd",
    },
}

_FULFILLMENT_OPTIONS: list[FulfillmentOption] = [
    FulfillmentOption(
        id="instant",
        label="Instant digital delivery",
        amount=Decimal("0"),
        estimated_delivery="Immediate",
    ),
]


def _resolve_line_items(items: list[LineItemRequest]) -> list[LineItem]:
    resolved: list[LineItem] = []
    for item in items:
        info = _CATALOG.get(item.id)
        if info is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown product id: {item.id}",
            )
        unit = info["unit_amount"]
        resolved.append(
            LineItem(
                id=item.id,
                description=info["description"],
                quantity=item.quantity,
                unit_amount=unit,
                currency=info["currency"],
                total=unit * item.quantity,
            )
        )
    return resolved


def _compute_totals(
    line_items: list[LineItem],
    shipping: Decimal = Decimal("0"),
) -> Totals:
    subtotal = sum((li.total for li in line_items), Decimal("0"))
    return Totals(
        subtotal=subtotal,
        shipping=shipping,
        tax=Decimal("0"),
        total=subtotal + shipping,
        currency=line_items[0].currency if line_items else "usd",
    )


def _build_links(checkout_id: str) -> list[CheckoutLink]:
    base = f"/api/v2/checkouts/{checkout_id}"
    return [
        CheckoutLink(rel="self", href=base),
        CheckoutLink(rel="complete", href=f"{base}/complete"),
        CheckoutLink(rel="cancel", href=f"{base}/cancel"),
    ]


def _determine_status(data: dict[str, Any]) -> CheckoutStatus:
    """Determine readiness: we need at least one line item to be payable."""
    if data.get("status") in (
        CheckoutStatus.completed,
        CheckoutStatus.canceled,
    ):
        return data["status"]
    if data.get("line_items"):
        return CheckoutStatus.ready_for_payment
    return CheckoutStatus.not_ready_for_payment


def _to_response(data: dict[str, Any]) -> CheckoutResponse:
    return CheckoutResponse(
        id=data["id"],
        buyer=data.get("buyer"),
        payment_provider=PaymentProvider(),
        status=data["status"],
        currency=data.get("currency", "usd"),
        line_items=data.get("line_items", []),
        fulfillment_options=data.get("fulfillment_options", _FULFILLMENT_OPTIONS),
        totals=data.get("totals", Totals()),
        messages=data.get("messages", []),
        links=_build_links(data["id"]),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


def _get_or_404(checkout_id: str) -> dict[str, Any]:
    data = _checkouts.get(checkout_id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkout {checkout_id} not found",
        )
    return data


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an ACP checkout session",
)
async def create_checkout(
    body: CreateCheckoutRequest,
    principal: Principal = Depends(require_principal),
) -> CheckoutResponse:
    """Create a new checkout session.

    The agent supplies line-item IDs (from the seller catalogue) and
    optionally buyer / fulfillment information.  The response includes
    the resolved line items, totals, available fulfillment options,
    and HATEOAS links for the next steps.
    """
    now = datetime.now(UTC).isoformat()
    checkout_id = _gen_id()

    line_items = _resolve_line_items(body.items)
    totals = _compute_totals(line_items)

    data: dict[str, Any] = {
        "id": checkout_id,
        "owner_id": principal.account_id,
        "buyer": body.buyer,
        "line_items": line_items,
        "fulfillment_address": body.fulfillment_address,
        "fulfillment_options": list(_FULFILLMENT_OPTIONS),
        "totals": totals,
        "currency": "usd",
        "messages": [],
        "status": CheckoutStatus.not_ready_for_payment,
        "created_at": now,
        "updated_at": now,
    }
    data["status"] = _determine_status(data)

    _checkouts[checkout_id] = data
    logger.info("ACP checkout created: %s by %s", checkout_id, principal.account_id)
    return _to_response(data)


@router.get(
    "/{checkout_id}",
    response_model=CheckoutResponse,
    summary="Retrieve checkout state",
)
async def get_checkout(
    checkout_id: str,
    principal: Principal = Depends(require_principal),
) -> CheckoutResponse:
    """Return the current state of a checkout session."""
    data = _get_or_404(checkout_id)
    return _to_response(data)


@router.put(
    "/{checkout_id}",
    response_model=CheckoutResponse,
    summary="Update checkout session",
)
async def update_checkout(
    checkout_id: str,
    body: UpdateCheckoutRequest,
    principal: Principal = Depends(require_principal),
) -> CheckoutResponse:
    """Update an existing checkout session.

    The agent can change line items, buyer details, fulfillment address,
    or select a fulfillment option.  The totals are recalculated
    automatically.
    """
    data = _get_or_404(checkout_id)

    if data["status"] in (CheckoutStatus.completed, CheckoutStatus.canceled):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Checkout is already {data['status'].value}; cannot update",
        )

    now = datetime.now(UTC).isoformat()

    if body.items is not None:
        line_items = _resolve_line_items(body.items)
        data["line_items"] = line_items
        data["totals"] = _compute_totals(line_items)

    if body.buyer is not None:
        data["buyer"] = body.buyer

    if body.fulfillment_address is not None:
        data["fulfillment_address"] = body.fulfillment_address

    if body.selected_fulfillment_option is not None:
        valid_ids = {fo.id for fo in _FULFILLMENT_OPTIONS}
        if body.selected_fulfillment_option not in valid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown fulfillment option: {body.selected_fulfillment_option}",
            )
        data["selected_fulfillment_option"] = body.selected_fulfillment_option

    data["updated_at"] = now
    data["status"] = _determine_status(data)

    logger.info("ACP checkout updated: %s", checkout_id)
    return _to_response(data)


@router.post(
    "/{checkout_id}/complete",
    response_model=CheckoutResponse,
    summary="Complete checkout with SPT payment",
)
async def complete_checkout(
    checkout_id: str,
    body: CompleteCheckoutRequest,
    principal: Principal = Depends(require_principal),
) -> CheckoutResponse:
    """Complete a checkout session using a Shared Payment Token.

    The agent provides an SPT (``spt_xxx``) obtained from its buyer
    principal.  Sardis validates the token, creates a PaymentIntent
    on the payment provider, and transitions the checkout to
    ``completed``.
    """
    data = _get_or_404(checkout_id)

    if data["status"] == CheckoutStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checkout is already completed",
        )
    if data["status"] == CheckoutStatus.canceled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checkout has been canceled",
        )
    if data["status"] == CheckoutStatus.not_ready_for_payment:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Checkout is not ready for payment — add items first",
        )

    token = body.payment_data.token
    if not token.startswith("spt_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment_data.token must be a valid SPT (spt_xxx)",
        )

    # --- SPT validation would happen here in production ---
    # In a live deployment this calls the Sardis SPT service / Stripe API
    # to validate the token, check usage_limits, and create the
    # PaymentIntent.  For now we accept any well-formed token.
    logger.info(
        "ACP checkout %s: processing SPT %s (provider=%s)",
        checkout_id,
        token,
        body.payment_data.provider,
    )

    now = datetime.now(UTC).isoformat()
    data["status"] = CheckoutStatus.completed
    data["updated_at"] = now
    data["payment_token"] = token
    data["payment_provider_used"] = body.payment_data.provider
    data["messages"].append(
        Message(role="seller", content="Payment received. Order confirmed."),
    )

    logger.info("ACP checkout completed: %s with SPT %s", checkout_id, token)
    return _to_response(data)


@router.post(
    "/{checkout_id}/cancel",
    response_model=CheckoutResponse,
    summary="Cancel checkout session",
)
async def cancel_checkout(
    checkout_id: str,
    principal: Principal = Depends(require_principal),
) -> CheckoutResponse:
    """Cancel a checkout session.

    Terminal checkouts (completed / already canceled) cannot be canceled
    again.
    """
    data = _get_or_404(checkout_id)

    if data["status"] == CheckoutStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot cancel a completed checkout",
        )
    if data["status"] == CheckoutStatus.canceled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checkout is already canceled",
        )

    now = datetime.now(UTC).isoformat()
    data["status"] = CheckoutStatus.canceled
    data["updated_at"] = now
    data["messages"].append(
        Message(role="seller", content="Checkout canceled by agent."),
    )

    logger.info("ACP checkout canceled: %s", checkout_id)
    return _to_response(data)
