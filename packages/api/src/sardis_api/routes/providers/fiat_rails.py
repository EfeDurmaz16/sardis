"""Unified fiat rails — provider-agnostic SEPA, ACH, RTP, Wire interface."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fiat-rails", tags=["fiat-rails"])


class FiatPayoutRequest(BaseModel):
    wallet_id: str
    amount_cents: int
    currency: str
    rail: str  # sepa, ach, rtp, fednow, wire
    destination: dict  # iban/bic or account_id
    reference: str = ""


class FiatPayoutQuoteRequest(BaseModel):
    amount_cents: int
    currency: str
    rail: str
    destination_country: str = "US"


def _not_implemented() -> HTTPException:
    return HTTPException(
        status_code=501,
        detail={
            "error": "not_implemented",
            "message": "Fiat rails integration is not yet available. Requires Lightspark Grid (SARDIS_LIGHTSPARK_API_KEY) or Striga (SARDIS_STRIGA_API_KEY) configuration.",
        },
    )


@router.post("/payout")
async def create_fiat_payout(req: FiatPayoutRequest):
    """
    Create a fiat payout — routes to the appropriate provider.

    Routing logic:
    - EUR + SEPA -> Striga
    - USD + RTP/FedNow -> Grid
    - USD + ACH -> Grid or Bridge (compare fees)
    - USD + Wire -> Grid
    """
    raise _not_implemented()


@router.post("/quote")
async def get_fiat_payout_quote(req: FiatPayoutQuoteRequest):
    """Get a quote for a fiat payout across available rails."""
    raise _not_implemented()


@router.get("/rails")
async def list_available_rails():
    """List all available fiat payment rails."""
    raise _not_implemented()
