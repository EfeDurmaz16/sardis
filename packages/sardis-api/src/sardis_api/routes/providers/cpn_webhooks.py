"""Circle Payments Network inbound webhook router."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os

from fastapi import APIRouter, Header, HTTPException, Request, status

logger = logging.getLogger("sardis.api.cpn_webhooks")

router = APIRouter(prefix="/cpn", tags=["cpn-webhooks"])

# Recognised CPN event types
PAYMENT_EVENTS = {
    "cpn.payment.completed",
    "cpn.payment.failed",
}

COLLECTION_EVENTS = {
    "cpn.collection.completed",
    "cpn.collection.failed",
}

ALL_CPN_EVENTS = PAYMENT_EVENTS | COLLECTION_EVENTS


def verify_cpn_signature(payload: bytes, signature: str, webhook_secret: str) -> bool:
    """Verify Circle CPN webhook signature using HMAC-SHA256.

    Circle CPN sends the hex-encoded HMAC-SHA256 of the raw request body in the
    ``Circle-Signature`` header.

    Args:
        payload: Raw request body bytes.
        signature: Value from the ``Circle-Signature`` header.
        webhook_secret: Shared secret configured in the Circle dashboard.

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.
    """
    try:
        computed = hmac.new(
            webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature.strip().lower())
    except Exception as exc:
        logger.error("CPN signature verification error: %s", exc)
        return False


@router.post("/webhooks", status_code=status.HTTP_200_OK)
async def handle_cpn_webhook(
    request: Request,
    circle_signature: str | None = Header(None, alias="Circle-Signature"),
) -> dict:
    """Handle inbound Circle CPN webhook events.

    Verifies the HMAC-SHA256 signature, parses the event body, and routes
    by event type. Always returns 200 OK after parsing so that Circle does
    not retry on transient handler errors.

    Returns:
        200 OK with ``{"received": True}`` on success.
        400 Bad Request on signature failure or unparseable payload.
    """
    webhook_secret = os.environ.get("CIRCLE_CPN_WEBHOOK_SECRET")
    if not webhook_secret:
        logger.error("CIRCLE_CPN_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    payload = await request.body()

    if not circle_signature:
        logger.warning("CPN webhook: missing Circle-Signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature",
        )

    if not verify_cpn_signature(payload, circle_signature, webhook_secret):
        logger.warning("CPN webhook: invalid signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        logger.error("CPN webhook: failed to parse JSON body: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )

    event_type = event.get("type") or event.get("eventType") or ""
    event_id = event.get("id") or event.get("eventId") or ""
    event_data = event.get("data") or {}

    logger.info("CPN webhook received: type=%s id=%s", event_type, event_id)

    try:
        if event_type in PAYMENT_EVENTS:
            await _handle_payment_event(event_type, event_id, event_data)
        elif event_type in COLLECTION_EVENTS:
            await _handle_collection_event(event_type, event_id, event_data)
        else:
            logger.debug("CPN webhook: unhandled event type %s", event_type)
    except Exception as exc:
        # Log but always return 200 to prevent CPN retries causing duplicates.
        logger.error(
            "CPN webhook handler error for event %s (%s): %s",
            event_type,
            event_id,
            exc,
            exc_info=True,
        )

    return {"received": True}


async def _handle_payment_event(
    event_type: str,
    event_id: str,
    data: dict,
) -> None:
    """Handle ``cpn.payment.*`` events (outbound payouts)."""
    payment_id = data.get("id") or data.get("paymentId") or data.get("payment_id") or event_id
    if event_type == "cpn.payment.completed":
        logger.info("CPN payment completed: payment_id=%s", payment_id)
    elif event_type == "cpn.payment.failed":
        reason = data.get("failureReason") or data.get("failure_reason") or "unknown"
        logger.warning("CPN payment failed: payment_id=%s reason=%s", payment_id, reason)


async def _handle_collection_event(
    event_type: str,
    event_id: str,
    data: dict,
) -> None:
    """Handle ``cpn.collection.*`` events (inbound receipts)."""
    collection_id = (
        data.get("id")
        or data.get("collectionId")
        or data.get("collection_id")
        or event_id
    )
    if event_type == "cpn.collection.completed":
        logger.info("CPN collection completed: collection_id=%s", collection_id)
    elif event_type == "cpn.collection.failed":
        reason = data.get("failureReason") or data.get("failure_reason") or "unknown"
        logger.warning(
            "CPN collection failed: collection_id=%s reason=%s", collection_id, reason
        )
