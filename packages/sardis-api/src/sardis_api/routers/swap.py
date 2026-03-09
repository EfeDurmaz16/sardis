"""CDP Swap and Bridge API endpoints.

Provides token swap and cross-chain bridge functionality via
the Coinbase Developer Platform API.
"""
from __future__ import annotations

import logging
import os
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request/Response Models ──────────────────────────────────────────────


class SwapQuoteRequest(BaseModel):
    from_token: str = Field(description="Source token address or symbol")
    to_token: str = Field(description="Destination token address or symbol")
    amount: Decimal = Field(description="Amount to swap")
    chain: str = Field(default="base", description="Chain name")
    slippage_bps: int = Field(default=100, description="Max slippage in basis points")


class SwapQuoteResponse(BaseModel):
    quote_id: str
    from_token: str
    to_token: str
    from_amount: str
    to_amount: str
    exchange_rate: str
    fee_amount: str
    chain: str
    expires_at: str


class SwapExecuteRequest(BaseModel):
    quote_id: str = Field(description="Quote ID from swap quote")


class SwapExecuteResponse(BaseModel):
    tx_hash: str
    from_amount: str
    to_amount: str
    status: str


class BridgeQuoteRequest(BaseModel):
    from_chain: str = Field(description="Source chain")
    to_chain: str = Field(description="Destination chain")
    token: str = Field(description="Token to bridge")
    amount: Decimal = Field(description="Amount to bridge")


class BridgeQuoteResponse(BaseModel):
    quote_id: str
    from_chain: str
    to_chain: str
    token: str
    from_amount: str
    to_amount: str
    fee_amount: str
    estimated_time_seconds: int


class VerificationResponse(BaseModel):
    address: str
    is_verified: bool
    attestation_uid: str | None = None
    attester: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────


def _get_cdp_client():
    """Get or create CDP Swap client."""
    from sardis_chain.cdp_swap import CDPSwapClient

    api_key = os.getenv("COINBASE_CDP_API_KEY_NAME", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CDP Swap not configured (COINBASE_CDP_API_KEY_NAME missing)",
        )
    return CDPSwapClient(api_key=api_key)


def _get_verifications_client():
    """Get or create Coinbase Verifications client."""
    from sardis_compliance.coinbase_verifications import CoinbaseVerificationsClient
    return CoinbaseVerificationsClient()


# ── Swap Endpoints ───────────────────────────────────────────────────────


@router.post("/swap/quote", response_model=SwapQuoteResponse)
async def get_swap_quote(request: SwapQuoteRequest):
    """Get a token swap quote via CDP."""
    client = _get_cdp_client()
    try:
        quote = await client.get_quote(
            from_token=request.from_token,
            to_token=request.to_token,
            amount=request.amount,
            chain=request.chain,
            slippage_bps=request.slippage_bps,
        )
        return SwapQuoteResponse(
            quote_id=quote.quote_id,
            from_token=quote.from_token,
            to_token=quote.to_token,
            from_amount=str(quote.from_amount),
            to_amount=str(quote.to_amount),
            exchange_rate=str(quote.exchange_rate),
            fee_amount=str(quote.fee_amount),
            chain=quote.chain,
            expires_at=quote.expires_at,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Swap quote failed: {e}",
        ) from e
    finally:
        await client.close()


@router.post("/swap/execute", response_model=SwapExecuteResponse)
async def execute_swap(request: SwapExecuteRequest):
    """Execute a swap from a previously obtained quote."""
    client = _get_cdp_client()
    try:
        result = await client.execute_swap(
            quote_id=request.quote_id,
            wallet_signer=None,  # Signer resolved from wallet context
        )
        return SwapExecuteResponse(
            tx_hash=result.tx_hash,
            from_amount=str(result.from_amount),
            to_amount=str(result.to_amount),
            status=result.status,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Swap execution failed: {e}",
        ) from e
    finally:
        await client.close()


# ── Bridge Endpoints ─────────────────────────────────────────────────────


@router.post("/bridge/quote", response_model=BridgeQuoteResponse)
async def get_bridge_quote(request: BridgeQuoteRequest):
    """Get a cross-chain bridge quote via CDP."""
    client = _get_cdp_client()
    try:
        quote = await client.get_bridge_quote(
            from_chain=request.from_chain,
            to_chain=request.to_chain,
            token=request.token,
            amount=request.amount,
        )
        return BridgeQuoteResponse(
            quote_id=quote.quote_id,
            from_chain=quote.from_chain,
            to_chain=quote.to_chain,
            token=quote.token,
            from_amount=str(quote.from_amount),
            to_amount=str(quote.to_amount),
            fee_amount=str(quote.fee_amount),
            estimated_time_seconds=quote.estimated_time_seconds,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Bridge quote failed: {e}",
        ) from e
    finally:
        await client.close()


# ── Cross-Currency Endpoints (USDC ↔ EURC) ──────────────────────────────


class CrossCurrencyQuoteRequest(BaseModel):
    from_currency: str = Field(description="Source currency (USDC, EURC, MXN, etc.)")
    to_currency: str = Field(default="USDC", description="Destination currency")
    amount: Decimal = Field(description="Amount to convert")
    side: str = Field(default="from", description="Which side the amount is on: 'from' or 'to'")


class CrossCurrencyQuoteResponse(BaseModel):
    quote_id: str
    from_currency: str
    from_amount: str
    to_currency: str
    to_amount: str
    rate: str
    expires_at: str | None = None


class CrossCurrencyTradeRequest(BaseModel):
    quote_id: str = Field(description="Quote ID from cross-currency quote")


class CrossCurrencyTradeResponse(BaseModel):
    trade_id: str
    quote_id: str
    from_currency: str
    from_amount: str
    to_currency: str
    to_amount: str
    status: str


def _get_cross_currency_client():
    """Get or create Circle Cross-Currency client."""
    from sardis_chain.circle_cross_currency import CircleCrossCurrencyClient

    api_key = os.getenv("CIRCLE_MINT_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Circle Cross-Currency not configured (CIRCLE_MINT_API_KEY missing)",
        )
    sandbox = os.getenv("SARDIS_ENVIRONMENT", "dev") != "prod"
    return CircleCrossCurrencyClient(api_key=api_key, sandbox=sandbox)


@router.post("/exchange/quote", response_model=CrossCurrencyQuoteResponse)
async def get_cross_currency_quote(request: CrossCurrencyQuoteRequest):
    """Get a cross-currency exchange quote (USDC ↔ EURC or fiat ↔ USDC).

    Tradable quotes have a locked rate valid for 3 seconds.
    """
    client = _get_cross_currency_client()
    try:
        from_amount = request.amount if request.side == "from" else None
        to_amount = request.amount if request.side == "to" else None

        quote = await client.get_quote(
            from_currency=request.from_currency,
            from_amount=from_amount,
            to_currency=request.to_currency,
            to_amount=to_amount,
        )
        return CrossCurrencyQuoteResponse(
            quote_id=quote.quote_id,
            from_currency=quote.from_currency,
            from_amount=str(quote.from_amount),
            to_currency=quote.to_currency,
            to_amount=str(quote.to_amount),
            rate=str(quote.rate),
            expires_at=quote.expires_at,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cross-currency quote failed: {e}",
        ) from e
    finally:
        await client.close()


@router.post("/exchange/trade", response_model=CrossCurrencyTradeResponse)
async def execute_cross_currency_trade(request: CrossCurrencyTradeRequest):
    """Execute a cross-currency trade from a previously obtained quote.

    Must be called within 3 seconds of quote creation.
    USDC ↔ EURC trades settle instantly.
    """
    client = _get_cross_currency_client()
    try:
        trade = await client.execute_trade(quote_id=request.quote_id)
        return CrossCurrencyTradeResponse(
            trade_id=trade.trade_id,
            quote_id=trade.quote_id,
            from_currency=trade.from_currency,
            from_amount=str(trade.from_amount),
            to_currency=trade.to_currency,
            to_amount=str(trade.to_amount),
            status=trade.status.value,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cross-currency trade failed: {e}",
        ) from e
    finally:
        await client.close()


@router.get("/exchange/settlements")
async def get_settlements():
    """Get settlement batches for pending and completed trades."""
    client = _get_cross_currency_client()
    try:
        batches = await client.get_settlements()
        return {
            "settlements": [
                {
                    "batch_id": b.batch_id,
                    "status": b.status.value,
                    "details": [
                        {
                            "type": d.detail_type,
                            "status": d.status,
                            "currency": d.currency,
                            "amount": str(d.amount),
                        }
                        for d in b.details
                    ],
                    "created_at": b.created_at,
                }
                for b in batches
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Settlement query failed: {e}",
        ) from e
    finally:
        await client.close()


# ── Verification Endpoints ───────────────────────────────────────────────


@router.get("/verifications/{address}", response_model=VerificationResponse)
async def check_verification(address: str):
    """Check Coinbase Verification status for an address."""
    client = _get_verifications_client()
    try:
        result = await client.check_verification(address)
        return VerificationResponse(
            address=result.address,
            is_verified=result.is_verified,
            attestation_uid=result.attestation_uid,
            attester=result.attester,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Verification check failed: {e}",
        ) from e
    finally:
        await client.close()
