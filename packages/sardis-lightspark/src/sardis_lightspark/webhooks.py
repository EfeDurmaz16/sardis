"""Lightspark Grid webhook handler with X-Grid-Signature verification."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from .exceptions import GridWebhookVerificationError

logger = logging.getLogger(__name__)


class GridWebhookEventType(str, Enum):
    """Grid webhook event types."""
    TRANSFER_COMPLETED = "transfer.completed"
    TRANSFER_FAILED = "transfer.failed"
    TRANSFER_REFUNDED = "transfer.refunded"
    PAYMENT_RECEIVED = "payment.received"
    UMA_PAYMENT_RECEIVED = "uma.payment.received"
    CUSTOMER_VERIFIED = "customer.verified"
    BANK_ACCOUNT_LINKED = "bank_account.linked"


@dataclass
class GridWebhookEvent:
    """Parsed Grid webhook event."""
    event_id: str
    event_type: GridWebhookEventType
    created_at: datetime
    data: dict[str, Any]

    @property
    def transfer_id(self) -> str | None:
        return self.data.get("transferId") or self.data.get("transfer_id")

    @property
    def amount_cents(self) -> int | None:
        amount = self.data.get("amount")
        return int(amount) if amount is not None else None

    @property
    def currency(self) -> str | None:
        return self.data.get("currency")

    @property
    def uma_address(self) -> str | None:
        return self.data.get("umaAddress") or self.data.get("uma_address")


class GridWebhookHandler:
    """Handler for Grid webhook events with X-Grid-Signature SHA-256 verification."""

    def __init__(self, webhook_secret: str):
        self._secret = webhook_secret

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Grid webhook signature (SHA-256 HMAC).

        Args:
            payload: Raw request body bytes
            signature: Value from X-Grid-Signature header

        Returns:
            True if signature is valid
        """
        expected = hmac.new(
            self._secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_event(self, payload: bytes) -> GridWebhookEvent:
        """Parse webhook payload into a GridWebhookEvent."""
        data = json.loads(payload)

        raw_type = data.get("type", data.get("event_type", ""))
        try:
            event_type = GridWebhookEventType(raw_type)
        except ValueError:
            logger.warning(f"Unknown Grid webhook event type: {raw_type}")
            event_type = GridWebhookEventType.TRANSFER_COMPLETED

        return GridWebhookEvent(
            event_id=data.get("eventId", data.get("event_id", data.get("id", ""))),
            event_type=event_type,
            created_at=datetime.now(UTC),
            data=data.get("data", data),
        )

    def verify_and_parse(
        self, payload: bytes, signature: str
    ) -> GridWebhookEvent:
        """
        Verify signature and parse webhook event.

        Raises:
            GridWebhookVerificationError: If signature verification fails
        """
        if not self.verify_signature(payload, signature):
            raise GridWebhookVerificationError("Invalid webhook signature")

        return self.parse_event(payload)
