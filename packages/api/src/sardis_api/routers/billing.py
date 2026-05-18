"""Billing API endpoints for subscription and usage management.

Supports Stripe and Polar.sh as billing providers via SARDIS_BILLING_PROVIDER env var.
Default: polar (April 2026 — Stripe live access frozen due to crypto onramp).
"""
from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_api.billing.config import PLAN_LIMITS, PLAN_PRICES_CENTS, BillingConfig
from sardis_api.billing.models import BillingAccount, PlanInfo, UsageSnapshot
from sardis_api.billing.polar_adapter import get_billing_provider, get_billing_provider_name
from sardis_api.services.stripe_billing import PLANS, StripeBillingService
from sardis_api.services.usage_metering import UsageMeteringService

logger = logging.getLogger(__name__)

# Module-level config instance
_billing_config = BillingConfig()

# Plan display names and descriptions for inline Stripe price_data fallback
PLAN_LABELS = {
    "dev": "Dev",
    "starter": "Starter",
    "growth": "Growth",
    "enterprise": "Enterprise",
}
PLAN_DESCRIPTIONS = {
    "dev": "Testnet only, 100 tx/mo, 2 agents, no SLA",
    "starter": "Production, unlimited tx, mainnet, 25 agents, SLA",
    "growth": "KYB, PEP screening, advanced audit, FX, 100 agents",
    "enterprise": "White-glove, dedicated support, unlimited",
}

router = APIRouter(
    prefix="/api/v2/billing",
    tags=["billing"],
    dependencies=[Depends(require_principal)],
)

# Webhook router — no auth (Stripe signs requests)
webhook_router = APIRouter(prefix="/api/v2/billing", tags=["billing"])


def _get_billing_service():
    """Return the active billing service (Stripe or Polar based on env var)."""
    return get_billing_provider()


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
    plan: str = Field(description="Plan name: dev, starter, growth, enterprise")
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


class PlansResponse(BaseModel):
    plans: list[PlanInfo]


class BillingAccountResponse(BaseModel):
    account: BillingAccount
    usage: UsageSnapshot


class BillingProviderResponse(BaseModel):
    provider: str
    portal_label: str


class CheckoutRequest(BaseModel):
    plan: str = Field(description="Plan to subscribe to: dev, starter, or growth")


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


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
    plan_info = PLANS.get(sub.plan, PLANS["dev"])

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

    event = json.loads(body)
    event_type = event.get("type", "")
    data = event.get("data", {})

    await billing.handle_webhook_event(event_type, data)

    return Response(status_code=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# New endpoints: plans, account, checkout, portal
# ---------------------------------------------------------------------------

_PAID_PLANS = {"dev", "starter", "growth"}


@webhook_router.get("/provider", response_model=BillingProviderResponse)
async def get_billing_provider_info():
    """Return the active billing provider. No auth required."""
    name = get_billing_provider_name()
    portal_labels = {"polar": "Manage on Polar", "stripe": "Manage on Stripe"}
    return BillingProviderResponse(
        provider=name,
        portal_label=portal_labels.get(name, "Manage Billing"),
    )


@webhook_router.get("/plans", response_model=PlansResponse)
async def list_plans():
    """Return all available plans with pricing and limits. No auth required."""
    plans = []
    for plan_name in ("dev", "starter", "growth", "enterprise"):
        limits = PLAN_LIMITS[plan_name]
        plans.append(
            PlanInfo(
                plan=plan_name,
                price_monthly_cents=PLAN_PRICES_CENTS[plan_name],
                api_calls_per_month=limits["api_calls_per_month"],
                agents=limits["agents"],
                tx_fee_bps=limits["tx_fee_bps"],
                monthly_tx_volume_cents=limits["monthly_tx_volume_cents"],
            )
        )
    return PlansResponse(plans=plans)


@router.get("/account", response_model=BillingAccountResponse)
async def get_account(
    principal: Principal = Depends(require_principal),
    billing: StripeBillingService = Depends(_get_billing_service),
):
    """Return billing account for the authenticated org (defaults to free plan)."""
    sub = await billing.get_or_create_subscription(principal.organization_id)
    plan_name = sub.plan or "dev"
    limits = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["dev"])

    account = BillingAccount(
        id=f"ba_{principal.organization_id}",
        org_id=principal.organization_id,
        plan=plan_name,
        status=sub.status,
        stripe_customer_id=sub.stripe_customer_id,
        stripe_subscription_id=sub.stripe_subscription_id,
    )
    usage = UsageSnapshot(
        api_calls_used=account.api_calls_this_period,
        api_calls_limit=limits["api_calls_per_month"],
        tx_volume_cents=account.tx_volume_this_period_cents,
        tx_volume_limit_cents=limits["monthly_tx_volume_cents"],
        agents_used=0,
        agents_limit=limits["agents"],
    )
    return BillingAccountResponse(account=account, usage=usage)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    principal: Principal = Depends(require_principal),
):
    """Create a checkout session for a paid plan subscription (Stripe or Polar)."""
    if not _billing_config.billing_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not enabled",
        )

    if body.plan not in _PAID_PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan must be one of: {sorted(_PAID_PLANS)}",
        )

    provider = get_billing_provider_name()
    dashboard_billing_url = os.getenv(
        "SARDIS_DASHBOARD_BILLING_URL", "https://app.sardis.sh/billing"
    )

    # --- Polar checkout path ---
    if provider == "polar":
        from sardis_api.billing.polar_adapter import PolarBillingAdapter
        polar = PolarBillingAdapter()
        try:
            result = await polar.create_checkout(
                org_id=principal.organization_id,
                plan=body.plan,
                success_url=f"{dashboard_billing_url}?success=1",
                cancel_url=f"{dashboard_billing_url}?canceled=1",
            )
            from sardis_api.analytics.posthog_tracker import PLAN_UPGRADED, track_event
            track_event(principal.user_id, PLAN_UPGRADED, {"plan": body.plan, "provider": "polar"})
            return CheckoutResponse(checkout_url=result.checkout_url)
        except Exception as exc:
            logger.error("Polar checkout failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Checkout session creation failed",
            ) from exc

    # --- Stripe checkout path ---
    try:
        import stripe  # type: ignore[import]
    except ImportError as exc:
        logger.error("stripe package is not installed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not available",
        ) from exc

    stripe.api_key = _billing_config.stripe_secret_key

    _plan_to_price = {
        "dev": _billing_config.stripe_price_dev,
        "starter": _billing_config.stripe_price_starter,
        "growth": _billing_config.stripe_price_growth,
    }
    price_id = _plan_to_price.get(body.plan, "")

    def _build_inline_line_items() -> list[dict]:
        plan_display = PLAN_LABELS.get(body.plan, body.plan.title())
        return [
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": PLAN_PRICES_CENTS[body.plan],
                    "recurring": {"interval": "month"},
                    "product_data": {
                        "name": f"Sardis {plan_display} Plan",
                        "description": PLAN_DESCRIPTIONS.get(body.plan, ""),
                    },
                },
                "quantity": 1,
            }
        ]

    checkout_kwargs = {
        "mode": "subscription",
        "success_url": f"{dashboard_billing_url}?success=1",
        "cancel_url": f"{dashboard_billing_url}?canceled=1",
        "metadata": {"org_id": principal.organization_id, "plan": body.plan},
    }

    try:
        if price_id:
            checkout_kwargs["line_items"] = [{"price": price_id, "quantity": 1}]
            session = stripe.checkout.Session.create(**checkout_kwargs)
        else:
            checkout_kwargs["line_items"] = _build_inline_line_items()
            session = stripe.checkout.Session.create(**checkout_kwargs)
    except Exception as exc:
        logger.error("Stripe checkout failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Checkout session creation failed",
        ) from exc

    from sardis_api.analytics.posthog_tracker import PLAN_UPGRADED, track_event
    track_event(principal.user_id, PLAN_UPGRADED, {"plan": body.plan, "provider": "stripe"})

    return CheckoutResponse(checkout_url=session.url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    principal: Principal = Depends(require_principal),
    billing=Depends(_get_billing_service),
):
    """Create a billing portal session for subscription management."""
    if not _billing_config.billing_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not enabled",
        )

    provider = get_billing_provider_name()

    # Polar: redirect to Polar dashboard (no portal API)
    if provider == "polar":
        return PortalResponse(portal_url="https://polar.sh/sardislabs/subscriptions")

    # Stripe: create portal session
    sub = await billing.get_or_create_subscription(principal.organization_id)
    if not sub.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No billing customer found for this organization",
        )

    try:
        import stripe  # type: ignore[import]
    except ImportError as exc:
        logger.error("stripe package is not installed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not available",
        ) from exc

    stripe.api_key = _billing_config.stripe_secret_key
    dashboard_billing_url = os.getenv(
        "SARDIS_DASHBOARD_BILLING_URL", "https://app.sardis.sh/billing"
    )

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=dashboard_billing_url,
        )
    except Exception as exc:
        logger.error("Stripe portal session creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create billing portal session",
        ) from exc

    return PortalResponse(portal_url=portal_session.url)
