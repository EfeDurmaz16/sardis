"""Webhook handling for card transaction events."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Optional
import hashlib
import hmac
import json
import logging

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Types of card webhook events."""
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_UPDATED = "transaction.updated"
    TRANSACTION_SETTLED = "transaction.settled"
    TRANSACTION_DECLINED = "transaction.declined"
    TRANSACTION_REVERSED = "transaction.reversed"
    CARD_CREATED = "card.created"
    CARD_ACTIVATED = "card.activated"
    CARD_FROZEN = "card.frozen"
    CARD_CANCELLED = "card.cancelled"


@dataclass
class WebhookEvent:
    """Parsed webhook event."""
    event_id: str
    event_type: WebhookEventType
    created_at: datetime
    data: dict[str, Any]
    
    # Convenience properties for transaction events
    @property
    def card_id(self) -> Optional[str]:
        return self.data.get("card_token") or self.data.get("card_id")
    
    @property
    def transaction_id(self) -> Optional[str]:
        return self.data.get("token") or self.data.get("transaction_id")
    
    @property
    def amount(self) -> Optional[Decimal]:
        amount = self.data.get("amount")
        if amount is not None:
            # Lithic sends amounts in cents
            return Decimal(str(amount)) / 100
        return None
    
    @property
    def merchant_name(self) -> Optional[str]:
        merchant = self.data.get("merchant", {})
        return merchant.get("descriptor") or merchant.get("name")


class CardWebhookHandler:
    """
    Handler for card provider webhooks.
    
    Verifies signatures and parses events from card providers.
    """
    
    def __init__(self, secret: str, provider: str = "lithic") -> None:
        """
        Initialize webhook handler.
        
        Args:
            secret: Webhook signing secret from provider
            provider: Provider name (lithic, marqeta, etc.)
        """
        self._secret = secret
        self._provider = provider
    
    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Raw request body bytes
            signature: Signature from provider header
            timestamp: Optional timestamp for replay protection
            
        Returns:
            True if signature is valid
        """
        if self._provider == "lithic":
            return self._verify_lithic_signature(payload, signature)
        elif self._provider == "marqeta":
            return self._verify_marqeta_signature(payload, signature)
        else:
            # For mock provider, always return True
            return True
    
    def _verify_lithic_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Lithic webhook signature (HMAC-SHA256)."""
        expected = hmac.new(
            self._secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    
    def _verify_marqeta_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Marqeta webhook signature."""
        # Marqeta uses a similar HMAC approach
        expected = hmac.new(
            self._secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    
    def parse_event(self, payload: bytes) -> WebhookEvent:
        """
        Parse webhook payload into an event.
        
        Args:
            payload: Raw request body bytes
            
        Returns:
            Parsed WebhookEvent
        """
        data = json.loads(payload)
        
        if self._provider == "lithic":
            return self._parse_lithic_event(data)
        elif self._provider == "marqeta":
            return self._parse_marqeta_event(data)
        else:
            return self._parse_generic_event(data)
    
    def _parse_lithic_event(self, data: dict) -> WebhookEvent:
        """Parse Lithic webhook event."""
        event_type_map = {
            "transaction.created": WebhookEventType.TRANSACTION_CREATED,
            "transaction.updated": WebhookEventType.TRANSACTION_UPDATED,
            "transaction.voided": WebhookEventType.TRANSACTION_REVERSED,
            "card.created": WebhookEventType.CARD_CREATED,
        }
        
        raw_type = data.get("type", "")
        event_type = event_type_map.get(raw_type, WebhookEventType.TRANSACTION_CREATED)
        
        return WebhookEvent(
            event_id=data.get("token", ""),
            event_type=event_type,
            created_at=datetime.now(timezone.utc),
            data=data.get("payload", data),
        )
    
    def _parse_marqeta_event(self, data: dict) -> WebhookEvent:
        """Parse Marqeta webhook event."""
        event_type_map = {
            "AUTHORIZATION": WebhookEventType.TRANSACTION_CREATED,
            "CLEARING": WebhookEventType.TRANSACTION_SETTLED,
            "REVERSAL": WebhookEventType.TRANSACTION_REVERSED,
        }
        
        raw_type = data.get("type", "")
        event_type = event_type_map.get(raw_type, WebhookEventType.TRANSACTION_CREATED)
        
        return WebhookEvent(
            event_id=data.get("token", ""),
            event_type=event_type,
            created_at=datetime.now(timezone.utc),
            data=data,
        )
    
    def _parse_generic_event(self, data: dict) -> WebhookEvent:
        """Parse generic webhook event."""
        return WebhookEvent(
            event_id=data.get("event_id", data.get("id", "")),
            event_type=WebhookEventType(data.get("type", "transaction.created")),
            created_at=datetime.now(timezone.utc),
            data=data,
        )
    
    def verify_and_parse(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> WebhookEvent:
        """
        Verify signature and parse webhook event.

        Args:
            payload: Raw request body bytes
            signature: Signature from provider header
            timestamp: Optional timestamp for replay protection

        Returns:
            Parsed WebhookEvent

        Raises:
            ValueError: If signature verification fails
        """
        if not self.verify_signature(payload, signature, timestamp):
            raise ValueError("Invalid webhook signature")

        return self.parse_event(payload)


class AutoConversionWebhookHandler:
    """
    Webhook handler that integrates with auto-conversion service.

    Automatically triggers USDC → USD conversion when card
    transactions are authorized.
    """

    def __init__(
        self,
        webhook_handler: CardWebhookHandler,
        card_to_wallet_map: dict[str, str],
        on_conversion_needed: Optional[Callable[[str, int, str], None]] = None,
    ):
        """
        Initialize auto-conversion webhook handler.

        Args:
            webhook_handler: Base webhook handler for signature verification
            card_to_wallet_map: Mapping of card_id -> wallet_id
            on_conversion_needed: Callback when conversion is needed.
                Args: (wallet_id, amount_cents, card_transaction_id)
        """
        self._handler = webhook_handler
        self._card_wallet_map = card_to_wallet_map
        self._on_conversion_needed = on_conversion_needed
        self._processed_events: set[str] = set()

    def register_card(self, card_id: str, wallet_id: str) -> None:
        """Register a card to wallet mapping."""
        self._card_wallet_map[card_id] = wallet_id
        logger.info(f"Registered card {card_id} for auto-conversion")

    def unregister_card(self, card_id: str) -> None:
        """Remove card from auto-conversion."""
        if card_id in self._card_wallet_map:
            del self._card_wallet_map[card_id]

    async def process_webhook(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Process webhook and trigger auto-conversion if needed.

        Args:
            payload: Raw webhook payload
            signature: Webhook signature
            timestamp: Optional timestamp

        Returns:
            Dictionary with processing result, or None if event skipped
        """
        # Verify and parse event
        event = self._handler.verify_and_parse(payload, signature, timestamp)

        # Skip if already processed (idempotency)
        if event.event_id in self._processed_events:
            logger.info(f"Skipping already processed event: {event.event_id}")
            return None

        self._processed_events.add(event.event_id)

        # Only process transaction created events (authorizations)
        if event.event_type != WebhookEventType.TRANSACTION_CREATED:
            logger.debug(f"Skipping non-authorization event: {event.event_type}")
            return {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "action": "skipped",
                "reason": "not_authorization",
            }

        # Check if this card is registered for auto-conversion
        card_id = event.card_id
        if not card_id or card_id not in self._card_wallet_map:
            logger.debug(f"Card not registered for auto-conversion: {card_id}")
            return {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "action": "skipped",
                "reason": "card_not_registered",
            }

        wallet_id = self._card_wallet_map[card_id]
        amount = event.amount

        if amount is None or amount <= 0:
            logger.warning(f"Invalid amount in webhook: {amount}")
            return {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "action": "skipped",
                "reason": "invalid_amount",
            }

        # Convert Decimal to cents
        amount_cents = int(amount * 100)

        logger.info(
            f"Card authorization detected - triggering auto-conversion: "
            f"card={card_id}, wallet={wallet_id}, amount=${amount_cents / 100:.2f}, "
            f"merchant={event.merchant_name}"
        )

        # Trigger conversion callback
        if self._on_conversion_needed:
            self._on_conversion_needed(wallet_id, amount_cents, event.transaction_id or "")

        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "action": "conversion_triggered",
            "wallet_id": wallet_id,
            "card_id": card_id,
            "amount_cents": amount_cents,
            "merchant": event.merchant_name,
            "transaction_id": event.transaction_id,
        }

    def clear_processed_events(self, older_than_count: int = 1000) -> None:
        """Clear old processed events to prevent memory growth."""
        if len(self._processed_events) > older_than_count * 2:
            # Keep only the most recent events (simple approach)
            self._processed_events.clear()
            logger.info("Cleared processed events cache")
