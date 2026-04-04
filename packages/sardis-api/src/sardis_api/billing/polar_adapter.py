"""Polar.sh billing adapter — alternative billing provider.

Used when SARDIS_BILLING_PROVIDER=polar. Implements the same interface as
StripeBillingService so the billing router can swap between them.

April 2026: Stripe froze live access due to crypto onramp feature usage.
Polar is the active billing provider until Stripe resolves.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger("sardis.billing.polar")

POLAR_API_URL = os.getenv("POLAR_API_URL", "https://api.polar.sh")
POLAR_ACCESS_TOKEN = os.getenv("POLAR_ACCESS_TOKEN", "")
POLAR_WEBHOOK_SECRET = os.getenv("POLAR_WEBHOOK_SECRET", "")

# Product IDs created on polar.sh dashboard
POLAR_PRODUCT_STARTER_ID = os.getenv("POLAR_PRODUCT_STARTER_ID", "")
POLAR_PRODUCT_GROWTH_ID = os.getenv("POLAR_PRODUCT_GROWTH_ID", "")

PLAN_TO_PRODUCT: dict[str, str] = {
    "starter": POLAR_PRODUCT_STARTER_ID,
    "growth": POLAR_PRODUCT_GROWTH_ID,
}


@dataclass
class PolarCheckoutResult:
    checkout_url: str
    checkout_id: str


@dataclass
class PolarSubscription:
    subscription_id: str
    plan: str
    status: str
    customer_email: str | None = None
    current_period_end: str | None = None


class PolarBillingAdapter:
    """Billing adapter using Polar.sh as Merchant of Record.

    Implements the same interface as StripeBillingService so the billing
    router can swap between them via SARDIS_BILLING_PROVIDER env var.
    """

    def __init__(self) -> None:
        self._token = POLAR_ACCESS_TOKEN
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    async def create_checkout(
        self,
        org_id: str,
        plan: str,
        success_url: str = "https://app.sardis.sh/billing?success=1",
        cancel_url: str = "https://app.sardis.sh/billing?canceled=1",
    ) -> PolarCheckoutResult:
        """Create a Polar checkout session for a subscription plan.

        Returns a checkout URL to redirect the user to.
        """
        product_id = PLAN_TO_PRODUCT.get(plan)
        if not product_id:
            raise ValueError(f"Unknown plan: {plan}. Available: {list(PLAN_TO_PRODUCT.keys())}")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{POLAR_API_URL}/v1/checkouts/",
                headers=self._headers,
                json={
                    "product_id": product_id,
                    "success_url": success_url,
                    "metadata": {
                        "org_id": org_id,
                        "plan": plan,
                        "source": "sardis_dashboard",
                    },
                },
            )

            if resp.status_code not in (200, 201):
                logger.error("Polar checkout creation failed: %s %s", resp.status_code, resp.text)
                raise RuntimeError(f"Polar checkout failed: {resp.status_code}")

            data = resp.json()
            checkout_url = data.get("url") or data.get("checkout_url", "")
            checkout_id = data.get("id", "")

            logger.info("Polar checkout created: %s for org %s plan %s", checkout_id, org_id, plan)

            return PolarCheckoutResult(checkout_url=checkout_url, checkout_id=checkout_id)

    async def get_subscription(self, subscription_id: str) -> PolarSubscription | None:
        """Get subscription details from Polar."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{POLAR_API_URL}/v1/subscriptions/{subscription_id}",
                headers=self._headers,
            )

            if resp.status_code != 200:
                return None

            data = resp.json()

            # Resolve plan from product_id
            product_id = data.get("product_id", "")
            plan = "free"
            for plan_name, pid in PLAN_TO_PRODUCT.items():
                if pid == product_id:
                    plan = plan_name
                    break

            return PolarSubscription(
                subscription_id=data.get("id", ""),
                plan=plan,
                status=data.get("status", "unknown"),
                customer_email=data.get("customer", {}).get("email"),
                current_period_end=data.get("current_period_end"),
            )

    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a Polar subscription."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(
                f"{POLAR_API_URL}/v1/subscriptions/{subscription_id}",
                headers=self._headers,
            )
            return resp.status_code in (200, 204)

    async def get_or_create_subscription(self, org_id: str):
        """Get subscription from DB (compatible with StripeBillingService interface)."""
        from sardis_api.services.stripe_billing import SubscriptionInfo
        try:
            from sardis_v2_core.database import Database
            pool = await Database.get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT plan, status, stripe_subscription_id FROM billing_subscriptions WHERE org_id = $1",
                    org_id,
                )
                if row:
                    return SubscriptionInfo(
                        org_id=org_id,
                        plan=row["plan"],
                        status=row["status"],
                        stripe_customer_id=None,
                        stripe_subscription_id=row["stripe_subscription_id"],
                    )
        except Exception as exc:
            logger.warning("Failed to get subscription for org %s: %s", org_id, exc)

        return SubscriptionInfo(
            org_id=org_id, plan="dev", status="active",
            stripe_customer_id=None, stripe_subscription_id=None,
        )

    async def create_subscription(self, org_id: str, plan: str, **kwargs):
        """Create/update subscription in DB."""
        from sardis_api.services.stripe_billing import SubscriptionInfo
        try:
            from sardis_v2_core.database import Database
            pool = await Database.get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO billing_subscriptions (org_id, plan, status, created_at, updated_at)
                    VALUES ($1, $2, 'active', now(), now())
                    ON CONFLICT (org_id) DO UPDATE SET plan = $2, status = 'active', updated_at = now()
                    """,
                    org_id, plan,
                )
        except Exception as exc:
            logger.error("Failed to create subscription: %s", exc)

        return SubscriptionInfo(org_id=org_id, plan=plan, status="active")

    async def get_invoices(self, org_id: str) -> list:
        """Polar doesn't expose invoices via API. Return empty list."""
        return []

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Alias for verify_webhook (compatible with StripeBillingService)."""
        return self.verify_webhook(body, signature)

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify Polar webhook signature."""
        if not POLAR_WEBHOOK_SECRET:
            logger.warning("POLAR_WEBHOOK_SECRET not set — skipping verification")
            return False

        expected = hmac.new(
            POLAR_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    async def handle_webhook_event(self, event_type: str, data: dict) -> None:
        """Process Polar webhook events.

        Key events:
        - subscription.created — new subscriber
        - subscription.updated — plan change
        - subscription.canceled — cancellation
        - order.created — one-time payment
        """
        if event_type in ("subscription.created", "subscription.updated"):
            metadata = data.get("metadata", {})
            org_id = metadata.get("org_id")
            plan = metadata.get("plan")
            subscription_id = data.get("id")
            status = data.get("status", "active")

            if org_id and plan:
                try:
                    from sardis_v2_core.database import Database
                    pool = await Database.get_pool()
                    async with pool.acquire() as conn:
                        await conn.execute(
                            """
                            INSERT INTO billing_subscriptions
                                (org_id, plan, status, stripe_subscription_id, created_at, updated_at)
                            VALUES ($1, $2, $3, $4, now(), now())
                            ON CONFLICT (org_id) DO UPDATE SET
                                plan = EXCLUDED.plan,
                                status = EXCLUDED.status,
                                stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                                updated_at = now()
                            """,
                            org_id, plan, status,
                            f"polar_{subscription_id}",  # Store with prefix for identification
                        )
                    logger.info("Polar subscription synced: org=%s plan=%s", org_id, plan)
                except Exception as exc:
                    logger.error("Failed to sync Polar subscription: %s", exc)

        elif event_type == "subscription.canceled":
            metadata = data.get("metadata", {})
            org_id = metadata.get("org_id")
            if org_id:
                try:
                    from sardis_v2_core.database import Database
                    pool = await Database.get_pool()
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE billing_subscriptions SET plan='free', status='canceled', updated_at=now() WHERE org_id=$1",
                            org_id,
                        )
                except Exception as exc:
                    logger.error("Failed to cancel Polar subscription: %s", exc)

        elif event_type == "order.created":
            logger.info("Polar order created: %s", data.get("id"))

        else:
            logger.debug("Unhandled Polar event: %s", event_type)


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def get_billing_provider():
    """Get the active billing provider based on SARDIS_BILLING_PROVIDER env var.

    Supports: "polar" (default since April 2026) and "stripe".
    """
    provider = os.getenv("SARDIS_BILLING_PROVIDER", "polar").lower()

    if provider == "polar":
        adapter = PolarBillingAdapter()
        if adapter.is_configured:
            logger.info("Using Polar billing provider")
            return adapter
        logger.warning("Polar not configured (no POLAR_ACCESS_TOKEN), falling back to Stripe")

    from sardis_api.services.stripe_billing import StripeBillingService
    return StripeBillingService()


def get_billing_provider_name() -> str:
    """Return the active provider name for frontend display."""
    provider = os.getenv("SARDIS_BILLING_PROVIDER", "polar").lower()
    if provider == "polar" and POLAR_ACCESS_TOKEN:
        return "polar"
    return "stripe"
