"""Stripe Crypto Onramp API — fiat-to-crypto wallet funding.

Provides endpoints for creating Stripe crypto onramp sessions
to fund agent wallets with stablecoins. Falls back to Coinbase
Onramp if Stripe is unavailable.

Reference: https://docs.stripe.com/crypto/onramp
"""
from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


class CreateOnrampRequest(BaseModel):
    wallet_address: str = Field(..., description="Destination wallet address")
    amount: str | None = Field(default=None, description="Fiat amount (e.g. '50.00')")
    currency: str = Field(default="usd", description="Fiat currency")
    crypto_currency: str = Field(default="usdc", description="Target crypto (usdc, eth)")
    network: str = Field(default="base", description="Destination network")
    mode: str = Field(default="embedded", description="embedded or hosted")


class OnrampResponse(BaseModel):
    session_id: str
    provider: str  # stripe or coinbase
    client_secret: str | None = None  # For Stripe embedded
    url: str | None = None  # For hosted mode or Coinbase
    status: str
    created_at: str


@router.post(
    "/onramp/session",
    response_model=OnrampResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a crypto onramp session",
)
async def create_onramp_session(
    req: CreateOnrampRequest,
    principal: Principal = Depends(require_principal),
) -> OnrampResponse:
    """Create a fiat-to-crypto onramp session.

    Uses Stripe crypto onramp (primary) with Coinbase Onramp fallback.
    """
    stripe_key = os.getenv("STRIPE_SECRET_KEY")

    # Try Stripe crypto onramp first
    if stripe_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.stripe.com/v1/crypto/onramp_sessions",
                    auth=(stripe_key, ""),
                    headers={"Stripe-Version": "2026-03-04.preview"},
                    data={
                        "wallet_addresses[ethereum]": req.wallet_address,
                        "destination_currency": req.crypto_currency,
                        "destination_network": req.network,
                        **({"source_amount": req.amount} if req.amount else {}),
                        "source_currency": req.currency,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return OnrampResponse(
                        session_id=data.get("id", ""),
                        provider="stripe",
                        client_secret=data.get("client_secret"),
                        url=data.get("redirect_url"),
                        status="created",
                        created_at=datetime.now(UTC).isoformat(),
                    )
                logger.warning("Stripe onramp returned %d: %s", resp.status_code, resp.text)
        except Exception as e:
            logger.warning("Stripe onramp failed: %s", e)

    # Fallback: Coinbase Onramp (hosted)
    coinbase_app_id = os.getenv("COINBASE_APP_ID", "sardis")
    from uuid import uuid4
    session_id = f"onramp_{uuid4().hex[:12]}"

    coinbase_url = (
        f"https://pay.coinbase.com/buy/select-asset"
        f"?appId={coinbase_app_id}"
        f"&addresses={{'0x{req.wallet_address[2:]}':['base']}}"
        f"&defaultAssetCode=USDC"
    )

    return OnrampResponse(
        session_id=session_id,
        provider="coinbase",
        client_secret=None,
        url=coinbase_url,
        status="created",
        created_at=datetime.now(UTC).isoformat(),
    )
