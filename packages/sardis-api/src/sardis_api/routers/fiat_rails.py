"""Unified fiat rails — provider-agnostic SEPA, ACH, RTP, Wire interface."""
from __future__ import annotations

import logging

from fastapi import APIRouter
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


@router.post("/payout")
async def create_fiat_payout(req: FiatPayoutRequest):
    """
    Create a fiat payout — routes to the appropriate provider.

    Routing logic:
    - EUR + SEPA → Striga
    - USD + RTP/FedNow → Grid
    - USD + ACH → Grid or Bridge (compare fees)
    - USD + Wire → Grid
    """
    # Provider selection based on currency + rail
    if req.currency.upper() == "EUR" and req.rail.upper() in ("SEPA", "SEPA_INSTANT"):
        provider = "striga_sepa"
    elif req.rail.upper() in ("RTP", "FEDNOW"):
        provider = "lightspark_grid"
    elif req.rail.upper() == "WIRE":
        provider = "lightspark_grid"
    else:
        provider = "lightspark_grid"  # Default to Grid for ACH

    return {
        "status": "pending",
        "wallet_id": req.wallet_id,
        "amount_cents": req.amount_cents,
        "currency": req.currency,
        "rail": req.rail,
        "provider": provider,
        "message": f"Fiat payout via {provider} — requires provider API key",
    }


@router.post("/quote")
async def get_fiat_payout_quote(req: FiatPayoutQuoteRequest):
    """Get a quote for a fiat payout across available rails."""
    quotes = []

    if req.currency.upper() == "EUR":
        quotes.append({
            "rail": "sepa",
            "provider": "striga_sepa",
            "fee_bps": 10,
            "estimated_time": "1-2 business days",
        })
        quotes.append({
            "rail": "sepa_instant",
            "provider": "striga_sepa",
            "fee_bps": 50,
            "estimated_time": "< 10 seconds",
        })
    elif req.currency.upper() == "USD":
        quotes.append({
            "rail": "ach",
            "provider": "lightspark_grid",
            "fee_bps": 25,
            "estimated_time": "1-3 business days",
        })
        quotes.append({
            "rail": "rtp",
            "provider": "lightspark_grid",
            "fee_bps": 75,
            "estimated_time": "< 10 seconds",
        })
        quotes.append({
            "rail": "wire",
            "provider": "lightspark_grid",
            "fee_bps": 100,
            "estimated_time": "Same/next business day",
        })

    return {
        "amount_cents": req.amount_cents,
        "currency": req.currency,
        "quotes": quotes,
    }


@router.get("/rails")
async def list_available_rails():
    """List all available fiat payment rails."""
    return {
        "rails": [
            {"rail": "ach", "currency": "USD", "provider": "lightspark_grid", "speed": "1-3 days"},
            {"rail": "ach_same_day", "currency": "USD", "provider": "lightspark_grid", "speed": "same day"},
            {"rail": "rtp", "currency": "USD", "provider": "lightspark_grid", "speed": "instant"},
            {"rail": "fednow", "currency": "USD", "provider": "lightspark_grid", "speed": "instant"},
            {"rail": "wire", "currency": "USD", "provider": "lightspark_grid", "speed": "same/next day"},
            {"rail": "sepa", "currency": "EUR", "provider": "striga_sepa", "speed": "1-2 days"},
            {"rail": "sepa_instant", "currency": "EUR", "provider": "striga_sepa", "speed": "instant"},
        ],
    }
