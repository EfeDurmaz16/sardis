"""Stripe Connect API router for Sardis Connect.

Endpoints for merchant Stripe Connect onboarding, status,
and webhook handling for account + payout events.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis.authz import Principal, require_principal

logger = logging.getLogger("sardis.api.stripe_connect")

router = APIRouter(dependencies=[Depends(require_principal)])
webhook_router = APIRouter(prefix="/stripe-connect", tags=["stripe-connect-webhooks"])


# ── Request / Response Models ────────────────────────────────────

class ConnectOnboardRequest(BaseModel):
    """Request to initiate Stripe Connect onboarding."""
    country: str = Field(default="US", max_length=2)
    email: str | None = Field(default=None, max_length=255)


class ConnectOnboardResponse(BaseModel):
    """Response with Stripe Account Link for onboarding redirect."""
    merchant_id: str
    stripe_account_id: str
    onboarding_url: str
    expires_at: str


class ConnectStatusResponse(BaseModel):
    """Current Stripe Connect account status."""
    merchant_id: str
    stripe_account_id: str | None
    onboarding_state: str
    charges_enabled: bool
    payouts_enabled: bool
    details_submitted: bool
    disabled_reason: str | None = None
    current_deadline: str | None = None
    requirements_currently_due: list[str] = []
    requirements_past_due: list[str] = []
    last_synced_at: str | None = None


class ConnectRefreshResponse(BaseModel):
    """New Account Link after refresh."""
    onboarding_url: str
    expires_at: str


# ── Dependencies ─────────────────────────────────────────────────

@dataclass
class StripeConnectDeps:
    merchant_repo: Any
    stripe_connect_provider: Any


def get_deps() -> StripeConnectDeps:
    raise RuntimeError("StripeConnectDeps not configured")


# ── Endpoints ────────────────────────────────────────────────────

@router.post(
    "/{merchant_id}/connect",
    response_model=ConnectOnboardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Stripe Connect onboarding",
)
async def start_connect_onboarding(
    merchant_id: str,
    body: ConnectOnboardRequest,
    principal: Principal = Depends(require_principal),
    deps: StripeConnectDeps = Depends(get_deps),
) -> ConnectOnboardResponse:
    """Create a Stripe Express account and return an onboarding link.

    If the merchant already has a Stripe account, creates a new
    Account Link for updating information.
    """
    merchant = await deps.merchant_repo.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    provider = deps.stripe_connect_provider

    # Create new account or reuse existing
    if merchant.stripe_account_id:
        # Already has an account — create an update link
        account_id = merchant.stripe_account_id
    else:
        # Create new Express account
        account = await provider.create_express_account(
            email=body.email,
            business_name=merchant.name,
            country=body.country,
            mcc_code=merchant.mcc_code,
            metadata={"sardis_merchant_id": merchant.merchant_id},
        )
        account_id = account.account_id

        # Persist account ID and switch settlement preference
        await deps.merchant_repo.update_merchant(
            merchant_id,
            stripe_account_id=account_id,
            stripe_onboarding_state="pending",
            settlement_preference="stripe_connect",
        )

    # Create Account Link
    link_type = "account_onboarding" if not merchant.stripe_account_id else "account_update"
    link = await provider.create_account_link(
        account_id=account_id,
        merchant_id=merchant_id,
        link_type=link_type,
    )

    return ConnectOnboardResponse(
        merchant_id=merchant_id,
        stripe_account_id=account_id,
        onboarding_url=link.url,
        expires_at=link.expires_at.isoformat(),
    )


@router.get(
    "/{merchant_id}/connect/status",
    response_model=ConnectStatusResponse,
    summary="Get Stripe Connect status",
)
async def get_connect_status(
    merchant_id: str,
    deps: StripeConnectDeps = Depends(get_deps),
) -> ConnectStatusResponse:
    """Get the current Stripe Connect onboarding and payout status."""
    merchant = await deps.merchant_repo.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    if not merchant.stripe_account_id:
        return ConnectStatusResponse(
            merchant_id=merchant_id,
            stripe_account_id=None,
            onboarding_state="not_started",
            charges_enabled=False,
            payouts_enabled=False,
            details_submitted=False,
        )

    # Fetch live status from Stripe
    provider = deps.stripe_connect_provider
    account = await provider.get_account_status(merchant.stripe_account_id)

    # Sync to DB
    await deps.merchant_repo.update_merchant(
        merchant_id,
        stripe_onboarding_state=account.onboarding_state,
        stripe_charges_enabled=account.charges_enabled,
        stripe_payouts_enabled=account.payouts_enabled,
        stripe_details_submitted=account.details_submitted,
        stripe_disabled_reason=account.disabled_reason,
        stripe_current_deadline=account.current_deadline,
        stripe_last_synced_at=datetime.now(UTC),
    )

    return ConnectStatusResponse(
        merchant_id=merchant_id,
        stripe_account_id=merchant.stripe_account_id,
        onboarding_state=account.onboarding_state,
        charges_enabled=account.charges_enabled,
        payouts_enabled=account.payouts_enabled,
        details_submitted=account.details_submitted,
        disabled_reason=account.disabled_reason,
        current_deadline=account.current_deadline.isoformat() if account.current_deadline else None,
        requirements_currently_due=account.requirements_currently_due,
        requirements_past_due=account.requirements_past_due,
        last_synced_at=datetime.now(UTC).isoformat(),
    )


@router.post(
    "/{merchant_id}/connect/refresh",
    response_model=ConnectRefreshResponse,
    summary="Refresh expired Account Link",
)
async def refresh_connect_link(
    merchant_id: str,
    deps: StripeConnectDeps = Depends(get_deps),
) -> ConnectRefreshResponse:
    """Create a new Account Link when the previous one expired.

    Account Links are single-use and expire within minutes.
    This endpoint generates a fresh one for the same account.
    """
    merchant = await deps.merchant_repo.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    if not merchant.stripe_account_id:
        raise HTTPException(status_code=400, detail="Merchant has no Stripe account. Call POST /connect first.")

    provider = deps.stripe_connect_provider
    link = await provider.create_account_link(
        account_id=merchant.stripe_account_id,
        merchant_id=merchant_id,
        link_type="account_onboarding",
    )

    return ConnectRefreshResponse(
        onboarding_url=link.url,
        expires_at=link.expires_at.isoformat(),
    )


# ── Webhook Handler ──────────────────────────────────────────────

CONNECT_EVENTS = {
    "account.updated",
    "payout.paid",
    "payout.failed",
    "payout.created",
}


@webhook_router.post(
    "/webhooks",
    status_code=200,
    summary="Stripe Connect webhook handler",
)
async def stripe_connect_webhook(
    request: Request,
    deps: StripeConnectDeps = Depends(get_deps),
) -> dict[str, str]:
    """Handle Stripe Connect webhook events.

    Processes account.updated (onboarding state changes) and
    payout events (settlement status tracking).

    Webhook must be configured with connect=True in Stripe Dashboard
    to receive events for connected accounts.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    provider = deps.stripe_connect_provider
    try:
        event = provider.verify_webhook_signature(payload, sig_header)
    except Exception as e:
        logger.warning("Stripe Connect webhook signature verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event.get("type", "") if isinstance(event, dict) else getattr(event, "type", "")
    event_data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else getattr(event.data, "object", {})

    if event_type not in CONNECT_EVENTS:
        return {"status": "ignored"}

    if event_type == "account.updated":
        await _handle_account_updated(event_data, deps)
    elif event_type in ("payout.paid", "payout.failed"):
        await _handle_payout_event(event_type, event_data, deps)

    return {"status": "ok"}


async def _handle_account_updated(account_data: Any, deps: StripeConnectDeps) -> None:
    """Sync Stripe account status to merchant record."""
    account_id = account_data.get("id") if isinstance(account_data, dict) else getattr(account_data, "id", None)
    if not account_id:
        return

    # Find merchant by stripe_account_id
    from sardis_v2_core.database import Database
    row = await Database.fetchrow(
        "SELECT external_id FROM merchants WHERE stripe_account_id = $1",
        account_id,
    )
    if not row:
        logger.warning("Stripe Connect webhook: no merchant for account %s", account_id)
        return

    merchant_id = row["external_id"]
    provider = deps.stripe_connect_provider
    status = await provider.get_account_status(account_id)

    await deps.merchant_repo.update_merchant(
        merchant_id,
        stripe_onboarding_state=status.onboarding_state,
        stripe_charges_enabled=status.charges_enabled,
        stripe_payouts_enabled=status.payouts_enabled,
        stripe_details_submitted=status.details_submitted,
        stripe_disabled_reason=status.disabled_reason,
        stripe_current_deadline=status.current_deadline,
        stripe_last_synced_at=datetime.now(UTC),
    )

    logger.info(
        "Stripe Connect account %s updated: state=%s charges=%s payouts=%s",
        account_id, status.onboarding_state, status.charges_enabled, status.payouts_enabled,
    )


async def _handle_payout_event(event_type: str, payout_data: Any, deps: StripeConnectDeps) -> None:
    """Track payout status for settlement reconciliation."""
    payout_id = payout_data.get("id") if isinstance(payout_data, dict) else getattr(payout_data, "id", None)
    payout_status = "paid" if event_type == "payout.paid" else "failed"

    failure_code = None
    failure_message = None
    if payout_status == "failed":
        failure_code = payout_data.get("failure_code") if isinstance(payout_data, dict) else getattr(payout_data, "failure_code", None)
        failure_message = payout_data.get("failure_message") if isinstance(payout_data, dict) else getattr(payout_data, "failure_message", None)

    # Update payout tracking record if exists
    from sardis_v2_core.database import Database
    await Database.execute(
        """
        UPDATE stripe_connect_payouts
        SET status = $1, failure_code = $2, failure_message = $3,
            stripe_payout_id = $4, updated_at = NOW()
        WHERE stripe_payout_id = $4 OR stripe_transfer_id IN (
            SELECT stripe_transfer_id FROM stripe_connect_payouts
            WHERE stripe_payout_id = $4
        )
        """,
        payout_status, failure_code, failure_message, payout_id,
    )

    logger.info("Stripe payout %s: status=%s", payout_id, payout_status)
