"""Visa TAP inbound webhook router for token lifecycle and authorization events."""
from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, Header, HTTPException, Request, status
from sardis_v2_core.delegated_adapters.visa_tap import verify_visa_tap_signature

logger = logging.getLogger("sardis.api.visa_tap_webhooks")

router = APIRouter(prefix="/visa-tap", tags=["visa-tap-webhooks"])

# ---------------------------------------------------------------------------
# Event type sets for routing
# ---------------------------------------------------------------------------

TOKEN_LIFECYCLE_EVENTS = {
    "token.suspended",
    "token.expired",
    "token.deactivated",
    "token.activated",
    "token.deleted",
}

AUTHORIZATION_EVENTS = {
    "authorization.approved",
    "authorization.declined",
    "authorization.reversed",
    "authorization.updated",
}


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


async def _handle_token_lifecycle(event_type: str, event_data: dict) -> None:
    """Process Visa token lifecycle events (suspended / expired / deactivated)."""
    token_id = event_data.get("tokenId") or event_data.get("token_id", "")
    logger.info(
        "Visa TAP token lifecycle event: type=%s token_id=%s",
        event_type,
        token_id,
    )
    # TODO: update DelegatedCredential status in DB when credential store is wired
    # e.g. await credential_store.update_status(token_id, new_status)


async def _handle_authorization_result(event_type: str, event_data: dict) -> None:
    """Process Visa TAP authorization result events."""
    transaction_id = (
        event_data.get("transactionId")
        or event_data.get("transaction_id", "")
    )
    response_code = event_data.get("responseCode", "")
    logger.info(
        "Visa TAP authorization event: type=%s transaction_id=%s response_code=%s",
        event_type,
        transaction_id,
        response_code,
    )
    # TODO: persist authorization outcome to ledger when wired


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------


@router.post("/webhooks", status_code=status.HTTP_200_OK)
async def handle_visa_tap_webhook(
    request: Request,
    x_visa_signature: str | None = Header(None, alias="X-Visa-Signature"),
):
    """Handle inbound Visa TAP webhook events.

    Receives token lifecycle events (suspended, expired, deactivated) and
    authorization results from Visa.  HMAC-SHA256 signature verification is
    performed using the VISA_TAP_WEBHOOK_SECRET environment variable.

    Returns:
        200 OK always — returning non-2xx would cause Visa to retry.
        400 Bad Request on missing or invalid signature.
    """
    # Read raw body before any parsing (signature is over raw bytes)
    payload = await request.body()

    # Resolve webhook secret
    webhook_secret = os.environ.get("VISA_TAP_WEBHOOK_SECRET")
    if not webhook_secret:
        logger.error("VISA_TAP_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    # Require signature header
    if not x_visa_signature:
        logger.warning("Missing X-Visa-Signature header on Visa TAP webhook")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature",
        )

    # Verify HMAC-SHA256 signature
    if not verify_visa_tap_signature(payload, x_visa_signature, webhook_secret):
        logger.warning("Visa TAP webhook signature verification failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Parse JSON body
    try:
        event = json.loads(payload)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Visa TAP webhook payload: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )

    event_type = str(event.get("type") or event.get("event_type") or "")
    event_data = event.get("data") or {}
    event_id = event.get("eventId") or event.get("event_id") or ""

    logger.info(
        "Visa TAP webhook received: type=%s event_id=%s",
        event_type,
        event_id,
    )

    # Route by event type — always return 200 even if handler raises
    try:
        if event_type in TOKEN_LIFECYCLE_EVENTS:
            await _handle_token_lifecycle(event_type, event_data)
        elif event_type in AUTHORIZATION_EVENTS:
            await _handle_authorization_result(event_type, event_data)
        else:
            logger.debug("Unhandled Visa TAP event type: %s", event_type)
    except Exception as e:
        # Log error but return 200 to prevent Visa retries on transient failures
        logger.error(
            "Error handling Visa TAP webhook event %s: %s",
            event_type,
            e,
            exc_info=True,
        )

    return {"received": True}
