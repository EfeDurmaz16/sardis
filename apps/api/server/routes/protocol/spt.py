"""Stripe Shared Payment Token (SPT) API endpoints.

Enables agents to grant sellers scoped, mandate-backed payment credentials.
An SPT is the cleanest expression of a Sardis spending mandate as a bounded,
revocable credential: a seller can pull payment up to the mandate's per-tx cap,
within its currency and expiry, and the agent can revoke it at any time.

Production guarantees (this module is fail-closed):
- grant: requires Stripe; verifies an active mandate; if the Stripe SPT call
  fails, returns an error (never a hollow token); persists the grant locally so
  it is auditable + revocable on the Sardis side.
- use:   loads the local SPT (org-scoped), enforces status/expiry and the
  mandate-derived per-use cap server-side (with row locking) BEFORE charging
  Stripe, and records spend.
- revoke: deactivates the Stripe token and marks the local record revoked.

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

# Stripe SPT grant endpoints. The test_helpers path is sandbox-only; production
# must use the live granted-tokens endpoint.
_STRIPE_SPT_TEST_HELPERS_URL = "https://api.stripe.com/v1/test_helpers/shared_payment/granted_tokens"
_STRIPE_SPT_PROD_URL = "https://api.stripe.com/v1/shared_payment/granted_tokens"


def _is_prod() -> bool:
    return os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower() in {"prod", "production"}


def _stripe_grant_url() -> str:
    return _STRIPE_SPT_PROD_URL if _is_prod() else _STRIPE_SPT_TEST_HELPERS_URL


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
    spt_id: str = Field(..., description="Granted SPT token_id (spt_xxx)")
    amount: int = Field(..., gt=0, description="Amount in smallest currency unit")
    currency: str = Field(default="usd")


class UseSPTResponse(BaseModel):
    payment_intent_id: str
    spt_id: str
    amount: int
    currency: str
    status: str


class RevokeSPTResponse(BaseModel):
    token_id: str
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
    """Grant an SPT backed by a Sardis spending mandate (fail-closed).

    The SPT usage_limits are derived from the mandate's bounds. If Stripe is
    configured and the grant call fails, this raises 502 rather than returning a
    token with no backing Stripe SPT.
    """
    from sardis.core.database import Database
    from sardis.core.spt import SharedPaymentToken, SPTSellerDetails, SPTUsageLimits

    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    # Verify the backing mandate is active and owned by this org.
    mandate = await Database.fetchrow(
        "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2 AND status = 'active'",
        req.mandate_id, principal.org_id,
    )
    if not mandate:
        raise HTTPException(status_code=404, detail="Active mandate not found")

    # Reject grants from an already-expired mandate (bad-case: stale authority).
    expires_at_dt = mandate.get("expires_at")
    if expires_at_dt is not None and expires_at_dt <= datetime.now(UTC):
        raise HTTPException(status_code=409, detail="Mandate has expired")

    limits = SPTUsageLimits(
        currency=(mandate.get("currency") or "USDC").lower(),
        max_amount=int(mandate["amount_per_tx"] * 100) if mandate.get("amount_per_tx") else 0,
        expires_at=int(expires_at_dt.timestamp()) if expires_at_dt else 0,
    )
    if limits.max_amount <= 0:
        raise HTTPException(status_code=409, detail="Mandate has no per-transaction amount to bound the SPT")

    spt = SharedPaymentToken(
        mandate_id=req.mandate_id,
        agent_id=mandate.get("agent_id"),
        usage_limits=limits,
        seller_details=SPTSellerDetails(
            network_id=req.seller_network_id,
            external_id=req.seller_external_id,
        ),
    )

    # Create the Stripe SPT. Fail-closed: any error => no token is returned.
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _stripe_grant_url(),
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
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Stripe API error: {exc}") from exc

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Stripe SPT grant failed: {resp.text}")

    spt.stripe_spt_id = resp.json().get("id")
    if not spt.stripe_spt_id:
        raise HTTPException(status_code=502, detail="Stripe SPT grant returned no token id")

    # Persist the grant so it is auditable + revocable on the Sardis side.
    await Database.execute(
        """
        INSERT INTO shared_payment_tokens (
            token_id, org_id, mandate_id, agent_id, stripe_spt_id, payment_method,
            currency, max_amount, expires_at, seller_network_id, seller_external_id,
            status, created_at
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'active',$12)
        """,
        spt.token_id, principal.org_id, req.mandate_id, spt.agent_id,
        spt.stripe_spt_id, req.payment_method, limits.currency, limits.max_amount,
        limits.expires_at, req.seller_network_id, req.seller_external_id,
        spt.created_at,
    )

    logger.info("Granted SPT %s from mandate %s (stripe=%s)", spt.token_id, req.mandate_id, spt.stripe_spt_id)

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
    """Use a granted SPT to create a Stripe PaymentIntent.

    Enforces the Sardis-side bounds (status / expiry / per-use cap) BEFORE
    charging Stripe, with row locking to record spend atomically. Does not trust
    Stripe usage_limits alone.
    """
    from sardis.core.database import Database

    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    now_ts = int(datetime.now(UTC).timestamp())

    # Atomically validate + reserve spend under a row lock so concurrent uses
    # cannot together exceed the per-use cap or use a revoked/expired token.
    async with Database.transaction() as conn:
        row = await conn.fetchrow(
            """
            SELECT token_id, org_id, stripe_spt_id, currency, max_amount,
                   expires_at, status, spent_amount, use_count
            FROM shared_payment_tokens
            WHERE token_id = $1 AND org_id = $2
            FOR UPDATE
            """,
            req.spt_id, principal.org_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="SPT not found")
        if row["status"] != "active":
            raise HTTPException(status_code=409, detail=f"SPT is {row['status']}")
        if row["expires_at"] and row["expires_at"] <= now_ts:
            await conn.execute(
                "UPDATE shared_payment_tokens SET status='expired' WHERE token_id=$1",
                req.spt_id,
            )
            raise HTTPException(status_code=409, detail="SPT has expired")
        if req.currency.lower() != row["currency"].lower():
            raise HTTPException(status_code=422, detail="Currency mismatch with SPT")
        # Per-use cap enforced server-side (the mandate-derived max_amount).
        if req.amount > int(row["max_amount"]):
            raise HTTPException(status_code=422, detail="Amount exceeds SPT per-use limit")

        stripe_spt_id = row["stripe_spt_id"]
        if not stripe_spt_id:
            raise HTTPException(status_code=409, detail="SPT has no Stripe token")

        # Charge Stripe.
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.stripe.com/v1/payment_intents",
                    auth=(stripe_key, ""),
                    data={
                        "amount": str(req.amount),
                        "currency": req.currency,
                        "shared_payment_granted_token": stripe_spt_id,
                        "confirm": "true",
                    },
                )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Stripe API error: {exc}") from exc
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()

        # Record spend under the same lock.
        await conn.execute(
            """
            UPDATE shared_payment_tokens
            SET spent_amount = spent_amount + $2,
                use_count = use_count + 1,
                status = 'used',
                used_at = now()
            WHERE token_id = $1
            """,
            req.spt_id, req.amount,
        )

    return UseSPTResponse(
        payment_intent_id=data.get("id", ""),
        spt_id=req.spt_id,
        amount=req.amount,
        currency=req.currency,
        status=data.get("status", "unknown"),
    )


@router.post(
    "/spt/{token_id}/revoke",
    response_model=RevokeSPTResponse,
    summary="Revoke a granted SPT",
)
async def revoke_spt(
    token_id: str,
    principal: Principal = Depends(require_principal),
) -> RevokeSPTResponse:
    """Revoke a granted SPT: deactivate the Stripe token and mark it revoked."""
    from sardis.core.database import Database

    row = await Database.fetchrow(
        "SELECT token_id, stripe_spt_id, status FROM shared_payment_tokens WHERE token_id=$1 AND org_id=$2",
        token_id, principal.org_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="SPT not found")
    if row["status"] == "revoked":
        return RevokeSPTResponse(token_id=token_id, status="revoked")

    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if stripe_key and row["stripe_spt_id"]:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.stripe.com/v1/shared_payment/granted_tokens/{row['stripe_spt_id']}/deactivate",
                    auth=(stripe_key, ""),
                )
        except httpx.HTTPError as exc:
            # Stripe deactivation best-effort; local revoke is the source of truth.
            logger.warning("Stripe SPT deactivate failed for %s: %s", token_id, exc)

    await Database.execute(
        "UPDATE shared_payment_tokens SET status='revoked', revoked_at=now(), revoked_reason='api_revoke' WHERE token_id=$1",
        token_id,
    )
    logger.info("Revoked SPT %s", token_id)
    return RevokeSPTResponse(token_id=token_id, status="revoked")


@router.get(
    "/spt/{token_id}",
    response_model=SPTResponse,
    summary="Get SPT details",
)
async def get_spt(
    token_id: str,
    principal: Principal = Depends(require_principal),
) -> SPTResponse:
    """Retrieve details of a granted SPT from the Sardis store (org-scoped)."""
    from sardis.core.database import Database

    row = await Database.fetchrow(
        "SELECT * FROM shared_payment_tokens WHERE token_id=$1 AND org_id=$2",
        token_id, principal.org_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="SPT not found")

    return SPTResponse(
        token_id=row["token_id"],
        stripe_spt_id=row["stripe_spt_id"],
        mandate_id=row["mandate_id"],
        status=row["status"],
        usage_limits={
            "currency": row["currency"],
            "max_amount": int(row["max_amount"]),
            "expires_at": int(row["expires_at"]),
        },
        seller_details={
            "network_id": row["seller_network_id"],
            "external_id": row["seller_external_id"],
        },
        created_at=row["created_at"].isoformat() if row.get("created_at") else "",
    )
