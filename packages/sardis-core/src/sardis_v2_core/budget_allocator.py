"""
Automated Budget Allocation System for Sardis Agent Economy.

Provides flexible budget allocation strategies for organizations managing multiple
AI agents with different spending patterns and performance characteristics.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class AllocationStrategy(str, Enum):
    """Budget allocation strategy types."""

    FIXED = "fixed"
    PROPORTIONAL = "proportional"
    PERFORMANCE_BASED = "performance_based"
    ROLLOVER = "rollover"


class BudgetPeriod(str, Enum):
    """Budget cycle period types."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class CycleStatus(str, Enum):
    """Budget cycle status."""

    ACTIVE = "active"
    CLOSED = "closed"


@dataclass
class BudgetAllocation:
    """Individual agent budget allocation within a cycle."""

    id: UUID
    agent_id: str
    amount: Decimal
    currency: str
    period: BudgetPeriod
    strategy: AllocationStrategy
    allocated_at: datetime
    expires_at: datetime
    cycle_id: UUID
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure Decimal types are properly initialized."""
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))


@dataclass
class BudgetCycle:
    """Budget cycle containing allocations for a specific time period."""

    id: UUID
    org_id: str
    period: BudgetPeriod
    start_date: datetime
    end_date: datetime
    total_budget: Decimal
    currency: str
    strategy: AllocationStrategy
    allocations: list[BudgetAllocation]
    status: CycleStatus
    created_at: datetime
    closed_at: datetime | None = None
    rollover_from: UUID | None = None
    rollover_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure Decimal types are properly initialized."""
        if not isinstance(self.total_budget, Decimal):
            self.total_budget = Decimal(str(self.total_budget))
        if not isinstance(self.rollover_amount, Decimal):
            self.rollover_amount = Decimal(str(self.rollover_amount))

    @property
    def allocated_total(self) -> Decimal:
        """Total amount allocated across all agents."""
        return sum((alloc.amount for alloc in self.allocations), Decimal("0"))

    @property
    def unallocated_amount(self) -> Decimal:
        """Remaining unallocated budget."""
        return self.total_budget - self.allocated_total

    @property
    def is_active(self) -> bool:
        """Check if cycle is currently active."""
        return self.status == CycleStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        """Check if cycle has passed its end date."""
        return datetime.now(timezone.utc) > self.end_date


class BaseAllocationStrategy(ABC):
    """Base class for budget allocation strategies."""

    @abstractmethod
    def allocate(
        self,
        total_budget: Decimal,
        agents: list[dict[str, Any]],
        history: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Calculate budget allocations for agents.

        Args:
            total_budget: Total budget to allocate
            agents: List of agent configs with id, name, and strategy-specific params
            history: Optional historical spending/performance data

        Returns:
            List of allocation dicts with agent_id and amount
        """
        pass


class FixedAllocation(BaseAllocationStrategy):
    """Fixed budget allocation - equal split or predefined amounts."""

    def allocate(
        self,
        total_budget: Decimal,
        agents: list[dict[str, Any]],
        history: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Allocate budget using fixed amounts.

        If agents specify 'fixed_amount', use that. Otherwise split equally.
        """
        if not agents:
            return []

        allocations = []
        predefined_total = Decimal("0")
        agents_without_fixed = []

        # First pass: collect predefined amounts
        for agent in agents:
            if "fixed_amount" in agent:
                amount = Decimal(str(agent["fixed_amount"]))
                allocations.append({"agent_id": agent["id"], "amount": amount})
                predefined_total += amount
            else:
                agents_without_fixed.append(agent)

        # Second pass: split remaining budget equally among agents without fixed amounts
        if agents_without_fixed:
            remaining = total_budget - predefined_total
            if remaining < 0:
                raise ValueError("Predefined amounts exceed total budget")

            equal_share = remaining / len(agents_without_fixed)
            for agent in agents_without_fixed:
                allocations.append({"agent_id": agent["id"], "amount": equal_share})
        else:
            # All agents have fixed amounts - check if they exceed budget
            if predefined_total > total_budget:
                raise ValueError("Predefined amounts exceed total budget")

        return allocations


class ProportionalAllocation(BaseAllocationStrategy):
    """Proportional allocation based on agent weights/percentages."""

    def allocate(
        self,
        total_budget: Decimal,
        agents: list[dict[str, Any]],
        history: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Allocate budget proportionally based on agent weights.

        Each agent must have a 'weight' parameter. Weights are normalized to sum to 1.
        """
        if not agents:
            return []

        # Validate that all agents have weights
        for agent in agents:
            if "weight" not in agent:
                raise ValueError(f"Agent {agent['id']} missing required 'weight' parameter")

        # Calculate total weight
        total_weight = sum(Decimal(str(agent["weight"])) for agent in agents)

        if total_weight <= 0:
            raise ValueError("Total weight must be positive")

        # Allocate proportionally
        allocations = []
        for agent in agents:
            weight = Decimal(str(agent["weight"]))
            proportion = weight / total_weight
            amount = total_budget * proportion
            allocations.append({"agent_id": agent["id"], "amount": amount})

        return allocations


class PerformanceBasedAllocation(BaseAllocationStrategy):
    """Performance-based allocation using ROI/efficiency metrics."""

    def __init__(self, min_allocation_pct: Decimal = Decimal("0.05")):
        """
        Initialize performance-based allocator.

        Args:
            min_allocation_pct: Minimum allocation percentage for any agent (default 5%)
        """
        self.min_allocation_pct = min_allocation_pct

    def allocate(
        self,
        total_budget: Decimal,
        agents: list[dict[str, Any]],
        history: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Allocate budget based on past performance metrics.

        Uses historical data to calculate ROI or efficiency scores.
        Falls back to equal allocation if no history available.
        """
        if not agents:
            return []

        if not history:
            # No history - fall back to equal allocation
            equal_share = total_budget / len(agents)
            return [{"agent_id": agent["id"], "amount": equal_share} for agent in agents]

        # Build performance map from history
        performance_map = {}
        for record in history:
            agent_id = record.get("agent_id")
            if not agent_id:
                continue

            spent = Decimal(str(record.get("spent", 0)))
            value = Decimal(str(record.get("value_generated", 0)))

            # Calculate ROI (value / spent)
            roi = value / spent if spent > 0 else Decimal("0")

            if agent_id not in performance_map:
                performance_map[agent_id] = {"roi": roi, "spent": spent, "value": value}
            else:
                # Average ROI across multiple records
                current = performance_map[agent_id]
                current["roi"] = (current["roi"] + roi) / 2
                current["spent"] += spent
                current["value"] += value

        # Calculate performance scores (normalized ROI)
        total_roi = sum(p["roi"] for p in performance_map.values())

        if total_roi <= 0:
            # No positive ROI - fall back to equal allocation
            equal_share = total_budget / len(agents)
            return [{"agent_id": agent["id"], "amount": equal_share} for agent in agents]

        # Allocate based on performance with minimum threshold
        allocations = []
        min_amount = total_budget * self.min_allocation_pct

        for agent in agents:
            agent_id = agent["id"]
            perf = performance_map.get(agent_id)

            if not perf:
                # No history for this agent - give minimum
                amount = min_amount
            else:
                # Allocate proportional to ROI
                roi_proportion = perf["roi"] / total_roi
                amount = max(total_budget * roi_proportion, min_amount)

            allocations.append({"agent_id": agent_id, "amount": amount})

        # Normalize to ensure we don't exceed total budget
        allocated_total = sum(a["amount"] for a in allocations)
        if allocated_total > total_budget:
            scale_factor = total_budget / allocated_total
            for allocation in allocations:
                allocation["amount"] *= scale_factor

        return allocations


class RolloverAllocation(BaseAllocationStrategy):
    """Rollover allocation - unused budget carries to next period with cap."""

    def __init__(self, rollover_cap_pct: Decimal = Decimal("0.25")):
        """
        Initialize rollover allocator.

        Args:
            rollover_cap_pct: Maximum rollover as percentage of total budget (default 25%)
        """
        self.rollover_cap_pct = rollover_cap_pct

    def allocate(
        self,
        total_budget: Decimal,
        agents: list[dict[str, Any]],
        history: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Allocate budget with rollover from previous period.

        Agents with unused budget get additional allocation (up to cap).
        """
        if not agents:
            return []

        # Calculate rollover amounts from history
        rollover_map = {}
        if history:
            for record in history:
                agent_id = record.get("agent_id")
                if not agent_id:
                    continue

                allocated = Decimal(str(record.get("allocated", 0)))
                spent = Decimal(str(record.get("spent", 0)))
                unused = allocated - spent

                if unused > 0:
                    # Cap rollover per agent
                    max_rollover = allocated * self.rollover_cap_pct
                    rollover = min(unused, max_rollover)
                    rollover_map[agent_id] = rollover

        total_rollover = sum(rollover_map.values())

        # Base allocation is equal split of fresh budget
        fresh_budget = total_budget - total_rollover
        if fresh_budget < 0:
            raise ValueError("Rollover amount exceeds total budget")

        base_share = fresh_budget / len(agents) if agents else Decimal("0")

        allocations = []
        for agent in agents:
            agent_id = agent["id"]
            rollover = rollover_map.get(agent_id, Decimal("0"))
            amount = base_share + rollover
            allocations.append({"agent_id": agent_id, "amount": amount})

        return allocations


class BudgetAllocator:
    """Main budget allocation orchestrator."""

    def __init__(self):
        """Initialize budget allocator with strategy registry."""
        self._cycles: dict[UUID, BudgetCycle] = {}
        self._strategies: dict[AllocationStrategy, BaseAllocationStrategy] = {
            AllocationStrategy.FIXED: FixedAllocation(),
            AllocationStrategy.PROPORTIONAL: ProportionalAllocation(),
            AllocationStrategy.PERFORMANCE_BASED: PerformanceBasedAllocation(),
            AllocationStrategy.ROLLOVER: RolloverAllocation(),
        }

    def _get_period_dates(
        self, period: BudgetPeriod, start_date: datetime | None = None
    ) -> tuple[datetime, datetime]:
        """Calculate start and end dates for a budget period."""
        if start_date is None:
            start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        if period == BudgetPeriod.WEEKLY:
            end_date = start_date + timedelta(days=7)
        elif period == BudgetPeriod.MONTHLY:
            # Approximate month as 30 days
            end_date = start_date + timedelta(days=30)
        elif period == BudgetPeriod.QUARTERLY:
            # Approximate quarter as 90 days
            end_date = start_date + timedelta(days=90)
        else:
            raise ValueError(f"Unsupported period: {period}")

        return start_date, end_date

    def create_cycle(
        self,
        org_id: str,
        period: BudgetPeriod,
        total_budget: Decimal,
        currency: str,
        strategy: AllocationStrategy,
        agent_configs: list[dict[str, Any]],
        start_date: datetime | None = None,
        history: list[dict[str, Any]] | None = None,
        rollover_from: UUID | None = None,
        rollover_amount: Decimal = Decimal("0"),
    ) -> BudgetCycle:
        """
        Create a new budget cycle with allocations.

        Args:
            org_id: Organization identifier
            period: Budget period type
            total_budget: Total budget for the cycle
            currency: Currency code (e.g., 'USDC')
            strategy: Allocation strategy to use
            agent_configs: List of agent configurations
            start_date: Optional start date (defaults to now)
            history: Optional historical data for performance-based allocation
            rollover_from: Optional previous cycle ID for rollover tracking
            rollover_amount: Amount rolled over from previous cycle

        Returns:
            Created BudgetCycle
        """
        cycle_id = uuid4()
        start_date, end_date = self._get_period_dates(period, start_date)

        # Get strategy implementation
        strategy_impl = self._strategies.get(strategy)
        if not strategy_impl:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Calculate allocations
        allocation_dicts = strategy_impl.allocate(total_budget, agent_configs, history)

        # Create BudgetAllocation objects
        allocations = [
            BudgetAllocation(
                id=uuid4(),
                agent_id=alloc["agent_id"],
                amount=alloc["amount"],
                currency=currency,
                period=period,
                strategy=strategy,
                allocated_at=datetime.now(timezone.utc),
                expires_at=end_date,
                cycle_id=cycle_id,
            )
            for alloc in allocation_dicts
        ]

        # Create cycle
        cycle = BudgetCycle(
            id=cycle_id,
            org_id=org_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_budget=total_budget,
            currency=currency,
            strategy=strategy,
            allocations=allocations,
            status=CycleStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            rollover_from=rollover_from,
            rollover_amount=rollover_amount,
        )

        self._cycles[cycle_id] = cycle
        return cycle

    def get_current_cycle(self, org_id: str) -> BudgetCycle | None:
        """
        Get the current active budget cycle for an organization.

        Args:
            org_id: Organization identifier

        Returns:
            Active BudgetCycle or None if no active cycle
        """
        now = datetime.now(timezone.utc)
        for cycle in self._cycles.values():
            if (
                cycle.org_id == org_id
                and cycle.status == CycleStatus.ACTIVE
                and cycle.start_date <= now <= cycle.end_date
            ):
                return cycle
        return None

    def get_cycle(self, cycle_id: UUID) -> BudgetCycle | None:
        """Get a specific budget cycle by ID."""
        return self._cycles.get(cycle_id)

    def close_cycle(
        self, cycle_id: UUID, spending_data: list[dict[str, Any]] | None = None
    ) -> BudgetCycle:
        """
        Close a budget cycle and calculate rollover.

        Args:
            cycle_id: Cycle to close
            spending_data: Actual spending data per agent

        Returns:
            Closed BudgetCycle with rollover calculated
        """
        cycle = self._cycles.get(cycle_id)
        if not cycle:
            raise ValueError(f"Cycle not found: {cycle_id}")

        if cycle.status == CycleStatus.CLOSED:
            raise ValueError(f"Cycle already closed: {cycle_id}")

        # Calculate unspent amount
        if spending_data:
            spending_map = {item["agent_id"]: Decimal(str(item["spent"])) for item in spending_data}
        else:
            spending_map = {}

        unspent_total = Decimal("0")
        for allocation in cycle.allocations:
            spent = spending_map.get(allocation.agent_id, Decimal("0"))
            unspent = allocation.amount - spent
            if unspent > 0:
                unspent_total += unspent

        # Update cycle
        cycle.status = CycleStatus.CLOSED
        cycle.closed_at = datetime.now(timezone.utc)
        cycle.metadata["unspent_total"] = str(unspent_total)
        cycle.metadata["spending_data"] = spending_data or []

        return cycle

    def get_agent_budget(self, agent_id: str, cycle_id: UUID | None = None) -> BudgetAllocation | None:
        """
        Get budget allocation for a specific agent.

        Args:
            agent_id: Agent identifier
            cycle_id: Optional specific cycle (defaults to current active cycles)

        Returns:
            BudgetAllocation or None if not found
        """
        if cycle_id:
            cycle = self._cycles.get(cycle_id)
            if cycle:
                for allocation in cycle.allocations:
                    if allocation.agent_id == agent_id:
                        return allocation
            return None

        # Search active cycles
        for cycle in self._cycles.values():
            if cycle.status == CycleStatus.ACTIVE:
                for allocation in cycle.allocations:
                    if allocation.agent_id == agent_id:
                        return allocation
        return None

    def get_budget_utilization(
        self, agent_id: str, cycle_id: UUID, spent_amount: Decimal
    ) -> dict[str, Any]:
        """
        Calculate budget utilization for an agent.

        Args:
            agent_id: Agent identifier
            cycle_id: Cycle identifier
            spent_amount: Amount spent so far

        Returns:
            Dict with allocated, spent, remaining, utilization_pct
        """
        allocation = self.get_agent_budget(agent_id, cycle_id)
        if not allocation:
            raise ValueError(f"No allocation found for agent {agent_id} in cycle {cycle_id}")

        spent = Decimal(str(spent_amount))
        remaining = allocation.amount - spent
        utilization_pct = (spent / allocation.amount * 100) if allocation.amount > 0 else Decimal("0")

        return {
            "agent_id": agent_id,
            "cycle_id": cycle_id,
            "allocated": allocation.amount,
            "spent": spent,
            "remaining": remaining,
            "utilization_pct": utilization_pct,
            "currency": allocation.currency,
            "expires_at": allocation.expires_at,
        }

    def adjust_allocation(
        self, agent_id: str, cycle_id: UUID, new_amount: Decimal, reason: str
    ) -> BudgetAllocation:
        """
        Adjust an agent's budget allocation.

        Args:
            agent_id: Agent identifier
            cycle_id: Cycle identifier
            new_amount: New allocation amount
            reason: Reason for adjustment

        Returns:
            Updated BudgetAllocation
        """
        cycle = self._cycles.get(cycle_id)
        if not cycle:
            raise ValueError(f"Cycle not found: {cycle_id}")

        if cycle.status != CycleStatus.ACTIVE:
            raise ValueError(f"Cannot adjust allocation in {cycle.status} cycle")

        # Find allocation
        allocation = None
        for alloc in cycle.allocations:
            if alloc.agent_id == agent_id:
                allocation = alloc
                break

        if not allocation:
            raise ValueError(f"No allocation found for agent {agent_id} in cycle {cycle_id}")

        # Update allocation
        old_amount = allocation.amount
        allocation.amount = Decimal(str(new_amount))
        allocation.metadata["adjustments"] = allocation.metadata.get("adjustments", [])
        allocation.metadata["adjustments"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "old_amount": str(old_amount),
                "new_amount": str(new_amount),
                "reason": reason,
            }
        )

        return allocation

    def auto_rollover(
        self,
        org_id: str,
        new_total_budget: Decimal,
        currency: str,
        agent_configs: list[dict[str, Any]],
        spending_data: list[dict[str, Any]],
    ) -> BudgetCycle:
        """
        Automatically create a new cycle with rollover from current cycle.

        Args:
            org_id: Organization identifier
            new_total_budget: Fresh budget for new cycle
            currency: Currency code
            agent_configs: Agent configurations for new cycle
            spending_data: Spending data from current cycle

        Returns:
            New BudgetCycle with rollover applied
        """
        current_cycle = self.get_current_cycle(org_id)
        if not current_cycle:
            raise ValueError(f"No active cycle found for org {org_id}")

        # Close current cycle
        closed_cycle = self.close_cycle(current_cycle.id, spending_data)

        # Calculate rollover
        unspent_total = Decimal(closed_cycle.metadata.get("unspent_total", "0"))

        # Prepare history for rollover strategy
        history = []
        for allocation in closed_cycle.allocations:
            spent = Decimal("0")
            for item in spending_data:
                if item["agent_id"] == allocation.agent_id:
                    spent = Decimal(str(item["spent"]))
                    break

            history.append(
                {"agent_id": allocation.agent_id, "allocated": allocation.amount, "spent": spent}
            )

        # Create new cycle with rollover
        return self.create_cycle(
            org_id=org_id,
            period=closed_cycle.period,
            total_budget=new_total_budget + unspent_total,
            currency=currency,
            strategy=AllocationStrategy.ROLLOVER,
            agent_configs=agent_configs,
            history=history,
            rollover_from=closed_cycle.id,
            rollover_amount=unspent_total,
        )

    def get_available_strategies(self) -> list[dict[str, str]]:
        """Get list of available allocation strategies."""
        return [
            {"name": strategy.value, "description": self._get_strategy_description(strategy)}
            for strategy in AllocationStrategy
        ]

    def _get_strategy_description(self, strategy: AllocationStrategy) -> str:
        """Get human-readable description of allocation strategy."""
        descriptions = {
            AllocationStrategy.FIXED: "Equal split or predefined amounts per agent",
            AllocationStrategy.PROPORTIONAL: "Percentage-based allocation using agent weights",
            AllocationStrategy.PERFORMANCE_BASED: "Based on ROI/efficiency metrics from past spending",
            AllocationStrategy.ROLLOVER: "Unused budget carries to next period (with cap)",
        }
        return descriptions.get(strategy, "Unknown strategy")
