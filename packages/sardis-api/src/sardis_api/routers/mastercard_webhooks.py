"""Mastercard Agent Pay inbound webhook router.

Handles MDES token lifecycle events and authorization results.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os

from fastapi import APIRouter, Header, HTTPException, Request, status

logger = logging.getLogger("sardis.api.mastercard_webhooks")

router = APIRouter(prefix="/mastercard", tags=["mastercard-webhooks"])

# Token lifecycle event types
TOKEN_LIFECYCLE_EVENTS = {
    "TOKEN_CREATED",
    "TOKEN_ACTIVE",
    "TOKEN_SUSPENDED",
    "TOKEN_DELETED",
    "TOKEN_EXPIRED",
}

# Authorization result event types
AUTHORIZATION_EVENTS = {
    "AUTHORIZATION_APPROVED",
    "AUTHORIZATION_DECLINED",
    "AUTHORIZATION_REVERSED",
}


def verify_mastercard_signature(payload: bytes, signature: str, webhook_secret: str) -> bool:
    """Verify Mastercard webhook HMAC-SHA256 signature.

    Args:
        payload: Raw request body bytes
        signature: Value from X-Mastercard-Signature header
        webhook_secret: Mastercard webhook signing secret

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        computed = hmac.new(
            webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)
    except Exception as e:
        logger.error("Mastercard signature verification error: %s", e)
        return False


@router.post("/webhooks", status_code=status.HTTP_200_OK)
async def handle_mastercard_webhook(
    request: Request,
    x_mastercard_signature: str | None = Header(None, alias="X-Mastercard-Signature"),
):
    """Handle inbound Mastercard Agent Pay / MDES webhook events.

    Processes token lifecycle events (created, active, suspended, deleted,
    expired) and authorization results (approved, declined, reversed).

    HMAC-SHA256 signature verification is performed using the
    MASTERCARD_WEBHOOK_SECRET environment variable when configured.

    Always returns 200 OK to acknowledge receipt and prevent retries,
    even when individual event processing encounters errors.
    """
    webhook_secret = os.environ.get("MASTERCARD_WEBHOOK_SECRET", "")

    payload = await request.body()

    # Verify signature when secret is configured
    if webhook_secret:
        if not x_mastercard_signature:
            logger.warning("Missing X-Mastercard-Signature header")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing signature",
            )
        if not verify_mastercard_signature(payload, x_mastercard_signature, webhook_secret):
            logger.warning("Mastercard webhook signature verification failed")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature",
            )
    else:
        logger.debug("MASTERCARD_WEBHOOK_SECRET not configured — skipping signature check")

    # Parse event payload
    try:
        event = json.loads(payload)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Mastercard webhook payload: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )

    event_type = str(event.get("type") or event.get("eventType") or "").strip().upper()
    event_id = str(event.get("id") or event.get("eventId") or "")

    logger.info(
        "Mastercard webhook received: type=%s id=%s",
        event_type,
        event_id,
    )

    try:
        if event_type in TOKEN_LIFECYCLE_EVENTS:
            _handle_token_lifecycle(event_type, event)
        elif event_type in AUTHORIZATION_EVENTS:
            _handle_authorization_result(event_type, event)
        else:
            logger.debug("Unhandled Mastercard event type: %s", event_type)
    except Exception as e:
        # Log error but return 200 to prevent Mastercard retries
        logger.error(
            "Error handling Mastercard webhook event %s: %s",
            event_type,
            e,
            exc_info=True,
        )

    return {"received": True}


def _handle_token_lifecycle(event_type: str, event: dict) -> None:
    """Process MDES token lifecycle event."""
    token_ref = (
        (event.get("data") or {}).get("tokenUniqueReference")
        or event.get("tokenUniqueReference")
        or ""
    )
    logger.info(
        "MDES token lifecycle: event=%s token_ref=%s",
        event_type,
        token_ref,
    )
    # TODO: Update DelegatedCredential status in store when token state changes
    # e.g. TOKEN_SUSPENDED → CredentialStatus.SUSPENDED
    #      TOKEN_DELETED   → CredentialStatus.REVOKED


def _handle_authorization_result(event_type: str, event: dict) -> None:
    """Process MDES authorization result event."""
    data = event.get("data") or event
    transaction_id = str(data.get("transactionId") or "")
    authorization_code = str(data.get("authorizationCode") or "")
    logger.info(
        "MDES authorization result: event=%s transaction_id=%s auth_code=%s",
        event_type,
        transaction_id,
        authorization_code,
    )
    # TODO: Record authorization outcome in ledger / audit trail
