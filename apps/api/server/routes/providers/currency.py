"""Multi-currency API routes — FX quotes, cross-currency settlement, unified balance."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
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


def _not_implemented() -> HTTPException:
    return HTTPException(
        status_code=501,
        detail={
            "error": "not_implemented",
            "message": "Multi-currency integration is not yet available. Requires Lightspark Grid or Striga provider configuration.",
        },
    )


@router.post("/convert")
async def convert_currency(req: FXConvertRequest):
    """
    Get cross-currency conversion quote with optimal path.

    Selects cheapest path:
    1. USDC -> Bridge -> USD (0.5%)
    2. USDC -> Grid FX -> EUR (~1.0%)
    3. EURC -> Striga -> EUR (0.3%)
    """
    raise _not_implemented()


@router.get("/balance/{wallet_id}")
async def get_unified_balance(wallet_id: str):
    """Get unified multi-currency balance for a wallet."""
    raise _not_implemented()


@router.get("/rates")
async def get_exchange_rates():
    """Get current exchange rates."""
    raise _not_implemented()
