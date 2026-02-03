"""In-memory spending policy store (demo/dev)."""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional

from .policy_store import AsyncPolicyStore
from .spending_policy import SpendingPolicy, create_default_policy
from .utils import TTLDict


class InMemoryPolicyStore(AsyncPolicyStore):
    """In-memory policy store (swap for PostgreSQL in production)."""

    DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60
    DEFAULT_MAX_ITEMS = 10000

    def __init__(
        self,
        *,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_items: int = DEFAULT_MAX_ITEMS,
    ) -> None:
        self._policies: TTLDict[str, SpendingPolicy] = TTLDict(
            ttl_seconds=ttl_seconds,
            max_items=max_items,
        )

    async def fetch_policy(self, agent_id: str) -> Optional[SpendingPolicy]:
        return self._policies.get(agent_id)

    async def set_policy(self, agent_id: str, policy: SpendingPolicy) -> None:
        self._policies[agent_id] = policy

    async def delete_policy(self, agent_id: str) -> bool:
        if agent_id in self._policies:
            del self._policies[agent_id]
            return True
        return False

    async def record_spend(self, agent_id: str, amount: Decimal) -> SpendingPolicy:
        """
        Update policy spend state (spent_total + time windows).

        Note: This is process-local only (demo/dev). Use PostgresPolicyStore in production.
        """
        if amount <= 0:
            raise ValueError("amount_must_be_positive")

        policy = self._policies.get(agent_id) or create_default_policy(agent_id)

        # Reset windows if needed, then record spend
        for window in (policy.daily_limit, policy.weekly_limit, policy.monthly_limit):
            if window is None:
                continue
            window.reset_if_expired()
            window.record_spend(amount)

        policy.spent_total += amount
        policy.updated_at = datetime.now(timezone.utc)
        self._policies[agent_id] = policy
        return policy
