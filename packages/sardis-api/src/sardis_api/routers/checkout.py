"""Agentic Checkout API endpoints (Pivot D)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from sardis_checkout.models import CheckoutRequest, CheckoutResponse, PaymentStatus
from sardis_checkout.orchestrator import CheckoutOrchestrator
from sardis_checkout.connectors.stripe import StripeConnector
from sardis_v2_core.wallets import Wallet
from sardis_v2_core.wallet_repository import WalletRepository
from sardis_v2_core.spending_policy import SpendingPolicy, SpendingScope
from sardis_v2_core.tokens import TokenType

router = APIRouter()


# Request/Response Models
class CreateCheckoutRequest(BaseModel):
    agent_id: str
    wallet_id: str
    amount: Decimal
    currency: str = "USDC"
    chain: str = "base"
    description: Optional[str] = None
    merchant_id: Optional[str] = None
    success_url: str = Field(default="https://example.com/success")
    cancel_url: str = Field(default="https://example.com/cancel")
    psp_preference: Optional[str] = None  # "stripe", "paypal", "coinbase", "circle"


class CheckoutStatusResponse(BaseModel):
    checkout_id: str
    status: str
    psp_name: Optional[str] = None
    redirect_url: Optional[str] = None
    amount: str
    currency: str
    created_at: str
    updated_at: str


@dataclass
class CheckoutDependencies:
    wallet_repo: WalletRepository
    orchestrator: CheckoutOrchestrator


def get_deps() -> CheckoutDependencies:
    raise NotImplementedError("Dependency override required")


# In-memory checkout store (swap for PostgreSQL in production)
_checkout_store: dict[str, CheckoutResponse] = {}


@router.post("", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def create_checkout(
    request: CreateCheckoutRequest,
    deps: CheckoutDependencies = Depends(get_deps),
):
    """
    Create a checkout session for agent payment.
    
    This endpoint:
    1. Validates wallet and policy
    2. Routes to appropriate PSP (Stripe, PayPal, etc.)
    3. Returns checkout session with redirect URL
    """
    # Get wallet
    wallet = await deps.wallet_repo.get(request.wallet_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
        )
    
    if wallet.agent_id != request.agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wallet does not belong to agent",
        )
    
    # Create checkout request
    checkout_req = CheckoutRequest(
        agent_id=request.agent_id,
        wallet_id=request.wallet_id,
        mandate_id=f"mandate_{uuid4().hex[:16]}",  # Generate mandate ID
        amount=request.amount,
        currency=request.currency,
        description=request.description or f"Payment for {request.agent_id}",
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )
    
    # Route to PSP via orchestrator
    checkout_resp = await deps.orchestrator.create_checkout(
        checkout_req,
        psp_preference=request.psp_preference,
    )
    
    # Store checkout session
    _checkout_store[checkout_resp.checkout_id] = checkout_resp
    
    return checkout_resp


@router.get("/{checkout_id}", response_model=CheckoutStatusResponse)
async def get_checkout_status(
    checkout_id: str,
    deps: CheckoutDependencies = Depends(get_deps),
):
    """Get checkout session status."""
    checkout = _checkout_store.get(checkout_id)
    if not checkout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout session not found",
        )
    
    # Get latest status from PSP
    status_from_psp = await deps.orchestrator.get_payment_status(
        checkout_id,
        checkout.psp_name,
    )
    
    # Update stored status
    checkout.status = status_from_psp
    _checkout_store[checkout_id] = checkout
    
    return CheckoutStatusResponse(
        checkout_id=checkout.checkout_id,
        status=checkout.status.value,
        psp_name=checkout.psp_name,
        redirect_url=checkout.redirect_url,
        amount=str(checkout.amount),
        currency=checkout.currency,
        created_at="",  # TODO: Add timestamps to CheckoutResponse
        updated_at="",
    )


@router.post("/webhooks/{psp}", status_code=status.HTTP_200_OK)
async def handle_psp_webhook(
    psp: str,
    request: Request,
    deps: CheckoutDependencies = Depends(get_deps),
):
    """
    Handle webhooks from PSPs (Stripe, PayPal, etc.).
    
    This endpoint processes payment status updates from PSPs.
    """
    try:
        payload = await request.json()
        headers = dict(request.headers)
        
        result = await deps.orchestrator.handle_webhook(
            psp=psp,
            payload=payload,
            headers=headers,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook processing failed: {str(e)}",
        )
