"""Striga API routes — vIBAN management, card ops, webhooks."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
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


def _not_implemented() -> HTTPException:
    return HTTPException(
        status_code=501,
        detail={
            "error": "not_implemented",
            "message": "Striga integration is not yet available. Configure SARDIS_STRIGA_API_KEY when the integration is ready.",
        },
    )


@router.post("/vibans")
async def create_viban(req: CreateVIBANRequest):
    """Create a vIBAN for SEPA payments."""
    raise _not_implemented()


@router.get("/vibans/{wallet_id}")
async def get_viban(wallet_id: str):
    """Get vIBAN details for a wallet."""
    raise _not_implemented()


@router.post("/cards")
async def create_striga_card(req: StrigaCardRequest):
    """Create a EUR virtual Visa card via Striga."""
    raise _not_implemented()


@router.post("/sepa/payout")
async def create_sepa_payout(req: SEPAPayoutRequest):
    """Create a SEPA payout."""
    raise _not_implemented()


@router.post("/webhooks")
async def striga_webhook(request: Request):
    """Handle Striga webhook events."""
    raise _not_implemented()
