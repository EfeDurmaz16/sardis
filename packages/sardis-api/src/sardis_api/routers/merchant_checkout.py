"""Merchant checkout API router for Pay with Sardis."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass

_CHECKOUT_CHAIN = os.getenv("SARDIS_CHECKOUT_CHAIN", "base")
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sardis_api.authz import require_principal
from sardis_api.kill_switch_dep import require_kill_switch_clear_checkout
from sardis_api.operational_alerts import alert_payment_failure
from sardis_guardrails.transaction_caps import get_transaction_cap_engine

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])
public_router = APIRouter()


def _fmt_amount(d: Decimal) -> str:
    """Format Decimal to clean string (strip trailing zeros)."""
    return f"{d:.2f}"


# ── Request / Response Models ──────────────────────────────────────

class CreateSessionRequest(BaseModel):
    merchant_id: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USDC")
    description: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    embed_origin: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    client_secret: str
    merchant_id: str
    amount: str
    currency: str
    description: Optional[str] = None
    status: str
    payment_method: Optional[str] = None
    tx_hash: Optional[str] = None
    redirect_url: str
    platform_fee: Optional[str] = None
    net_amount: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: str


class SessionDetailsResponse(BaseModel):
    session_id: str
    merchant_name: str
    merchant_logo_url: Optional[str] = None
    amount: str
    currency: str
    description: Optional[str] = None
    status: str
    expires_at: Optional[str] = None
    embed_origin: Optional[str] = None
    settlement_address: Optional[str] = None


class ConnectWalletRequest(BaseModel):
    wallet_id: str


class PayRequest(BaseModel):
    wallet_id: str


class PaymentResultResponse(BaseModel):
    session_id: str
    status: str
    tx_hash: Optional[str] = None
    amount: str
    currency: str
    merchant_id: str
    platform_fee: Optional[str] = None
    net_amount: Optional[str] = None


class ConnectExternalWalletRequest(BaseModel):
    address: str
    signature: str
    message: str


class ConfirmExternalPaymentRequest(BaseModel):
    tx_hash: str
    address: str


class BalanceResponse(BaseModel):
    wallet_id: str
    balance: str
    currency: str = "USDC"
    chain: str = "base"


# ── Dependencies ──────────────────────────────────────────────────

@dataclass
class MerchantCheckoutDependencies:
    merchant_repo: Any
    sardis_connector: Any
    wallet_manager: Any = None
    checkout_base_url: str = "https://checkout.sardis.sh"


def get_deps() -> MerchantCheckoutDependencies:
    raise RuntimeError("MerchantCheckoutDependencies not configured")


# ── Authenticated Endpoints (merchant-side) ────────────────────────

@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Create a checkout session for a merchant."""
    from sardis_checkout.models import CheckoutRequest

    merchant = await deps.merchant_repo.get_merchant(body.merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    if not merchant.is_active:
        raise HTTPException(status_code=400, detail="Merchant is inactive")

    metadata = {"merchant_id": body.merchant_id, **body.metadata}
    if body.embed_origin:
        metadata["embed_origin"] = body.embed_origin

    request = CheckoutRequest(
        agent_id=f"merchant_{body.merchant_id}",
        wallet_id=merchant.settlement_wallet_id or "",
        mandate_id="",
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata=metadata,
    )

    response = await deps.sardis_connector.create_checkout_session(request)

    return SessionResponse(
        session_id=response.checkout_id,
        client_secret=response.metadata.get("client_secret", ""),
        merchant_id=body.merchant_id,
        amount=_fmt_amount(body.amount),
        currency=body.currency,
        description=body.description,
        status="pending",
        redirect_url=response.redirect_url or "",
        expires_at=response.expires_at.isoformat() if response.expires_at else None,
        created_at=response.created_at.isoformat(),
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Get session status (merchant-side)."""
    session = await deps.merchant_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.session_id,
        client_secret=session.client_secret,
        merchant_id=session.merchant_id,
        amount=_fmt_amount(session.amount),
        currency=session.currency,
        description=session.description,
        status=session.status,
        payment_method=session.payment_method,
        tx_hash=session.tx_hash,
        redirect_url=f"{deps.checkout_base_url}/s/{session.client_secret}",
        platform_fee=_fmt_amount(session.platform_fee_amount) if session.platform_fee_amount else None,
        net_amount=_fmt_amount(session.net_amount) if session.net_amount else None,
        expires_at=session.expires_at.isoformat() if session.expires_at else None,
        created_at=session.created_at.isoformat(),
    )


# ── Public Endpoints (checkout page calls these via client_secret) ─

async def _get_session_by_secret(client_secret: str, deps: MerchantCheckoutDependencies):
    """Helper to look up session by client_secret and raise 404 if not found."""
    session = await deps.merchant_repo.get_session_by_secret(client_secret)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@public_router.get("/sessions/client/{client_secret}/details", response_model=SessionDetailsResponse)
async def get_session_details(
    client_secret: str,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Get checkout info for the hosted checkout page (public, no auth)."""
    session = await _get_session_by_secret(client_secret, deps)

    merchant = await deps.merchant_repo.get_merchant(session.merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # Resolve merchant's settlement wallet address for external wallet payments
    settlement_address: Optional[str] = None
    if merchant.settlement_wallet_id and deps.wallet_manager:
        try:
            wallet = await deps.wallet_manager.get_wallet(merchant.settlement_wallet_id)
            if wallet:
                settlement_address = wallet.get_address(_CHECKOUT_CHAIN) or None
        except Exception:
            logger.warning("Failed to resolve settlement address for merchant %s", merchant.merchant_id)

    return SessionDetailsResponse(
        session_id=session.session_id,
        merchant_name=merchant.name,
        merchant_logo_url=merchant.logo_url,
        amount=_fmt_amount(session.amount),
        currency=session.currency,
        description=session.description,
        status=session.status,
        expires_at=session.expires_at.isoformat() if session.expires_at else None,
        embed_origin=session.embed_origin,
        settlement_address=settlement_address,
    )


@public_router.post("/sessions/client/{client_secret}/connect")
async def connect_wallet(
    client_secret: str,
    body: ConnectWalletRequest,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Connect a payer wallet to a checkout session."""
    session = await _get_session_by_secret(client_secret, deps)
    if session.status != "pending":
        raise HTTPException(status_code=400, detail=f"Session status is '{session.status}'")

    from datetime import datetime, timezone
    if session.expires_at and datetime.now(timezone.utc) > session.expires_at:
        await deps.merchant_repo.update_session(session.session_id, status="expired")
        raise HTTPException(status_code=400, detail="Session has expired")

    # Look up the wallet's on-chain address
    wallet_address = ""
    if deps.wallet_manager:
        try:
            wallet = await deps.wallet_manager.get_wallet(body.wallet_id)
            if wallet:
                wallet_address = wallet.get_address(_CHECKOUT_CHAIN) or ""
        except Exception:
            logger.warning("Failed to get address for wallet %s", body.wallet_id)

    update_kwargs: dict[str, Any] = {"payer_wallet_id": body.wallet_id}
    if wallet_address:
        update_kwargs["payer_wallet_address"] = wallet_address
    await deps.merchant_repo.update_session(session.session_id, **update_kwargs)
    return {
        "status": "connected",
        "session_id": session.session_id,
        "wallet_id": body.wallet_id,
        "wallet_address": wallet_address,
    }


@public_router.post("/sessions/client/{client_secret}/pay", response_model=PaymentResultResponse)
async def pay_session(
    client_secret: str,
    body: PayRequest,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
    _ks: None = Depends(require_kill_switch_clear_checkout),
):
    """Execute payment from connected wallet."""
    session = await _get_session_by_secret(client_secret, deps)

    # Enforce global transaction caps for checkout payments
    if session.amount and session.amount > 0:
        cap_engine = get_transaction_cap_engine()
        cap_result = await cap_engine.check_and_record(
            amount=session.amount,
            org_id=session.merchant_id,
        )
        if not cap_result.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "transaction_cap_exceeded",
                    "cap_type": cap_result.cap_type,
                    "message": cap_result.message,
                },
            )

    try:
        result = await deps.sardis_connector.execute_payment(
            session_id=session.session_id,
            payer_wallet_id=body.wallet_id,
        )
    except ValueError as e:
        asyncio.create_task(alert_payment_failure(
            error=str(e),
            org_id=session.merchant_id,
            tx_id=session.session_id,
        ))
        raise HTTPException(status_code=400, detail=str(e))

    return PaymentResultResponse(
        session_id=result["session_id"],
        status=result["status"],
        tx_hash=result.get("tx_hash"),
        amount=result["amount"],
        currency=result["currency"],
        merchant_id=result["merchant_id"],
        platform_fee=result.get("platform_fee"),
        net_amount=result.get("net_amount"),
    )


@public_router.get("/sessions/client/{client_secret}/balance", response_model=BalanceResponse)
async def get_session_balance(
    client_secret: str,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Poll payer wallet USDC balance (for fund-and-pay flow)."""
    session = await _get_session_by_secret(client_secret, deps)
    if not session.payer_wallet_id:
        raise HTTPException(status_code=400, detail="No wallet connected to session")

    balance = Decimal("0")
    if deps.wallet_manager:
        try:
            wallet = await deps.wallet_manager.get_wallet(session.payer_wallet_id)
            if wallet:
                from sardis_v2_core.tokens import TokenType
                balance = await wallet.get_balance(_CHECKOUT_CHAIN, TokenType.USDC, rpc_client=None)
        except Exception:
            logger.warning("Failed to get balance for wallet %s", session.payer_wallet_id)

    return BalanceResponse(
        wallet_id=session.payer_wallet_id,
        balance=str(balance),
    )


# ── External Wallet Endpoints ─────────────────────────────────────


@public_router.post("/sessions/client/{client_secret}/connect-external")
async def connect_external_wallet(
    client_secret: str,
    body: ConnectExternalWalletRequest,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Connect an external wallet via EIP-191 signature verification."""
    session = await _get_session_by_secret(client_secret, deps)
    if session.status != "pending":
        raise HTTPException(status_code=400, detail=f"Session status is '{session.status}'")

    from datetime import datetime, timezone
    if session.expires_at and datetime.now(timezone.utc) > session.expires_at:
        await deps.merchant_repo.update_session(session.session_id, status="expired")
        raise HTTPException(status_code=400, detail="Session has expired")

    # Verify EIP-191 signature
    try:
        from eth_account.messages import encode_defunct
        from eth_account import Account

        msg = encode_defunct(text=body.message)
        recovered = Account.recover_message(msg, signature=body.signature)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if recovered.lower() != body.address.lower():
        raise HTTPException(
            status_code=400,
            detail="Signature does not match the provided address",
        )

    # Verify the message contains the session client_secret prefix (prevents replay)
    cs_prefix = client_secret[:8]
    if cs_prefix not in body.message:
        raise HTTPException(
            status_code=400,
            detail="Signed message does not match this session",
        )

    await deps.merchant_repo.update_session(
        session.session_id,
        payer_wallet_address=body.address,
        payment_method="external_wallet",
    )

    return {
        "status": "connected",
        "address": body.address,
        "session_id": session.session_id,
    }


@public_router.post(
    "/sessions/client/{client_secret}/confirm-external-payment",
    response_model=PaymentResultResponse,
)
async def confirm_external_payment(
    client_secret: str,
    body: ConfirmExternalPaymentRequest,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Confirm an external wallet payment by tx hash."""
    session = await _get_session_by_secret(client_secret, deps)

    # Enforce global transaction caps for external wallet payments
    if session.amount and session.amount > 0:
        cap_engine = get_transaction_cap_engine()
        cap_result = await cap_engine.check_and_record(
            amount=session.amount,
            org_id=session.merchant_id,
        )
        if not cap_result.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "transaction_cap_exceeded",
                    "cap_type": cap_result.cap_type,
                    "message": cap_result.message,
                },
            )

    if session.payment_method != "external_wallet":
        raise HTTPException(
            status_code=400,
            detail="Session is not using external wallet payment",
        )
    if not session.payer_wallet_address or session.payer_wallet_address.lower() != body.address.lower():
        raise HTTPException(
            status_code=400,
            detail="Address does not match the connected wallet",
        )

    # On-chain verification: verify the tx actually transferred the correct
    # amount to the merchant's settlement address before marking as paid
    merchant = await deps.merchant_repo.get_merchant(session.merchant_id)
    settlement_address: Optional[str] = None
    if merchant and merchant.settlement_wallet_id and deps.wallet_manager:
        try:
            wallet = await deps.wallet_manager.get_wallet(merchant.settlement_wallet_id)
            if wallet:
                settlement_address = wallet.get_address(_CHECKOUT_CHAIN) or None
        except Exception:
            logger.warning("Failed to resolve settlement address for verification")

    if settlement_address:
        from sardis_api.services.onchain_verification import verify_usdc_transfer

        verification = await verify_usdc_transfer(
            tx_hash=body.tx_hash,
            expected_recipient=settlement_address,
            expected_amount=session.amount,
            chain=_CHECKOUT_CHAIN,
        )
        if not verification.verified:
            logger.warning(
                "On-chain verification failed for session %s: %s",
                session.session_id, verification.error,
            )
            raise HTTPException(
                status_code=400,
                detail=f"On-chain verification failed: {verification.error}",
            )
    else:
        logger.warning(
            "No settlement address for merchant %s — skipping on-chain verification",
            session.merchant_id,
        )

    await deps.merchant_repo.update_session(
        session.session_id,
        status="paid",
        tx_hash=body.tx_hash,
    )

    # Fire webhook
    try:
        from sardis_checkout.merchant_webhooks import fire_webhook
        merchant = await deps.merchant_repo.get_merchant(session.merchant_id)
        if merchant and merchant.webhook_url:
            await fire_webhook(
                deps.merchant_repo,
                merchant,
                "payment.completed",
                {
                    "session_id": session.session_id,
                    "status": "paid",
                    "tx_hash": body.tx_hash,
                    "amount": _fmt_amount(session.amount),
                    "currency": session.currency,
                    "payment_method": "external_wallet",
                },
            )
    except Exception:
        logger.warning("Failed to fire webhook for session %s", session.session_id)

    return PaymentResultResponse(
        session_id=session.session_id,
        status="paid",
        tx_hash=body.tx_hash,
        amount=_fmt_amount(session.amount),
        currency=session.currency,
        merchant_id=session.merchant_id,
        platform_fee=_fmt_amount(session.platform_fee_amount) if session.platform_fee_amount else None,
        net_amount=_fmt_amount(session.net_amount) if session.net_amount else None,
    )


# ── SSE Streaming Endpoint ────────────────────────────────────────

@public_router.get("/sessions/client/{client_secret}/stream")
async def stream_session_updates(
    client_secret: str,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Server-Sent Events stream for real-time session status updates."""
    session = await _get_session_by_secret(client_secret, deps)

    async def event_generator():
        terminal_statuses = {"paid", "settled", "expired", "failed"}
        current_session = session
        while True:
            balance = "0"
            if current_session.payer_wallet_id and deps.wallet_manager:
                try:
                    wallet = await deps.wallet_manager.get_wallet(current_session.payer_wallet_id)
                    if wallet:
                        from sardis_v2_core.tokens import TokenType
                        balance = str(await wallet.get_balance(_CHECKOUT_CHAIN, TokenType.USDC, rpc_client=None))
                except Exception:
                    pass

            data = json.dumps({
                "status": current_session.status,
                "balance": balance,
                "tx_hash": current_session.tx_hash,
            })
            yield f"data: {data}\n\n"

            if current_session.status in terminal_statuses:
                break

            await asyncio.sleep(2)
            current_session = await deps.merchant_repo.get_session(current_session.session_id)
            if not current_session:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Checkout Links (public) ───────────────────────────────────────

@public_router.get("/links/{slug}")
async def resolve_checkout_link(
    slug: str,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Resolve a checkout link slug to a new session and redirect."""
    link = await deps.merchant_repo.get_checkout_link_by_slug(slug)
    if not link:
        raise HTTPException(status_code=404, detail="Checkout link not found")

    from sardis_checkout.models import CheckoutRequest

    request = CheckoutRequest(
        agent_id=f"merchant_{link.merchant_id}",
        wallet_id="",
        mandate_id="",
        amount=link.amount,
        currency=link.currency,
        description=link.description,
        metadata={"merchant_id": link.merchant_id, "link_id": link.link_id},
    )

    response = await deps.sardis_connector.create_checkout_session(request)
    client_secret = response.metadata.get("client_secret", "")

    from fastapi.responses import RedirectResponse
    return RedirectResponse(
        url=f"{deps.checkout_base_url}/s/{client_secret}",
        status_code=302,
    )


# ── Coinbase Onramp Session Token ────────────────────────────────


class OnrampTokenRequest(BaseModel):
    wallet_address: str


class OnrampTokenResponse(BaseModel):
    session_token: str
    onramp_url: str


def _generate_cdp_jwt(request_method: str, request_path: str) -> str:
    """Generate a JWT for CDP API authentication (Ed25519).

    CDP expects the URI claim as "METHOD host/path",
    e.g. "POST api.developer.coinbase.com/onramp/v1/token".
    """
    import base64
    import time
    import uuid

    import jwt
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key_id = os.getenv("CDP_API_KEY_ID", "")
    key_secret = os.getenv("CDP_API_KEY_SECRET", "")

    if not key_id or not key_secret:
        raise ValueError("CDP_API_KEY_ID and CDP_API_KEY_SECRET must be set")

    raw_key = base64.b64decode(key_secret)
    private_key = Ed25519PrivateKey.from_private_bytes(raw_key[:32])

    uri = f"{request_method} api.developer.coinbase.com{request_path}"
    now = int(time.time())

    payload = {
        "sub": key_id,
        "iss": "coinbase-cloud",
        "nbf": now,
        "exp": now + 120,
        "uris": [uri],
    }
    headers = {
        "kid": key_id,
        "nonce": uuid.uuid4().hex,
        "typ": "JWT",
    }

    return jwt.encode(payload, private_key, algorithm="EdDSA", headers=headers)


@public_router.post(
    "/sessions/client/{client_secret}/onramp-token",
    response_model=OnrampTokenResponse,
)
async def get_onramp_token(
    client_secret: str,
    body: OnrampTokenRequest,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Generate a Coinbase Onramp session token for the fund-and-pay flow."""
    session = await _get_session_by_secret(client_secret, deps)

    # Auth: wallet must be connected and address must match
    if not session.payer_wallet_address:
        raise HTTPException(
            status_code=400,
            detail="No wallet connected to session. Connect a wallet first.",
        )
    if body.wallet_address != session.payer_wallet_address:
        raise HTTPException(
            status_code=400,
            detail="Wallet address does not match the connected wallet.",
        )

    try:
        token = _generate_cdp_jwt("POST", "/onramp/v1/token")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    import httpx

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.developer.coinbase.com/onramp/v1/token",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "addresses": [
                    {
                        "address": body.wallet_address,
                        "blockchains": ["base"],
                    }
                ],
                "assets": ["USDC"],
            },
        )

    if resp.status_code != 200:
        error_preview = resp.text[:500] if len(resp.text) > 500 else resp.text
        logger.error("CDP onramp token error: status=%s body=%s", resp.status_code, error_preview)
        raise HTTPException(
            status_code=502,
            detail=f"Coinbase onramp API returned {resp.status_code}",
        )

    data = resp.json()
    session_token = data.get("token", "")

    from urllib.parse import urlencode

    onramp_params = urlencode({
        "sessionToken": session_token,
        "defaultAsset": "USDC",
        "defaultNetwork": "base",
        "presetFiatAmount": str(int(float(_fmt_amount(session.amount)) + 1)),
    })
    onramp_url = f"https://pay.coinbase.com/buy/select-asset?{onramp_params}"

    return OnrampTokenResponse(
        session_token=session_token,
        onramp_url=onramp_url,
    )
