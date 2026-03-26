"""Fiat-to-crypto onramp API — wallet funding via Turnkey, Stripe, Coinbase, and Conduit.

Provides endpoints for:
  1. Generic onramp session (``POST /onramp/session``) — Stripe → Coinbase fallback.
  2. Wallet-specific funding via Turnkey native onramp:
     - ``POST /wallets/{wallet_id}/fund``       — initiate onramp
     - ``GET  /wallets/{wallet_id}/fund/status/{session_id}`` — check status
  3. Conduit Pay onramp (fiat → USDC direct to Tempo, no bridge):
     - ``POST /wallets/{wallet_id}/fund`` with ``provider="conduit"``
     - ``GET  /wallets/{wallet_id}/fund/status/{session_id}`` — check status

Turnkey onramp supports Coinbase and MoonPay as providers with no redirects
(embedded in-app).  Provider API keys must be pre-uploaded to the Turnkey
dashboard.

Conduit Pay is Tempo's official onramp partner.  USDC arrives natively on
Tempo — no bridge required.  Requires ``CONDUIT_API_KEY`` and
``CONDUIT_API_SECRET`` env vars.

References:
  - https://docs.turnkey.com/api-reference/activities/init-fiat-on-ramp
  - https://docs.stripe.com/crypto/onramp
  - https://docs.conduit.financial/api-reference/introduction
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
    provider: Literal["coinbase", "moonpay", "conduit"] = Field(
        default="coinbase",
        description="Onramp provider: 'coinbase', 'moonpay', or 'conduit' (direct to Tempo)",
    )
    crypto_currency: str = Field(default="usdc", description="Target crypto (usdc, eth, sol, btc)")
    network: str | None = Field(
        default=None,
        description="Target chain: 'base' (default), 'ethereum', 'solana', 'bitcoin', 'tempo'. "
        "Defaults to 'base' for Coinbase/MoonPay, 'tempo' for Conduit. "
        "Omit to use the platform default.",
    )
    target_chain: str | None = Field(
        default=None,
        description="Alias for 'network'. If both are set, 'target_chain' takes precedence.",
    )
    country_code: str | None = Field(
        default=None,
        description="ISO 3166-1 alpha-2 country code (optional)",
    )
    country_subdivision_code: str | None = Field(
        default=None,
        description="ISO 3166-2 subdivision code (required if US)",
    )
    conduit_customer_id: str | None = Field(
        default=None,
        description="Conduit customer ID (required for Conduit provider if pre-registered). "
        "Omit to auto-create a customer.",
    )
    conduit_source_payment_method_id: str | None = Field(
        default=None,
        description="Conduit source payment method ID (bank account). "
        "Required for Conduit provider to execute the onramp.",
    )


class WalletFundResponse(BaseModel):
    """Response for ``POST /wallets/{wallet_id}/fund``."""

    session_id: str = Field(description="Turnkey activity ID or Conduit transaction ID")
    widget_url: str = Field(
        default="",
        description="Embeddable onramp URL (no redirect needed). Empty for Conduit.",
    )
    transaction_id: str = Field(description="Onramp transaction ID for status polling")
    provider: str = Field(description="'coinbase', 'moonpay', or 'conduit'")
    target_chain: str = Field(description="Resolved target chain (e.g. 'base', 'tempo')")
    target_token: str = Field(description="Resolved target token (e.g. 'USDC')")
    wallet_id: str
    wallet_address: str
    status: str = "created"
    created_at: str
    # Conduit-specific fields
    quote_id: str | None = Field(default=None, description="Conduit quote ID (Conduit only)")
    source_amount: str | None = Field(default=None, description="Fiat amount charged")
    target_amount: str | None = Field(default=None, description="Crypto amount to receive")
    deposit_instructions: dict | None = Field(
        default=None,
        description="Deposit instructions for completing the onramp (Conduit only)",
    )


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


def _get_conduit_onramp_service():
    """Lazily build a ConduitOnrampService from env vars.

    Returns ``None`` if Conduit is not configured.
    """
    try:
        from sardis_api.services.conduit_onramp import get_conduit_service

        return get_conduit_service()
    except Exception as exc:
        logger.warning("Failed to initialise ConduitOnrampService: %s", exc)
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

        db = await Database.get_pool()
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
    summary="Fund a wallet via fiat onramp",
    tags=["wallets", "onramp"],
)
async def fund_wallet(
    wallet_id: str,
    req: WalletFundRequest,
    principal: Principal = Depends(require_principal),
) -> WalletFundResponse:
    """Initiate a fiat-to-crypto onramp for a specific wallet.

    **Providers:**

    - ``coinbase`` / ``moonpay``: Uses Turnkey's native ``init_fiat_on_ramp``
      activity.  Returns an embeddable ``widget_url``.
    - ``conduit``: Uses Conduit Pay for direct fiat → USDC settlement on Tempo.
      No bridge required — USDC arrives natively on Tempo (chain ID 4217).
      Requires ``CONDUIT_API_KEY`` and ``CONDUIT_API_SECRET`` env vars.
    """
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

    # ------------------------------------------------------------------
    # Conduit provider path — direct to Tempo
    # ------------------------------------------------------------------
    if req.provider == "conduit":
        return await _fund_wallet_conduit(wallet_id, wallet_address, req)

    # ------------------------------------------------------------------
    # Turnkey provider path (coinbase / moonpay)
    # ------------------------------------------------------------------
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

    # Determine sandbox mode from environment
    sandbox = os.getenv("SARDIS_ENVIRONMENT", "dev") != "production"

    # Resolve target network — default to 'base' for Turnkey providers
    # (Tempo is not supported by Turnkey/Coinbase/MoonPay onramp)
    resolved_network = (req.target_chain or req.network or "base").lower()
    if resolved_network == "tempo":
        logger.info("Turnkey onramp does not support Tempo; falling back to 'base'")
        resolved_network = "base"

    try:
        session = await svc.create_onramp_session(
            wallet_address=wallet_address,
            amount_usd=req.amount,
            currency=req.currency,
            provider=req.provider,
            network=resolved_network,
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


async def _fund_wallet_conduit(
    wallet_id: str,
    wallet_address: str,
    req: WalletFundRequest,
) -> WalletFundResponse:
    """Handle the Conduit provider path for fund_wallet.

    Flow: get_quote → create_onramp_transaction.
    The wallet payment method and customer are assumed to be pre-registered
    via the ``conduit_customer_id`` and ``conduit_source_payment_method_id``
    fields in the request.  If not provided, only the quote step is executed
    and the deposit instructions are returned for the caller to complete.
    """
    from sardis_api.services.conduit_onramp import ConduitAPIError

    conduit_svc = _get_conduit_onramp_service()
    if conduit_svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Conduit onramp not configured. Ensure CONDUIT_API_KEY and "
                "CONDUIT_API_SECRET environment variables are set."
            ),
        )

    if not req.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount is required for Conduit onramp.",
        )

    # Resolve target chain — default to Tempo for Conduit
    target_chain = (req.target_chain or req.network or "tempo").lower()

    try:
        # Step 1: Get a quote
        quote = await conduit_svc.get_quote(
            amount_usd=req.amount,
            target_asset=req.crypto_currency.upper(),
            target_network=target_chain,
            source_currency=req.currency,
        )

        # Step 2: If source payment method is provided, execute the transaction
        tx_id = ""
        tx_status = "quote_ready"
        deposit_instructions = None

        if req.conduit_source_payment_method_id:
            # Create a wallet payment method for the destination if not already done
            # (in production, this would be pre-registered)
            dest_pm = await conduit_svc.create_wallet_payment_method(
                customer_id=req.conduit_customer_id or "",
                wallet_address=wallet_address,
                network=target_chain,
                asset=req.crypto_currency.upper(),
            )

            tx = await conduit_svc.create_onramp_transaction(
                quote_id=quote.quote_id,
                source_payment_method_id=req.conduit_source_payment_method_id,
                destination_payment_method_id=dest_pm.payment_method_id,
                reference=f"sardis_{wallet_id}",
            )
            tx_id = tx.transaction_id
            tx_status = tx.status
            deposit_instructions = tx.deposit_instructions
        else:
            tx_id = quote.quote_id  # Use quote ID as session reference

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except ConduitAPIError as exc:
        logger.error("Conduit onramp failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Conduit API error: {exc.detail}",
        )
    except Exception as exc:
        logger.error("Conduit onramp unexpected error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create onramp session with Conduit",
        )

    return WalletFundResponse(
        session_id=tx_id,
        widget_url="",  # Conduit does not use a widget
        transaction_id=tx_id,
        provider="conduit",
        target_chain=target_chain,
        target_token=quote.target_asset,
        wallet_id=wallet_id,
        wallet_address=wallet_address,
        status=tx_status,
        created_at=datetime.now(UTC).isoformat(),
        quote_id=quote.quote_id,
        source_amount=quote.source_amount,
        target_amount=quote.target_amount,
        deposit_instructions=deposit_instructions,
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
    provider: str | None = None,
    principal: Principal = Depends(require_principal),
) -> WalletFundStatusResponse:
    """Check the status of an onramp transaction.

    Pass ``refresh=true`` to force a status refresh from the provider.
    Pass ``provider=conduit`` to query Conduit instead of Turnkey.

    The ``session_id`` is the ``transaction_id`` returned by
    ``POST /wallets/{wallet_id}/fund``.
    """
    # Conduit path
    if provider == "conduit":
        conduit_svc = _get_conduit_onramp_service()
        if conduit_svc is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Conduit onramp not configured.",
            )
        try:
            tx_status = await conduit_svc.get_transaction_status(session_id)
        except Exception as exc:
            logger.error("Conduit status check failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to query Conduit transaction status",
            )
        return WalletFundStatusResponse(
            session_id=session_id,
            transaction_id=tx_status.transaction_id,
            status=tx_status.status,
            wallet_id=wallet_id,
        )

    # Turnkey path (default)
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
