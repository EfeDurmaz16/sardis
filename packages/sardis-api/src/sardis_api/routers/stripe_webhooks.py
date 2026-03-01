"""Stripe inbound webhook router for Treasury and Issuing events."""
from __future__ import annotations

import hmac
import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

logger = logging.getLogger("sardis.api.stripe_webhooks")

router = APIRouter(prefix="/stripe", tags=["stripe-webhooks"])

# Event type sets for routing
TREASURY_EVENTS = {
    "treasury.received_credit",
    "treasury.outbound_payment.posted",
    "treasury.outbound_payment.failed",
    "treasury.financial_account.features_status_updated",
}

ISSUING_EVENTS = {
    "issuing_authorization.request",
    "issuing_authorization.created",
    "issuing_authorization.updated",
    "issuing_transaction.created",
    "issuing_transaction.updated",
}


class StripeWebhookDeps:
    """Dependencies for Stripe webhook handling."""

    def __init__(self, treasury_provider, issuing_provider):
        self.treasury_provider = treasury_provider
        self.issuing_provider = issuing_provider


def get_deps() -> StripeWebhookDeps:
    """Dependency injection placeholder - must be overridden."""
    raise NotImplementedError("Must be overridden")


def verify_stripe_signature(payload: bytes, signature: str, webhook_secret: str) -> bool:
    """Verify Stripe webhook signature using HMAC-SHA256.

    Args:
        payload: Raw request body bytes
        signature: Value from Stripe-Signature header
        webhook_secret: Stripe webhook signing secret

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Parse signature header (format: "t=timestamp,v1=signature,v0=signature")
        sig_parts = {}
        for part in signature.split(","):
            key, value = part.split("=", 1)
            sig_parts[key] = value

        timestamp = sig_parts.get("t")
        expected_sig = sig_parts.get("v1")

        if not timestamp or not expected_sig:
            logger.warning("Missing timestamp or signature in Stripe-Signature header")
            return False

        # Construct signed payload: timestamp.payload
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"

        # Compute HMAC-SHA256
        computed_sig = hmac.new(
            webhook_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Compare signatures
        return hmac.compare_digest(computed_sig, expected_sig)

    except Exception as e:
        logger.error("Signature verification failed: %s", e)
        return False


@router.post("/webhooks", status_code=status.HTTP_200_OK)
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    deps: StripeWebhookDeps = Depends(get_deps),
):
    """Handle inbound Stripe webhook events for Treasury and Issuing.

    This endpoint receives events from Stripe when:
    - Treasury: Credits received, outbound payments completed/failed, feature status changes
    - Issuing: Card authorizations, transactions created/updated

    Signature verification is performed to ensure events are authentic.
    Events are routed to appropriate handlers based on event type prefix.

    Returns:
        200 OK on success (even if handler fails, to prevent Stripe retries)
        400 Bad Request on signature verification failure
    """
    # Get webhook secret from environment
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    # Read raw body
    payload = await request.body()

    # Verify signature
    if not stripe_signature:
        logger.warning("Missing Stripe-Signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature",
        )

    # Try using Stripe SDK if available, otherwise use manual verification
    try:
        import stripe

        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, webhook_secret
            )
            event_type = event.get("type")
            event_data = event.get("data", {}).get("object", {})
            logger.info("Stripe webhook received: %s (id=%s)", event_type, event.get("id"))
        except stripe.error.SignatureVerificationError as e:
            logger.warning("Stripe signature verification failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature",
            )
        except Exception as e:
            logger.error("Error constructing Stripe event: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid event",
            )

    except ImportError:
        # Stripe SDK not available, use manual verification
        logger.debug("Stripe SDK not available, using manual signature verification")

        if not verify_stripe_signature(payload, stripe_signature, webhook_secret):
            logger.warning("Manual signature verification failed")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature",
            )

        # Parse event from payload
        import json
        try:
            event = json.loads(payload)
            event_type = event.get("type")
            event_data = event.get("data", {}).get("object", {})
            logger.info("Stripe webhook received: %s (id=%s)", event_type, event.get("id"))
        except json.JSONDecodeError as e:
            logger.error("Failed to parse webhook payload: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON",
            )

    # Route event to appropriate handler
    try:
        if event_type in TREASURY_EVENTS:
            logger.info("Routing %s to Treasury handler", event_type)
            await deps.treasury_provider.handle_webhook(event_type, event_data)

        elif event_type in ISSUING_EVENTS:
            logger.info("Routing %s to Issuing handler", event_type)

            # Special handling for authorization.request (requires response)
            if event_type == "issuing_authorization.request":
                # This requires real-time response with approve/decline
                response = await deps.issuing_provider.handle_authorization_webhook(
                    payload, stripe_signature
                )

                # Persist authorization decision for audit trail
                try:
                    authorization = event_data
                    merchant_data = authorization.get("merchant_data", {})
                    amount_cents = authorization.get("amount", 0)
                    card_id = authorization.get("card", {})
                    if isinstance(card_id, dict):
                        card_id = card_id.get("id", "")
                    approved = response.get("approved", False)
                    reason = (response.get("metadata") or {}).get("reason", "")

                    from sardis_v2_core.database import Database
                    async with Database.connection() as conn:
                        await conn.execute(
                            """INSERT INTO card_transactions
                               (transaction_id, card_id, provider_tx_id, amount, currency,
                                merchant_name, merchant_category, merchant_id,
                                status, decline_reason, created_at)
                               SELECT $1, vc.id, $3, $4, $5, $6, $7, $8, $9, $10, $11
                               FROM virtual_cards vc
                               WHERE vc.provider_card_id = $2
                               LIMIT 1""",
                            f"auth_{authorization.get('id', uuid.uuid4().hex[:16])}",
                            str(card_id),
                            authorization.get("id", ""),
                            abs(amount_cents) / 100,
                            authorization.get("currency", "usd").upper(),
                            merchant_data.get("name", ""),
                            merchant_data.get("category_code", ""),
                            merchant_data.get("network_id", ""),
                            "approved" if approved else "declined",
                            reason if not approved else None,
                            datetime.now(timezone.utc),
                        )
                    logger.info(
                        "Authorization decision persisted: card=%s amount=%s approved=%s",
                        card_id, amount_cents, approved,
                    )
                except Exception as persist_err:
                    # Never fail the webhook response due to persistence error
                    logger.error("Failed to persist authorization decision: %s", persist_err)

                return response
            else:
                # Other issuing events are informational
                logger.debug("Issuing event %s recorded (no action required)", event_type)

        else:
            logger.debug("Unhandled Stripe event type: %s", event_type)

    except Exception as e:
        # Log error but return 200 to prevent Stripe retries
        # Stripe will retry on non-2xx responses, which could cause duplicates
        logger.error(
            "Error handling webhook event %s: %s",
            event_type,
            e,
            exc_info=True,
        )

    return {"received": True}
