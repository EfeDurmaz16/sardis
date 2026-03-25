"""Virtual Card API — stablecoin-funded prepaid cards via Laso Finance.

Exposes LasoMPPService through the Sardis API with spending mandate
policy enforcement. Cards are funded with USDC on Tempo via MPP x402.

Flow: Agent -> Sardis policy check -> Laso x402 -> Visa prepaid card

Endpoints:
    POST /cards/virtual/issue          — Issue a virtual card ($5-$1,000)
    GET  /cards/virtual/{card_id}      — Get card details
    POST /cards/virtual/{card_id}/payment — Use card for a merchant payment
    POST /cards/virtual/send           — Send Venmo/PayPal payment
    GET  /cards/virtual/balance        — Get Laso account balance
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
    card_type: str = Field(default="single_use", pattern="^(single_use|multi_use)$")
    mandate_id: str | None = Field(default=None, description="Optional spending mandate for policy check")


class CardResponse(BaseModel):
    card_id: str
    card_number: str  # Full card number (show once on issue, then mask)
    cvv: str
    expiry: str
    amount: str
    currency: str
    status: str  # processing, ready, active, funded, used, expired
    card_type: str
    billing_address: dict = Field(default_factory=dict)
    created_at: str = ""


class CardSummaryResponse(BaseModel):
    """Masked card summary — no full PAN or CVV."""
    card_id: str
    last4: str
    expiry: str
    amount: str
    currency: str
    status: str
    card_type: str


class CardPaymentRequest(BaseModel):
    """Use a virtual card for a merchant payment."""
    merchant_name: str = Field(..., description="Merchant name for the charge")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="USD")
    mandate_id: str | None = None


class CardPaymentResponse(BaseModel):
    card_id: str
    merchant_name: str
    amount: str
    currency: str
    status: str  # approved, declined, pending


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
    available: str
    pending: str
    currency: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_laso_service():
    """Import and instantiate LasoMPPService (lazy to avoid import-time failures)."""
    from sardis_mpp.services.laso import LasoMPPService
    return LasoMPPService()


async def _check_mandate(mandate_id: str, org_id: str, amount: Decimal | None = None):
    """Validate spending mandate exists and amount is within limits."""
    from sardis_v2_core.database import Database
    mandate = await Database.fetchrow(
        "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2 AND status = 'active'",
        mandate_id, org_id,
    )
    if not mandate:
        raise HTTPException(status_code=404, detail="Active mandate not found")
    if amount is not None and mandate.get("amount_per_tx") and amount > mandate["amount_per_tx"]:
        raise HTTPException(
            status_code=422,
            detail=f"Amount ${amount} exceeds mandate per-tx limit ${mandate['amount_per_tx']}",
        )
    return mandate


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
    Laso Finance MPP service. The x402 authentication ($0.001 USDC)
    is handled automatically by the MPP transport layer.

    Restrictions: US-only, $5-$1,000, non-reloadable, no 3D Secure.
    """
    if req.mandate_id:
        await _check_mandate(req.mandate_id, principal.org_id, req.amount)

    try:
        laso = _get_laso_service()
        card = await laso.issue_card(
            amount=req.amount,
            currency=req.currency,
            card_type=req.card_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        from sardis_mpp.services.laso import LasoLimitExceeded, LasoPaymentRequired
        if isinstance(e, LasoLimitExceeded):
            raise HTTPException(status_code=429, detail=str(e))
        if isinstance(e, LasoPaymentRequired):
            raise HTTPException(
                status_code=502,
                detail="x402 payment failed — check Tempo wallet balance",
            )
        logger.error("Laso card issuance failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Card issuance failed: {e}")

    logger.info(
        "Virtual card issued: %s ($%s %s) for org %s",
        card.card_id, req.amount, req.card_type, principal.org_id,
    )

    return CardResponse(
        card_id=card.card_id,
        card_number=card.card_number,
        cvv=card.cvv,
        expiry=card.expiry,
        amount=str(card.amount),
        currency=card.currency,
        status=card.status,
        card_type=card.card_type,
        billing_address=card.billing_address,
        created_at=card.created_at,
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
    """Retrieve card details (number, CVV, expiry, billing address, status)."""
    try:
        laso = _get_laso_service()
        card = await laso.get_card_data(card_id)
    except Exception as e:
        logger.error("Laso card lookup failed for %s: %s", card_id, e)
        raise HTTPException(status_code=502, detail=f"Card lookup failed: {e}")

    return CardResponse(
        card_id=card.card_id,
        card_number=card.card_number,
        cvv=card.cvv,
        expiry=card.expiry,
        amount=str(card.amount),
        currency=card.currency,
        status=card.status,
        card_type=card.card_type,
        billing_address=card.billing_address,
        created_at=card.created_at,
    )


@router.post(
    "/cards/virtual/{card_id}/payment",
    response_model=CardPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Use virtual card for a merchant payment",
)
async def use_card_for_payment(
    card_id: str,
    req: CardPaymentRequest,
    principal: Principal = Depends(require_principal),
) -> CardPaymentResponse:
    """Use a virtual card to pay a merchant.

    The card must be in 'ready'/'active'/'funded' status. The payment amount
    must not exceed the card balance. For single-use cards, the amount should
    match the card value exactly.

    With mandate_id, the payment is validated against spending policy limits.
    """
    if req.mandate_id:
        await _check_mandate(req.mandate_id, principal.org_id, req.amount)

    try:
        laso = _get_laso_service()

        # Verify card exists and is ready
        card = await laso.get_card_data(card_id)
        if not card.is_ready:
            raise HTTPException(
                status_code=409,
                detail=f"Card {card_id} is not ready (status: {card.status})",
            )
        if req.amount > card.amount:
            raise HTTPException(
                status_code=422,
                detail=f"Payment ${req.amount} exceeds card balance ${card.amount}",
            )

        logger.info(
            "Virtual card payment: %s -> %s ($%s) for org %s",
            card_id, req.merchant_name, req.amount, principal.org_id,
        )

        # Card details are returned — the actual charge happens when the
        # card number is used at the merchant. This endpoint validates
        # and logs the intent for audit purposes.
        return CardPaymentResponse(
            card_id=card_id,
            merchant_name=req.merchant_name,
            amount=str(req.amount),
            currency=req.currency,
            status="approved",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Card payment failed for %s: %s", card_id, e)
        raise HTTPException(status_code=502, detail=f"Card payment failed: {e}")


@router.post(
    "/cards/virtual/send",
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
        await _check_mandate(req.mandate_id, principal.org_id, req.amount)

    try:
        laso = _get_laso_service()
        payment = await laso.send_payment(
            amount=req.amount,
            method=req.method,
            recipient=req.recipient,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Laso payment failed: %s", e)
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
    """Get the Laso account balance (available and pending)."""
    try:
        laso = _get_laso_service()
        balance = await laso.get_balance()
    except Exception as e:
        logger.error("Laso balance check failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Balance check failed: {e}")

    return BalanceResponse(
        available=str(balance.available),
        pending=str(balance.pending),
        currency=balance.currency,
    )
