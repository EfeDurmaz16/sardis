"""
Recurring Payments Engine for Sardis.

Implements subscription management with:
- Subscription registry (merchant, amount, billing cycle)
- Pre-billing balance checks and auto-funding
- Subscription-aware ASA matching for card authorizations
- Owner notifications (webhook, email)
- Shared card model: one card, many subscriptions via ASA matching

Architecture:
┌──────────────────────────────────────────────────────────────────┐
│                    SUBSCRIPTION LIFECYCLE                        │
│                                                                  │
│  Create → Pre-Billing Check → Fund/Approve → ASA Match → Settle │
│            (T-48h cron)      (auto or HITL)  (Lithic)   (ledger)│
│                                                                  │
│  Notifications sent at each stage to agent owner                 │
└──────────────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BillingCycle(str, Enum):
    """Subscription billing frequency."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class SubscriptionStatus(str, Enum):
    """Subscription lifecycle status."""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"


class BillingEventStatus(str, Enum):
    """Status of a single billing event."""
    PENDING = "pending"
    BALANCE_CHECKED = "balance_checked"
    FUNDING = "funding"
    AWAITING_APPROVAL = "awaiting_approval"
    FUNDED = "funded"
    CHARGED = "charged"
    FAILED = "failed"
    SKIPPED = "skipped"


class NotificationType(str, Enum):
    """Types of owner notifications."""
    UPCOMING_BILLING = "upcoming_billing"
    AUTO_FUNDED = "auto_funded"
    APPROVAL_REQUIRED = "approval_required"
    CHARGE_COMPLETED = "charge_completed"
    CHARGE_FAILED = "charge_failed"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    POLICY_BLOCKED = "policy_blocked"
    SUBSCRIPTION_PAUSED = "subscription_paused"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class Subscription:
    """A recurring payment linked to a wallet."""

    id: str = field(default_factory=lambda: f"sub_{uuid.uuid4().hex[:16]}")
    wallet_id: str = ""
    owner_id: str = ""  # agent owner for notifications

    # Merchant info
    merchant: str = ""  # merchant domain or descriptor
    merchant_mcc: Optional[str] = None

    # Billing details
    amount_cents: int = 0  # expected charge amount
    currency: str = "USD"
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    billing_day: int = 1  # day of month (1-28) or day of week (0-6 for weekly)
    next_billing: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Card association
    card_id: Optional[str] = None  # shared card or dedicated

    # Approval settings
    auto_approve: bool = True
    auto_approve_threshold_cents: int = 10000  # $100 default

    # Amount tolerance for matching (e.g., $20 subscription might charge $20.99)
    amount_tolerance_cents: int = 500  # $5 tolerance

    # Notifications
    notify_owner: bool = True
    notification_channel: Optional[str] = None  # webhook URL or email

    # Status
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    last_charged_at: Optional[datetime] = None
    failure_count: int = 0
    max_failures: int = 3  # pause after N consecutive failures

    # Timestamps
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def amount(self) -> Decimal:
        """Amount as Decimal dollars."""
        return Decimal(self.amount_cents) / 100

    def matches_charge(
        self, merchant_descriptor: str, amount_cents: int
    ) -> bool:
        """Check if a card charge matches this subscription."""
        # Merchant match: substring check (e.g., "OPENAI" in "OPENAI *API")
        merchant_upper = self.merchant.upper()
        descriptor_upper = merchant_descriptor.upper()
        if merchant_upper not in descriptor_upper and descriptor_upper not in merchant_upper:
            return False

        # Amount match: within tolerance
        diff = abs(amount_cents - self.amount_cents)
        if diff > self.amount_tolerance_cents:
            return False

        return True

    def compute_next_billing(self) -> datetime:
        """Calculate the next billing date after the current one."""
        now = self.next_billing
        if self.billing_cycle == BillingCycle.WEEKLY:
            return now + timedelta(weeks=1)
        elif self.billing_cycle == BillingCycle.MONTHLY:
            month = now.month + 1
            year = now.year
            if month > 12:
                month = 1
                year += 1
            day = min(self.billing_day, 28)  # cap at 28 for safety
            return now.replace(year=year, month=month, day=day)
        elif self.billing_cycle == BillingCycle.QUARTERLY:
            month = now.month + 3
            year = now.year
            while month > 12:
                month -= 12
                year += 1
            day = min(self.billing_day, 28)
            return now.replace(year=year, month=month, day=day)
        elif self.billing_cycle == BillingCycle.ANNUAL:
            return now.replace(year=now.year + 1)
        return now + timedelta(days=30)  # fallback


@dataclass
class BillingEvent:
    """Record of a single billing cycle execution."""

    id: str = field(default_factory=lambda: f"bill_{uuid.uuid4().hex[:16]}")
    subscription_id: str = ""
    wallet_id: str = ""

    scheduled_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: BillingEventStatus = BillingEventStatus.PENDING
    amount_cents: int = 0

    # Linked records
    fund_tx_id: Optional[str] = None  # auto-conversion transaction
    approval_id: Optional[str] = None  # HITL approval request
    charge_tx_id: Optional[str] = None  # Lithic transaction ID

    error: Optional[str] = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class OwnerNotification:
    """Notification to send to the agent owner."""

    id: str = field(default_factory=lambda: f"notif_{uuid.uuid4().hex[:16]}")
    subscription_id: str = ""
    owner_id: str = ""
    notification_type: NotificationType = NotificationType.UPCOMING_BILLING
    channel: Optional[str] = None  # webhook URL or email
    payload: Dict[str, Any] = field(default_factory=dict)
    sent: bool = False
    sent_at: Optional[datetime] = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ---------------------------------------------------------------------------
# Service Protocol
# ---------------------------------------------------------------------------

class SubscriptionServiceProtocol(Protocol):
    """Interface for subscription storage backends."""

    async def create(self, subscription: Subscription) -> Subscription: ...
    async def get(self, sub_id: str) -> Optional[Subscription]: ...
    async def list_by_wallet(self, wallet_id: str) -> List[Subscription]: ...
    async def update_status(
        self, sub_id: str, status: SubscriptionStatus
    ) -> Optional[Subscription]: ...
    async def update_next_billing(
        self, sub_id: str, next_billing: datetime
    ) -> None: ...
    async def get_due_subscriptions(
        self, within_hours: int = 48
    ) -> List[Subscription]: ...
    async def match_charge(
        self,
        card_id: str,
        merchant_descriptor: str,
        amount_cents: int,
    ) -> Optional[Subscription]: ...
    async def record_billing_event(
        self, event: BillingEvent
    ) -> BillingEvent: ...
    async def get_billing_history(
        self, sub_id: str, limit: int = 20
    ) -> List[BillingEvent]: ...


# ---------------------------------------------------------------------------
# In-Memory Implementation
# ---------------------------------------------------------------------------

class SubscriptionService:
    """In-memory subscription service for testing and simulated mode."""

    def __init__(self) -> None:
        self._subscriptions: Dict[str, Subscription] = {}
        self._billing_events: Dict[str, BillingEvent] = {}
        self._notifications: List[OwnerNotification] = []

    async def create(self, subscription: Subscription) -> Subscription:
        """Register a new subscription."""
        self._subscriptions[subscription.id] = subscription
        logger.info(
            f"Subscription created: {subscription.id} "
            f"merchant={subscription.merchant} "
            f"amount=${subscription.amount_cents / 100:.2f}/{subscription.billing_cycle.value}"
        )
        return subscription

    async def get(self, sub_id: str) -> Optional[Subscription]:
        """Get subscription by ID."""
        return self._subscriptions.get(sub_id)

    async def list_by_wallet(self, wallet_id: str) -> List[Subscription]:
        """List all subscriptions for a wallet."""
        return [
            s
            for s in self._subscriptions.values()
            if s.wallet_id == wallet_id
        ]

    async def list_active(self) -> List[Subscription]:
        """List all active subscriptions."""
        return [
            s
            for s in self._subscriptions.values()
            if s.status == SubscriptionStatus.ACTIVE
        ]

    async def cancel(self, sub_id: str) -> Optional[Subscription]:
        """Cancel a subscription."""
        sub = self._subscriptions.get(sub_id)
        if sub:
            sub.status = SubscriptionStatus.CANCELLED
            sub.updated_at = datetime.now(timezone.utc)
        return sub

    async def pause(self, sub_id: str) -> Optional[Subscription]:
        """Pause a subscription (can be resumed)."""
        sub = self._subscriptions.get(sub_id)
        if sub:
            sub.status = SubscriptionStatus.PAUSED
            sub.updated_at = datetime.now(timezone.utc)
        return sub

    async def resume(self, sub_id: str) -> Optional[Subscription]:
        """Resume a paused subscription."""
        sub = self._subscriptions.get(sub_id)
        if sub and sub.status == SubscriptionStatus.PAUSED:
            sub.status = SubscriptionStatus.ACTIVE
            sub.failure_count = 0
            sub.updated_at = datetime.now(timezone.utc)
        return sub

    async def update_status(
        self, sub_id: str, status: SubscriptionStatus
    ) -> Optional[Subscription]:
        """Update subscription status."""
        sub = self._subscriptions.get(sub_id)
        if sub:
            sub.status = status
            sub.updated_at = datetime.now(timezone.utc)
        return sub

    async def update_next_billing(
        self, sub_id: str, next_billing: datetime
    ) -> None:
        """Update the next billing date."""
        sub = self._subscriptions.get(sub_id)
        if sub:
            sub.next_billing = next_billing
            sub.updated_at = datetime.now(timezone.utc)

    async def record_charge(self, sub_id: str, charge_tx_id: str) -> None:
        """Record a successful charge and advance billing date."""
        sub = self._subscriptions.get(sub_id)
        if sub:
            sub.last_charged_at = datetime.now(timezone.utc)
            sub.failure_count = 0
            sub.next_billing = sub.compute_next_billing()
            sub.updated_at = datetime.now(timezone.utc)
            logger.info(
                f"Subscription {sub_id} charged (tx={charge_tx_id}), "
                f"next billing: {sub.next_billing.isoformat()}"
            )

    async def record_failure(self, sub_id: str, error: str) -> None:
        """Record a billing failure. Auto-pauses after max_failures."""
        sub = self._subscriptions.get(sub_id)
        if sub:
            sub.failure_count += 1
            sub.updated_at = datetime.now(timezone.utc)
            if sub.failure_count >= sub.max_failures:
                sub.status = SubscriptionStatus.PAST_DUE
                logger.warning(
                    f"Subscription {sub_id} marked PAST_DUE after "
                    f"{sub.failure_count} failures"
                )

    async def get_due_subscriptions(
        self, within_hours: int = 48
    ) -> List[Subscription]:
        """Get active subscriptions due within the given timeframe."""
        cutoff = datetime.now(timezone.utc) + timedelta(hours=within_hours)
        return [
            s
            for s in self._subscriptions.values()
            if s.status == SubscriptionStatus.ACTIVE and s.next_billing <= cutoff
        ]

    async def match_charge(
        self,
        card_id: str,
        merchant_descriptor: str,
        amount_cents: int,
    ) -> Optional[Subscription]:
        """
        Match a card charge to a known subscription.

        Uses merchant descriptor substring matching and amount tolerance.
        Returns the best matching active subscription or None.
        """
        candidates = []
        for sub in self._subscriptions.values():
            if sub.status != SubscriptionStatus.ACTIVE:
                continue
            # Card must match (None = any card on the wallet)
            if sub.card_id and sub.card_id != card_id:
                continue
            if sub.matches_charge(merchant_descriptor, amount_cents):
                candidates.append(sub)

        if not candidates:
            return None

        # If multiple matches, prefer closest amount match
        candidates.sort(key=lambda s: abs(s.amount_cents - amount_cents))
        return candidates[0]

    async def record_billing_event(
        self, event: BillingEvent
    ) -> BillingEvent:
        """Record a billing event."""
        self._billing_events[event.id] = event
        return event

    async def get_billing_history(
        self, sub_id: str, limit: int = 20
    ) -> List[BillingEvent]:
        """Get billing history for a subscription."""
        events = [
            e
            for e in self._billing_events.values()
            if e.subscription_id == sub_id
        ]
        events.sort(key=lambda e: e.created_at, reverse=True)
        return events[:limit]

    async def queue_notification(
        self, notification: OwnerNotification
    ) -> None:
        """Queue a notification for delivery."""
        self._notifications.append(notification)
        logger.info(
            f"Notification queued: {notification.notification_type.value} "
            f"for subscription {notification.subscription_id}"
        )

    async def get_pending_notifications(self) -> List[OwnerNotification]:
        """Get unsent notifications."""
        return [n for n in self._notifications if not n.sent]

    async def mark_notification_sent(self, notif_id: str) -> None:
        """Mark a notification as sent."""
        for n in self._notifications:
            if n.id == notif_id:
                n.sent = True
                n.sent_at = datetime.now(timezone.utc)
                break


# ---------------------------------------------------------------------------
# Billing Processor (Pre-Billing Cron Job)
# ---------------------------------------------------------------------------

class BillingProcessor:
    """
    Pre-billing processor that runs via APScheduler.

    Checks upcoming subscriptions, verifies balance, triggers
    auto-funding or approval requests, and notifies owners.
    """

    def __init__(
        self,
        subscription_service: SubscriptionService,
        balance_checker: Optional[Callable[[str], Any]] = None,
        auto_funder: Optional[Callable[[str, int], Any]] = None,
        approval_creator: Optional[Callable[[str, int, str, str], Any]] = None,
        notification_sender: Optional[Callable[[OwnerNotification], Any]] = None,
    ) -> None:
        """
        Args:
            subscription_service: Subscription storage backend
            balance_checker: async (wallet_id) -> UnifiedBalance or similar
            auto_funder: async (wallet_id, amount_cents) -> conversion result
            approval_creator: async (wallet_id, amount_cents, merchant, reason) -> approval
            notification_sender: async (notification) -> send result
        """
        self._subs = subscription_service
        self._check_balance = balance_checker
        self._auto_fund = auto_funder
        self._create_approval = approval_creator
        self._send_notification = notification_sender

    async def process_upcoming_billings(
        self, within_hours: int = 48
    ) -> List[BillingEvent]:
        """
        Process all subscriptions due within the given timeframe.

        Called by APScheduler daily cron job.

        Returns:
            List of billing events created during processing.
        """
        due_subs = await self._subs.get_due_subscriptions(within_hours)
        if not due_subs:
            logger.debug("No subscriptions due for billing")
            return []

        logger.info(f"Processing {len(due_subs)} upcoming subscriptions")
        events: List[BillingEvent] = []

        for sub in due_subs:
            event = await self._process_single(sub)
            events.append(event)

        return events

    async def _process_single(self, sub: Subscription) -> BillingEvent:
        """Process a single subscription billing."""
        event = BillingEvent(
            subscription_id=sub.id,
            wallet_id=sub.wallet_id,
            scheduled_at=sub.next_billing,
            amount_cents=sub.amount_cents,
        )

        try:
            # 1. Check wallet balance
            if self._check_balance:
                balance = await self._check_balance(sub.wallet_id)
                total_cents = getattr(balance, "total_balance_cents", 0)
                if total_cents < sub.amount_cents:
                    event.status = BillingEventStatus.FAILED
                    event.error = "insufficient_balance"
                    await self._subs.record_billing_event(event)
                    await self._subs.record_failure(sub.id, "insufficient_balance")
                    await self._notify(
                        sub, NotificationType.INSUFFICIENT_BALANCE,
                        {"balance_cents": total_cents, "required_cents": sub.amount_cents},
                    )
                    return event

            event.status = BillingEventStatus.BALANCE_CHECKED

            # 2. Auto-approve or request approval
            needs_approval = (
                not sub.auto_approve
                or sub.amount_cents > sub.auto_approve_threshold_cents
            )

            if needs_approval and self._create_approval:
                approval = await self._create_approval(
                    sub.wallet_id,
                    sub.amount_cents,
                    sub.merchant,
                    f"Recurring payment: {sub.merchant} ${sub.amount_cents / 100:.2f}",
                )
                event.status = BillingEventStatus.AWAITING_APPROVAL
                event.approval_id = getattr(approval, "id", str(approval))
                await self._subs.record_billing_event(event)
                await self._notify(
                    sub, NotificationType.APPROVAL_REQUIRED,
                    {"amount_cents": sub.amount_cents, "merchant": sub.merchant},
                )
                return event

            # 3. Auto-fund: ensure USD balance for card charge
            if self._auto_fund:
                fund_result = await self._auto_fund(
                    sub.wallet_id, sub.amount_cents
                )
                event.fund_tx_id = getattr(fund_result, "id", None)
                event.status = BillingEventStatus.FUNDED
                await self._notify(
                    sub, NotificationType.AUTO_FUNDED,
                    {"amount_cents": sub.amount_cents, "merchant": sub.merchant},
                )
            else:
                event.status = BillingEventStatus.FUNDED

            await self._subs.record_billing_event(event)
            logger.info(
                f"Subscription {sub.id} pre-billed: "
                f"status={event.status.value} amount=${sub.amount_cents / 100:.2f}"
            )
            return event

        except Exception as e:
            logger.error(f"Billing error for subscription {sub.id}: {e}")
            event.status = BillingEventStatus.FAILED
            event.error = str(e)
            await self._subs.record_billing_event(event)
            await self._subs.record_failure(sub.id, str(e))
            await self._notify(
                sub, NotificationType.CHARGE_FAILED,
                {"error": str(e), "amount_cents": sub.amount_cents},
            )
            return event

    async def handle_charge_settled(
        self, card_id: str, merchant_descriptor: str, amount_cents: int,
        charge_tx_id: str,
    ) -> Optional[Subscription]:
        """
        Called when a card charge settles (from Lithic webhook).

        Matches the charge to a subscription, records it, and
        advances the billing date.
        """
        sub = await self._subs.match_charge(
            card_id, merchant_descriptor, amount_cents
        )
        if not sub:
            return None

        await self._subs.record_charge(sub.id, charge_tx_id)

        event = BillingEvent(
            subscription_id=sub.id,
            wallet_id=sub.wallet_id,
            scheduled_at=sub.next_billing,
            amount_cents=amount_cents,
            status=BillingEventStatus.CHARGED,
            charge_tx_id=charge_tx_id,
        )
        await self._subs.record_billing_event(event)

        await self._notify(
            sub, NotificationType.CHARGE_COMPLETED,
            {
                "amount_cents": amount_cents,
                "merchant": merchant_descriptor,
                "charge_tx_id": charge_tx_id,
                "next_billing": sub.next_billing.isoformat(),
            },
        )

        logger.info(
            f"Subscription {sub.id} charge settled: "
            f"${amount_cents / 100:.2f} from {merchant_descriptor}"
        )
        return sub

    async def _notify(
        self,
        sub: Subscription,
        notif_type: NotificationType,
        payload: Dict[str, Any],
    ) -> None:
        """Send notification to subscription owner."""
        if not sub.notify_owner:
            return

        notification = OwnerNotification(
            subscription_id=sub.id,
            owner_id=sub.owner_id,
            notification_type=notif_type,
            channel=sub.notification_channel,
            payload={
                "subscription_id": sub.id,
                "wallet_id": sub.wallet_id,
                "merchant": sub.merchant,
                **payload,
            },
        )

        await self._subs.queue_notification(notification)

        if self._send_notification:
            try:
                await self._send_notification(notification)
                await self._subs.mark_notification_sent(notification.id)
            except Exception as e:
                logger.error(
                    f"Failed to send notification {notification.id}: {e}"
                )
