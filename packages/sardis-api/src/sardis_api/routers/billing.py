"""Billing API endpoints for subscription and usage management.

Provides plan management, usage tracking, and Stripe webhook handling.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_api.services.stripe_billing import PLANS, StripeBillingService
from sardis_api.services.usage_metering import UsageMeteringService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/billing",
    tags=["billing"],
    dependencies=[Depends(require_principal)],
)

# Webhook router — no auth (Stripe signs requests)
webhook_router = APIRouter(prefix="/api/v2/billing", tags=["billing"])


def _get_billing_service() -> StripeBillingService:
    return StripeBillingService()


def _get_metering_service() -> UsageMeteringService:
    return UsageMeteringService()


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class UsageResponse(BaseModel):
    org_id: str
    period_start: str
    period_end: str
    transactions: int = 0
    cards_issued: int = 0
    policy_checks: int = 0
    api_calls: int = 0


class PlanResponse(BaseModel):
    plan: str
    display_name: str
    monthly_price_cents: int
    tx_fee_bps: int
    tx_limit: int
    agent_limit: int
    card_limit: int
    status: str
    stripe_customer_id: str | None = None


class SubscribeRequest(BaseModel):
    plan: str = Field(description="Plan name: free, growth, scale, enterprise")
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None


class SubscribeResponse(BaseModel):
    org_id: str
    plan: str
    status: str
    message: str


class InvoiceItem(BaseModel):
    id: str
    amount_due: int
    currency: str
    status: str
    created: int
    invoice_pdf: str | None = None


class InvoicesResponse(BaseModel):
    org_id: str
    invoices: list[InvoiceItem]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    principal: Principal = Depends(require_principal),
    metering: UsageMeteringService = Depends(_get_metering_service),
):
    """Get current billing period usage for the authenticated organization."""
    usage = await metering.get_usage(principal.organization_id)
    return UsageResponse(
        org_id=usage.org_id,
        period_start=usage.period_start,
        period_end=usage.period_end,
        transactions=usage.transactions,
        cards_issued=usage.cards_issued,
        policy_checks=usage.policy_checks,
        api_calls=usage.api_calls,
    )


@router.get("/plan", response_model=PlanResponse)
async def get_plan(
    principal: Principal = Depends(require_principal),
    billing: StripeBillingService = Depends(_get_billing_service),
):
    """Get current subscription plan and limits."""
    sub = await billing.get_or_create_subscription(principal.organization_id)
    plan_info = PLANS.get(sub.plan, PLANS["free"])

    return PlanResponse(
        plan=plan_info.name,
        display_name=plan_info.display_name,
        monthly_price_cents=plan_info.monthly_price_cents,
        tx_fee_bps=plan_info.tx_fee_bps,
        tx_limit=plan_info.tx_limit,
        agent_limit=plan_info.agent_limit,
        card_limit=plan_info.card_limit,
        status=sub.status,
        stripe_customer_id=sub.stripe_customer_id,
    )


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    body: SubscribeRequest,
    principal: Principal = Depends(require_principal),
    billing: StripeBillingService = Depends(_get_billing_service),
):
    """Create or change subscription plan."""
    if body.plan not in PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan. Must be one of: {list(PLANS.keys())}",
        )

    sub = await billing.create_subscription(
        org_id=principal.organization_id,
        plan=body.plan,
        stripe_customer_id=body.stripe_customer_id,
        stripe_subscription_id=body.stripe_subscription_id,
    )

    return SubscribeResponse(
        org_id=sub.org_id,
        plan=sub.plan,
        status=sub.status,
        message=f"Subscribed to {PLANS[body.plan].display_name} plan",
    )


@router.get("/invoices", response_model=InvoicesResponse)
async def get_invoices(
    principal: Principal = Depends(require_principal),
    billing: StripeBillingService = Depends(_get_billing_service),
):
    """Get invoice history for the authenticated organization."""
    invoices = await billing.get_invoices(principal.organization_id)
    return InvoicesResponse(
        org_id=principal.organization_id,
        invoices=[InvoiceItem(**inv) for inv in invoices],
    )


@webhook_router.post("/webhook")
async def stripe_billing_webhook(
    request: Request,
    billing: StripeBillingService = Depends(_get_billing_service),
):
    """Handle Stripe Billing webhook events."""
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    if not billing.verify_webhook_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    import json
    event = json.loads(body)
    event_type = event.get("type", "")
    data = event.get("data", {})

    await billing.handle_webhook_event(event_type, data)

    return Response(status_code=status.HTTP_200_OK)
