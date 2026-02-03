"""In-memory spending policy store (demo/dev)."""

from __future__ import annotations

from typing import Optional

from .policy_store import AsyncPolicyStore
from .spending_policy import SpendingPolicy
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

