"""Stripe Billing integration for subscription management.

Handles customer creation, subscription lifecycle, usage reporting,
and webhook processing for Stripe Billing.

Tiers (canonical names from billing/config.py):
  Free:       $0/mo  — 1K API calls, 2 agents, 1.5% tx fee, $1K/mo volume
  Starter:    $49/mo — 50K API calls, 10 agents, 1.0% tx fee, $25K/mo volume
  Growth:     $249/mo — 500K API calls, 100 agents, 0.75% tx fee, $250K/mo volume
  Enterprise: custom — unlimited, 0.5% tx fee
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class BillingPlan:
    name: str
    display_name: str
    monthly_price_cents: int
    tx_fee_bps: int  # basis points (50 = 0.5%)
    tx_limit: int  # -1 = unlimited
    agent_limit: int
    card_limit: int


PLANS: dict[str, BillingPlan] = {
    "free": BillingPlan("free", "Free", 0, 150, 100, 2, 1),
    "starter": BillingPlan("starter", "Starter", 4900, 100, 10000, 10, 25),
    "growth": BillingPlan("growth", "Growth", 24900, 75, 100000, 100, -1),
    "enterprise": BillingPlan("enterprise", "Enterprise", 0, 50, -1, -1, -1),
}


@dataclass
class SubscriptionInfo:
    org_id: str
    plan: str
    status: str
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_start: str | None = None
    current_period_end: str | None = None


class StripeBillingService:
    """Manage Stripe Billing subscriptions and usage reporting."""

    def __init__(self) -> None:
        self._stripe_key = os.getenv("SARDIS_STRIPE_BILLING_SECRET_KEY", "")
        self._webhook_secret = os.getenv("SARDIS_STRIPE_BILLING_WEBHOOK_SECRET", "")

    @property
    def stripe_configured(self) -> bool:
        return bool(self._stripe_key)

    async def get_or_create_subscription(self, org_id: str) -> SubscriptionInfo:
        """Get existing subscription or return default free tier."""
        try:
            from sardis_v2_core.database import Database

            pool = await Database.get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT org_id, stripe_customer_id, stripe_subscription_id,
                           plan, status, current_period_start, current_period_end
                    FROM billing_subscriptions
                    WHERE org_id = $1
                    """,
                    org_id,
                )

            if row:
                return SubscriptionInfo(
                    org_id=row["org_id"],
                    plan=row["plan"],
                    status=row["status"],
                    stripe_customer_id=row["stripe_customer_id"],
                    stripe_subscription_id=row["stripe_subscription_id"],
                    current_period_start=row["current_period_start"].isoformat() if row["current_period_start"] else None,
                    current_period_end=row["current_period_end"].isoformat() if row["current_period_end"] else None,
                )

            # No subscription — return free tier default
            return SubscriptionInfo(org_id=org_id, plan="free", status="active")

        except Exception as e:
            logger.error("Failed to get subscription for %s: %s", org_id, e)
            return SubscriptionInfo(org_id=org_id, plan="free", status="active")

    async def create_subscription(
        self,
        org_id: str,
        plan: str,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
    ) -> SubscriptionInfo:
        """Create or update a billing subscription."""
        if plan not in PLANS:
            raise ValueError(f"Invalid plan: {plan}. Must be one of: {list(PLANS.keys())}")

        now = datetime.now(UTC)

        try:
            from sardis_v2_core.database import Database

            pool = await Database.get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO billing_subscriptions
                        (org_id, stripe_customer_id, stripe_subscription_id, plan, status,
                         current_period_start, current_period_end, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, 'active', $5, $5 + INTERVAL '30 days', $5, $5)
                    ON CONFLICT (org_id) DO UPDATE SET
                        stripe_customer_id = COALESCE(EXCLUDED.stripe_customer_id, billing_subscriptions.stripe_customer_id),
                        stripe_subscription_id = COALESCE(EXCLUDED.stripe_subscription_id, billing_subscriptions.stripe_subscription_id),
                        plan = EXCLUDED.plan,
                        status = 'active',
                        current_period_start = EXCLUDED.current_period_start,
                        current_period_end = EXCLUDED.current_period_end,
                        updated_at = EXCLUDED.updated_at
                    """,
                    org_id,
                    stripe_customer_id,
                    stripe_subscription_id,
                    plan,
                    now,
                )

            logger.info("Subscription created/updated for %s: plan=%s", org_id, plan)

            return SubscriptionInfo(
                org_id=org_id,
                plan=plan,
                status="active",
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                current_period_start=now.isoformat(),
                current_period_end=(now.replace(day=1) + timedelta(days=32)).replace(day=1).isoformat(),
            )

        except Exception as e:
            logger.error("Failed to create subscription for %s: %s", org_id, e)
            raise

    async def get_invoices(self, org_id: str) -> list[dict]:
        """Get invoice history for an organization.

        If Stripe is configured, fetches from Stripe API.
        Otherwise returns empty list (free tier has no invoices).
        """
        sub = await self.get_or_create_subscription(org_id)
        if not sub.stripe_customer_id or not self.stripe_configured:
            return []

        try:
            import stripe

            stripe.api_key = self._stripe_key
            invoices = stripe.Invoice.list(customer=sub.stripe_customer_id, limit=10)
            return [
                {
                    "id": inv.id,
                    "amount_due": inv.amount_due,
                    "currency": inv.currency,
                    "status": inv.status,
                    "created": inv.created,
                    "invoice_pdf": inv.invoice_pdf,
                }
                for inv in invoices.data
            ]
        except Exception as e:
            logger.error("Failed to fetch Stripe invoices for %s: %s", org_id, e)
            return []

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature."""
        if not self._webhook_secret:
            logger.warning("Stripe billing webhook secret not configured")
            return False

        try:
            import stripe

            stripe.Webhook.construct_event(payload, signature, self._webhook_secret)
            return True
        except Exception:
            return False

    def _resolve_plan_from_price(self, price_id: str) -> str | None:
        """Map a Stripe price ID back to a plan name.

        Reads SARDIS_BILLING_STRIPE_PRICE_STARTER / _GROWTH env vars.
        Returns None if no match (caller should keep existing plan).
        """
        starter_price = os.getenv("SARDIS_BILLING_STRIPE_PRICE_STARTER", "")
        growth_price = os.getenv("SARDIS_BILLING_STRIPE_PRICE_GROWTH", "")
        if price_id and price_id == starter_price:
            return "starter"
        if price_id and price_id == growth_price:
            return "growth"
        return None

    async def handle_webhook_event(self, event_type: str, data: dict) -> None:
        """Process a Stripe webhook event."""
        if event_type == "checkout.session.completed":
            session = data.get("object", {})
            metadata = session.get("metadata", {})
            org_id = metadata.get("org_id")
            plan = metadata.get("plan")
            stripe_customer_id = session.get("customer")
            stripe_subscription_id = session.get("subscription")

            if org_id and plan:
                try:
                    await self.create_subscription(
                        org_id=org_id,
                        plan=plan,
                        stripe_customer_id=stripe_customer_id,
                        stripe_subscription_id=stripe_subscription_id,
                    )
                    logger.info(
                        "Checkout completed: org=%s plan=%s customer=%s",
                        org_id, plan, stripe_customer_id,
                    )
                except Exception as e:
                    logger.error("Failed to process checkout.session.completed: %s", e)
            else:
                logger.warning(
                    "checkout.session.completed missing org_id or plan in metadata: %s",
                    metadata,
                )

        elif event_type == "customer.subscription.updated":
            sub_data = data.get("object", {})
            stripe_customer_id = sub_data.get("customer")
            sub_status = sub_data.get("status", "active")

            # Try to resolve plan from the subscription's price
            items = sub_data.get("items", {}).get("data", [])
            price_id = items[0].get("price", {}).get("id", "") if items else ""
            resolved_plan = self._resolve_plan_from_price(price_id)

            if stripe_customer_id:
                try:
                    from sardis_v2_core.database import get_pool

                    pool = await get_pool()
                    async with pool.acquire() as conn:
                        if resolved_plan:
                            await conn.execute(
                                """
                                UPDATE billing_subscriptions
                                SET status = $1, plan = $2, updated_at = NOW()
                                WHERE stripe_customer_id = $3
                                """,
                                sub_status,
                                resolved_plan,
                                stripe_customer_id,
                            )
                        else:
                            await conn.execute(
                                """
                                UPDATE billing_subscriptions
                                SET status = $1, updated_at = NOW()
                                WHERE stripe_customer_id = $2
                                """,
                                sub_status,
                                stripe_customer_id,
                            )
                except Exception as e:
                    logger.error("Failed to update subscription from webhook: %s", e)

        elif event_type == "customer.subscription.deleted":
            sub_data = data.get("object", {})
            stripe_customer_id = sub_data.get("customer")

            if stripe_customer_id:
                try:
                    from sardis_v2_core.database import get_pool

                    pool = await get_pool()
                    async with pool.acquire() as conn:
                        await conn.execute(
                            """
                            UPDATE billing_subscriptions
                            SET status = 'canceled', plan = 'free', updated_at = NOW()
                            WHERE stripe_customer_id = $1
                            """,
                            stripe_customer_id,
                        )
                except Exception as e:
                    logger.error("Failed to cancel subscription from webhook: %s", e)

        elif event_type == "invoice.payment_failed":
            inv = data.get("object", {})
            logger.warning(
                "Invoice payment failed: id=%s customer=%s",
                inv.get("id"), inv.get("customer"),
            )

        else:
            logger.debug("Unhandled Stripe billing webhook: %s", event_type)
