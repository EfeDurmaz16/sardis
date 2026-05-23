"""Fiat-to-crypto onramp API — wallet funding via Turnkey, Stripe, Coinbase, and Conduit.

Provides endpoints for:
  1. Generic onramp session (``POST /onramp/session``) — Stripe → Coinbase fallback.
  2. Wallet-specific funding via Turnkey native onramp:
     - ``POST /wallets/{wallet_id}/fund``       — initiate onramp
     - ``GET  /wallets/{wallet_id}/fund/status/{session_id}`` — check status
  3. Conduit Pay onramp (fiat → USDC direct to Tempo, no bridge):
     - ``POST /wallets/{wallet_id}/fund`` with ``provider="conduit"``
     - ``GET  /wallets/{wallet_id}/fund/status/{session_id}`` — check status
  4. Stripe Crypto Onramp — dedicated session + hosted-link endpoints:
     - ``POST /onramp/stripe/session``          — create Stripe onramp session
     - ``GET  /onramp/stripe/link/{wallet_id}`` — hosted redirect link
  5. Stripe Crypto Onramp webhook:
     - ``POST /webhooks/stripe-onramp``          — handle status updates

Turnkey onramp supports Coinbase and MoonPay as providers with no redirects
(embedded in-app).  Provider API keys must be pre-uploaded to the Turnkey
dashboard.

Conduit Pay is Tempo's official onramp partner.  USDC arrives natively on
Tempo — no bridge required.  Requires ``CONDUIT_API_KEY`` and
``CONDUIT_API_SECRET`` env vars.

References:
  - https://docs.turnkey.com/api-reference/activities/init-fiat-on-ramp
  - https://docs.stripe.com/crypto/onramp
  - https://docs.stripe.com/api/crypto/onramp_sessions/create
  - https://docs.conduit.financial/api-reference/introduction
"""
from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import logging
import os
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from server.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
# Separate router for webhook (no auth — Stripe signs the payload)
webhook_router = APIRouter(tags=["stripe-onramp-webhooks"])
logger = logging.getLogger(__name__)

# Chain name → Stripe network name mapping
_CHAIN_TO_STRIPE_NETWORK: dict[str, str] = {
    "base": "base",
    "base_sepolia": "base",
    "ethereum": "ethereum",
    "polygon": "polygon",
    "arbitrum": "ethereum",  # Stripe doesn't have separate arbitrum network
    "optimism": "ethereum",  # Stripe doesn't have separate optimism network
    "solana": "solana",
}

# Stripe wallet_addresses keys differ from network names
_STRIPE_WALLET_ADDRESS_KEYS: dict[str, str] = {
    "base": "ethereum",       # Base uses ethereum wallet key (same EVM address)
    "ethereum": "ethereum",
    "polygon": "polygon",
    "solana": "solana",
    "stellar": "stellar",
    "bitcoin": "bitcoin",
    "avalanche": "avalanche",
}


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
        from sardis.wallet.turnkey_client import TurnkeyClient

        from server.services.turnkey_onramp import TurnkeyOnrampService

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
        from server.services.conduit_onramp import get_conduit_service

        return get_conduit_service()
    except Exception as exc:
        logger.warning("Failed to initialise ConduitOnrampService: %s", exc)
        return None


async def _resolve_wallet_address(wallet_id: str) -> str:
    """Resolve a Sardis wallet ID to its primary EVM address.

    Falls back to treating ``wallet_id`` as a raw address if it looks like one.
    For wallets with empty addresses (created before Turnkey fix), attempts
    to provision an address on-the-fly via Turnkey.
    """
    if wallet_id.startswith("0x") and len(wallet_id) == 42:
        return wallet_id

    try:
        from sardis.core import WalletRepository
        from sardis.core.database import Database

        db = await Database.get_pool()
        if db is None:
            raise RuntimeError("Database pool not available")
        repo = WalletRepository(db)
        wallet = await repo.get(wallet_id)
        if wallet is None:
            raise ValueError(f"Wallet {wallet_id} not found")
        # Prefer base address, then first available EVM address
        addresses: dict = getattr(wallet, "addresses", {}) or {}
        for chain in ("base", "base_sepolia", "ethereum", "polygon", "arbitrum", "optimism", "tempo"):
            if chain in addresses and addresses[chain]:
                return addresses[chain]
        # Last resort: any address value
        if addresses:
            first_val = next(iter(addresses.values()), None)
            if first_val:
                return first_val

        # ---------------------------------------------------------------
        # Wallet has no addresses at all (created before Turnkey fix).
        # Try to provision an address on-the-fly via Turnkey.
        # ---------------------------------------------------------------
        logger.warning(
            "Wallet %s has no stored addresses; attempting Turnkey address provision",
            wallet_id,
        )
        try:
            provisioned = await _provision_wallet_address(wallet_id, wallet, repo)
            if provisioned:
                return provisioned
        except Exception as prov_exc:
            logger.warning("On-the-fly address provision failed for %s: %s", wallet_id, prov_exc)

        raise ValueError(f"Wallet {wallet_id} has no EVM address")
    except ImportError:
        logger.warning("sardis.core not available; treating wallet_id as address")
        return wallet_id
    except Exception:
        raise


async def _provision_wallet_address(
    wallet_id: str,
    wallet: object,
    repo: object,
) -> str | None:
    """Attempt to get an address from Turnkey for a wallet with no stored addresses.

    Turnkey creates one Ethereum key that works on all EVM chains.
    If successful, persists the address under 'base' and returns it.
    """
    api_key = os.getenv("TURNKEY_API_PUBLIC_KEY") or os.getenv("TURNKEY_API_KEY")
    api_private = os.getenv("TURNKEY_API_PRIVATE_KEY")
    org_id = os.getenv("TURNKEY_ORGANIZATION_ID")

    if not (api_key and api_private and org_id):
        return None

    try:
        from sardis.wallet.turnkey_client import TurnkeyClient

        client = TurnkeyClient(
            api_key=api_key,
            api_private_key=api_private,
            organization_id=org_id,
        )

        # Try to get wallet accounts from Turnkey using the wallet_id
        # The wallet_id might be stored as a Turnkey wallet ID or we may
        # need to query by sub-organization
        tk_wallet_id = getattr(wallet, "turnkey_wallet_id", None) or wallet_id

        # Attempt to get accounts for this wallet
        accounts = await client.get_wallet_accounts(tk_wallet_id)
        if accounts:
            for acct in accounts:
                addr = getattr(acct, "address", None) or acct.get("address", None) if isinstance(acct, dict) else None
                if addr and addr.startswith("0x"):
                    # Persist the address for future use
                    try:
                        if hasattr(wallet, "set_address") and hasattr(repo, "update"):
                            wallet.set_address("base", addr)
                            await repo.update(wallet)
                            logger.info("Provisioned address %s for wallet %s", addr, wallet_id)
                    except Exception as persist_exc:
                        logger.warning("Failed to persist provisioned address: %s", persist_exc)
                    return addr
    except Exception as exc:
        logger.debug("Turnkey address provision attempt failed: %s", exc)

    return None


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
    # Env var compatibility: production backend exposes the key as
    # STRIPE_API_KEY (per gcloud secrets mapping), older local .env files
    # and tests use STRIPE_SECRET_KEY. Accept either so the Stripe crypto
    # onramp path actually runs instead of silently falling back to
    # Coinbase, which is what was happening in production — STRIPE_SECRET_KEY
    # was unset, the code skipped the entire Stripe block, and users saw
    # pay.coinbase.com every time they clicked "Add Funds".
    stripe_key = os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")

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
        logger.warning("Wallet not found for onramp %s: %s", wallet_id, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
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
        logger.warning("Invalid onramp parameters: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid onramp request parameters",
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
    from server.services.conduit_onramp import ConduitAPIError

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
        logger.warning("Invalid Conduit onramp parameters: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid onramp request parameters",
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


# ===========================================================================
# Stripe Crypto Onramp — dedicated endpoints
# ===========================================================================


class StripeOnrampSessionRequest(BaseModel):
    """Request body for ``POST /onramp/stripe/session``."""

    wallet_id: str = Field(
        ...,
        description="Sardis wallet ID (wal_...) or raw 0x address.",
    )
    amount: str | None = Field(
        default=None,
        description="Fiat amount in decimal (e.g. '50.00'). "
        "If omitted, user chooses the amount in the Stripe UI.",
    )
    chain: str | None = Field(
        default=None,
        description="Target chain: 'base' (default), 'ethereum', 'polygon', etc.",
    )
    destination_currency: str = Field(
        default="usdc",
        description="Crypto currency to purchase (usdc, eth, btc, etc.).",
    )
    source_currency: str = Field(
        default="usd",
        description="Fiat currency code (usd, eur, gbp).",
    )
    lock_wallet_address: bool = Field(
        default=True,
        description="Lock the wallet address so the user cannot change it.",
    )


class StripeOnrampSessionResponse(BaseModel):
    """Response for ``POST /onramp/stripe/session``."""

    session_id: str = Field(description="Stripe CryptoOnrampSession ID")
    client_secret: str = Field(description="Client secret for embedded onramp widget")
    redirect_url: str = Field(description="Stripe-hosted onramp URL")
    status: str = Field(description="Session status (initialized, etc.)")
    wallet_address: str = Field(description="Resolved wallet address")
    destination_network: str = Field(description="Resolved Stripe network name")
    created_at: str


class StripeOnrampLinkResponse(BaseModel):
    """Response for ``GET /onramp/stripe/link/{wallet_id}``."""

    url: str = Field(description="Stripe-hosted onramp redirect URL")
    wallet_address: str
    destination_network: str


class StripeOnrampWebhookEvent(BaseModel):
    """Parsed Stripe Crypto Onramp webhook event."""

    session_id: str
    status: str
    wallet_address: str | None = None
    destination_currency: str | None = None
    destination_network: str | None = None
    source_amount: str | None = None
    destination_amount: str | None = None
    transaction_id: str | None = None
    received_at: str


# ---------------------------------------------------------------------------
# Stripe Crypto Onramp — helpers
# ---------------------------------------------------------------------------


async def _create_stripe_onramp_session(
    *,
    wallet_address: str,
    chain: str,
    amount: str | None,
    destination_currency: str,
    source_currency: str,
    lock_wallet_address: bool,
    customer_ip: str | None,
) -> dict:
    """Call Stripe API to create a CryptoOnrampSession.

    Uses httpx directly — avoids hard dependency on the ``stripe`` SDK.

    Raises:
        HTTPException on Stripe API errors.
    """
    stripe_key = os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")
    if not stripe_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe API key not configured (set STRIPE_SECRET_KEY).",
        )

    stripe_network = _CHAIN_TO_STRIPE_NETWORK.get(chain.lower(), chain.lower())

    # Stripe wallet_addresses uses "ethereum" key for all EVM chains (Base, Polygon, etc.)
    wallet_key = _STRIPE_WALLET_ADDRESS_KEYS.get(stripe_network, "ethereum")

    # Build form-encoded body per Stripe API convention
    form_data: dict[str, str] = {
        f"wallet_addresses[{wallet_key}]": wallet_address,
        "destination_currencies[0]": destination_currency.lower(),
        "destination_currency": destination_currency.lower(),
        "destination_network": stripe_network,
        "source_currency": source_currency.lower(),
    }

    # Include the wallet's network AND ethereum (required for wallet_addresses[ethereum])
    networks = {stripe_network, "ethereum"} if wallet_key == "ethereum" else {stripe_network}
    for i, net in enumerate(sorted(networks)):
        form_data[f"destination_networks[{i}]"] = net

    if lock_wallet_address:
        form_data["lock_wallet_address"] = "true"
    if amount:
        form_data["source_amount"] = amount
    if customer_ip:
        form_data["customer_ip_address"] = customer_ip

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://api.stripe.com/v1/crypto/onramp_sessions",
            auth=(stripe_key, ""),
            data=form_data,
        )

    if resp.status_code != 200:
        detail = resp.text
        try:
            err = resp.json()
            detail = err.get("error", {}).get("message", resp.text)
        except Exception:
            pass
        logger.error(
            "Stripe onramp session creation failed (%d): %s",
            resp.status_code,
            detail,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe Crypto Onramp error: {detail}",
        )

    return resp.json()


def _get_client_ip(request: Request) -> str | None:
    """Best-effort extraction of the client IP from the request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return None


# ---------------------------------------------------------------------------
# POST /onramp/stripe/session — Create a Stripe Crypto Onramp session
# ---------------------------------------------------------------------------


@router.post(
    "/onramp/stripe/session",
    response_model=StripeOnrampSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Stripe Crypto Onramp session",
    tags=["onramp", "stripe"],
)
async def create_stripe_onramp_session(
    req: StripeOnrampSessionRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
) -> StripeOnrampSessionResponse:
    """Create a Stripe Crypto Onramp session for a Sardis wallet.

    The returned ``client_secret`` can be used with the embedded Stripe
    Onramp widget, and the ``redirect_url`` points to the Stripe-hosted
    onramp page.

    Requires ``STRIPE_SECRET_KEY`` (or ``STRIPE_API_KEY``) env var.
    """
    # Resolve wallet address
    try:
        wallet_address = await _resolve_wallet_address(req.wallet_id)
    except ValueError as exc:
        logger.warning("Wallet not found for Stripe onramp %s: %s", req.wallet_id, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
        )
    except Exception as exc:
        logger.error("Failed to resolve wallet for Stripe onramp: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve wallet address",
        )

    chain = (req.chain or "base").lower()
    customer_ip = _get_client_ip(request)

    data = await _create_stripe_onramp_session(
        wallet_address=wallet_address,
        chain=chain,
        amount=req.amount,
        destination_currency=req.destination_currency,
        source_currency=req.source_currency,
        lock_wallet_address=req.lock_wallet_address,
        customer_ip=customer_ip,
    )

    stripe_network = _CHAIN_TO_STRIPE_NETWORK.get(chain, chain)

    return StripeOnrampSessionResponse(
        session_id=data.get("id", ""),
        client_secret=data.get("client_secret", ""),
        redirect_url=data.get("redirect_url", ""),
        status=data.get("status", "initialized"),
        wallet_address=wallet_address,
        destination_network=stripe_network,
        created_at=datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /onramp/stripe/link/{wallet_id} — Stripe-hosted onramp link
# ---------------------------------------------------------------------------


@router.get(
    "/onramp/stripe/link/{wallet_id}",
    response_model=StripeOnrampLinkResponse,
    summary="Get a Stripe-hosted onramp link for a wallet",
    tags=["onramp", "stripe"],
)
async def get_stripe_onramp_link(
    wallet_id: str,
    chain: str = "base",
    destination_currency: str = "usdc",
    source_currency: str = "usd",
    amount: str | None = None,
    principal: Principal = Depends(require_principal),
) -> StripeOnrampLinkResponse:
    """Return a Stripe-hosted onramp URL (``crypto.link.com``) for a wallet.

    This constructs the URL with query parameters — no backend session is
    created.  For full control (locked wallet, embedded widget), use
    ``POST /onramp/stripe/session`` instead.

    The URL opens a Stripe-hosted page where the user can purchase crypto
    with a credit/debit card and have it delivered to their Sardis wallet.
    """
    try:
        wallet_address = await _resolve_wallet_address(wallet_id)
    except ValueError as exc:
        logger.warning("Wallet not found for Stripe link %s: %s", wallet_id, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
        )
    except Exception as exc:
        logger.error("Failed to resolve wallet for Stripe link: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve wallet address",
        )

    stripe_network = _CHAIN_TO_STRIPE_NETWORK.get(chain.lower(), chain.lower())

    # Build the crypto.link.com hosted URL with pre-filled params
    wallet_key = _STRIPE_WALLET_ADDRESS_KEYS.get(stripe_network, "ethereum")
    params: dict[str, str] = {
        "destination_currency": destination_currency.lower(),
        "destination_network": stripe_network,
        "source_currency": source_currency.lower(),
        f"wallet_addresses[{wallet_key}]": wallet_address,
    }
    if amount:
        params["source_amount"] = amount

    # For EVM chains, also add ethereum key if not already there
    if wallet_key == "ethereum":
        pass  # already set
    else:
        key = f"wallet_addresses[{wallet_key}]"
        if key not in params:
            params[key] = wallet_address

    url = f"https://crypto.link.com?{urlencode(params)}"

    return StripeOnrampLinkResponse(
        url=url,
        wallet_address=wallet_address,
        destination_network=stripe_network,
    )


# ===========================================================================
# Stripe Crypto Onramp — Webhook handler
# ===========================================================================


def _verify_stripe_onramp_signature(
    payload: bytes,
    signature: str,
    webhook_secret: str,
) -> bool:
    """Verify a Stripe webhook signature (HMAC-SHA256).

    The Stripe-Signature header has the format ``t=<timestamp>,v1=<sig>``.
    """
    try:
        sig_parts: dict[str, str] = {}
        for part in signature.split(","):
            key, value = part.split("=", 1)
            sig_parts[key] = value

        timestamp = sig_parts.get("t")
        expected_sig = sig_parts.get("v1")
        if not timestamp or not expected_sig:
            return False

        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        computed = hmac_mod.new(
            webhook_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac_mod.compare_digest(computed, expected_sig)
    except Exception as exc:
        logger.warning("Stripe onramp signature verification error: %s", exc)
        return False


@webhook_router.post(
    "/webhooks/stripe-onramp",
    status_code=status.HTTP_200_OK,
    summary="Handle Stripe Crypto Onramp webhook events",
    tags=["webhooks", "stripe-onramp"],
)
async def handle_stripe_onramp_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
) -> dict:
    """Receive ``crypto.onramp_session.updated`` events from Stripe.

    Stripe sends this event every time the status of an onramp session
    changes.  Statuses include:

    - ``initialized`` — session created, user hasn't started yet
    - ``rejected``    — Stripe KYC / fraud rejection
    - ``payment``     — user is on the payment page
    - ``processing``  — payment succeeded, crypto delivery in progress
    - ``fulfillment_complete`` — crypto delivered to wallet

    The webhook secret is read from ``STRIPE_ONRAMP_WEBHOOK_SECRET``.
    Falls back to ``STRIPE_WEBHOOK_SECRET`` if the onramp-specific one
    is not set.

    Returns 200 OK in all cases to prevent Stripe retries.  Errors are
    logged but do not surface to Stripe.
    """
    webhook_secret = (
        os.getenv("STRIPE_ONRAMP_WEBHOOK_SECRET")
        or os.getenv("STRIPE_WEBHOOK_SECRET")
    )

    payload = await request.body()

    # --- Signature verification ----------------------------------------
    if webhook_secret:
        if not stripe_signature:
            logger.warning("Stripe onramp webhook missing Stripe-Signature header")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe-Signature header",
            )

        # Prefer Stripe SDK if available
        verified_event: dict | None = None
        try:
            import stripe

            try:
                verified_event = stripe.Webhook.construct_event(
                    payload, stripe_signature, webhook_secret,
                )
            except stripe.error.SignatureVerificationError:
                logger.warning("Stripe onramp webhook: SDK signature verification failed")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid signature",
                )
        except ImportError:
            # Fallback: manual HMAC verification
            if not _verify_stripe_onramp_signature(payload, stripe_signature, webhook_secret):
                logger.warning("Stripe onramp webhook: manual signature verification failed")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid signature",
                )

        if verified_event is not None:
            event = verified_event
        else:
            event = json.loads(payload)
    else:
        # No webhook secret configured — accept in dev, warn loudly
        env = os.getenv("SARDIS_ENVIRONMENT", "dev").lower()
        if env not in ("dev", "development", "test"):
            logger.error(
                "STRIPE_ONRAMP_WEBHOOK_SECRET not set in %s environment — "
                "rejecting webhook",
                env,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook secret not configured",
            )
        logger.warning("Stripe onramp webhook: no secret configured (dev mode)")
        event = json.loads(payload)

    # --- Process the event ---------------------------------------------
    event_type = event.get("type", "")
    event_id = event.get("id", "")
    session_obj = event.get("data", {}).get("object", {})
    session_id = session_obj.get("id", "")
    session_status = session_obj.get("status", "")

    logger.info(
        "Stripe onramp webhook: type=%s event_id=%s session=%s status=%s",
        event_type,
        event_id,
        session_id,
        session_status,
    )

    if event_type not in (
        "crypto.onramp_session.updated",
        "crypto.onramp_session.completed",
    ):
        logger.debug("Ignoring non-onramp event type: %s", event_type)
        return {"received": True, "processed": False}

    # Extract transaction details
    tx_details = session_obj.get("transaction_details") or {}
    wallet_address = None
    wallet_addresses = tx_details.get("wallet_address") or tx_details.get("wallet_addresses") or {}
    if isinstance(wallet_addresses, dict):
        wallet_address = next(iter(wallet_addresses.values()), None)
    elif isinstance(wallet_addresses, str):
        wallet_address = wallet_addresses

    parsed = StripeOnrampWebhookEvent(
        session_id=session_id,
        status=session_status,
        wallet_address=wallet_address,
        destination_currency=tx_details.get("destination_currency"),
        destination_network=tx_details.get("destination_network"),
        source_amount=tx_details.get("source_amount"),
        destination_amount=tx_details.get("destination_amount"),
        transaction_id=tx_details.get("transaction_id"),
        received_at=datetime.now(UTC).isoformat(),
    )

    # Persist to database if available
    try:
        await _persist_onramp_event(parsed, event_id)
    except Exception as exc:
        # Never fail the webhook response due to persistence errors
        logger.error("Failed to persist onramp event %s: %s", event_id, exc)

    # Log fulfillment for operational visibility
    if session_status in ("fulfillment_complete", "processing"):
        logger.info(
            "Stripe onramp %s: session=%s wallet=%s amount=%s %s → %s %s tx=%s",
            session_status,
            session_id,
            wallet_address,
            parsed.source_amount,
            "fiat",
            parsed.destination_amount,
            parsed.destination_currency,
            parsed.transaction_id,
        )

    return {"received": True, "processed": True, "session_id": session_id, "status": session_status}


async def _persist_onramp_event(event: StripeOnrampWebhookEvent, event_id: str) -> None:
    """Best-effort persistence of onramp webhook events to the database.

    Inserts into ``onramp_events`` table if it exists.  Silently skips
    if the table or database is unavailable.
    """
    try:
        from sardis.core.database import Database

        pool = await Database.get_pool()
        if pool is None:
            return

        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO onramp_events
                   (event_id, session_id, status, wallet_address,
                    destination_currency, destination_network,
                    source_amount, destination_amount,
                    transaction_id, provider, received_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                   ON CONFLICT (event_id) DO NOTHING""",
                event_id,
                event.session_id,
                event.status,
                event.wallet_address,
                event.destination_currency,
                event.destination_network,
                event.source_amount,
                event.destination_amount,
                event.transaction_id,
                "stripe",
                datetime.now(UTC),
            )
    except Exception as exc:
        # Table may not exist yet — that is fine
        logger.debug("onramp_events persistence skipped: %s", exc)
