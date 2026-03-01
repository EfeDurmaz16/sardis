"""Agentic Checkout API endpoints (Pivot D)."""
from __future__ import annotations

import json as _json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from sardis_checkout.models import CheckoutRequest, CheckoutResponse, PaymentStatus
from sardis_checkout.orchestrator import CheckoutOrchestrator
from sardis_v2_core.wallets import Wallet
from sardis_v2_core.wallet_repository import WalletRepository
from sardis_v2_core.spending_policy import SpendingPolicy, SpendingScope
from sardis_v2_core.tokens import TokenType
from sardis_v2_core.database import Database

from sardis_api.authz import require_principal, Principal
from sardis_api.webhook_replay import run_with_replay_protection

router = APIRouter(dependencies=[Depends(require_principal)])
public_router = APIRouter()


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


async def _save_checkout(checkout: CheckoutResponse, organization_id: str) -> None:
    """Save checkout session to PostgreSQL."""
    now = datetime.now(timezone.utc)
    await Database.execute(
        """
        INSERT INTO checkouts (checkout_id, organization_id, status, amount, currency, metadata, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (checkout_id) DO UPDATE SET
            status = EXCLUDED.status,
            updated_at = EXCLUDED.updated_at
        """,
        checkout.checkout_id,
        organization_id,
        checkout.status.value if hasattr(checkout.status, "value") else str(checkout.status),
        str(checkout.amount),
        checkout.currency,
        _json.dumps({
            "psp_name": checkout.psp_name,
            "redirect_url": checkout.redirect_url,
        }),
        now,
        now,
    )


async def _get_checkout(checkout_id: str, organization_id: str) -> Optional[dict]:
    """Get checkout from PostgreSQL, scoped to organization."""
    return await Database.fetchrow(
        "SELECT * FROM checkouts WHERE checkout_id = $1 AND organization_id = $2",
        checkout_id,
        organization_id,
    )


@router.post("", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def create_checkout(
    request: CreateCheckoutRequest,
    deps: CheckoutDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
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
    await _save_checkout(checkout_resp, principal.organization_id)

    return checkout_resp


@router.get("/{checkout_id}", response_model=CheckoutStatusResponse)
async def get_checkout_status(
    checkout_id: str,
    deps: CheckoutDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Get checkout session status."""
    row = await _get_checkout(checkout_id, principal.organization_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout session not found",
        )

    metadata = row["metadata"] if isinstance(row["metadata"], dict) else _json.loads(row["metadata"] or "{}")
    psp_name = metadata.get("psp_name")

    # Get latest status from PSP
    status_from_psp = await deps.orchestrator.get_payment_status(
        checkout_id,
        psp_name,
    )

    # Update stored status
    await Database.execute(
        "UPDATE checkouts SET status = $1, updated_at = $2 WHERE checkout_id = $3",
        status_from_psp.value if hasattr(status_from_psp, "value") else str(status_from_psp),
        datetime.now(timezone.utc),
        checkout_id,
    )

    return CheckoutStatusResponse(
        checkout_id=checkout_id,
        status=status_from_psp.value if hasattr(status_from_psp, "value") else str(status_from_psp),
        psp_name=psp_name,
        redirect_url=metadata.get("redirect_url"),
        amount=row["amount"],
        currency=row["currency"],
        created_at=row["created_at"].isoformat() if row["created_at"] else "",
        updated_at=row["updated_at"].isoformat() if row["updated_at"] else "",
    )


@public_router.post("/webhooks/{psp}", status_code=status.HTTP_200_OK)
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
        psp = psp.strip().lower()
        raw = await request.body()
        headers = dict(request.headers)

        # Fail closed: verify provider signatures before parsing/processing.
        connector = getattr(deps.orchestrator, "connectors", {}).get(psp)
        if connector is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"PSP {psp} not configured")

        signature_header = "stripe-signature" if psp == "stripe" else f"x-{psp}-signature"
        signature = headers.get(signature_header, "")
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing {signature_header} header",
            )

        ok = await connector.verify_webhook(raw, signature)
        if not ok:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

        payload = _json.loads(raw)

        event_id = payload.get("id") or headers.get("idempotency-key")
        if not event_id:
            import hashlib
            event_id = hashlib.sha256(raw).hexdigest()

        async def _process():
            return await deps.orchestrator.handle_webhook(
                psp=psp,
                payload=payload,
                headers=headers,
            )

        return await run_with_replay_protection(
            request=request,
            provider=f"psp:{psp}",
            event_id=str(event_id),
            body=raw,
            ttl_seconds=7 * 24 * 60 * 60,
            response_on_duplicate={"status": "received"},
            fn=_process,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook processing failed: {str(e)}",
        )


@router.get("/checkout/payment-methods")
async def get_payment_methods(
    principal: Principal = Depends(require_principal),
):
    """Return enabled payment methods for the checkout."""
    configured = os.getenv(
        "SARDIS_CHECKOUT_PAYMENT_METHODS", "card,apple_pay,google_pay,link"
    ).split(",")

    methods = []
    for m in configured:
        m = m.strip()
        if m:
            methods.append({
                "id": m,
                "enabled": True,
                "requires_activation": m in ("klarna", "paypal"),
            })
    return {"payment_methods": methods}
