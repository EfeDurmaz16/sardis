"""Webhook handling for card transaction events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
import hashlib
import hmac
import json


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
