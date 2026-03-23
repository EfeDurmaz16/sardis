"""Virtual Card API — stablecoin-funded prepaid cards via Laso Finance.

Exposes LasoMPPService through the Sardis API with spending mandate
policy enforcement. Cards are funded with USDC on Tempo via MPP x402.

Flow: Agent → Sardis policy check → Laso x402 → Visa prepaid card

Endpoints:
    POST /cards/virtual/issue — Issue a virtual card ($5-$1,000)
    GET  /cards/virtual/{card_id} — Get card details
    POST /cards/virtual/payment — Send Venmo/PayPal payment
    GET  /cards/virtual/balance — Get Laso account balance
"""
from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class IssueCardRequest(BaseModel):
    amount: Decimal = Field(..., ge=5, le=1000, description="Card amount in USD ($5-$1,000)")
    currency: str = Field(default="USD")
    mandate_id: str | None = Field(default=None, description="Optional spending mandate for policy check")


class CardResponse(BaseModel):
    card_id: str
    card_number: str  # Full card number (show once, then mask)
    cvv: str
    expiry: str
    amount: str
    currency: str
    status: str  # processing, ready, used, expired
    card_type: str


class SendPaymentRequest(BaseModel):
    amount: Decimal = Field(..., ge=5, le=1000)
    method: str = Field(..., pattern="^(venmo|paypal)$")
    recipient: str = Field(..., description="Phone (Venmo) or email (PayPal)")
    mandate_id: str | None = None


class PaymentResponse(BaseModel):
    payment_id: str
    amount: str
    method: str
    recipient: str
    status: str


class BalanceResponse(BaseModel):
    balance: dict


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/cards/virtual/issue",
    response_model=CardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a virtual prepaid card via Laso Finance",
)
async def issue_virtual_card(
    req: IssueCardRequest,
    principal: Principal = Depends(require_principal),
) -> CardResponse:
    """Issue a stablecoin-funded virtual Visa prepaid card.

    Checks spending mandate (if provided), then issues card via
    Laso Finance MPP service. Card is funded with USDC on Tempo.

    Restrictions: US-only, $5-$1,000, non-reloadable, no 3D Secure.
    """
    # Policy check against mandate if provided
    if req.mandate_id:
        from sardis_v2_core.database import Database
        mandate = await Database.fetchrow(
            "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2 AND status = 'active'",
            req.mandate_id, principal.org_id,
        )
        if not mandate:
            raise HTTPException(status_code=404, detail="Active mandate not found")
        if mandate.get("amount_per_tx") and req.amount > mandate["amount_per_tx"]:
            raise HTTPException(
                status_code=422,
                detail=f"Card amount ${req.amount} exceeds mandate per-tx limit ${mandate['amount_per_tx']}",
            )

    # Issue via Laso
    try:
        from sardis_mpp.services.laso import LasoMPPService
        laso = LasoMPPService()
        card = await laso.issue_card(amount=req.amount, currency=req.currency)
    except Exception as e:
        logger.error("Laso card issuance failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Card issuance failed: {e}")

    logger.info("Virtual card issued: %s ($%s)", card.card_id, req.amount)

    return CardResponse(
        card_id=card.card_id,
        card_number=card.card_number,
        cvv=card.cvv,
        expiry=card.expiry,
        amount=str(card.amount),
        currency=card.currency,
        status=card.status,
        card_type=card.card_type,
    )


@router.get(
    "/cards/virtual/{card_id}",
    response_model=CardResponse,
    summary="Get virtual card details",
)
async def get_virtual_card(
    card_id: str,
    principal: Principal = Depends(require_principal),
) -> CardResponse:
    """Retrieve card details (number, CVV, expiry, status)."""
    try:
        from sardis_mpp.services.laso import LasoMPPService
        laso = LasoMPPService()
        data = await laso.get_card_data(card_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Card lookup failed: {e}")

    return CardResponse(
        card_id=card_id,
        card_number=data.get("card_number", ""),
        cvv=data.get("cvv", ""),
        expiry=data.get("expiry", ""),
        amount=str(data.get("amount", "0")),
        currency=data.get("currency", "USD"),
        status=data.get("status", "unknown"),
        card_type=data.get("type", "single_use"),
    )


@router.post(
    "/cards/virtual/payment",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send Venmo/PayPal payment via Laso",
)
async def send_payment(
    req: SendPaymentRequest,
    principal: Principal = Depends(require_principal),
) -> PaymentResponse:
    """Send payment via Venmo (phone) or PayPal (email).

    Funded with USDC on Tempo. Requires human confirmation before processing.
    """
    if req.mandate_id:
        from sardis_v2_core.database import Database
        mandate = await Database.fetchrow(
            "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2 AND status = 'active'",
            req.mandate_id, principal.org_id,
        )
        if not mandate:
            raise HTTPException(status_code=404, detail="Active mandate not found")

    try:
        from sardis_mpp.services.laso import LasoMPPService
        laso = LasoMPPService()
        payment = await laso.send_payment(
            amount=req.amount,
            method=req.method,
            recipient=req.recipient,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Payment failed: {e}")

    return PaymentResponse(
        payment_id=payment.payment_id,
        amount=str(payment.amount),
        method=payment.method,
        recipient=payment.recipient,
        status=payment.status,
    )


@router.get(
    "/cards/virtual/balance",
    response_model=BalanceResponse,
    summary="Get Laso account balance",
)
async def get_balance(
    principal: Principal = Depends(require_principal),
) -> BalanceResponse:
    try:
        from sardis_mpp.services.laso import LasoMPPService
        laso = LasoMPPService()
        data = await laso.get_balance()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Balance check failed: {e}")

    return BalanceResponse(balance=data)
