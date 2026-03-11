"""Billing data models."""
from __future__ import annotations

from pydantic import BaseModel


class BillingAccount(BaseModel):
    id: str
    org_id: str
    plan: str = "free"
    status: str = "active"
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    api_calls_this_period: int = 0
    tx_volume_this_period_cents: int = 0


class PlanInfo(BaseModel):
    plan: str
    price_monthly_cents: int
    api_calls_per_month: int | None
    agents: int | None
    tx_fee_bps: int
    monthly_tx_volume_cents: int | None


class UsageSnapshot(BaseModel):
    api_calls_used: int
    api_calls_limit: int | None
    tx_volume_cents: int
    tx_volume_limit_cents: int | None
    agents_used: int
    agents_limit: int | None
