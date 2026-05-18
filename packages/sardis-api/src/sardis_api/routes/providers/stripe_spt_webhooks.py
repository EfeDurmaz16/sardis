"""Stripe SPT inbound webhook router for payment_intent events."""
from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, Header, HTTPException, Request, status

from .stripe_webhooks import verify_stripe_signature

logger = logging.getLogger("sardis.api.stripe_spt_webhooks")

router = APIRouter(prefix="/stripe-spt", tags=["stripe-spt-webhooks"])

# Event types handled by this router
SPT_EVENTS = {
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
}


@router.post("/webhooks", status_code=status.HTTP_200_OK)
async def handle_stripe_spt_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
) -> dict:
    """Handle inbound Stripe SPT webhook events for payment_intent lifecycle.

    Verifies the Stripe-Signature header using HMAC-SHA256 before processing.
    Always returns 200 OK after verification to prevent Stripe from retrying.

    Handled events:
    - ``payment_intent.succeeded``: payment completed successfully
    - ``payment_intent.payment_failed``: payment attempt failed

    Returns:
        200 OK with ``{"received": True}`` on success.
        400 Bad Request on missing/invalid signature or malformed payload.
    """
    webhook_secret = os.environ.get("STRIPE_SPT_WEBHOOK_SECRET")
    if not webhook_secret:
        logger.error("STRIPE_SPT_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    payload = await request.body()

    if not stripe_signature:
        logger.warning("Missing Stripe-Signature header on SPT webhook")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature",
        )

    if not verify_stripe_signature(payload, stripe_signature, webhook_secret):
        logger.warning("Stripe SPT webhook signature verification failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Stripe SPT webhook payload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        ) from exc

    event_type: str = event.get("type", "")
    event_id: str = event.get("id", "")
    payment_intent: dict = event.get("data", {}).get("object", {})
    pi_id: str = payment_intent.get("id", "")

    logger.info(
        "Stripe SPT webhook received: type=%s id=%s payment_intent=%s",
        event_type,
        event_id,
        pi_id,
    )

    try:
        if event_type == "payment_intent.succeeded":
            _handle_payment_succeeded(event_id, payment_intent)
        elif event_type == "payment_intent.payment_failed":
            _handle_payment_failed(event_id, payment_intent)
        else:
            logger.debug("Unhandled Stripe SPT event type: %s", event_type)
    except Exception as exc:
        # Log the error but always return 200 to prevent Stripe retries
        logger.error(
            "Error handling Stripe SPT webhook event %s (id=%s): %s",
            event_type,
            event_id,
            exc,
            exc_info=True,
        )

    return {"received": True}


def _handle_payment_succeeded(event_id: str, payment_intent: dict) -> None:
    """Process a succeeded payment_intent event."""
    pi_id = payment_intent.get("id", "")
    amount = payment_intent.get("amount", 0)
    currency = payment_intent.get("currency", "").upper()
    logger.info(
        "Stripe SPT payment_intent.succeeded event_id=%s pi=%s amount=%s %s",
        event_id,
        pi_id,
        amount,
        currency,
    )


def _handle_payment_failed(event_id: str, payment_intent: dict) -> None:
    """Process a payment_failed payment_intent event."""
    pi_id = payment_intent.get("id", "")
    last_error = payment_intent.get("last_payment_error", {})
    error_code = last_error.get("code", "unknown")
    error_message = last_error.get("message", "")
    logger.warning(
        "Stripe SPT payment_intent.payment_failed event_id=%s pi=%s code=%s message=%s",
        event_id,
        pi_id,
        error_code,
        error_message,
    )
