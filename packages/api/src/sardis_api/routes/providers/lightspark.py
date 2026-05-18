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


def _not_implemented() -> HTTPException:
    return HTTPException(
        status_code=501,
        detail={
            "error": "not_implemented",
            "message": "Lightspark Grid integration is not yet available. Configure SARDIS_LIGHTSPARK_API_KEY when the integration is ready.",
        },
    )


@router.post("/uma/create")
async def create_uma_address(req: CreateUMARequest):
    """Create a UMA address ($agent@sardis.sh)."""
    raise _not_implemented()


@router.get("/uma/{wallet_id}")
async def get_uma_address(wallet_id: str):
    """Get UMA address for a wallet."""
    raise _not_implemented()


@router.post("/uma/send")
async def send_uma_payment(req: SendUMAPaymentRequest):
    """Send payment to a UMA address."""
    raise _not_implemented()


@router.post("/payouts")
async def create_payout(req: CreatePayoutRequest):
    """Create a fiat payout (ACH/RTP/FedNow/Wire)."""
    raise _not_implemented()


@router.post("/fx/quote")
async def get_fx_quote(req: FXQuoteRequest):
    """Get an FX quote."""
    raise _not_implemented()


@router.post("/plaid/link-token")
async def create_plaid_link_token(req: PlaidLinkRequest):
    """Create a Plaid Link token for bank account linking."""
    raise _not_implemented()


@router.post("/webhooks")
async def grid_webhook(request: Request):
    """Handle Grid webhook events."""
    raise _not_implemented()
