"""Fiat Off-ramp API — EURC/USDC → EUR/USD bank settlement.

Powered by Bridge.xyz Tempo integration. Supports:
- Liquidation addresses (auto-convert deposits to fiat)
- Direct transfers (wallet → bank account)

Flow: USDC → EURC (on-chain DEX swap) → EUR (Bridge.xyz off-ramp → bank)
"""
from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


class CreateLiquidationRequest(BaseModel):
    token: str = Field(default="EURC", description="EURC or USDC")
    destination_currency: str = Field(default="eur", description="Target fiat: eur, usd, gbp")
    payment_rail: str = Field(default="wire", pattern="^(wire|ach|sepa)$")
    external_account_id: str = Field(default="", description="Bridge.xyz external bank account ID")


class LiquidationResponse(BaseModel):
    address_id: str
    deposit_address: str  # Send stablecoins here → auto-converts to fiat
    token: str
    destination_currency: str
    payment_rail: str
    status: str


class WithdrawRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    source_currency: str = Field(default="eurc")
    destination_currency: str = Field(default="eur")
    payment_rail: str = Field(default="wire", pattern="^(wire|ach|sepa)$")
    external_account_id: str = Field(...)


class WithdrawResponse(BaseModel):
    transfer_id: str
    amount: str
    source_currency: str
    destination_currency: str
    payment_rail: str
    status: str
    fee: str


@router.post(
    "/offramp/liquidation",
    response_model=LiquidationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create auto-convert liquidation address",
)
async def create_liquidation(
    req: CreateLiquidationRequest,
    principal: Principal = Depends(require_principal),
) -> LiquidationResponse:
    """Create a liquidation address for automatic fiat settlement.

    Send EURC/USDC to the returned address → Bridge.xyz auto-converts
    to fiat and settles to your linked bank account.
    """
    from sardis_chain.bridge_xyz import BridgeXYZAdapter

    bridge = BridgeXYZAdapter()
    if not bridge.is_configured:
        raise HTTPException(status_code=503, detail="BRIDGE_API_KEY not configured")

    try:
        result = await bridge.create_liquidation_address(
            customer_id=principal.org_id,
            token=req.token,
            destination_currency=req.destination_currency,
            payment_rail=req.payment_rail,
            external_account_id=req.external_account_id,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bridge.xyz error: {e}")

    return LiquidationResponse(
        address_id=result.address_id,
        deposit_address=result.deposit_address,
        token=result.token,
        destination_currency=result.destination_currency,
        payment_rail=result.payment_rail,
        status=result.status,
    )


@router.post(
    "/offramp/withdraw",
    response_model=WithdrawResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Withdraw stablecoins to fiat bank account",
)
async def withdraw_to_fiat(
    req: WithdrawRequest,
    principal: Principal = Depends(require_principal),
) -> WithdrawResponse:
    """Initiate a fiat off-ramp transfer.

    Converts EURC/USDC from your Tempo wallet to fiat and
    settles to your bank account via wire/ACH/SEPA.
    """
    from sardis_chain.bridge_xyz import BridgeXYZAdapter

    bridge = BridgeXYZAdapter()
    if not bridge.is_configured:
        raise HTTPException(status_code=503, detail="BRIDGE_API_KEY not configured")

    try:
        result = await bridge.create_offramp_transfer(
            customer_id=principal.org_id,
            amount=req.amount,
            source_currency=req.source_currency,
            destination_currency=req.destination_currency,
            payment_rail=req.payment_rail,
            external_account_id=req.external_account_id,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bridge.xyz error: {e}")

    return WithdrawResponse(
        transfer_id=result.transfer_id,
        amount=str(result.amount),
        source_currency=result.source_currency,
        destination_currency=result.destination_currency,
        payment_rail=result.payment_rail,
        status=result.status,
        fee=str(result.fee),
    )
