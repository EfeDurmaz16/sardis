"""Virtual card models for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import SardisModel


class Card(SardisModel):
    id: str
    card_id: str
    wallet_id: str
    provider: str
    provider_card_id: Optional[str] = None
    card_type: str = "multi_use"
    status: str = "pending"
    limit_per_tx: float = 0.0
    limit_daily: float = 0.0
    limit_monthly: float = 0.0
    funded_amount: float = 0.0
    created_at: Optional[datetime] = None


class CardTransaction(SardisModel):
    transaction_id: str
    card_id: str
    amount: str
    currency: str
    merchant_name: str
    merchant_category: str
    status: str
    created_at: str
    settled_at: Optional[str] = None
    decline_reason: Optional[str] = None


class SimulateCardPurchaseResponse(SardisModel):
    transaction: CardTransaction
    policy: dict
    card: Card

