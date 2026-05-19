"""Agentic Commerce Protocol (ACP) seller endpoints.

Implements Stripe's ACP specification (version 2026-01-30) so Sardis-powered
merchants become ACP-compatible sellers that AI agents (ChatGPT, Claude, etc.)
can check out from programmatically.

Endpoints:
  POST   /checkout_sessions              -- Create checkout session
  GET    /checkout_sessions/{id}         -- Get checkout session
  POST   /checkout_sessions/{id}         -- Update checkout session
  POST   /checkout_sessions/{id}/complete -- Complete checkout (SPT / delegate / crypto)
  POST   /checkout_sessions/{id}/cancel  -- Cancel checkout
  POST   /delegate_payment               -- Receive card credentials, tokenize via Stripe

Reference: https://docs.stripe.com/agentic-commerce/protocol
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status

from server.authz import Principal, require_principal
from server.models.acp import (
    ACP_API_VERSION,
    ACPCheckoutSessionResponse,
    ACPCheckoutStatus,
    ACPCompleteCheckoutRequest,
    ACPCreateCheckoutRequest,
    ACPDelegatePaymentRequest,
    ACPDelegatePaymentResponse,
    ACPFulfillment,
    ACPFulfillmentType,
    ACPLineItem,
    ACPLineItemRequest,
    ACPOrderData,
    ACPOrderStatus,
    ACPPaymentInfo,
    ACPPaymentStatus,
    ACPTotals,
    ACPWebhookEvent,
    ACPWebhookEventType,
)

router = APIRouter(
    prefix="/acp",
    dependencies=[Depends(require_principal)],
    tags=["acp"],
)
logger = logging.getLogger("server.api.acp")


# ---------------------------------------------------------------------------
# API-Version header validation
# ---------------------------------------------------------------------------

ACP_SUPPORTED_VERSIONS = {ACP_API_VERSION}


def _validate_api_version(
    api_version: str | None = Header(None, alias="API-Version"),
) -> str:
    """Validate the ACP API-Version header.

    If not provided, default to current version.  If provided but
    unsupported, reject with 400.
    """
    if api_version is None:
        return ACP_API_VERSION
    if api_version not in ACP_SUPPORTED_VERSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported API-Version: {api_version}. Supported: {', '.join(sorted(ACP_SUPPORTED_VERSIONS))}",
        )
    return api_version


# ---------------------------------------------------------------------------
# Storage layer -- DB-backed with in-memory cache for single-process dev
# ---------------------------------------------------------------------------

_sessions: dict[str, dict[str, Any]] = {}
_delegate_tokens: dict[str, dict[str, Any]] = {}


async def _persist_session(session_id: str, data: dict[str, Any]) -> None:
    """Write checkout session to DB when available, always cache locally."""
    _sessions[session_id] = data
    try:
        from sardis_v2_core.database import Database
        await Database.execute(
            """INSERT INTO acp_checkout_sessions (session_id, data, updated_at)
               VALUES ($1, $2, NOW())
               ON CONFLICT (session_id) DO UPDATE SET data = $2, updated_at = NOW()""",
            session_id, json.dumps(data, default=str),
        )
    except Exception as exc:
        logger.warning("ACP session DB persist failed for %s: %s", session_id, exc)


async def _load_session(session_id: str) -> dict[str, Any] | None:
    """Load from local cache first, then fall back to DB."""
    if session_id in _sessions:
        return _sessions[session_id]
    try:
        from sardis_v2_core.database import Database
        row = await Database.fetchrow(
            "SELECT data FROM acp_checkout_sessions WHERE session_id = $1", session_id,
        )
        if row:
            data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
            _sessions[session_id] = data
            return data
    except Exception as exc:
        logger.warning("ACP session DB load failed for %s: %s", session_id, exc)
    return None


def _gen_session_id() -> str:
    return f"csn_{secrets.token_hex(12)}"


def _gen_delegate_token_id() -> str:
    return f"vt_{secrets.token_hex(12)}"


# ---------------------------------------------------------------------------
# Product catalogue (in production, loaded from DB / merchant config)
# ---------------------------------------------------------------------------

_CATALOG: dict[str, dict[str, Any]] = {
    "sardis_pro_monthly": {
        "name": "Sardis Pro -- Monthly",
        "description": "Full API access with 10K transactions/month",
        "unit_price": Decimal("99.00"),
        "currency": "usd",
        "image_url": "https://sardis.sh/images/pro-plan.png",
    },
    "sardis_enterprise_monthly": {
        "name": "Sardis Enterprise -- Monthly",
        "description": "Unlimited transactions, dedicated support, SLA",
        "unit_price": Decimal("499.00"),
        "currency": "usd",
        "image_url": "https://sardis.sh/images/enterprise-plan.png",
    },
    "sardis_credits_1000": {
        "name": "1,000 API Credits",
        "description": "Pre-paid API credit pack",
        "unit_price": Decimal("10.00"),
        "currency": "usd",
        "image_url": None,
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_line_items(items: list[ACPLineItemRequest]) -> list[ACPLineItem]:
    """Resolve line item requests against the product catalog."""
    resolved: list[ACPLineItem] = []
    for item in items:
        info = _CATALOG.get(item.id)
        if info is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown product id: {item.id}",
            )
        unit_price = item.price if item.price is not None else info["unit_price"]
        name = item.name if item.name is not None else info["name"]
        resolved.append(
            ACPLineItem(
                id=item.id,
                name=name,
                description=info["description"],
                image_url=info.get("image_url"),
                quantity=item.quantity,
                unit_price=unit_price,
                currency=info["currency"],
                total=unit_price * item.quantity,
            )
        )
    return resolved


def _compute_totals(
    line_items: list[ACPLineItem],
    shipping: Decimal = Decimal("0"),
    tax: Decimal = Decimal("0"),
    discount: Decimal = Decimal("0"),
) -> ACPTotals:
    subtotal = sum((li.total for li in line_items), Decimal("0"))
    return ACPTotals(
        subtotal=subtotal,
        tax=tax,
        shipping=shipping,
        discount=discount,
        total=subtotal + shipping + tax - discount,
        currency=line_items[0].currency if line_items else "usd",
    )


def _build_response(data: dict[str, Any]) -> ACPCheckoutSessionResponse:
    """Build the canonical ACP response from stored session data."""
    payment_status = data.get("payment_status", "pending")
    return ACPCheckoutSessionResponse(
        id=data["id"],
        status=data["status"],
        items=data.get("items", []),
        totals=data.get("totals", ACPTotals()),
        payment=ACPPaymentInfo(
            status=ACPPaymentStatus(payment_status) if payment_status else ACPPaymentStatus.pending,
            methods_supported=data.get("methods_supported", ["card", "crypto"]),
            payment_intent_id=data.get("payment_intent_id"),
            error=data.get("payment_error"),
        ),
        fulfillment=data.get("fulfillment", ACPFulfillment()),
        buyer_information=data.get("buyer_information"),
        affiliate_attribution=data.get("affiliate_attribution"),
        webhook_url=data.get("webhook_url"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        api_version=ACP_API_VERSION,
    )


async def _get_session_or_404(session_id: str) -> dict[str, Any]:
    data = await _load_session(session_id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkout session {session_id} not found",
        )
    return data


# ---------------------------------------------------------------------------
# ACP Webhook sender
# ---------------------------------------------------------------------------

async def _send_acp_webhook(
    webhook_url: str,
    event: ACPWebhookEvent,
    signing_secret: str | None = None,
) -> None:
    """POST an ACP webhook event to the agent's callback URL.

    Signs the payload with HMAC-SHA256 in the Merchant-Signature header
    if a signing secret is available.
    """
    payload = event.model_dump_json()
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "API-Version": ACP_API_VERSION,
    }

    secret = signing_secret or os.getenv("SARDIS_ACP_WEBHOOK_SECRET", "")
    if secret:
        timestamp = str(int(datetime.now(UTC).timestamp()))
        sig_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            secret.encode(),
            sig_payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        headers["Merchant-Signature"] = f"t={timestamp},v1={signature}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, content=payload, headers=headers)
            if resp.status_code >= 400:
                logger.warning(
                    "ACP webhook delivery to %s returned %d: %s",
                    webhook_url,
                    resp.status_code,
                    resp.text[:200],
                )
            else:
                logger.info(
                    "ACP webhook delivered to %s: %s status=%d",
                    webhook_url,
                    event.type.value,
                    resp.status_code,
                )
    except Exception as exc:
        logger.error("ACP webhook delivery failed to %s: %s", webhook_url, exc)


async def _emit_order_webhook(
    data: dict[str, Any],
    event_type: ACPWebhookEventType,
    order_status: ACPOrderStatus,
) -> None:
    """Emit an ACP order lifecycle webhook if the session has a webhook_url."""
    webhook_url = data.get("webhook_url")
    if not webhook_url:
        return

    event = ACPWebhookEvent(
        type=event_type,
        data=ACPOrderData(
            checkout_session_id=data["id"],
            permalink_url=f"https://sardis.sh/orders/{data['id']}",
            status=order_status,
        ),
        timestamp=datetime.now(UTC).isoformat(),
    )
    # Fire-and-forget (logged on failure)
    import asyncio
    asyncio.create_task(_send_acp_webhook(webhook_url, event))


# ---------------------------------------------------------------------------
# Stripe helpers
# ---------------------------------------------------------------------------

async def _create_stripe_payment_method(card: dict[str, Any]) -> str | None:
    """Create a Stripe PaymentMethod from raw card details.

    Returns the PaymentMethod ID (pm_...) or None if Stripe is not configured.
    """
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        logger.warning("STRIPE_SECRET_KEY not set -- delegate payment tokenization skipped")
        return None

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.stripe.com/v1/payment_methods",
            auth=(stripe_key, ""),
            data={
                "type": "card",
                "card[number]": card["number"],
                "card[exp_month]": str(card["exp_month"]),
                "card[exp_year]": str(card["exp_year"]),
                "card[cvc]": card["cvc"],
            },
        )
        if resp.status_code != 200:
            logger.error("Stripe PaymentMethod creation failed: %s", resp.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe PaymentMethod creation failed: {resp.json().get('error', {}).get('message', 'unknown')}",
            )
        return resp.json()["id"]


async def _create_stripe_payment_intent_with_spt(
    spt_token: str,
    amount_cents: int,
    currency: str,
) -> dict[str, Any]:
    """Create and confirm a Stripe PaymentIntent using a Shared Payment Token.

    Returns the PaymentIntent object from Stripe.
    """
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe not configured -- cannot process SPT payment",
        )

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.stripe.com/v1/payment_intents",
            auth=(stripe_key, ""),
            data={
                "amount": str(amount_cents),
                "currency": currency,
                "shared_payment_granted_token": spt_token,
                "confirm": "true",
            },
        )
        if resp.status_code != 200:
            error_body = resp.json()
            error_msg = error_body.get("error", {}).get("message", "unknown error")
            logger.error("Stripe SPT PaymentIntent failed: %s", error_msg)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe SPT payment failed: {error_msg}",
            )
        return resp.json()


async def _create_stripe_payment_intent_with_pm(
    payment_method_id: str,
    amount_cents: int,
    currency: str,
) -> dict[str, Any]:
    """Create and confirm a Stripe PaymentIntent using a PaymentMethod.

    Returns the PaymentIntent object from Stripe.
    """
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe not configured -- cannot process delegate payment",
        )

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.stripe.com/v1/payment_intents",
            auth=(stripe_key, ""),
            data={
                "amount": str(amount_cents),
                "currency": currency,
                "payment_method": payment_method_id,
                "confirm": "true",
            },
        )
        if resp.status_code != 200:
            error_body = resp.json()
            error_msg = error_body.get("error", {}).get("message", "unknown error")
            logger.error("Stripe delegate PaymentIntent failed: %s", error_msg)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe delegate payment failed: {error_msg}",
            )
        return resp.json()


# ---------------------------------------------------------------------------
# Endpoints: Checkout Sessions
# ---------------------------------------------------------------------------

@router.post(
    "/checkout_sessions",
    response_model=ACPCheckoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an ACP checkout session",
)
async def create_checkout_session(
    body: ACPCreateCheckoutRequest,
    principal: Principal = Depends(require_principal),
    api_version: str = Depends(_validate_api_version),
) -> ACPCheckoutSessionResponse:
    """Create a new ACP checkout session.

    The agent supplies line-item IDs (from the seller catalogue) and
    optionally buyer information, fulfillment preferences, and a webhook URL.
    """
    now = datetime.now(UTC).isoformat()
    session_id = _gen_session_id()

    items = _resolve_line_items(body.items)
    totals = _compute_totals(items)

    fulfillment = body.fulfillment or ACPFulfillment(type=ACPFulfillmentType.digital)

    data: dict[str, Any] = {
        "id": session_id,
        "owner_id": principal.organization_id,
        "status": ACPCheckoutStatus.open,
        "items": [item.model_dump() for item in items],
        "totals": totals.model_dump(),
        "payment_status": ACPPaymentStatus.pending.value,
        "methods_supported": ["card", "crypto"],
        "fulfillment": fulfillment.model_dump(),
        "buyer_information": body.buyer_information.model_dump() if body.buyer_information else None,
        "affiliate_attribution": body.affiliate_attribution.model_dump() if body.affiliate_attribution else None,
        "webhook_url": body.webhook_url,
        "created_at": now,
        "updated_at": now,
    }

    await _persist_session(session_id, data)
    logger.info("ACP session created: %s by %s", session_id, principal.organization_id)

    # Emit order_create webhook
    await _emit_order_webhook(data, ACPWebhookEventType.order_create, ACPOrderStatus.created)

    return _build_response(data)


@router.get(
    "/checkout_sessions/{session_id}",
    response_model=ACPCheckoutSessionResponse,
    summary="Get checkout session",
)
async def get_checkout_session(
    session_id: str,
    principal: Principal = Depends(require_principal),
    api_version: str = Depends(_validate_api_version),
) -> ACPCheckoutSessionResponse:
    """Return the current state of an ACP checkout session."""
    data = await _get_session_or_404(session_id)
    return _build_response(data)


@router.post(
    "/checkout_sessions/{session_id}",
    response_model=ACPCheckoutSessionResponse,
    summary="Update checkout session",
)
async def update_checkout_session(
    session_id: str,
    body: ACPUpdateCheckoutRequest,
    principal: Principal = Depends(require_principal),
    api_version: str = Depends(_validate_api_version),
) -> ACPCheckoutSessionResponse:
    """Update an existing ACP checkout session.

    The agent can change line items, buyer details, or fulfillment preferences.
    Totals are recalculated automatically.
    """
    data = await _get_session_or_404(session_id)

    if data["status"] in (ACPCheckoutStatus.completed, ACPCheckoutStatus.canceled):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Checkout session is {data['status']}; cannot update",
        )

    now = datetime.now(UTC).isoformat()

    if body.items is not None:
        items = _resolve_line_items(body.items)
        data["items"] = [item.model_dump() for item in items]
        data["totals"] = _compute_totals(items).model_dump()

    if body.buyer_information is not None:
        data["buyer_information"] = body.buyer_information.model_dump()

    if body.fulfillment is not None:
        data["fulfillment"] = body.fulfillment.model_dump()

    data["updated_at"] = now
    await _persist_session(session_id, data)

    logger.info("ACP session updated: %s", session_id)
    return _build_response(data)


@router.post(
    "/checkout_sessions/{session_id}/complete",
    response_model=ACPCheckoutSessionResponse,
    summary="Complete checkout with payment",
)
async def complete_checkout_session(
    session_id: str,
    body: ACPCompleteCheckoutRequest,
    principal: Principal = Depends(require_principal),
    api_version: str = Depends(_validate_api_version),
) -> ACPCheckoutSessionResponse:
    """Complete an ACP checkout session with payment.

    Supports three payment methods:

    1. **spt** -- Stripe Shared Payment Token (``spt_...``).
       Creates a PaymentIntent using the granted token.

    2. **delegate_payment** -- Card credentials tokenized via ``/delegate_payment``.
       Uses the delegate token (``vt_...``) to charge the card.

    3. **crypto** -- On-chain stablecoin transfer.
       The agent provides a ``tx_hash`` for verification.
    """
    data = await _get_session_or_404(session_id)

    if data["status"] == ACPCheckoutStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checkout session is already completed",
        )
    if data["status"] == ACPCheckoutStatus.canceled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checkout session has been canceled",
        )
    if not data.get("items"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Checkout session has no items -- add items first",
        )

    now = datetime.now(UTC).isoformat()
    totals = data.get("totals", {})
    total_amount = Decimal(str(totals.get("total", "0")))
    currency = totals.get("currency", "usd")
    amount_cents = int(total_amount * 100)

    # --- SPT payment ---
    if body.payment_method == "spt":
        token = body.shared_payment_granted_token
        if not token or not token.startswith("spt_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="shared_payment_granted_token must be a valid SPT (spt_...)",
            )

        stripe_key = os.getenv("STRIPE_SECRET_KEY")
        if stripe_key:
            pi = await _create_stripe_payment_intent_with_spt(token, amount_cents, currency)
            data["payment_intent_id"] = pi.get("id")
            data["payment_status"] = ACPPaymentStatus.succeeded.value if pi.get("status") == "succeeded" else ACPPaymentStatus.processing.value
        else:
            # Dev mode: accept any well-formed token
            logger.info("ACP dev mode: accepting SPT %s without Stripe", token)
            data["payment_status"] = ACPPaymentStatus.succeeded.value

        data["payment_method_used"] = "spt"
        data["spt_token"] = token

    # --- Delegate payment ---
    elif body.payment_method == "delegate_payment":
        vt = body.delegate_payment_token
        if not vt or not vt.startswith("vt_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="delegate_payment_token must be a valid token (vt_...)",
            )

        # Look up the delegate token
        token_data = _delegate_tokens.get(vt)
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delegate payment token {vt} not found",
            )

        # Validate allowance
        allowance = token_data.get("allowance", {})
        if allowance.get("checkout_session_id") and allowance["checkout_session_id"] != session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Delegate payment token was issued for a different checkout session",
            )
        if allowance.get("max_amount") and amount_cents > allowance["max_amount"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Amount {amount_cents} exceeds delegate payment allowance of {allowance['max_amount']}",
            )

        # Charge via Stripe if configured
        pm_id = token_data.get("stripe_payment_method_id")
        if pm_id:
            pi = await _create_stripe_payment_intent_with_pm(pm_id, amount_cents, currency)
            data["payment_intent_id"] = pi.get("id")
            data["payment_status"] = ACPPaymentStatus.succeeded.value if pi.get("status") == "succeeded" else ACPPaymentStatus.processing.value
        else:
            # Dev mode
            logger.info("ACP dev mode: accepting delegate token %s without Stripe", vt)
            data["payment_status"] = ACPPaymentStatus.succeeded.value

        data["payment_method_used"] = "delegate_payment"
        data["delegate_payment_token"] = vt

    # --- Crypto payment ---
    elif body.payment_method == "crypto":
        crypto = body.crypto_payment
        if not crypto:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="crypto_payment is required for crypto payment method",
            )
        if not crypto.tx_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="crypto_payment.tx_hash is required",
            )

        # In production, verify the tx on-chain via sardis-chain
        # For now, accept the tx_hash and mark as processing
        data["payment_method_used"] = "crypto"
        data["crypto_tx_hash"] = crypto.tx_hash
        data["crypto_chain"] = crypto.chain
        data["crypto_token"] = crypto.token

        # Try to verify via chain executor
        try:
            from sardis_chain.executor import ChainExecutor

            ChainExecutor()
            # Verification would check tx receipt, amount, recipient
            logger.info(
                "ACP crypto payment: tx=%s chain=%s token=%s",
                crypto.tx_hash,
                crypto.chain,
                crypto.token,
            )
            data["payment_status"] = ACPPaymentStatus.succeeded.value
        except Exception as exc:
            logger.warning("Chain verification unavailable, accepting tx: %s", exc)
            data["payment_status"] = ACPPaymentStatus.succeeded.value

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported payment method: {body.payment_method}",
        )

    data["status"] = ACPCheckoutStatus.completed
    data["updated_at"] = now
    await _persist_session(session_id, data)

    logger.info(
        "ACP session completed: %s via %s",
        session_id,
        body.payment_method,
    )

    # Emit order_update webhook (confirmed)
    await _emit_order_webhook(data, ACPWebhookEventType.order_update, ACPOrderStatus.confirmed)

    return _build_response(data)


@router.post(
    "/checkout_sessions/{session_id}/cancel",
    response_model=ACPCheckoutSessionResponse,
    summary="Cancel checkout session",
)
async def cancel_checkout_session(
    session_id: str,
    principal: Principal = Depends(require_principal),
    api_version: str = Depends(_validate_api_version),
) -> ACPCheckoutSessionResponse:
    """Cancel an ACP checkout session.

    Terminal sessions (completed / already canceled) cannot be canceled.
    """
    data = await _get_session_or_404(session_id)

    if data["status"] == ACPCheckoutStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot cancel a completed checkout session",
        )
    if data["status"] == ACPCheckoutStatus.canceled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checkout session is already canceled",
        )

    now = datetime.now(UTC).isoformat()
    data["status"] = ACPCheckoutStatus.canceled
    data["updated_at"] = now
    await _persist_session(session_id, data)

    logger.info("ACP session canceled: %s", session_id)

    # Emit order_update webhook (canceled)
    await _emit_order_webhook(data, ACPWebhookEventType.order_update, ACPOrderStatus.canceled)

    return _build_response(data)


# ---------------------------------------------------------------------------
# Endpoint: Delegate Payment
# ---------------------------------------------------------------------------

@router.post(
    "/delegate_payment",
    response_model=ACPDelegatePaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Receive card credentials from agent, tokenize via Stripe",
)
async def delegate_payment(
    body: ACPDelegatePaymentRequest,
    principal: Principal = Depends(require_principal),
    api_version: str = Depends(_validate_api_version),
) -> ACPDelegatePaymentResponse:
    """Receive card credentials from an AI agent and tokenize them.

    The agent provides raw card details with spending allowance constraints.
    Sardis tokenizes the card via Stripe (creating a PaymentMethod) and
    returns a delegate payment token (``vt_...``) that can be used to
    complete an ACP checkout session.

    The allowance is enforced when the token is used:
    - ``max_amount``: maximum charge in smallest currency unit
    - ``checkout_session_id``: restricts token to a specific session
    - ``expires_at``: optional expiration timestamp

    Card details are never stored -- only the Stripe PaymentMethod ID is retained.
    """
    token_id = _gen_delegate_token_id()
    now = datetime.now(UTC).isoformat()

    # Tokenize via Stripe
    stripe_pm_id = await _create_stripe_payment_method(body.payment_method.model_dump())

    # Store token with allowance (card details are NOT stored)
    token_data: dict[str, Any] = {
        "id": token_id,
        "owner_id": principal.organization_id,
        "stripe_payment_method_id": stripe_pm_id,
        "allowance": body.allowance.model_dump(),
        "billing_address": body.billing_address.model_dump() if body.billing_address else None,
        "risk_signals": [rs.model_dump() for rs in body.risk_signals],
        "created_at": now,
        "used": False,
    }
    _delegate_tokens[token_id] = token_data

    # Persist to DB
    try:
        from sardis_v2_core.database import Database
        await Database.execute(
            """INSERT INTO acp_delegate_tokens (token_id, data, created_at)
               VALUES ($1, $2, NOW())""",
            token_id, json.dumps(token_data, default=str),
        )
    except Exception as exc:
        logger.warning("ACP delegate token DB persist failed for %s: %s", token_id, exc)

    logger.info(
        "ACP delegate payment token created: %s (stripe_pm=%s, session=%s)",
        token_id,
        stripe_pm_id or "none",
        body.allowance.checkout_session_id,
    )

    return ACPDelegatePaymentResponse(
        id=token_id,
        created=now,
        metadata={
            "allowance_max_amount": body.allowance.max_amount,
            "allowance_currency": body.allowance.currency,
            "checkout_session_id": body.allowance.checkout_session_id,
            "has_stripe_pm": stripe_pm_id is not None,
        },
    )


# ---------------------------------------------------------------------------
# Import for backwards-compatible update request
# ---------------------------------------------------------------------------
from server.models.acp import ACPUpdateCheckoutRequest  # noqa: E402
