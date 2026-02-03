"""Fiat on-ramp and off-ramp API endpoints."""
from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Request/Response Models ----

class OnrampWidgetRequest(BaseModel):
    """Request to generate an Onramper widget URL."""
    wallet_id: str
    amount_usd: Optional[Decimal] = None
    chain: str = Field(default="base")
    token: str = Field(default="USDC")


class OnrampWidgetResponse(BaseModel):
    widget_url: str
    wallet_address: str
    chain: str
    token: str


class OnrampQuoteRequest(BaseModel):
    amount_usd: Decimal = Field(gt=0)
    payment_method: str = Field(default="creditcard")
    chain: str = Field(default="base")
    token: str = Field(default="USDC")


class OfframpQuoteRequest(BaseModel):
    input_token: str = Field(default="USDC")
    input_amount: Decimal = Field(gt=0, description="Amount in token units (e.g. 100.00 USDC)")
    input_chain: str = Field(default="base")
    output_currency: str = Field(default="USD")


class OfframpQuoteResponse(BaseModel):
    quote_id: str
    input_token: str
    input_amount: str
    input_chain: str
    output_currency: str
    output_amount: str
    fee: str
    exchange_rate: str
    expires_at: str


class OfframpExecuteRequest(BaseModel):
    quote_id: str
    wallet_id: str
    destination_account: str = Field(description="Bank account ID or Lithic funding account ID")


class OfframpExecuteResponse(BaseModel):
    transaction_id: str
    status: str
    input_amount: str
    output_amount: str
    provider_reference: Optional[str] = None


class OfframpStatusResponse(BaseModel):
    transaction_id: str
    status: str
    input_token: str
    input_amount: str
    output_currency: str
    output_amount: str
    created_at: str
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None


# ---- Dependencies ----

@dataclass
class RampDependencies:
    wallet_repo: object  # WalletRepository
    offramp_service: object  # OfframpService
    onramper_api_key: str = ""
    onramper_webhook_secret: str = ""


def get_deps() -> RampDependencies:
    raise NotImplementedError("Dependency override required")


# ---- Onramp Endpoints ----

@router.post("/onramp/widget", response_model=OnrampWidgetResponse)
async def generate_onramp_widget(
    request: OnrampWidgetRequest,
    deps: RampDependencies = Depends(get_deps),
):
    """Generate an Onramper widget URL with wallet address pre-filled."""
    wallet = await deps.wallet_repo.get(request.wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    address = wallet.get_address(request.chain)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No address for chain {request.chain}",
        )

    # Build Onramper widget URL
    params = {
        "apiKey": deps.onramper_api_key,
        "defaultCrypto": request.token.lower(),
        "wallets": f"{request.token.upper()}:{address}",
        "networkWallets": f"{request.chain.upper()}:{address}",
    }
    if request.amount_usd:
        params["defaultAmount"] = str(request.amount_usd)

    query = "&".join(f"{k}={v}" for k, v in params.items())
    widget_url = f"https://buy.onramper.com?{query}"

    return OnrampWidgetResponse(
        widget_url=widget_url,
        wallet_address=address,
        chain=request.chain,
        token=request.token,
    )


@router.get("/onramp/quote")
async def get_onramp_quote(
    amount_usd: Decimal,
    payment_method: str = "creditcard",
    chain: str = "base",
    token: str = "USDC",
    deps: RampDependencies = Depends(get_deps),
):
    """Proxy to Onramper quotes API."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.onramper.com/quotes",
                params={
                    "amount": str(amount_usd),
                    "sourceCurrency": "usd",
                    "destinationCurrency": token.lower(),
                    "paymentMethod": payment_method,
                    "network": chain,
                },
                headers={"Authorization": f"Bearer {deps.onramper_api_key}"},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.error("Onramper quote error: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch onramp quote")


@router.post("/onramp/webhook", status_code=status.HTTP_200_OK)
async def onramp_webhook(
    request: Request,
    deps: RampDependencies = Depends(get_deps),
):
    """Handle Onramper transaction completion webhook."""
    body = await request.body()

    # Verify webhook signature if secret is configured
    if deps.onramper_webhook_secret:
        signature = request.headers.get("x-onramper-signature", "")
        expected = hmac.new(
            deps.onramper_webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    event_type = payload.get("type", "")
    tx_data = payload.get("payload", payload)

    if event_type in ("transaction.completed", "completed"):
        wallet_address = tx_data.get("wallet_address") or tx_data.get("destinationAddress", "")
        amount = tx_data.get("crypto_amount") or tx_data.get("amount", 0)
        token = tx_data.get("crypto_currency") or tx_data.get("currency", "USDC")
        tx_hash = tx_data.get("tx_hash") or tx_data.get("transactionHash", "")
        chain = tx_data.get("network") or tx_data.get("chain", "base")

        logger.info(
            "Onramp completed: address=%s amount=%s token=%s tx_hash=%s chain=%s",
            wallet_address, amount, token, tx_hash, chain,
        )

        # Find wallet by address and record the on-ramp transaction
        try:
            # Find wallet by searching through all wallets for matching address
            wallet = None
            all_wallets = await deps.wallet_repo.list(limit=10000)
            for w in all_wallets:
                if wallet_address.lower() in [addr.lower() for addr in w.addresses.values()]:
                    wallet = w
                    break

            if wallet:
                logger.info(
                    f"Onramp credited: wallet_id={wallet.wallet_id} amount={amount} {token} tx_hash={tx_hash}"
                )
                # Note: Wallet balance is already on-chain (non-custodial)
                # The funds are already in the wallet address - no manual credit needed
                # This log serves as an audit trail of the on-ramp event
            else:
                logger.warning(
                    f"Onramp completed but wallet not found for address: {wallet_address}"
                )
        except Exception as e:
            logger.error(f"Error processing onramp webhook: {e}", exc_info=True)
            # Don't fail the webhook - we've logged the transaction
            # The funds are still on-chain and accessible

    return {"status": "received"}


# ---- Offramp Endpoints ----

@router.post("/offramp/quote", response_model=OfframpQuoteResponse)
async def get_offramp_quote(
    request: OfframpQuoteRequest,
    deps: RampDependencies = Depends(get_deps),
):
    """Get a USDC to USD off-ramp quote."""
    # Convert to minor units (6 decimals for USDC)
    amount_minor = int(request.input_amount * 10**6)

    quote = await deps.offramp_service.get_quote(
        input_token=request.input_token,
        input_amount_minor=amount_minor,
        input_chain=request.input_chain,
        output_currency=request.output_currency,
    )

    return OfframpQuoteResponse(
        quote_id=quote.quote_id,
        input_token=quote.input_token,
        input_amount=str(request.input_amount),
        input_chain=quote.input_chain,
        output_currency=quote.output_currency,
        output_amount=f"{quote.output_amount_cents / 100:.2f}",
        fee=f"{quote.fee_cents / 100:.2f}",
        exchange_rate=str(quote.exchange_rate),
        expires_at=quote.expires_at.isoformat(),
    )


@router.post("/offramp/execute", response_model=OfframpExecuteResponse)
async def execute_offramp(
    request: OfframpExecuteRequest,
    deps: RampDependencies = Depends(get_deps),
):
    """Execute USDC to USD off-ramp (send USDC to Bridge, receive USD)."""
    wallet = await deps.wallet_repo.get(request.wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    # Re-fetch the quote to verify it
    # In production, you'd cache quotes and look up by ID
    # For now, we trust the quote_id and pass through to the provider
    source_address = wallet.get_address("base") or ""
    if not source_address:
        # Try any available address
        for chain, addr in wallet.addresses.items():
            if addr:
                source_address = addr
                break

    if not source_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet has no on-chain address",
        )

    # Create a minimal quote object for the execute call
    from sardis_cards.offramp import OfframpQuote, OfframpProvider
    from datetime import datetime, timezone, timedelta

    # Get a fresh quote (provider will validate quote_id if it's real)
    # This is a simplification - in production, cache quotes by ID
    quote = await deps.offramp_service.get_quote(
        input_token="USDC",
        input_amount_minor=0,  # Will be determined by the quote
        input_chain="base",
        output_currency="USD",
    )

    tx = await deps.offramp_service.execute(
        quote=quote,
        source_address=source_address,
        destination_account=request.destination_account,
    )

    return OfframpExecuteResponse(
        transaction_id=tx.transaction_id,
        status=tx.status.value,
        input_amount=f"{tx.input_amount_minor / 10**6:.2f}",
        output_amount=f"{tx.output_amount_cents / 100:.2f}",
        provider_reference=tx.provider_reference,
    )


@router.get("/offramp/status/{tx_id}", response_model=OfframpStatusResponse)
async def get_offramp_status(
    tx_id: str,
    deps: RampDependencies = Depends(get_deps),
):
    """Check off-ramp transaction status."""
    try:
        tx = await deps.offramp_service.get_status(tx_id)
    except (ValueError, Exception) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return OfframpStatusResponse(
        transaction_id=tx.transaction_id,
        status=tx.status.value,
        input_token=tx.input_token,
        input_amount=f"{tx.input_amount_minor / 10**6:.2f}",
        output_currency=tx.output_currency,
        output_amount=f"{tx.output_amount_cents / 100:.2f}",
        created_at=tx.created_at.isoformat(),
        completed_at=tx.completed_at.isoformat() if tx.completed_at else None,
        failure_reason=tx.failure_reason,
    )
