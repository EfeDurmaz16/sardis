"""Subscription Mandates — recurring payment authorization.

Subscriptions generate payment objects on a schedule, enabling
recurring agent-to-service payments with automatic dunning.

Usage::

    sub = SubscriptionMandate(
        mandate_id="mandate_abc123",
        merchant_id="merchant_openai",
        billing_cycle=BillingCycle.MONTHLY,
        charge_amount=Decimal("20.00"),
    )
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.subscription")


class BillingCycle(str, Enum):
    """Supported billing intervals."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class SubscriptionStatus(str, Enum):
    """Lifecycle states for a subscription."""
    PENDING = "pending"              # Created, awaiting first charge
    ACTIVE = "active"                # Current, charges processing normally
    PAST_DUE = "past_due"           # Payment failed, in grace period
    DUNNING = "dunning"             # Retry cycle in progress
    PAUSED = "paused"               # Manually paused by principal
    CANCELLED = "cancelled"          # Cancelled (no more charges)
    EXPIRED = "expired"             # Reached end date
    TRIAL = "trial"                 # In trial period


SUBSCRIPTION_VALID_TRANSITIONS: dict[tuple[str, str], str] = {
    (SubscriptionStatus.PENDING, SubscriptionStatus.ACTIVE): "activate",
    (SubscriptionStatus.PENDING, SubscriptionStatus.TRIAL): "start_trial",
    (SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE): "convert",
    (SubscriptionStatus.TRIAL, SubscriptionStatus.CANCELLED): "cancel",
    (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE): "payment_failed",
    (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED): "pause",
    (SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED): "cancel",
    (SubscriptionStatus.ACTIVE, SubscriptionStatus.EXPIRED): "expire",
    (SubscriptionStatus.PAST_DUE, SubscriptionStatus.DUNNING): "start_dunning",
    (SubscriptionStatus.PAST_DUE, SubscriptionStatus.ACTIVE): "payment_succeeded",
    (SubscriptionStatus.DUNNING, SubscriptionStatus.ACTIVE): "payment_succeeded",
    (SubscriptionStatus.DUNNING, SubscriptionStatus.CANCELLED): "exhaust_retries",
    (SubscriptionStatus.PAUSED, SubscriptionStatus.ACTIVE): "resume",
    (SubscriptionStatus.PAUSED, SubscriptionStatus.CANCELLED): "cancel",
}

# Days between dunning retries
DUNNING_SCHEDULE = [1, 3, 5, 7]  # Retry at 1, 3, 5, 7 days

CYCLE_DAYS = {
    BillingCycle.DAILY: 1,
    BillingCycle.WEEKLY: 7,
    BillingCycle.BIWEEKLY: 14,
    BillingCycle.MONTHLY: 30,
    BillingCycle.QUARTERLY: 90,
    BillingCycle.ANNUAL: 365,
}


@dataclass
class DunningRule:
    """Configuration for payment retry behavior."""
    max_retries: int = 4
    retry_schedule_days: list[int] = field(default_factory=lambda: list(DUNNING_SCHEDULE))
    cancel_after_exhausted: bool = True
    notify_on_failure: bool = True


@dataclass
class ChargeIntent:
    """A single charge attempt within a subscription cycle."""

    charge_id: str = field(default_factory=lambda: f"chg_{uuid4().hex[:12]}")
    subscription_id: str = ""
    payment_object_id: str | None = None
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"
    billing_period_start: datetime | None = None
    billing_period_end: datetime | None = None
    status: str = "pending"  # pending, processing, succeeded, failed, cancelled
    attempt_number: int = 1
    failure_reason: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SubscriptionMandate:
    """A recurring payment authorization tied to a spending mandate."""

    # Identity
    subscription_id: str = field(default_factory=lambda: f"sub_{uuid4().hex[:12]}")
    org_id: str = ""
    mandate_id: str = ""
    merchant_id: str = ""
    agent_id: str | None = None

    # Billing
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    charge_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"
    description: str | None = None

    # Grace & dunning
    grace_period_days: int = 3
    dunning_rules: DunningRule = field(default_factory=DunningRule)

    # Trial
    trial_days: int = 0
    trial_end: datetime | None = None

    # Schedule
    current_period_start: datetime = field(default_factory=lambda: datetime.now(UTC))
    current_period_end: datetime | None = None
    anchor_day: int | None = None  # Day of month for monthly billing

    # Lifecycle
    status: SubscriptionStatus = SubscriptionStatus.PENDING
    charges_count: int = 0
    total_charged: Decimal = field(default_factory=lambda: Decimal("0"))
    last_charge_at: datetime | None = None
    next_charge_at: datetime | None = None
    cancelled_at: datetime | None = None
    ends_at: datetime | None = None

    # Audit
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def compute_next_charge(self) -> datetime:
        """Calculate the next charge date based on billing cycle."""
        base = self.last_charge_at or self.current_period_start
        days = CYCLE_DAYS.get(self.billing_cycle, 30)
        return base + timedelta(days=days)

    def is_in_grace_period(self) -> bool:
        """Check if we're within the grace period after a failed charge."""
        if self.status != SubscriptionStatus.PAST_DUE:
            return False
        if self.next_charge_at is None:
            return False
        grace_end = self.next_charge_at + timedelta(days=self.grace_period_days)
        return datetime.now(UTC) <= grace_end

    @property
    def is_active(self) -> bool:
        return self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL)


@dataclass
class UsageMeter:
    """Metered usage tracking for usage-based billing."""

    meter_id: str = field(default_factory=lambda: f"meter_{uuid4().hex[:12]}")
    subscription_id: str = ""
    metric_name: str = ""  # e.g., "api_calls", "tokens_used", "compute_hours"
    unit_price: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"

    # Accumulated usage
    current_usage: Decimal = field(default_factory=lambda: Decimal("0"))
    billing_period_usage: Decimal = field(default_factory=lambda: Decimal("0"))

    # Limits
    included_units: Decimal = field(default_factory=lambda: Decimal("0"))
    max_units: Decimal | None = None  # None = unlimited

    # Countersignature
    requires_countersignature: bool = True
    last_countersigned_at: datetime | None = None
    last_countersigned_usage: Decimal = field(default_factory=lambda: Decimal("0"))

    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def billable_usage(self) -> Decimal:
        """Usage above included units."""
        excess = self.billing_period_usage - self.included_units
        return max(excess, Decimal("0"))

    @property
    def billable_amount(self) -> Decimal:
        """Amount owed for billable usage."""
        return (self.billable_usage * self.unit_price).quantize(Decimal("0.000001"))
