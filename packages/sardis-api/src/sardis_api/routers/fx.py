"""FX and Bridge API endpoints.

Cross-currency stablecoin swaps and cross-chain bridge transfers.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class FXQuoteRequest(BaseModel):
    from_currency: str = Field(..., description="Source currency (e.g., USDC)")
    to_currency: str = Field(..., description="Target currency (e.g., EURC)")
    from_amount: Decimal = Field(..., gt=0)
    chain: str = Field(default="tempo")
    slippage_bps: int = Field(default=50, ge=1, le=1000)


class FXQuoteResponse(BaseModel):
    quote_id: str
    from_currency: str
    to_currency: str
    from_amount: str
    to_amount: str
    rate: str
    effective_rate: str
    slippage_bps: int
    provider: str
    chain: str
    status: str
    expires_at: str
    created_at: str


class FXExecuteRequest(BaseModel):
    quote_id: str = Field(..., description="Quote ID to execute")


class FXRatesResponse(BaseModel):
    rates: list[dict]
    updated_at: str


class BridgeTransferRequest(BaseModel):
    from_chain: str = Field(...)
    to_chain: str = Field(...)
    token: str = Field(default="USDC")
    amount: Decimal = Field(..., gt=0)
    bridge_provider: str = Field(default="relay")


class BridgeTransferResponse(BaseModel):
    transfer_id: str
    from_chain: str
    to_chain: str
    token: str
    amount: str
    bridge_provider: str
    bridge_fee: str
    status: str
    estimated_seconds: int
    created_at: str


# ---------------------------------------------------------------------------
# FX Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/fx/quote",
    response_model=FXQuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request an FX quote for a stablecoin swap",
)
async def create_fx_quote(
    req: FXQuoteRequest,
    principal: Principal = Depends(require_principal),
) -> FXQuoteResponse:
    from sardis_v2_core.database import Database

    # Determine provider based on chain
    provider = "tempo_dex" if req.chain == "tempo" else "uniswap_v3"

    # Get rate (simplified — in production, query the DEX orderbook)
    rate = _get_indicative_rate(req.from_currency, req.to_currency)
    to_amount = (req.from_amount * rate).quantize(Decimal("0.000001"))

    quote_id = f"fxq_{uuid4().hex[:12]}"
    expires_at = datetime.now(UTC) + timedelta(seconds=30)

    await Database.execute(
        """INSERT INTO fx_quotes
           (quote_id, from_currency, to_currency, from_amount, to_amount,
            rate, slippage_bps, provider, chain, status, expires_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)""",
        quote_id, req.from_currency, req.to_currency,
        req.from_amount, to_amount, rate, req.slippage_bps,
        provider, req.chain, "quoted", expires_at,
    )

    return FXQuoteResponse(
        quote_id=quote_id,
        from_currency=req.from_currency,
        to_currency=req.to_currency,
        from_amount=str(req.from_amount),
        to_amount=str(to_amount),
        rate=str(rate),
        effective_rate=str(to_amount / req.from_amount if req.from_amount else rate),
        slippage_bps=req.slippage_bps,
        provider=provider,
        chain=req.chain,
        status="quoted",
        expires_at=expires_at.isoformat(),
        created_at=datetime.now(UTC).isoformat(),
    )


@router.post(
    "/fx/execute",
    response_model=FXQuoteResponse,
    summary="Execute an FX swap from a quote",
)
async def execute_fx_quote(
    req: FXExecuteRequest,
    principal: Principal = Depends(require_principal),
) -> FXQuoteResponse:
    from sardis_v2_core.database import Database

    async with Database.transaction() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM fx_quotes WHERE quote_id = $1 FOR UPDATE NOWAIT",
            req.quote_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Quote not found")
        if row["status"] != "quoted":
            raise HTTPException(status_code=409, detail=f"Quote is {row['status']}")
        if datetime.now(UTC) > row["expires_at"]:
            await conn.execute(
                "UPDATE fx_quotes SET status = 'expired', updated_at = now() WHERE quote_id = $1",
                req.quote_id,
            )
            raise HTTPException(status_code=410, detail="Quote has expired")

        # Execute the swap (in production, submit on-chain tx)
        await conn.execute(
            """UPDATE fx_quotes SET status = 'executing', updated_at = now()
               WHERE quote_id = $1""",
            req.quote_id,
        )

        # Mark completed (simplified — would wait for on-chain confirmation)
        await conn.execute(
            """UPDATE fx_quotes SET status = 'completed', updated_at = now()
               WHERE quote_id = $1""",
            req.quote_id,
        )

    updated = await Database.fetchrow(
        "SELECT * FROM fx_quotes WHERE quote_id = $1", req.quote_id
    )
    return _quote_row_to_response(updated)


@router.get(
    "/fx/rates",
    response_model=FXRatesResponse,
    summary="Get current indicative FX rates",
)
async def get_fx_rates(
    principal: Principal = Depends(require_principal),
) -> FXRatesResponse:
    pairs = [
        ("USDC", "EURC"), ("EURC", "USDC"),
        ("USDC", "USDT"), ("USDT", "USDC"),
    ]
    rates = []
    for from_c, to_c in pairs:
        rate = _get_indicative_rate(from_c, to_c)
        rates.append({
            "from": from_c,
            "to": to_c,
            "rate": str(rate),
            "provider": "tempo_dex",
        })
    return FXRatesResponse(
        rates=rates,
        updated_at=datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# Bridge Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/bridge/transfer",
    response_model=BridgeTransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a cross-chain bridge transfer",
)
async def create_bridge_transfer(
    req: BridgeTransferRequest,
    principal: Principal = Depends(require_principal),
) -> BridgeTransferResponse:
    from sardis_v2_core.database import Database

    if req.from_chain == req.to_chain:
        raise HTTPException(status_code=422, detail="Source and destination chains must differ")

    transfer_id = f"brt_{uuid4().hex[:12]}"
    fee = _estimate_bridge_fee(req.bridge_provider, req.amount)

    await Database.execute(
        """INSERT INTO bridge_transfers
           (transfer_id, from_chain, to_chain, token, amount,
            bridge_provider, bridge_fee, status, estimated_seconds)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
        transfer_id, req.from_chain, req.to_chain, req.token,
        req.amount, req.bridge_provider, fee, "pending",
        _estimate_bridge_time(req.bridge_provider),
    )

    return BridgeTransferResponse(
        transfer_id=transfer_id,
        from_chain=req.from_chain,
        to_chain=req.to_chain,
        token=req.token,
        amount=str(req.amount),
        bridge_provider=req.bridge_provider,
        bridge_fee=str(fee),
        status="pending",
        estimated_seconds=_estimate_bridge_time(req.bridge_provider),
        created_at=datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Indicative rates (in production, fetched from DEX orderbook)
_INDICATIVE_RATES: dict[tuple[str, str], Decimal] = {
    ("USDC", "EURC"): Decimal("0.9215"),
    ("EURC", "USDC"): Decimal("1.0852"),
    ("USDC", "USDT"): Decimal("1.0000"),
    ("USDT", "USDC"): Decimal("1.0000"),
}


def _get_indicative_rate(from_c: str, to_c: str) -> Decimal:
    return _INDICATIVE_RATES.get((from_c, to_c), Decimal("1.0"))


def _estimate_bridge_fee(provider: str, amount: Decimal) -> Decimal:
    # Simplified fee estimation
    fee_bps = {"relay": 5, "across": 8, "squid": 10, "bungee": 12, "layerzero": 15}
    bps = fee_bps.get(provider, 10)
    return (amount * Decimal(bps) / Decimal(10000)).quantize(Decimal("0.000001"))


def _estimate_bridge_time(provider: str) -> int:
    times = {"relay": 30, "across": 60, "squid": 120, "bungee": 90, "layerzero": 180}
    return times.get(provider, 60)


def _quote_row_to_response(row) -> FXQuoteResponse:
    return FXQuoteResponse(
        quote_id=row["quote_id"],
        from_currency=row["from_currency"],
        to_currency=row["to_currency"],
        from_amount=str(row["from_amount"]),
        to_amount=str(row["to_amount"]),
        rate=str(row["rate"]),
        effective_rate=str(row["to_amount"] / row["from_amount"] if row["from_amount"] else row["rate"]),
        slippage_bps=row["slippage_bps"],
        provider=row["provider"],
        chain=row["chain"],
        status=row["status"],
        expires_at=row["expires_at"].isoformat(),
        created_at=row["created_at"].isoformat(),
    )
