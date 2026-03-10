"""Lightspark Grid API routes — UMA, payouts, FX, Plaid, webhooks."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grid", tags=["lightspark-grid"])


class CreateUMARequest(BaseModel):
    wallet_id: str
    agent_id: str
    currency: str = "USD"


class SendUMAPaymentRequest(BaseModel):
    from_wallet_id: str
    to_address: str  # $agent@sardis.sh
    amount_cents: int
    currency: str = "USD"


class CreatePayoutRequest(BaseModel):
    wallet_id: str
    amount_cents: int
    currency: str = "USD"
    rail: str = "ach"  # ach, rtp, fednow, wire
    account_id: str = ""
    reference: str = "Sardis payout"


class FXQuoteRequest(BaseModel):
    from_currency: str
    to_currency: str
    amount_cents: int


class PlaidLinkRequest(BaseModel):
    customer_id: str
    redirect_uri: str | None = None


@router.post("/uma/create")
async def create_uma_address(req: CreateUMARequest):
    """Create a UMA address ($agent@sardis.sh)."""
    return {
        "status": "created",
        "address": f"${req.agent_id}@sardis.sh",
        "wallet_id": req.wallet_id,
        "currency": req.currency,
        "message": "Grid UMA creation requires SARDIS_LIGHTSPARK_API_KEY",
    }


@router.get("/uma/{wallet_id}")
async def get_uma_address(wallet_id: str):
    """Get UMA address for a wallet."""
    return {
        "wallet_id": wallet_id,
        "message": "Grid UMA lookup requires SARDIS_LIGHTSPARK_API_KEY",
    }


@router.post("/uma/send")
async def send_uma_payment(req: SendUMAPaymentRequest):
    """Send payment to a UMA address."""
    return {
        "status": "processing",
        "from_wallet_id": req.from_wallet_id,
        "to_address": req.to_address,
        "amount_cents": req.amount_cents,
        "currency": req.currency,
        "message": "Grid UMA send requires SARDIS_LIGHTSPARK_API_KEY",
    }


@router.post("/payouts")
async def create_payout(req: CreatePayoutRequest):
    """Create a fiat payout (ACH/RTP/FedNow/Wire)."""
    return {
        "status": "processing",
        "wallet_id": req.wallet_id,
        "amount_cents": req.amount_cents,
        "currency": req.currency,
        "rail": req.rail,
        "message": "Grid payout requires SARDIS_LIGHTSPARK_API_KEY",
    }


@router.post("/fx/quote")
async def get_fx_quote(req: FXQuoteRequest):
    """Get an FX quote."""
    return {
        "from_currency": req.from_currency,
        "to_currency": req.to_currency,
        "amount_cents": req.amount_cents,
        "message": "Grid FX requires SARDIS_LIGHTSPARK_API_KEY",
    }


@router.post("/plaid/link-token")
async def create_plaid_link_token(req: PlaidLinkRequest):
    """Create a Plaid Link token for bank account linking."""
    return {
        "customer_id": req.customer_id,
        "message": "Grid Plaid integration requires SARDIS_LIGHTSPARK_API_KEY",
    }


@router.post("/webhooks")
async def grid_webhook(request: Request):
    """Handle Grid webhook events."""
    payload = await request.body()
    signature = request.headers.get("X-Grid-Signature", "")

    if not signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    logger.info(f"Received Grid webhook, payload size: {len(payload)}")

    return {"status": "received"}
