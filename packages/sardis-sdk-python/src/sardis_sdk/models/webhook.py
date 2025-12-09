"""Webhook models for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import Field

from .base import SardisModel


class WebhookEventType(str, Enum):
    """Webhook event types."""
    
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    HOLD_CREATED = "hold.created"
    HOLD_CAPTURED = "hold.captured"
    HOLD_VOIDED = "hold.voided"
    HOLD_EXPIRED = "hold.expired"
    WALLET_FUNDED = "wallet.funded"
    WALLET_LOW_BALANCE = "wallet.low_balance"
    OFFER_RECEIVED = "offer.received"
    OFFER_ACCEPTED = "offer.accepted"
    OFFER_COMPLETED = "offer.completed"


class Webhook(SardisModel):
    """A webhook subscription."""
    
    webhook_id: str = Field(alias="id")
    organization_id: str
    url: str
    events: list[str]
    is_active: bool = True
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    last_delivery_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WebhookEvent(SardisModel):
    """A webhook event."""
    
    event_id: str = Field(alias="id")
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


class WebhookDelivery(SardisModel):
    """A webhook delivery attempt."""
    
    delivery_id: str = Field(alias="id")
    subscription_id: str
    event_id: str
    event_type: str
    url: str
    status_code: Optional[int] = None
    success: bool = False
    error: Optional[str] = None
    duration_ms: int = 0
    attempt_number: int = 1
    created_at: datetime


class CreateWebhookRequest(SardisModel):
    """Request to create a webhook subscription."""
    
    url: str
    events: list[str]
    organization_id: Optional[str] = None


class UpdateWebhookRequest(SardisModel):
    """Request to update a webhook subscription."""
    
    url: Optional[str] = None
    events: Optional[list[str]] = None
    is_active: Optional[bool] = None
