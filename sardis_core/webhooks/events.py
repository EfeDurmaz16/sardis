"""Webhook event definitions."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
import uuid
import json


class EventType(str, Enum):
    """Types of webhook events."""
    
    # Payment events
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"
    
    # Wallet events
    WALLET_CREATED = "wallet.created"
    WALLET_FUNDED = "wallet.funded"
    WALLET_UPDATED = "wallet.updated"
    WALLET_DEACTIVATED = "wallet.deactivated"
    
    # Limit events
    LIMIT_EXCEEDED = "limit.exceeded"
    LIMIT_WARNING = "limit.warning"  # e.g., 80% of limit reached
    LIMIT_UPDATED = "limit.updated"
    
    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DEACTIVATED = "agent.deactivated"
    
    # Risk events
    RISK_ALERT = "risk.alert"
    FRAUD_DETECTED = "fraud.detected"
    
    # Service authorization events
    SERVICE_AUTHORIZED = "service.authorized"
    SERVICE_REVOKED = "service.revoked"


@dataclass
class WebhookEvent:
    """
    Represents a webhook event to be delivered.
    
    Events follow a consistent structure for easy parsing
    by webhook consumers.
    """
    
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex}")
    event_type: EventType = EventType.PAYMENT_COMPLETED
    
    # Event data
    data: dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    api_version: str = "2024-01"
    
    # Delivery tracking
    delivery_attempts: int = 0
    last_delivery_attempt: Optional[datetime] = None
    delivered: bool = False
    
    def to_dict(self) -> dict:
        """Convert event to dictionary for JSON serialization."""
        return {
            "id": self.event_id,
            "type": self.event_type.value,
            "data": self._serialize_data(self.data),
            "created_at": self.created_at.isoformat(),
            "api_version": self.api_version,
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    def _serialize_data(self, data: dict) -> dict:
        """Serialize data for JSON, handling special types."""
        result = {}
        for key, value in data.items():
            if isinstance(value, Decimal):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = self._serialize_data(value)
            elif hasattr(value, 'value'):  # Enum
                result[key] = value.value
            else:
                result[key] = value
        return result


# Event factory functions for common events
def create_payment_completed_event(
    tx_id: str,
    from_wallet: str,
    to_wallet: str,
    amount: Decimal,
    fee: Decimal,
    currency: str,
    purpose: Optional[str] = None
) -> WebhookEvent:
    """Create a payment.completed event."""
    return WebhookEvent(
        event_type=EventType.PAYMENT_COMPLETED,
        data={
            "transaction": {
                "id": tx_id,
                "from_wallet": from_wallet,
                "to_wallet": to_wallet,
                "amount": amount,
                "fee": fee,
                "total": amount + fee,
                "currency": currency,
                "purpose": purpose,
                "status": "completed",
            }
        }
    )


def create_payment_failed_event(
    tx_id: str,
    from_wallet: str,
    to_wallet: str,
    amount: Decimal,
    currency: str,
    error: str
) -> WebhookEvent:
    """Create a payment.failed event."""
    return WebhookEvent(
        event_type=EventType.PAYMENT_FAILED,
        data={
            "transaction": {
                "id": tx_id,
                "from_wallet": from_wallet,
                "to_wallet": to_wallet,
                "amount": amount,
                "currency": currency,
                "status": "failed",
                "error": error,
            }
        }
    )


def create_wallet_created_event(
    wallet_id: str,
    agent_id: str,
    initial_balance: Decimal,
    currency: str
) -> WebhookEvent:
    """Create a wallet.created event."""
    return WebhookEvent(
        event_type=EventType.WALLET_CREATED,
        data={
            "wallet": {
                "id": wallet_id,
                "agent_id": agent_id,
                "balance": initial_balance,
                "currency": currency,
            }
        }
    )


def create_limit_exceeded_event(
    wallet_id: str,
    agent_id: str,
    limit_type: str,  # "per_tx" or "total"
    limit_value: Decimal,
    attempted_amount: Decimal,
    currency: str
) -> WebhookEvent:
    """Create a limit.exceeded event."""
    return WebhookEvent(
        event_type=EventType.LIMIT_EXCEEDED,
        data={
            "wallet_id": wallet_id,
            "agent_id": agent_id,
            "limit_type": limit_type,
            "limit_value": limit_value,
            "attempted_amount": attempted_amount,
            "currency": currency,
        }
    )


def create_risk_alert_event(
    wallet_id: str,
    agent_id: str,
    risk_score: float,
    risk_factors: list[str],
    recommended_action: str
) -> WebhookEvent:
    """Create a risk.alert event."""
    return WebhookEvent(
        event_type=EventType.RISK_ALERT,
        data={
            "wallet_id": wallet_id,
            "agent_id": agent_id,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "recommended_action": recommended_action,
        }
    )

