"""PostgreSQL-backed subscription service.

Persists subscriptions and billing events to Neon PostgreSQL.
Pattern follows ``db_balance.py`` / ``policy_store_postgres.py``.

Tables used:
- ``subscriptions`` — subscription registry
- ``billing_events`` — per-cycle billing records
- ``subscription_notifications`` — owner notification queue
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .subscriptions import (
    BillingCycle,
    BillingEvent,
    BillingEventStatus,
    NotificationType,
    OwnerNotification,
    Subscription,
    SubscriptionStatus,
)

logger = logging.getLogger(__name__)


class PostgresSubscriptionService:
    """
    PostgreSQL-backed subscription service.

    Replaces the in-memory ``SubscriptionService`` with persistent
    storage for production use.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool

    # ------------------------------------------------------------------
    # Subscription CRUD
    # ------------------------------------------------------------------

    async def create(self, subscription: Subscription) -> Subscription:
        """Persist a new subscription."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO subscriptions (
                    id, wallet_id, owner_id, merchant, merchant_mcc,
                    amount_cents, currency, billing_cycle, billing_day,
                    next_billing, card_id, auto_approve,
                    auto_approve_threshold_cents, amount_tolerance_cents,
                    notify_owner, notification_channel, status,
                    failure_count, max_failures, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
                )
                """,
                subscription.id,
                subscription.wallet_id,
                subscription.owner_id,
                subscription.merchant,
                subscription.merchant_mcc,
                subscription.amount_cents,
                subscription.currency,
                subscription.billing_cycle.value,
                subscription.billing_day,
                subscription.next_billing,
                subscription.card_id,
                subscription.auto_approve,
                subscription.auto_approve_threshold_cents,
                subscription.amount_tolerance_cents,
                subscription.notify_owner,
                subscription.notification_channel,
                subscription.status.value,
                subscription.failure_count,
                subscription.max_failures,
                subscription.created_at,
                subscription.updated_at,
            )
        logger.info(
            f"Subscription created: {subscription.id} "
            f"merchant={subscription.merchant} "
            f"amount=${subscription.amount_cents / 100:.2f}/{subscription.billing_cycle.value}"
        )
        return subscription

    async def get(self, sub_id: str) -> Optional[Subscription]:
        """Get subscription by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM subscriptions WHERE id = $1", sub_id
            )
        if not row:
            return None
        return self._row_to_subscription(row)

    async def list_by_wallet(self, wallet_id: str) -> List[Subscription]:
        """List all subscriptions for a wallet."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM subscriptions WHERE wallet_id = $1 ORDER BY created_at DESC",
                wallet_id,
            )
        return [self._row_to_subscription(r) for r in rows]

    async def list_active(self) -> List[Subscription]:
        """List all active subscriptions."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM subscriptions WHERE status = 'active' ORDER BY next_billing ASC"
            )
        return [self._row_to_subscription(r) for r in rows]

    async def cancel(self, sub_id: str) -> Optional[Subscription]:
        """Cancel a subscription."""
        return await self.update_status(sub_id, SubscriptionStatus.CANCELLED)

    async def pause(self, sub_id: str) -> Optional[Subscription]:
        """Pause a subscription."""
        return await self.update_status(sub_id, SubscriptionStatus.PAUSED)

    async def resume(self, sub_id: str) -> Optional[Subscription]:
        """Resume a paused subscription."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE subscriptions
                SET status = 'active', failure_count = 0, updated_at = $2
                WHERE id = $1 AND status = 'paused'
                RETURNING *
                """,
                sub_id,
                datetime.now(timezone.utc),
            )
        return self._row_to_subscription(row) if row else None

    async def update_status(
        self, sub_id: str, status: SubscriptionStatus
    ) -> Optional[Subscription]:
        """Update subscription status."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE subscriptions SET status = $2, updated_at = $3
                WHERE id = $1 RETURNING *
                """,
                sub_id,
                status.value,
                datetime.now(timezone.utc),
            )
        return self._row_to_subscription(row) if row else None

    async def update_next_billing(
        self, sub_id: str, next_billing: datetime
    ) -> None:
        """Update the next billing date."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE subscriptions SET next_billing = $2, updated_at = $3
                WHERE id = $1
                """,
                sub_id,
                next_billing,
                datetime.now(timezone.utc),
            )

    async def record_charge(self, sub_id: str, charge_tx_id: str) -> None:
        """Record a successful charge and advance billing date."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM subscriptions WHERE id = $1 FOR UPDATE",
                sub_id,
            )
            if not row:
                return

            sub = self._row_to_subscription(row)
            next_billing = sub.compute_next_billing()

            await conn.execute(
                """
                UPDATE subscriptions
                SET last_charged_at = $2, failure_count = 0,
                    next_billing = $3, updated_at = $4
                WHERE id = $1
                """,
                sub_id,
                datetime.now(timezone.utc),
                next_billing,
                datetime.now(timezone.utc),
            )
        logger.info(
            f"Subscription {sub_id} charged (tx={charge_tx_id}), "
            f"next billing: {next_billing.isoformat()}"
        )

    async def record_failure(self, sub_id: str, error: str) -> None:
        """Record a billing failure. Auto-marks PAST_DUE after max_failures."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT failure_count, max_failures FROM subscriptions WHERE id = $1 FOR UPDATE",
                sub_id,
            )
            if not row:
                return

            new_count = row["failure_count"] + 1
            new_status = "past_due" if new_count >= row["max_failures"] else "active"

            await conn.execute(
                """
                UPDATE subscriptions
                SET failure_count = $2, status = $3, updated_at = $4
                WHERE id = $1
                """,
                sub_id,
                new_count,
                new_status,
                datetime.now(timezone.utc),
            )

            if new_status == "past_due":
                logger.warning(
                    f"Subscription {sub_id} marked PAST_DUE after {new_count} failures"
                )

    # ------------------------------------------------------------------
    # Due subscriptions & charge matching
    # ------------------------------------------------------------------

    async def get_due_subscriptions(
        self, within_hours: int = 48
    ) -> List[Subscription]:
        """Get active subscriptions due within the given timeframe."""
        pool = await self._get_pool()
        cutoff = datetime.now(timezone.utc) + timedelta(hours=within_hours)
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM subscriptions
                WHERE status = 'active' AND next_billing <= $1
                ORDER BY next_billing ASC
                """,
                cutoff,
            )
        return [self._row_to_subscription(r) for r in rows]

    async def match_charge(
        self,
        card_id: str,
        merchant_descriptor: str,
        amount_cents: int,
    ) -> Optional[Subscription]:
        """
        Match a card charge to a known subscription.

        Uses SQL ILIKE for merchant matching and amount range check.
        """
        pool = await self._get_pool()
        merchant_pattern = f"%{merchant_descriptor.upper()}%"
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM subscriptions
                WHERE status = 'active'
                  AND (card_id IS NULL OR card_id = $1)
                  AND UPPER(merchant) LIKE $2
                  AND ABS(amount_cents - $3) <= amount_tolerance_cents
                ORDER BY ABS(amount_cents - $3) ASC
                LIMIT 1
                """,
                card_id,
                merchant_pattern,
                amount_cents,
            )
        if not rows:
            # Try reverse match: subscription merchant in descriptor
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM subscriptions
                    WHERE status = 'active'
                      AND (card_id IS NULL OR card_id = $1)
                      AND $2 ILIKE '%' || merchant || '%'
                      AND ABS(amount_cents - $3) <= amount_tolerance_cents
                    ORDER BY ABS(amount_cents - $3) ASC
                    LIMIT 1
                    """,
                    card_id,
                    merchant_descriptor,
                    amount_cents,
                )
        return self._row_to_subscription(rows[0]) if rows else None

    # ------------------------------------------------------------------
    # Billing Events
    # ------------------------------------------------------------------

    async def record_billing_event(self, event: BillingEvent) -> BillingEvent:
        """Persist a billing event."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO billing_events (
                    id, subscription_id, wallet_id, scheduled_at,
                    status, amount_cents, fund_tx_id, approval_id,
                    charge_tx_id, error, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    fund_tx_id = EXCLUDED.fund_tx_id,
                    approval_id = EXCLUDED.approval_id,
                    charge_tx_id = EXCLUDED.charge_tx_id,
                    error = EXCLUDED.error
                """,
                event.id,
                event.subscription_id,
                event.wallet_id,
                event.scheduled_at,
                event.status.value,
                event.amount_cents,
                event.fund_tx_id,
                event.approval_id,
                event.charge_tx_id,
                event.error,
                event.created_at,
            )
        return event

    async def get_billing_history(
        self, sub_id: str, limit: int = 20
    ) -> List[BillingEvent]:
        """Get billing history for a subscription."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM billing_events
                WHERE subscription_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                sub_id,
                limit,
            )
        return [self._row_to_billing_event(r) for r in rows]

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    async def queue_notification(self, notification: OwnerNotification) -> None:
        """Queue a notification for delivery."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO subscription_notifications (
                    id, subscription_id, owner_id, notification_type,
                    channel, payload, sent, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                notification.id,
                notification.subscription_id,
                notification.owner_id,
                notification.notification_type.value,
                notification.channel,
                __import__("json").dumps(notification.payload),
                notification.sent,
                notification.created_at,
            )
        logger.info(
            f"Notification queued: {notification.notification_type.value} "
            f"for subscription {notification.subscription_id}"
        )

    async def get_pending_notifications(self) -> List[OwnerNotification]:
        """Get unsent notifications."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM subscription_notifications
                WHERE sent = false
                ORDER BY created_at ASC
                LIMIT 100
                """
            )
        return [self._row_to_notification(r) for r in rows]

    async def mark_notification_sent(self, notif_id: str) -> None:
        """Mark a notification as sent."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE subscription_notifications
                SET sent = true, sent_at = $2
                WHERE id = $1
                """,
                notif_id,
                datetime.now(timezone.utc),
            )

    # ------------------------------------------------------------------
    # Row mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_subscription(row) -> Subscription:
        return Subscription(
            id=row["id"],
            wallet_id=row["wallet_id"],
            owner_id=row["owner_id"] or "",
            merchant=row["merchant"],
            merchant_mcc=row["merchant_mcc"],
            amount_cents=row["amount_cents"],
            currency=row["currency"],
            billing_cycle=BillingCycle(row["billing_cycle"]),
            billing_day=row["billing_day"],
            next_billing=row["next_billing"],
            card_id=row["card_id"],
            auto_approve=row["auto_approve"],
            auto_approve_threshold_cents=row["auto_approve_threshold_cents"],
            amount_tolerance_cents=row["amount_tolerance_cents"],
            notify_owner=row["notify_owner"],
            notification_channel=row["notification_channel"],
            status=SubscriptionStatus(row["status"]),
            last_charged_at=row["last_charged_at"],
            failure_count=row["failure_count"],
            max_failures=row["max_failures"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_billing_event(row) -> BillingEvent:
        return BillingEvent(
            id=row["id"],
            subscription_id=row["subscription_id"],
            wallet_id=row["wallet_id"],
            scheduled_at=row["scheduled_at"],
            status=BillingEventStatus(row["status"]),
            amount_cents=row["amount_cents"],
            fund_tx_id=row["fund_tx_id"],
            approval_id=row["approval_id"],
            charge_tx_id=row["charge_tx_id"],
            error=row["error"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_notification(row) -> OwnerNotification:
        payload = row["payload"]
        if isinstance(payload, str):
            payload = __import__("json").loads(payload)
        return OwnerNotification(
            id=row["id"],
            subscription_id=row["subscription_id"],
            owner_id=row["owner_id"],
            notification_type=NotificationType(row["notification_type"]),
            channel=row["channel"],
            payload=payload or {},
            sent=row["sent"],
            sent_at=row["sent_at"],
            created_at=row["created_at"],
        )
