"""Fiat-to-crypto onramp API — wallet funding via Turnkey, Stripe, and Coinbase.

Provides endpoints for:
  1. Generic onramp session (``POST /onramp/session``) — Stripe → Coinbase fallback.
  2. Wallet-specific funding via Turnkey native onramp:
     - ``POST /wallets/{wallet_id}/fund``       — initiate onramp
     - ``GET  /wallets/{wallet_id}/fund/status/{session_id}`` — check status

Turnkey onramp supports Coinbase and MoonPay as providers with no redirects
(embedded in-app).  Provider API keys must be pre-uploaded to the Turnkey
dashboard.

References:
  - https://docs.turnkey.com/api-reference/activities/init-fiat-on-ramp
  - https://docs.stripe.com/crypto/onramp
"""
from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Legacy generic onramp models (Stripe / Coinbase)
# ---------------------------------------------------------------------------


class CreateOnrampRequest(BaseModel):
    wallet_address: str = Field(..., description="Destination wallet address")
    amount: str | None = Field(default=None, description="Fiat amount (e.g. '50.00')")
    currency: str = Field(default="usd", description="Fiat currency")
    crypto_currency: str = Field(default="usdc", description="Target crypto (usdc, eth)")
    network: str = Field(default="base", description="Destination network")
    mode: str = Field(default="embedded", description="embedded or hosted")


class OnrampResponse(BaseModel):
    session_id: str
    provider: str  # stripe, coinbase, turnkey_coinbase, turnkey_moonpay
    client_secret: str | None = None  # For Stripe embedded
    url: str | None = None  # For hosted mode or Coinbase
    status: str
    created_at: str


# ---------------------------------------------------------------------------
# Turnkey wallet-fund models
# ---------------------------------------------------------------------------


class WalletFundRequest(BaseModel):
    """Request body for ``POST /wallets/{wallet_id}/fund``."""

    amount: str | None = Field(
        default=None,
        description="Fiat amount as string (e.g. '100'). Must exceed 20 per Turnkey rules. "
        "If omitted, the user chooses the amount in the onramp widget.",
    )
    currency: str = Field(default="USD", description="ISO 4217 fiat currency code")
    provider: Literal["coinbase", "moonpay"] = Field(
        default="coinbase",
        description="Onramp provider: 'coinbase' or 'moonpay'",
    )
    crypto_currency: str = Field(default="usdc", description="Target crypto (usdc, eth, sol, btc)")
    network: str | None = Field(
        default=None,
        description="Target chain: 'base' (default), 'ethereum', 'solana', 'bitcoin'. "
        "Omit to use the platform default.",
    )
    country_code: str | None = Field(
        default=None,
        description="ISO 3166-1 alpha-2 country code (optional)",
    )
    country_subdivision_code: str | None = Field(
        default=None,
        description="ISO 3166-2 subdivision code (required if US)",
    )


class WalletFundResponse(BaseModel):
    """Response for ``POST /wallets/{wallet_id}/fund``."""

    session_id: str = Field(description="Turnkey activity ID")
    widget_url: str = Field(description="Embeddable onramp URL (no redirect needed)")
    transaction_id: str = Field(description="Turnkey onramp transaction ID for status polling")
    provider: str = Field(description="'coinbase' or 'moonpay'")
    target_chain: str = Field(description="Resolved target chain (e.g. 'base')")
    target_token: str = Field(description="Resolved target token (e.g. 'USDC')")
    wallet_id: str
    wallet_address: str
    status: str = "created"
    created_at: str


class WalletFundStatusResponse(BaseModel):
    """Response for ``GET /wallets/{wallet_id}/fund/status/{session_id}``."""

    session_id: str
    transaction_id: str
    status: str
    wallet_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_turnkey_onramp_service():
    """Lazily build a TurnkeyOnrampService from env vars.

    Returns ``None`` if Turnkey is not configured.
    """
    api_key = os.getenv("TURNKEY_API_PUBLIC_KEY") or os.getenv("TURNKEY_API_KEY")
    api_private = os.getenv("TURNKEY_API_PRIVATE_KEY")
    org_id = os.getenv("TURNKEY_ORGANIZATION_ID")

    if not (api_key and api_private and org_id):
        return None

    try:
        from sardis_wallet.turnkey_client import TurnkeyClient

        from sardis_api.services.turnkey_onramp import TurnkeyOnrampService

        client = TurnkeyClient(
            api_key=api_key,
            api_private_key=api_private,
            organization_id=org_id,
        )
        return TurnkeyOnrampService(turnkey_client=client)
    except Exception as exc:
        logger.warning("Failed to initialise TurnkeyOnrampService: %s", exc)
        return None


async def _resolve_wallet_address(wallet_id: str) -> str:
    """Resolve a Sardis wallet ID to its primary EVM address.

    Falls back to treating ``wallet_id`` as a raw address if it looks like one.
    """
    if wallet_id.startswith("0x") and len(wallet_id) == 42:
        return wallet_id

    try:
        from sardis_v2_core import WalletRepository
        from sardis_v2_core.database import Database

        db = Database.get_pool()
        if db is None:
            raise RuntimeError("Database pool not available")
        repo = WalletRepository(db)
        wallet = await repo.get(wallet_id)
        if wallet is None:
            raise ValueError(f"Wallet {wallet_id} not found")
        # Prefer base address, then first available EVM address
        addresses: dict = getattr(wallet, "addresses", {}) or {}
        for chain in ("base", "base_sepolia", "ethereum", "polygon", "arbitrum", "optimism"):
            if chain in addresses and addresses[chain]:
                return addresses[chain]
        # Last resort: any address value
        if addresses:
            return next(iter(addresses.values()))
        raise ValueError(f"Wallet {wallet_id} has no EVM address")
    except ImportError:
        logger.warning("sardis_v2_core not available; treating wallet_id as address")
        return wallet_id
    except Exception:
        raise


# ---------------------------------------------------------------------------
# Endpoints — Legacy generic onramp
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Endpoints — Turnkey wallet fund
# ---------------------------------------------------------------------------


@router.post(
    "/wallets/{wallet_id}/fund",
    response_model=WalletFundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Fund a wallet via Turnkey native onramp",
    tags=["wallets", "onramp"],
)
async def fund_wallet(
    wallet_id: str,
    req: WalletFundRequest,
    principal: Principal = Depends(require_principal),
) -> WalletFundResponse:
    """Initiate a fiat-to-crypto onramp for a specific wallet.

    Uses Turnkey's native ``init_fiat_on_ramp`` activity with Coinbase or MoonPay
    as the provider.  The response includes an embeddable ``widget_url`` — no
    redirects are required.

    **Provider API keys** must be pre-uploaded to the Turnkey dashboard.
    """
    svc = _get_turnkey_onramp_service()
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Turnkey onramp not configured. Ensure TURNKEY_API_KEY, "
                "TURNKEY_API_PRIVATE_KEY, and TURNKEY_ORGANIZATION_ID are set, "
                "and that provider credentials are uploaded to the Turnkey dashboard."
            ),
        )

    # Resolve the wallet's EVM address
    try:
        wallet_address = await _resolve_wallet_address(wallet_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Failed to resolve wallet address for %s: %s", wallet_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve wallet address",
        )

    # Determine sandbox mode from environment
    sandbox = os.getenv("SARDIS_ENVIRONMENT", "dev") != "production"

    try:
        session = await svc.create_onramp_session(
            wallet_address=wallet_address,
            amount_usd=req.amount,
            currency=req.currency,
            provider=req.provider,
            network=req.network,
            crypto_currency=req.crypto_currency,
            country_code=req.country_code,
            country_subdivision_code=req.country_subdivision_code,
            sandbox=sandbox,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Turnkey onramp session creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create onramp session with Turnkey",
        )

    return WalletFundResponse(
        session_id=session.session_id,
        widget_url=session.onramp_url,
        transaction_id=session.transaction_id,
        provider=session.provider,
        target_chain=session.target_chain,
        target_token=session.target_token,
        wallet_id=wallet_id,
        wallet_address=wallet_address,
        status="created",
        created_at=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/wallets/{wallet_id}/fund/status/{session_id}",
    response_model=WalletFundStatusResponse,
    summary="Check onramp funding status",
    tags=["wallets", "onramp"],
)
async def fund_wallet_status(
    wallet_id: str,
    session_id: str,
    refresh: bool = False,
    principal: Principal = Depends(require_principal),
) -> WalletFundStatusResponse:
    """Check the status of a Turnkey onramp transaction.

    Pass ``refresh=true`` to force a status refresh from the provider
    (Coinbase / MoonPay).  Otherwise the cached status is returned.

    The ``session_id`` is the ``transaction_id`` returned by
    ``POST /wallets/{wallet_id}/fund``.
    """
    svc = _get_turnkey_onramp_service()
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Turnkey onramp not configured.",
        )

    try:
        tx_status = await svc.get_transaction_status(
            transaction_id=session_id,
            refresh=refresh,
        )
    except Exception as exc:
        logger.error("Turnkey onramp status check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to query onramp transaction status",
        )

    return WalletFundStatusResponse(
        session_id=session_id,
        transaction_id=tx_status.transaction_id,
        status=tx_status.status,
        wallet_id=wallet_id,
    )
