"""Usage metering service for billing-grade event tracking.

Tracks API calls, transactions, card issuances, and policy checks
per organization. Backed by PostgreSQL for billing accuracy.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class UsageSummary:
    org_id: str
    period_start: str
    period_end: str
    transactions: int = 0
    cards_issued: int = 0
    policy_checks: int = 0
    api_calls: int = 0


# Tier limits: plan -> {event_type -> monthly_limit}
# Canonical plan names: free, starter, growth, enterprise (from billing/config.py)
TIER_LIMITS: dict[str, dict[str, int]] = {
    "free": {"transaction": 100, "card_issued": 1, "policy_check": 1000, "api_call": 1000},
    "starter": {"transaction": 10000, "card_issued": 10, "policy_check": 50000, "api_call": 50000},
    "growth": {"transaction": 100000, "card_issued": 25, "policy_check": 500000, "api_call": 500000},
    "enterprise": {"transaction": -1, "card_issued": -1, "policy_check": -1, "api_call": -1},  # -1 = unlimited
}


class UsageMeteringService:
    """Track and query usage events per organization."""

    async def track_event(
        self,
        org_id: str,
        event_type: str,
        quantity: int = 1,
    ) -> None:
        """Record a usage event. Best-effort — failures are logged, not raised."""
        try:
            from sardis_v2_core.database import Database

            pool = await Database.get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO usage_events (org_id, event_type, quantity, created_at)
                    VALUES ($1, $2, $3, $4)
                    """,
                    org_id,
                    event_type,
                    quantity,
                    datetime.now(UTC),
                )
        except Exception as e:
            logger.warning("Failed to track usage event for %s: %s", org_id, e)

    async def get_usage(
        self,
        org_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> UsageSummary:
        """Get aggregated usage for an organization in a given period."""
        now = datetime.now(UTC)
        if period_start is None:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period_end is None:
            period_end = now

        try:
            from sardis_v2_core.database import Database

            pool = await Database.get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT event_type, COALESCE(SUM(quantity), 0) AS total
                    FROM usage_events
                    WHERE org_id = $1
                      AND created_at >= $2
                      AND created_at < $3
                    GROUP BY event_type
                    """,
                    org_id,
                    period_start,
                    period_end,
                )

            totals = {row["event_type"]: int(row["total"]) for row in rows}

            return UsageSummary(
                org_id=org_id,
                period_start=period_start.isoformat(),
                period_end=period_end.isoformat(),
                transactions=totals.get("transaction", 0),
                cards_issued=totals.get("card_issued", 0),
                policy_checks=totals.get("policy_check", 0),
                api_calls=totals.get("api_call", 0),
            )

        except Exception as e:
            logger.error("Failed to get usage for %s: %s", org_id, e)
            return UsageSummary(
                org_id=org_id,
                period_start=period_start.isoformat(),
                period_end=period_end.isoformat(),
            )

    async def check_limit(self, org_id: str, event_type: str, plan: str = "free") -> bool:
        """Check if an org is within their plan limits for an event type.

        Returns True if the event is allowed, False if limit exceeded.
        """
        limits = TIER_LIMITS.get(plan, TIER_LIMITS["free"])
        limit = limits.get(event_type, 0)
        if limit == -1:
            return True  # unlimited

        usage = await self.get_usage(org_id)
        current = getattr(usage, {
            "transaction": "transactions",
            "card_issued": "cards_issued",
            "policy_check": "policy_checks",
            "api_call": "api_calls",
        }.get(event_type, "api_calls"), 0)

        return current < limit
