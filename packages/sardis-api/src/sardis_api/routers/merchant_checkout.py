"""Merchant checkout API router for Pay with Sardis."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()
public_router = APIRouter()


# ── Request / Response Models ──────────────────────────────────────

class CreateSessionRequest(BaseModel):
    merchant_id: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USDC")
    description: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    session_id: str
    merchant_id: str
    amount: str
    currency: str
    description: Optional[str] = None
    status: str
    payment_method: Optional[str] = None
    tx_hash: Optional[str] = None
    redirect_url: str
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

    request = CheckoutRequest(
        agent_id=f"merchant_{body.merchant_id}",
        wallet_id=merchant.settlement_wallet_id or "",
        mandate_id="",
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"merchant_id": body.merchant_id, **body.metadata},
    )

    response = await deps.sardis_connector.create_checkout_session(request)

    return SessionResponse(
        session_id=response.checkout_id,
        merchant_id=body.merchant_id,
        amount=str(body.amount),
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
        merchant_id=session.merchant_id,
        amount=str(session.amount),
        currency=session.currency,
        description=session.description,
        status=session.status,
        payment_method=session.payment_method,
        tx_hash=session.tx_hash,
        redirect_url=f"{deps.checkout_base_url}/{session.session_id}",
        expires_at=session.expires_at.isoformat() if session.expires_at else None,
        created_at=session.created_at.isoformat(),
    )


# ── Public Endpoints (checkout page calls these) ──────────────────

@public_router.get("/sessions/{session_id}/details", response_model=SessionDetailsResponse)
async def get_session_details(
    session_id: str,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Get checkout info for the hosted checkout page (public, no auth)."""
    session = await deps.merchant_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    merchant = await deps.merchant_repo.get_merchant(session.merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    return SessionDetailsResponse(
        session_id=session.session_id,
        merchant_name=merchant.name,
        merchant_logo_url=merchant.logo_url,
        amount=str(session.amount),
        currency=session.currency,
        description=session.description,
        status=session.status,
        expires_at=session.expires_at.isoformat() if session.expires_at else None,
    )


@public_router.post("/sessions/{session_id}/connect")
async def connect_wallet(
    session_id: str,
    body: ConnectWalletRequest,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Connect a payer wallet to a checkout session."""
    session = await deps.merchant_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "pending":
        raise HTTPException(status_code=400, detail=f"Session status is '{session.status}'")

    from datetime import datetime, timezone
    if session.expires_at and datetime.now(timezone.utc) > session.expires_at:
        await deps.merchant_repo.update_session(session_id, status="expired")
        raise HTTPException(status_code=400, detail="Session has expired")

    await deps.merchant_repo.update_session(
        session_id,
        payer_wallet_id=body.wallet_id,
    )
    return {"status": "connected", "session_id": session_id, "wallet_id": body.wallet_id}


@public_router.post("/sessions/{session_id}/pay", response_model=PaymentResultResponse)
async def pay_session(
    session_id: str,
    body: PayRequest,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Execute payment from connected wallet."""
    try:
        result = await deps.sardis_connector.execute_payment(
            session_id=session_id,
            payer_wallet_id=body.wallet_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PaymentResultResponse(
        session_id=result["session_id"],
        status=result["status"],
        tx_hash=result.get("tx_hash"),
        amount=result["amount"],
        currency=result["currency"],
        merchant_id=result["merchant_id"],
    )


@public_router.get("/sessions/{session_id}/balance", response_model=BalanceResponse)
async def get_session_balance(
    session_id: str,
    deps: MerchantCheckoutDependencies = Depends(get_deps),
):
    """Poll payer wallet USDC balance (for fund-and-pay flow)."""
    session = await deps.merchant_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.payer_wallet_id:
        raise HTTPException(status_code=400, detail="No wallet connected to session")

    balance = Decimal("0")
    if deps.wallet_manager:
        try:
            wallet = await deps.wallet_manager.get_wallet(session.payer_wallet_id)
            if wallet:
                from sardis_v2_core.tokens import TokenType
                balance = await wallet.get_balance("base", TokenType.USDC, rpc_client=None)
        except Exception:
            logger.warning("Failed to get balance for wallet %s", session.payer_wallet_id)

    return BalanceResponse(
        wallet_id=session.payer_wallet_id,
        balance=str(balance),
    )
