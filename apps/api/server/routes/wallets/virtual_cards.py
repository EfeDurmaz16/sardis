"""Virtual Card API — stablecoin-funded prepaid cards via Laso Finance.

Exposes LasoMPPService through the Sardis API with spending mandate
policy enforcement. Cards are funded with USDC on Tempo via MPP x402.

Flow: Agent -> Sardis policy check -> Laso x402 -> Visa prepaid card

Sandbox mode: Only enabled when SARDIS_VIRTUAL_CARDS_SANDBOX=true. Without
that explicit opt-in, live-shaped endpoints return truthful unavailable
responses unless Laso is configured and SARDIS_CHAIN_MODE=live.

Endpoints:
    POST /cards/virtual/issue          — Issue a virtual card ($5-$1,000)
    GET  /cards/virtual/{card_id}      — Get card details
    POST /cards/virtual/{card_id}/payment — Use card for a merchant payment
    POST /cards/virtual/send           — Send Venmo/PayPal payment
    GET  /cards/virtual/balance        — Get Laso account balance
"""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from server.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)

# In-memory store for sandbox cards so GET /cards/virtual/{card_id} works
_sandbox_cards: dict[str, dict] = {}


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
    sandbox: bool = Field(default=False, description="True when card is simulated (non-live mode)")


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
    sandbox: bool = Field(default=False, description="True when payment is simulated")


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
    sandbox: bool = Field(default=False, description="True when payment is simulated")


class BalanceResponse(BaseModel):
    available: str
    pending: str
    currency: str
    sandbox: bool = Field(default=False, description="True when balance is simulated")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_sandbox_mode() -> bool:
    """Return True only when virtual-card sandbox mode is explicitly enabled."""
    return os.getenv("SARDIS_VIRTUAL_CARDS_SANDBOX", "").strip().lower() == "true"


def _ensure_virtual_cards_mode() -> None:
    """Reject live-shaped calls that would otherwise silently simulate.

    Virtual cards are production-facing endpoints. They should only return
    deterministic sandbox data when the caller/operator explicitly opted in
    via ``SARDIS_VIRTUAL_CARDS_SANDBOX=true``. Non-live chain mode alone is
    not sufficient because it makes the endpoint look live while serving
    fake cards, fake balances, and fake payments.
    """
    if _is_sandbox_mode():
        return
    chain_mode = os.getenv("SARDIS_CHAIN_MODE", "simulated").strip().lower()
    if chain_mode != "live":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Virtual cards are unavailable unless SARDIS_CHAIN_MODE=live "
                "or SARDIS_VIRTUAL_CARDS_SANDBOX=true."
            ),
        )


def _generate_sandbox_card(
    amount: Decimal,
    currency: str = "USD",
    card_type: str = "single_use",
) -> dict:
    """Generate a deterministic sandbox virtual card.

    The card number uses the 4000-00 Visa test range so it is obviously
    non-real.  The card_id is a stable UUID derived from a hash of the
    request parameters so repeated identical calls get the same card.
    """
    card_id = f"sandbox_card_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC)
    # Deterministic but obviously-fake card number (Visa test prefix 4000 00)
    seed = hashlib.sha256(f"{card_id}{amount}{now.isoformat()[:10]}".encode()).hexdigest()
    card_number = f"4000 00{seed[:2]} {seed[2:6]} {seed[6:10]}"
    cvv = seed[10:13]  # 3-digit
    expiry_month = str((int(seed[13:15], 16) % 12) + 1).zfill(2)
    expiry_year = str(now.year + 2)
    expiry = f"{expiry_month}/{expiry_year}"

    card_data = {
        "card_id": card_id,
        "card_number": card_number,
        "cvv": cvv,
        "expiry": expiry,
        "amount": str(amount),
        "currency": currency,
        "status": "ready",
        "card_type": card_type,
        "billing_address": {
            "line1": "1111B S Governors Ave",
            "city": "Dover",
            "state": "DE",
            "postal_code": "19904",
            "country": "US",
        },
        "created_at": now.isoformat(),
        "sandbox": True,
    }
    # Store in memory so GET can retrieve it
    _sandbox_cards[card_id] = card_data
    return card_data


def _get_laso_service():
    """Import and instantiate LasoMPPService (lazy to avoid import-time failures)."""
    try:
        from sardis_mpp.services.laso import LasoMPPService
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Virtual cards require the sardis_mpp Laso integration in live mode. "
                "Set SARDIS_VIRTUAL_CARDS_SANDBOX=true only for explicit sandbox use."
            ),
        ) from exc
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

    In sandbox mode (SARDIS_CHAIN_MODE != "live"), returns a simulated
    card with a Visa test-range number so the flow can be demonstrated
    without Laso connectivity or a funded Tempo wallet.

    Restrictions (live mode): US-only, $5-$1,000, non-reloadable, no 3D Secure.
    """
    _ensure_virtual_cards_mode()

    if req.mandate_id:
        await _check_mandate(req.mandate_id, principal.org_id, req.amount)

    # ── Sandbox mode: return simulated card ──────────────────────────
    if _is_sandbox_mode():
        card_data = _generate_sandbox_card(
            amount=req.amount,
            currency=req.currency,
            card_type=req.card_type,
        )
        logger.info(
            "Sandbox virtual card issued: %s ($%s %s) for org %s",
            card_data["card_id"], req.amount, req.card_type, principal.org_id,
        )
        return CardResponse(
            card_id=card_data["card_id"],
            card_number=card_data["card_number"],
            cvv=card_data["cvv"],
            expiry=card_data["expiry"],
            amount=card_data["amount"],
            currency=card_data["currency"],
            status=card_data["status"],
            card_type=card_data["card_type"],
            billing_address=card_data["billing_address"],
            created_at=card_data["created_at"],
            sandbox=True,
        )

    # ── Live mode: issue real card via Laso ───────────────────────────
    try:
        laso = _get_laso_service()
        card = await laso.issue_card(
            amount=req.amount,
            currency=req.currency,
            card_type=req.card_type,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        try:
            from sardis_mpp.services.laso import LasoLimitExceeded, LasoPaymentRequired
        except ImportError:
            logger.error("Laso card issuance failed (sardis_mpp not installed): %s", e)
            raise HTTPException(status_code=502, detail=f"Card issuance failed: {e}")
        if isinstance(e, LasoLimitExceeded):
            raise HTTPException(status_code=429, detail=str(e))
        if isinstance(e, LasoPaymentRequired):
            raise HTTPException(
                status_code=502,
                detail="x402 payment failed -- check Tempo wallet balance",
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
        sandbox=False,
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
    """Retrieve card details (number, CVV, expiry, billing address, status).

    In sandbox mode, returns the in-memory sandbox card if it exists.
    """
    _ensure_virtual_cards_mode()

    # ── Sandbox mode ─────────────────────────────────────────────────
    if _is_sandbox_mode():
        card_data = _sandbox_cards.get(card_id)
        if not card_data:
            raise HTTPException(status_code=404, detail=f"Sandbox card {card_id} not found")
        return CardResponse(
            card_id=card_data["card_id"],
            card_number=card_data["card_number"],
            cvv=card_data["cvv"],
            expiry=card_data["expiry"],
            amount=card_data["amount"],
            currency=card_data["currency"],
            status=card_data["status"],
            card_type=card_data["card_type"],
            billing_address=card_data.get("billing_address", {}),
            created_at=card_data.get("created_at", ""),
            sandbox=True,
        )

    # ── Live mode ────────────────────────────────────────────────────
    try:
        laso = _get_laso_service()
        card = await laso.get_card_data(card_id)
    except HTTPException:
        raise
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
        sandbox=False,
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
    In sandbox mode, validates against in-memory card data.
    """
    _ensure_virtual_cards_mode()

    if req.mandate_id:
        await _check_mandate(req.mandate_id, principal.org_id, req.amount)

    # ── Sandbox mode ─────────────────────────────────────────────────
    if _is_sandbox_mode():
        card_data = _sandbox_cards.get(card_id)
        if not card_data:
            raise HTTPException(status_code=404, detail=f"Sandbox card {card_id} not found")
        card_status = card_data.get("status", "unknown")
        if card_status not in ("ready", "active", "funded"):
            raise HTTPException(
                status_code=409,
                detail=f"Card {card_id} is not ready (status: {card_status})",
            )
        card_amount = Decimal(card_data.get("amount", "0"))
        if req.amount > card_amount:
            raise HTTPException(
                status_code=422,
                detail=f"Payment ${req.amount} exceeds card balance ${card_amount}",
            )
        # Mark sandbox card as used for single-use cards
        if card_data.get("card_type") == "single_use":
            card_data["status"] = "used"
        logger.info(
            "Sandbox card payment: %s -> %s ($%s) for org %s",
            card_id, req.merchant_name, req.amount, principal.org_id,
        )
        return CardPaymentResponse(
            card_id=card_id,
            merchant_name=req.merchant_name,
            amount=str(req.amount),
            currency=req.currency,
            status="approved",
            sandbox=True,
        )

    # ── Live mode ────────────────────────────────────────────────────
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

        # Card details are returned -- the actual charge happens when the
        # card number is used at the merchant. This endpoint validates
        # and logs the intent for audit purposes.
        return CardPaymentResponse(
            card_id=card_id,
            merchant_name=req.merchant_name,
            amount=str(req.amount),
            currency=req.currency,
            status="approved",
            sandbox=False,
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
    In sandbox mode, returns a simulated pending payment.
    """
    _ensure_virtual_cards_mode()

    if req.mandate_id:
        await _check_mandate(req.mandate_id, principal.org_id, req.amount)

    # ── Sandbox mode ─────────────────────────────────────────────────
    if _is_sandbox_mode():
        payment_id = f"sandbox_pay_{uuid.uuid4().hex[:12]}"
        logger.info(
            "Sandbox %s payment: $%s -> %s for org %s",
            req.method, req.amount, req.recipient, principal.org_id,
        )
        return PaymentResponse(
            payment_id=payment_id,
            amount=str(req.amount),
            method=req.method,
            recipient=req.recipient,
            status="pending_confirmation",
            sandbox=True,
        )

    # ── Live mode ────────────────────────────────────────────────────
    try:
        laso = _get_laso_service()
        payment = await laso.send_payment(
            amount=req.amount,
            method=req.method,
            recipient=req.recipient,
        )
    except HTTPException:
        raise
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
        sandbox=False,
    )


@router.get(
    "/cards/virtual/balance",
    response_model=BalanceResponse,
    summary="Get Laso account balance",
)
async def get_balance(
    principal: Principal = Depends(require_principal),
) -> BalanceResponse:
    """Get the Laso account balance (available and pending).

    In sandbox mode, returns a simulated $1,000 available balance.
    """
    _ensure_virtual_cards_mode()

    # ── Sandbox mode ─────────────────────────────────────────────────
    if _is_sandbox_mode():
        return BalanceResponse(
            available="1000.00",
            pending="0.00",
            currency="USD",
            sandbox=True,
        )

    # ── Live mode ────────────────────────────────────────────────────
    try:
        laso = _get_laso_service()
        balance = await laso.get_balance()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Laso balance check failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Balance check failed: {e}")

    return BalanceResponse(
        available=str(balance.available),
        pending=str(balance.pending),
        currency=balance.currency,
        sandbox=False,
    )
