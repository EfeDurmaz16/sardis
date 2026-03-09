"""Virtual card models for Sardis SDK."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import SardisModel

if TYPE_CHECKING:
    from datetime import datetime


class Card(SardisModel):
    id: str
    card_id: str
    wallet_id: str
    provider: str
    provider_card_id: str | None = None
    card_type: str = "multi_use"
    status: str = "pending"
    limit_per_tx: float = 0.0
    limit_daily: float = 0.0
    limit_monthly: float = 0.0
    funded_amount: float = 0.0
    created_at: datetime | None = None


class CardTransaction(SardisModel):
    transaction_id: str
    card_id: str
    amount: str
    currency: str
    merchant_name: str
    merchant_category: str
    status: str
    created_at: str
    settled_at: str | None = None
    decline_reason: str | None = None


class SimulateCardPurchaseResponse(SardisModel):
    transaction: CardTransaction
    policy: dict
    card: Card

