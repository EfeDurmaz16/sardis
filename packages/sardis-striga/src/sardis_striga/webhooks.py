"""Striga webhook handler with HMAC-SHA256 signature verification."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from .exceptions import StrigaWebhookVerificationError

logger = logging.getLogger(__name__)


class StrigaWebhookEventType(str, Enum):
    """Striga webhook event types."""
    # Card events
    CARD_CREATED = "card.created"
    CARD_ACTIVATED = "card.activated"
    CARD_FROZEN = "card.frozen"
    CARD_UNFROZEN = "card.unfrozen"
    CARD_CANCELLED = "card.cancelled"
    CARD_EXPIRED = "card.expired"

    # Transaction events
    TRANSACTION_AUTHORIZATION = "transaction.authorization"
    TRANSACTION_SETTLED = "transaction.settled"
    TRANSACTION_DECLINED = "transaction.declined"
    TRANSACTION_REVERSED = "transaction.reversed"
    TRANSACTION_REFUND = "transaction.refund"

    # SEPA events
    SEPA_INCOMING = "sepa.incoming"
    SEPA_OUTGOING_COMPLETED = "sepa.outgoing.completed"
    SEPA_OUTGOING_FAILED = "sepa.outgoing.failed"

    # Swap events
    SWAP_COMPLETED = "swap.completed"
    SWAP_FAILED = "swap.failed"

    # KYC events
    KYC_APPROVED = "kyc.approved"
    KYC_REJECTED = "kyc.rejected"
    KYC_REVIEW = "kyc.review"

    # Wallet events
    WALLET_DEPOSIT = "wallet.deposit"
    WALLET_WITHDRAWAL = "wallet.withdrawal"


@dataclass
class StrigaWebhookEvent:
    """Parsed Striga webhook event."""
    event_id: str
    event_type: StrigaWebhookEventType
    created_at: datetime
    data: dict[str, Any]

    @property
    def user_id(self) -> str | None:
        return self.data.get("userId") or self.data.get("user_id")

    @property
    def wallet_id(self) -> str | None:
        return self.data.get("walletId") or self.data.get("wallet_id")

    @property
    def card_id(self) -> str | None:
        return self.data.get("cardId") or self.data.get("card_id")

    @property
    def transaction_id(self) -> str | None:
        return self.data.get("transactionId") or self.data.get("transaction_id")

    @property
    def amount_cents(self) -> int | None:
        amount = self.data.get("amount")
        if amount is not None:
            return int(amount)
        return None

    @property
    def currency(self) -> str | None:
        return self.data.get("currency")


class StrigaWebhookHandler:
    """Handler for Striga webhook events with HMAC-SHA256 verification."""

    def __init__(self, webhook_secret: str):
        self._secret = webhook_secret

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Striga webhook signature (HMAC-SHA256).

        Args:
            payload: Raw request body bytes
            signature: Signature from X-Striga-Signature header

        Returns:
            True if signature is valid
        """
        expected = hmac.new(
            self._secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_event(self, payload: bytes) -> StrigaWebhookEvent:
        """
        Parse webhook payload into a StrigaWebhookEvent.

        Args:
            payload: Raw request body bytes

        Returns:
            Parsed StrigaWebhookEvent
        """
        data = json.loads(payload)

        raw_type = data.get("type", data.get("event_type", ""))
        try:
            event_type = StrigaWebhookEventType(raw_type)
        except ValueError:
            logger.warning(f"Unknown Striga webhook event type: {raw_type}")
            event_type = StrigaWebhookEventType.TRANSACTION_AUTHORIZATION

        return StrigaWebhookEvent(
            event_id=data.get("eventId", data.get("event_id", data.get("id", ""))),
            event_type=event_type,
            created_at=datetime.now(UTC),
            data=data.get("data", data),
        )

    def verify_and_parse(
        self, payload: bytes, signature: str
    ) -> StrigaWebhookEvent:
        """
        Verify signature and parse webhook event.

        Args:
            payload: Raw request body bytes
            signature: Signature from X-Striga-Signature header

        Returns:
            Parsed StrigaWebhookEvent

        Raises:
            StrigaWebhookVerificationError: If signature verification fails
        """
        if not self.verify_signature(payload, signature):
            raise StrigaWebhookVerificationError("Invalid webhook signature")

        return self.parse_event(payload)
