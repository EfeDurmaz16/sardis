"""Striga API routes — vIBAN management, card ops, webhooks."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/striga", tags=["striga"])


class CreateVIBANRequest(BaseModel):
    wallet_id: str
    currency: str = "EUR"


class StrigaCardRequest(BaseModel):
    wallet_id: str
    currency: str = "EUR"
    limit_per_tx: float = 500.0
    limit_daily: float = 2000.0
    limit_monthly: float = 10000.0


class SEPAPayoutRequest(BaseModel):
    wallet_id: str
    amount: float
    iban: str
    bic: str = ""
    beneficiary_name: str = ""
    reference: str = "Sardis payout"
    instant: bool = False


@router.post("/vibans")
async def create_viban(req: CreateVIBANRequest):
    """Create a vIBAN for SEPA payments."""
    return {
        "status": "created",
        "wallet_id": req.wallet_id,
        "currency": req.currency,
        "message": "Striga vIBAN creation requires SARDIS_STRIGA_API_KEY",
    }


@router.get("/vibans/{wallet_id}")
async def get_viban(wallet_id: str):
    """Get vIBAN details for a wallet."""
    return {
        "wallet_id": wallet_id,
        "message": "Striga vIBAN lookup requires SARDIS_STRIGA_API_KEY",
    }


@router.post("/cards")
async def create_striga_card(req: StrigaCardRequest):
    """Create a EUR virtual Visa card via Striga."""
    return {
        "status": "created",
        "wallet_id": req.wallet_id,
        "currency": req.currency,
        "provider": "striga",
        "message": "Striga card creation requires SARDIS_STRIGA_API_KEY",
    }


@router.post("/sepa/payout")
async def create_sepa_payout(req: SEPAPayoutRequest):
    """Create a SEPA payout."""
    return {
        "status": "processing",
        "wallet_id": req.wallet_id,
        "amount": req.amount,
        "iban": req.iban,
        "rail": "sepa_instant" if req.instant else "sepa",
        "message": "Striga SEPA payout requires SARDIS_STRIGA_API_KEY",
    }


@router.post("/webhooks")
async def striga_webhook(request: Request):
    """Handle Striga webhook events."""
    payload = await request.body()
    signature = request.headers.get("X-Striga-Signature", "")

    if not signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    logger.info(f"Received Striga webhook, payload size: {len(payload)}")

    return {"status": "received"}
