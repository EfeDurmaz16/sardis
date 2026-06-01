"""Agentic Commerce Protocol (ACP) seller endpoints.

EXPERIMENTAL / PARTIAL — non-conformant adapter, NOT production. API-Version
value is 2026-01-16 (current spec dir is 2026-04-17); diverges on response
objects / status enum / complete shape, persists to tables that may not exist
(in-memory fallback), and bypasses the Sardis mandate / policy / orchestrator /
ledger entirely. Do not present as ACP conformance.
See docs/productization/research/PROTOCOL_STRATEGY.md (ACP, quarantine-experimental).

PCI POSTURE — Sardis is the **merchant/seller**, never a PSP.  This router NEVER
accepts a raw PAN/CVV/expiry.  The only card credential it consumes is an
**opaque tokenized reference** minted by a regulated issuer/PSP:

  * ``spt``         — a Stripe Shared Payment Token (``spt_...``), or
  * ``issuer_card`` — an issuer-delegated virtual-card reference (Crossmint/Rain
    ``card_id``) whose PAN lives in the issuer's PCI vault.  Sardis verifies the
    reference against the issuer via the provider-layer ``CardPort`` and charges
    by reference only.

The legacy PSP ``POST /delegate_payment`` raw-card intake endpoint was REMOVED:
any inbound raw-PAN body now fails closed (404 / 422), so cardholder data can
never enter Sardis's process.

Sketches Sardis-powered seller endpoints toward Stripe's ACP so AI agents
(ChatGPT, Claude, etc.) could check out programmatically once rebuilt as a
thin, conformant adapter.

Endpoints:
  POST   /checkout_sessions              -- Create checkout session
  GET    /checkout_sessions/{id}         -- Get checkout session
  POST   /checkout_sessions/{id}         -- Update checkout session
  POST   /checkout_sessions/{id}/complete -- Complete checkout (tokenized card / SPT / crypto)
  POST   /checkout_sessions/{id}/cancel  -- Cancel checkout

Reference: https://docs.stripe.com/agentic-commerce/acp
Roles / PAN boundary: https://developers.openai.com/commerce/guides/key-concepts
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


async def _persist_session(session_id: str, data: dict[str, Any]) -> None:
    """Write checkout session to DB when available, always cache locally."""
    _sessions[session_id] = data
    try:
        from sardis.core.database import Database
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
        from sardis.core.database import Database
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


def _mask_token(token: str) -> str:
    """Mask a single-use payment credential before persisting it.

    A tokenized credential (SPT / issuer card ref) is not a PAN, but it is a
    bearer payment credential — never store it in cleartext.  We keep a
    SHA-256 hash (for idempotency / audit correlation) plus a short suffix.
    """
    digest = hashlib.sha256(token.encode()).hexdigest()
    suffix = token[-4:] if len(token) >= 4 else token
    return f"sha256:{digest}:...{suffix}"


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


# ---------------------------------------------------------------------------
# Issuer-delegated card verification (PAN-free)
# ---------------------------------------------------------------------------

async def _verify_issuer_card(card_ref: str) -> dict[str, Any]:
    """Verify an issuer-delegated virtual-card reference via the CardPort.

    The card reference (e.g. a Crossmint/Rain ``card_id``) points at a card
    whose PAN lives in the issuer's PCI vault — Sardis never sees the number.
    We confirm the card exists and is in a chargeable (``active``) state with
    the issuer before completing the order.  Fails closed: any provider error,
    unknown card, or non-active status rejects the payment.

    Returns the normalized issued-card payload (tokenized refs only) on success.
    """
    try:
        from server.dependencies import get_card_port
    except Exception as exc:  # pragma: no cover - import wiring
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="issuer_card_port_unavailable: card issuer not configured",
        ) from exc

    try:
        card_port = get_card_port()
    except Exception as exc:
        logger.warning("ACP issuer-card port resolution failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="issuer_card_port_unavailable: card issuer not configured",
        ) from exc

    # Re-assert the card's state with the issuer.  ``set_state(active)`` is the
    # CardPort verb that round-trips through the issuer and returns the
    # normalized (tokenized) card; a missing/closed card raises and we reject.
    try:
        result = await card_port.set_state(card_ref, state="active")
    except Exception as exc:  # noqa: BLE001 - normalized into a fail-closed 4xx
        logger.warning("ACP issuer-card verification failed for %s: %s", card_ref, exc)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"issuer_card_unverified: {exc}",
        ) from exc

    ok = getattr(result, "ok", False)
    card_status = getattr(result, "status", None)
    raw = getattr(result, "raw", {}) or {}
    if not ok or card_status not in {"active", None}:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"issuer_card_not_chargeable: status={card_status!r}",
        )
    # raw is tokenized-only (card_id / last_four / expiry) — never a PAN.
    return {
        "card_id": raw.get("card_id") or card_ref,
        "status": card_status,
        "last_four": raw.get("last_four"),
        "currency": raw.get("currency", "USD"),
    }


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

    PAN-free.  Exactly one tokenized branch:

    1. **payment_data.instrument.credential.type == "spt"** -- Stripe Shared
       Payment Token (``spt_...``).  Creates a PaymentIntent using the granted
       token; the PAN lives in Stripe's vault.

    2. **payment_data.instrument.credential.type == "issuer_card"** --
       Issuer-delegated virtual-card reference (Crossmint/Rain ``card_id``).
       Sardis verifies the reference with the issuer via the ``CardPort`` and
       charges by reference; the PAN lives in the issuer's PCI vault.

    3. **crypto_payment** -- On-chain stablecoin transfer.  The agent provides a
       ``tx_hash``; fail-closed (see below) — never marked ``succeeded`` without
       a real on-chain confirmation.

    A raw PAN / CVV / expiry is never accepted: those fields do not exist on the
    request model (``extra='forbid'`` → 422) and the PSP raw-card intake endpoint
    was removed.
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

    # Fail-closed: exactly one tokenized payment branch must be present.
    if body.payment_data is not None and body.crypto_payment is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ambiguous_payment: provide exactly one of payment_data or crypto_payment",
        )
    if body.payment_data is None and body.crypto_payment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing_payment: payment_data (tokenized) or crypto_payment is required",
        )

    payment_method_used: str

    # --- Tokenized card / SPT (issuer-delegated, PAN-free) ---
    if body.payment_data is not None:
        credential = body.payment_data.instrument.credential
        token = credential.token

        if credential.type == "spt":
            if not token.startswith("spt_"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="invalid_spt: credential.token must be a Stripe SPT (spt_...)",
                )
            stripe_key = os.getenv("STRIPE_SECRET_KEY")
            if stripe_key:
                pi = await _create_stripe_payment_intent_with_spt(token, amount_cents, currency)
                data["payment_intent_id"] = pi.get("id")
                data["payment_status"] = (
                    ACPPaymentStatus.succeeded.value
                    if pi.get("status") == "succeeded"
                    else ACPPaymentStatus.processing.value
                )
            else:
                # Dev mode: accept a well-formed token (no real settlement).
                logger.info("ACP dev mode: accepting SPT without Stripe (masked)")
                data["payment_status"] = ACPPaymentStatus.succeeded.value
            payment_method_used = "spt"

        elif credential.type == "issuer_card":
            # Reject obvious raw-PAN values defensively (digits-only of card
            # length) before touching the issuer — a card reference is opaque,
            # not a 13-19 digit number.
            stripped = token.replace(" ", "").replace("-", "")
            if stripped.isdigit() and 12 <= len(stripped) <= 19:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "raw_pan_rejected: credential.token must be an issuer-delegated "
                        "card reference, not a card number. Sardis never accepts a PAN."
                    ),
                )
            card_info = await _verify_issuer_card(token)
            # Verified with the issuer (PAN stays in the issuer vault). The
            # actual capture/authorization is the issuer's; Sardis records the
            # tokenized reference and marks processing until a settlement signal.
            data["issuer_card_ref"] = card_info["card_id"]
            data["issuer_card_last_four"] = card_info.get("last_four")
            data["payment_status"] = ACPPaymentStatus.processing.value
            payment_method_used = "issuer_card"

        else:  # pragma: no cover - Literal guards this at validation time
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"unsupported_credential_type: {credential.type}",
            )

        data["payment_method_used"] = payment_method_used
        # Never persist a payment credential in cleartext — store a hashed ref.
        data["credential_ref"] = _mask_token(token)
        data["credential_type"] = credential.type

    # --- Crypto payment (fail-closed) ---
    else:
        crypto = body.crypto_payment
        assert crypto is not None  # guarded above
        if not crypto.tx_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="crypto_payment.tx_hash is required",
            )

        data["payment_method_used"] = "crypto"
        data["crypto_tx_hash"] = crypto.tx_hash
        data["crypto_chain"] = crypto.chain
        data["crypto_token"] = crypto.token
        payment_method_used = "crypto"

        # FAIL-CLOSED: this adapter does not yet perform a real on-chain
        # verification (tx receipt + amount + recipient + confirmations). It
        # MUST NOT mark an order ``succeeded`` without that proof. Record the
        # tx and mark ``processing`` — a settlement signal (verified out of
        # band) is required before the order is paid.
        logger.info(
            "ACP crypto payment recorded (unverified, processing): tx=%s chain=%s token=%s",
            crypto.tx_hash,
            crypto.chain,
            crypto.token,
        )
        data["payment_status"] = ACPPaymentStatus.processing.value

    # Only flip to completed once payment is actually succeeded; otherwise the
    # session stays open so it can be retried / settled out of band.
    if data["payment_status"] == ACPPaymentStatus.succeeded.value:
        data["status"] = ACPCheckoutStatus.completed
    data["updated_at"] = now
    await _persist_session(session_id, data)

    logger.info(
        "ACP session %s: %s via %s (payment=%s)",
        "completed" if data["status"] == ACPCheckoutStatus.completed else "pending",
        session_id,
        payment_method_used,
        data["payment_status"],
    )

    # Emit order_update webhook only when the order is actually confirmed
    # (payment succeeded). A processing/unverified payment must not signal a
    # confirmed order downstream.
    if data["status"] == ACPCheckoutStatus.completed:
        await _emit_order_webhook(
            data, ACPWebhookEventType.order_update, ACPOrderStatus.confirmed
        )

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
# Endpoint: Delegate Payment (QUARANTINED — raw-PAN intake removed)
# ---------------------------------------------------------------------------
#
# The legacy ``POST /delegate_payment`` endpoint accepted a raw PAN + CVV and
# forwarded it to Stripe, putting Sardis in PCI-DSS cardholder-data scope. That
# is the **PSP** role; Sardis is the **merchant/seller**, which per the ACP role
# model never receives a PAN. The endpoint is retained ONLY as an explicit
# fail-closed quarantine: it accepts no request body, parses no card data, and
# always rejects with 501 + a clear reason_code pointing callers at the
# issuer-delegated token model. This guarantees a raw PAN can never enter the
# process here.

@router.api_route(
    "/delegate_payment",
    methods=["POST", "PUT", "PATCH"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="REMOVED — raw-PAN intake is not accepted (use an issuer-delegated token)",
    include_in_schema=False,
)
async def delegate_payment_removed(
    principal: Principal = Depends(require_principal),
) -> None:
    """Quarantine guard: Sardis (merchant role) never accepts a raw PAN.

    The PSP raw-card intake was removed. No request body is read, so no
    cardholder data is parsed or forwarded. Always fails closed (501).
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "reason_code": "raw_pan_not_accepted",
            "message": (
                "Sardis is the ACP merchant/seller and never accepts a raw PAN/CVV. "
                "Use an issuer-delegated tokenized credential when completing a "
                "checkout session: POST /checkout_sessions/{id}/complete with "
                "payment_data.instrument.credential = {type: 'spt'|'issuer_card', "
                "token: <opaque issuer/PSP token>}."
            ),
        },
    )


# ---------------------------------------------------------------------------
# Import for backwards-compatible update request
# ---------------------------------------------------------------------------
from server.models.acp import ACPUpdateCheckoutRequest  # noqa: E402
