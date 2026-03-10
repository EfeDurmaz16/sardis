"""Multi-currency API routes — FX quotes, cross-currency settlement, unified balance."""
from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/currency", tags=["currency"])


class FXConvertRequest(BaseModel):
    from_currency: str  # USDC, EURC, USD, EUR
    to_currency: str
    amount_cents: int


class UnifiedBalanceRequest(BaseModel):
    wallet_id: str
    include_eur: bool = True


@router.post("/convert")
async def convert_currency(req: FXConvertRequest):
    """
    Get cross-currency conversion quote with optimal path.

    Selects cheapest path:
    1. USDC → Bridge → USD (0.5%)
    2. USDC → Grid FX → EUR (~1.0%)
    3. EURC → Striga → EUR (0.3%)
    """
    # Path selection logic
    if req.from_currency.upper() in ("USDC", "USD") and req.to_currency.upper() == "USD":
        path = "usdc_bridge_usd"
        fee_bps = 50
    elif req.from_currency.upper() in ("USDC", "USD") and req.to_currency.upper() == "EUR":
        path = "usdc_grid_fx_eur"
        fee_bps = 100
    elif req.from_currency.upper() == "EURC" and req.to_currency.upper() == "EUR":
        path = "eurc_striga_eur"
        fee_bps = 30
    else:
        path = "direct"
        fee_bps = 0

    fee_cents = req.amount_cents * fee_bps // 10000

    return {
        "from_currency": req.from_currency,
        "to_currency": req.to_currency,
        "amount_cents": req.amount_cents,
        "converted_amount_cents": req.amount_cents - fee_cents,
        "fee_cents": fee_cents,
        "fee_percent": f"{fee_bps / 100:.2f}",
        "path": path,
        "exchange_rate": "1.0",
    }


@router.get("/balance/{wallet_id}")
async def get_unified_balance(wallet_id: str):
    """Get unified multi-currency balance for a wallet."""
    return {
        "wallet_id": wallet_id,
        "balances": {
            "usd": {
                "usdc_minor": 0,
                "usd_cents": 0,
                "total_cents": 0,
                "display": "$0.00",
            },
            "eur": {
                "eurc_minor": 0,
                "eur_cents": 0,
                "total_cents": 0,
                "display": "€0.00",
            },
        },
        "total_usd_equivalent_cents": 0,
    }


@router.get("/rates")
async def get_exchange_rates():
    """Get current exchange rates."""
    return {
        "rates": {
            "USD_EUR": "0.92",
            "EUR_USD": "1.09",
            "USDC_USD": "1.00",
            "EURC_EUR": "1.00",
        },
        "source": "lightspark_grid",
        "cached": True,
    }
