"""Stripe Shared Payment Token (SPT) API endpoints.

Enables agents to grant scoped payment credentials to sellers via Stripe.
Maps Sardis spending mandates to SPT usage_limits.

Reference: https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens
"""
from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from server.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


class GrantSPTRequest(BaseModel):
    mandate_id: str = Field(..., description="Spending mandate to back the SPT")
    payment_method: str = Field(default="pm_card_visa", description="Stripe PaymentMethod ID")
    seller_network_id: str = Field(default="internal")
    seller_external_id: str = Field(default="", description="Cart/order/connected-account ID")


class SPTResponse(BaseModel):
    token_id: str
    stripe_spt_id: str | None
    mandate_id: str | None
    status: str
    usage_limits: dict
    seller_details: dict
    created_at: str


class UseSPTRequest(BaseModel):
    spt_id: str = Field(..., description="Granted SPT ID (spt_xxx)")
    amount: int = Field(..., gt=0, description="Amount in smallest currency unit")
    currency: str = Field(default="usd")


class UseSPTResponse(BaseModel):
    payment_intent_id: str
    spt_id: str
    amount: int
    currency: str
    status: str


@router.post(
    "/spt/grant",
    response_model=SPTResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Grant a Shared Payment Token from a mandate",
)
async def grant_spt(
    req: GrantSPTRequest,
    principal: Principal = Depends(require_principal),
) -> SPTResponse:
    """Grant an SPT backed by a Sardis spending mandate.

    The SPT usage_limits are derived from the mandate's bounds.
    """
    from sardis.core.database import Database
    from sardis.core.spt import SharedPaymentToken, SPTSellerDetails, SPTUsageLimits

    # Verify mandate
    mandate = await Database.fetchrow(
        "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2 AND status = 'active'",
        req.mandate_id, principal.org_id,
    )
    if not mandate:
        raise HTTPException(status_code=404, detail="Active mandate not found")

    # Build SPT from mandate
    limits = SPTUsageLimits(
        currency=mandate.get("currency", "USDC").lower(),
        max_amount=int(mandate["amount_per_tx"] * 100) if mandate.get("amount_per_tx") else 10000,
        expires_at=int(mandate["expires_at"].timestamp()) if mandate.get("expires_at") else 0,
    )

    spt = SharedPaymentToken(
        mandate_id=req.mandate_id,
        agent_id=mandate.get("agent_id"),
        usage_limits=limits,
        seller_details=SPTSellerDetails(
            network_id=req.seller_network_id,
            external_id=req.seller_external_id,
        ),
    )

    # Call Stripe API to create the SPT (if STRIPE_SECRET_KEY is set)
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if stripe_key:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.stripe.com/v1/test_helpers/shared_payment/granted_tokens",
                    auth=(stripe_key, ""),
                    data={
                        "payment_method": req.payment_method,
                        "usage_limits[currency]": limits.currency,
                        "usage_limits[max_amount]": str(limits.max_amount),
                        "usage_limits[expires_at]": str(limits.expires_at),
                        "seller_details[network_id]": req.seller_network_id,
                        "seller_details[external_id]": req.seller_external_id or principal.org_id,
                    },
                )
                if resp.status_code == 200:
                    stripe_data = resp.json()
                    spt.stripe_spt_id = stripe_data.get("id")
        except Exception as e:
            logger.warning("Stripe SPT creation failed: %s", e)

    logger.info("Granted SPT %s from mandate %s", spt.token_id, req.mandate_id)

    return SPTResponse(
        token_id=spt.token_id,
        stripe_spt_id=spt.stripe_spt_id,
        mandate_id=spt.mandate_id,
        status=spt.status,
        usage_limits={
            "currency": limits.currency,
            "max_amount": limits.max_amount,
            "expires_at": limits.expires_at,
        },
        seller_details={
            "network_id": spt.seller_details.network_id,
            "external_id": spt.seller_details.external_id,
        },
        created_at=spt.created_at.isoformat(),
    )


@router.post(
    "/spt/use",
    response_model=UseSPTResponse,
    summary="Use a granted SPT to create a PaymentIntent",
)
async def use_spt(
    req: UseSPTRequest,
    principal: Principal = Depends(require_principal),
) -> UseSPTResponse:
    """Use a granted SPT to create a Stripe PaymentIntent."""
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.stripe.com/v1/payment_intents",
                auth=(stripe_key, ""),
                data={
                    "amount": str(req.amount),
                    "currency": req.currency,
                    "shared_payment_granted_token": req.spt_id,
                    "confirm": "true",
                },
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Stripe API error: {e}")

    return UseSPTResponse(
        payment_intent_id=data.get("id", ""),
        spt_id=req.spt_id,
        amount=req.amount,
        currency=req.currency,
        status=data.get("status", "unknown"),
    )


@router.get(
    "/spt/{spt_id}",
    response_model=SPTResponse,
    summary="Get SPT details",
)
async def get_spt(
    spt_id: str,
    principal: Principal = Depends(require_principal),
) -> SPTResponse:
    """Retrieve details of a granted SPT."""
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.stripe.com/v1/shared_payment/granted_tokens/{spt_id}",
                auth=(stripe_key, ""),
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail="SPT not found")
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Stripe API error: {e}")

    limits = data.get("usage_limits", {})
    return SPTResponse(
        token_id=spt_id,
        stripe_spt_id=data.get("id"),
        mandate_id=None,
        status="active" if not data.get("deactivated_at") else "deactivated",
        usage_limits={
            "currency": limits.get("currency", "usd"),
            "max_amount": limits.get("max_amount", 0),
            "expires_at": limits.get("expires_at", 0),
        },
        seller_details={},
        created_at=datetime.fromtimestamp(data.get("created", 0), tz=UTC).isoformat(),
    )
