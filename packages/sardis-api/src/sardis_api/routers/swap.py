"""CDP Swap and Bridge API endpoints.

Provides token swap and cross-chain bridge functionality via
the Coinbase Developer Platform API.
"""
from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
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
    attestation_uid: Optional[str] = None
    attester: Optional[str] = None


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
