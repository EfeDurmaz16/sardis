"""Spending policy definition store.

This store holds the *policy definition* (SpendingPolicy per agent).
It is distinct from SpendingPolicyStore which tracks *spend state* in a DB.
"""

from __future__ import annotations

from typing import Optional, Protocol

from .spending_policy import SpendingPolicy


class AsyncPolicyStore(Protocol):
    async def fetch_policy(self, agent_id: str) -> Optional[SpendingPolicy]: ...
    async def set_policy(self, agent_id: str, policy: SpendingPolicy) -> None: ...
    async def delete_policy(self, agent_id: str) -> bool: ...

