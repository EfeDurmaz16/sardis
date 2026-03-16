"""Polar.sh webhook endpoint for subscription lifecycle events."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/polar-webhook")
async def polar_webhook(request: Request):
    """Handle Polar.sh webhook events.

    Events:
    - subscription.created — new subscriber, sync to billing_subscriptions
    - subscription.updated — plan change
    - subscription.canceled — cancellation, downgrade to free
    - order.created — one-time payment
    """
    body = await request.body()
    signature = request.headers.get("x-polar-signature", "")

    from sardis_api.billing.polar_adapter import PolarBillingAdapter

    adapter = PolarBillingAdapter()

    if adapter.is_configured and signature:
        if not adapter.verify_webhook(body, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    try:
        import json
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("type", payload.get("event", ""))
    data = payload.get("data", payload)

    logger.info("Polar webhook received: %s", event_type)

    await adapter.handle_webhook_event(event_type, data)

    return {"received": True}
