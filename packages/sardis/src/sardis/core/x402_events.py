"""x402 event normalization (commercetools webhook event converter pattern).

Converts x402 settlement state transitions into Sardis-canonical event types
for the webhook/event system.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

# Canonical x402 event types
X402_EVENT_CHALLENGE_CREATED = "x402.challenge.created"
X402_EVENT_PAYMENT_VERIFIED = "x402.payment.verified"
X402_EVENT_PAYMENT_SETTLED = "x402.payment.settled"
X402_EVENT_PAYMENT_FAILED = "x402.payment.failed"
X402_EVENT_DRY_RUN = "x402.payment.dry_run"

ALL_X402_EVENT_TYPES = [
    X402_EVENT_CHALLENGE_CREATED,
    X402_EVENT_PAYMENT_VERIFIED,
    X402_EVENT_PAYMENT_SETTLED,
    X402_EVENT_PAYMENT_FAILED,
    X402_EVENT_DRY_RUN,
]


def normalize_x402_event(
    event_type: str,
    *,
    payment_id: str = "",
    network: str = "",
    amount: str = "",
    currency: str = "USDC",
    source: str = "server",
    agent_id: str = "",
    org_id: str = "",
    tx_hash: str = "",
    error: str = "",
    resource_uri: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize an x402 state transition into a Sardis event.

    Returns a dict suitable for the webhook/event delivery system.
    """
    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:16]}",
        "event_type": event_type,
        "timestamp": int(time.time()),
        "data": {
            "payment_id": payment_id,
            "network": network,
            "amount": amount,
            "currency": currency,
            "source": source,
            "agent_id": agent_id,
            "org_id": org_id,
        },
    }

    if tx_hash:
        event["data"]["tx_hash"] = tx_hash
    if error:
        event["data"]["error"] = error
    if resource_uri:
        event["data"]["resource_uri"] = resource_uri
    if extra:
        event["data"].update(extra)

    return event


def settlement_status_to_event_type(status: str) -> str | None:
    """Map settlement status to event type."""
    mapping = {
        "verified": X402_EVENT_PAYMENT_VERIFIED,
        "settled": X402_EVENT_PAYMENT_SETTLED,
        "failed": X402_EVENT_PAYMENT_FAILED,
    }
    return mapping.get(status)


__all__ = [
    "X402_EVENT_CHALLENGE_CREATED",
    "X402_EVENT_PAYMENT_VERIFIED",
    "X402_EVENT_PAYMENT_SETTLED",
    "X402_EVENT_PAYMENT_FAILED",
    "X402_EVENT_DRY_RUN",
    "ALL_X402_EVENT_TYPES",
    "normalize_x402_event",
    "settlement_status_to_event_type",
]
