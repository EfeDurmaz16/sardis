"""Group policy evaluator for multi-agent governance.

Aggregates spending across all agents in each group the agent belongs to.
Rules:
- DENY always wins for merchant rules
- Most restrictive numerical limit wins
- Fail-closed on errors
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

logger = logging.getLogger(__name__)

# Period-appropriate TTLs for spend counters
_TTL_DAILY = 86_400        # 24 hours
_TTL_MONTHLY = 2_678_400   # 31 days
_TTL_TOTAL = 31_536_000    # 365 days (effectively no expiry)


@dataclass(slots=True)
class GroupPolicyResult:
    """Result of group policy evaluation."""
    allowed: bool
    reason: str
    group_id: str | None = None
    group_name: str | None = None


class GroupPolicyPort(Protocol):
    """Protocol interface for group policy evaluation in the orchestrator."""

    async def evaluate(
        self,
        agent_id: str,
        amount: Decimal,
        fee: Decimal,
        merchant_id: str | None = None,
        merchant_category: str | None = None,
    ) -> GroupPolicyResult: ...


class GroupPolicyEvaluator:
    """Evaluates group-level spending policies across all groups an agent belongs to.

    Design decisions:
    - DENY always wins: If any group blocks a merchant, the payment is denied.
    - Most restrictive wins: For numerical limits, the tightest limit applies.
    - Fail-closed: Errors in evaluation result in denial.
    """

    def __init__(
        self,
        group_repo: AgentGroupRepository,
        spending_tracker: GroupSpendingTracker | None = None,
    ) -> None:
        from .agent_groups import AgentGroupRepository
        self._group_repo: AgentGroupRepository = group_repo
        self._spending: GroupSpendingTracker = spending_tracker or InMemoryGroupSpendingTracker()

    async def evaluate(
        self,
        agent_id: str,
        amount: Decimal,
        fee: Decimal,
        merchant_id: str | None = None,
        merchant_category: str | None = None,
    ) -> GroupPolicyResult:
        """Evaluate payment against all groups the agent belongs to.

        Returns GroupPolicyResult with allowed=True only if ALL groups permit it.
        """
        try:
            groups = await self._group_repo.get_groups_for_agent(agent_id)
        except Exception as e:
            logger.error("Failed to fetch groups for agent %s: %s", agent_id, e)
            return GroupPolicyResult(allowed=False, reason="group_policy_error")

        if not groups:
            # Agent is not in any group — group policy does not apply
            return GroupPolicyResult(allowed=True, reason="no_group_membership")

        total_cost = amount + fee

        for group in groups:
            # --- Merchant policy checks (DENY wins) ---
            if merchant_id:
                mp = group.merchant_policy

                # Check blocked merchants
                if mp.blocked_merchants:
                    if merchant_id.lower() in [m.lower() for m in mp.blocked_merchants]:
                        return GroupPolicyResult(
                            allowed=False,
                            reason="group_merchant_blocked",
                            group_id=group.group_id,
                            group_name=group.name,
                        )

                # Check blocked categories
                if merchant_category and mp.blocked_categories:
                    if merchant_category.lower() in [c.lower() for c in mp.blocked_categories]:
                        return GroupPolicyResult(
                            allowed=False,
                            reason="group_category_blocked",
                            group_id=group.group_id,
                            group_name=group.name,
                        )

                # Check allowed merchants (whitelist mode)
                if mp.allowed_merchants is not None:
                    if merchant_id.lower() not in [m.lower() for m in mp.allowed_merchants]:
                        return GroupPolicyResult(
                            allowed=False,
                            reason="group_merchant_not_allowed",
                            group_id=group.group_id,
                            group_name=group.name,
                        )

                # Check allowed categories (whitelist mode)
                if merchant_category and mp.allowed_categories is not None:
                    if merchant_category.lower() not in [c.lower() for c in mp.allowed_categories]:
                        return GroupPolicyResult(
                            allowed=False,
                            reason="group_category_not_allowed",
                            group_id=group.group_id,
                            group_name=group.name,
                        )

            # --- Budget checks (most restrictive wins) ---
            budget = group.budget

            # Per-transaction limit
            if total_cost > budget.per_transaction:
                return GroupPolicyResult(
                    allowed=False,
                    reason="group_per_transaction_limit",
                    group_id=group.group_id,
                    group_name=group.name,
                )

            # Aggregate spending checks
            try:
                spending = await self._spending.get_group_spending(group.group_id)
            except Exception as e:
                logger.error("Failed to get spending for group %s: %s", group.group_id, e)
                return GroupPolicyResult(
                    allowed=False,
                    reason="group_spending_lookup_error",
                    group_id=group.group_id,
                    group_name=group.name,
                )

            if spending.daily + total_cost > budget.daily:
                return GroupPolicyResult(
                    allowed=False,
                    reason="group_daily_limit",
                    group_id=group.group_id,
                    group_name=group.name,
                )

            if spending.monthly + total_cost > budget.monthly:
                return GroupPolicyResult(
                    allowed=False,
                    reason="group_monthly_limit",
                    group_id=group.group_id,
                    group_name=group.name,
                )

            if spending.total + total_cost > budget.total:
                return GroupPolicyResult(
                    allowed=False,
                    reason="group_total_limit",
                    group_id=group.group_id,
                    group_name=group.name,
                )

        return GroupPolicyResult(allowed=True, reason="OK")

    async def record_spend(
        self,
        agent_id: str,
        amount: Decimal,
    ) -> None:
        """Record a spend against all groups the agent belongs to."""
        try:
            groups = await self._group_repo.get_groups_for_agent(agent_id)
            for group in groups:
                await self._spending.record_spend(group.group_id, amount)
        except Exception as e:
            logger.error("Failed to record group spend for agent %s: %s", agent_id, e)


# ============ Spending Tracker ============


@dataclass(slots=True)
class GroupSpending:
    """Current spending totals for a group."""
    daily: Decimal = Decimal("0")
    monthly: Decimal = Decimal("0")
    total: Decimal = Decimal("0")


class GroupSpendingTracker(Protocol):
    """Protocol for tracking group spending."""

    async def get_group_spending(self, group_id: str) -> GroupSpending: ...
    async def record_spend(self, group_id: str, amount: Decimal) -> None: ...


class InMemoryGroupSpendingTracker:
    """Redis-backed group spending tracker with in-memory fallback.

    Uses per-period keys with period-appropriate TTLs:
    - {group_id}:daily   -> TTL = 24 hours
    - {group_id}:monthly -> TTL = 31 days
    - {group_id}:total   -> TTL = 365 days
    """

    def __init__(self) -> None:
        from sardis_v2_core.redis_state import RedisStateStore
        self._store = RedisStateStore(namespace="group_spending")

    async def get_group_spending(self, group_id: str) -> GroupSpending:
        daily_data = await self._store.get(f"{group_id}:daily")
        monthly_data = await self._store.get(f"{group_id}:monthly")
        total_data = await self._store.get(f"{group_id}:total")
        return GroupSpending(
            daily=Decimal(str(daily_data.get("value", "0"))) if daily_data else Decimal("0"),
            monthly=Decimal(str(monthly_data.get("value", "0"))) if monthly_data else Decimal("0"),
            total=Decimal(str(total_data.get("value", "0"))) if total_data else Decimal("0"),
        )

    async def record_spend(self, group_id: str, amount: Decimal) -> None:
        # Update daily counter
        daily_data = await self._store.get(f"{group_id}:daily")
        daily = Decimal(str(daily_data["value"])) + amount if daily_data else amount
        await self._store.set(f"{group_id}:daily", {"value": str(daily)}, ttl=_TTL_DAILY)

        # Update monthly counter
        monthly_data = await self._store.get(f"{group_id}:monthly")
        monthly = Decimal(str(monthly_data["value"])) + amount if monthly_data else amount
        await self._store.set(f"{group_id}:monthly", {"value": str(monthly)}, ttl=_TTL_MONTHLY)

        # Update total counter
        total_data = await self._store.get(f"{group_id}:total")
        total = Decimal(str(total_data["value"])) + amount if total_data else amount
        await self._store.set(f"{group_id}:total", {"value": str(total)}, ttl=_TTL_TOTAL)
