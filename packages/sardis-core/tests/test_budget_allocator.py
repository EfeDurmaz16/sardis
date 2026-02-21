"""
Tests for budget allocation system.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from sardis_v2_core.budget_allocator import (
    AllocationStrategy,
    BudgetAllocator,
    BudgetPeriod,
    CycleStatus,
    FixedAllocation,
    PerformanceBasedAllocation,
    ProportionalAllocation,
    RolloverAllocation,
)


class TestFixedAllocation:
    """Test fixed allocation strategy."""

    def test_equal_split(self):
        """Test equal split when no fixed amounts specified."""
        strategy = FixedAllocation()
        agents = [{"id": "agent1"}, {"id": "agent2"}, {"id": "agent3"}]
        total_budget = Decimal("1000")

        allocations = strategy.allocate(total_budget, agents)

        assert len(allocations) == 3
        for alloc in allocations:
            assert alloc["amount"] == Decimal("1000") / 3

    def test_predefined_amounts(self):
        """Test allocation with predefined fixed amounts."""
        strategy = FixedAllocation()
        agents = [
            {"id": "agent1", "fixed_amount": "300"},
            {"id": "agent2", "fixed_amount": "200"},
            {"id": "agent3"},  # Will get remaining
        ]
        total_budget = Decimal("1000")

        allocations = strategy.allocate(total_budget, agents)

        assert len(allocations) == 3
        alloc_map = {a["agent_id"]: a["amount"] for a in allocations}
        assert alloc_map["agent1"] == Decimal("300")
        assert alloc_map["agent2"] == Decimal("200")
        assert alloc_map["agent3"] == Decimal("500")  # Remaining

    def test_exceeds_budget(self):
        """Test error when fixed amounts exceed budget."""
        strategy = FixedAllocation()
        agents = [
            {"id": "agent1", "fixed_amount": "600"},
            {"id": "agent2", "fixed_amount": "600"},
        ]
        total_budget = Decimal("1000")

        with pytest.raises(ValueError, match="exceed total budget"):
            strategy.allocate(total_budget, agents)


class TestProportionalAllocation:
    """Test proportional allocation strategy."""

    def test_weighted_allocation(self):
        """Test allocation based on weights."""
        strategy = ProportionalAllocation()
        agents = [
            {"id": "agent1", "weight": "2"},  # 50%
            {"id": "agent2", "weight": "1"},  # 25%
            {"id": "agent3", "weight": "1"},  # 25%
        ]
        total_budget = Decimal("1000")

        allocations = strategy.allocate(total_budget, agents)

        assert len(allocations) == 3
        alloc_map = {a["agent_id"]: a["amount"] for a in allocations}
        assert alloc_map["agent1"] == Decimal("500")
        assert alloc_map["agent2"] == Decimal("250")
        assert alloc_map["agent3"] == Decimal("250")

    def test_missing_weight(self):
        """Test error when agent missing weight."""
        strategy = ProportionalAllocation()
        agents = [{"id": "agent1", "weight": "1"}, {"id": "agent2"}]  # Missing weight
        total_budget = Decimal("1000")

        with pytest.raises(ValueError, match="missing required 'weight'"):
            strategy.allocate(total_budget, agents)


class TestPerformanceBasedAllocation:
    """Test performance-based allocation strategy."""

    def test_roi_based_allocation(self):
        """Test allocation based on ROI from history."""
        strategy = PerformanceBasedAllocation(min_allocation_pct=Decimal("0.1"))
        agents = [{"id": "agent1"}, {"id": "agent2"}]
        history = [
            {"agent_id": "agent1", "spent": "100", "value_generated": "300"},  # ROI = 3
            {"agent_id": "agent2", "spent": "100", "value_generated": "100"},  # ROI = 1
        ]
        total_budget = Decimal("1000")

        allocations = strategy.allocate(total_budget, agents, history)

        assert len(allocations) == 2
        alloc_map = {a["agent_id"]: a["amount"] for a in allocations}
        # agent1 should get more due to higher ROI
        assert alloc_map["agent1"] > alloc_map["agent2"]

    def test_no_history_fallback(self):
        """Test fallback to equal allocation when no history."""
        strategy = PerformanceBasedAllocation()
        agents = [{"id": "agent1"}, {"id": "agent2"}]
        total_budget = Decimal("1000")

        allocations = strategy.allocate(total_budget, agents)

        assert len(allocations) == 2
        for alloc in allocations:
            assert alloc["amount"] == Decimal("500")

    def test_minimum_allocation(self):
        """Test that agents without history get minimum allocation before normalization."""
        strategy = PerformanceBasedAllocation(min_allocation_pct=Decimal("0.05"))
        agents = [{"id": "agent1"}, {"id": "agent2"}]
        history = [
            {"agent_id": "agent1", "spent": "100", "value_generated": "500"},  # ROI = 5
            # agent2 has no history
        ]
        total_budget = Decimal("1000")

        allocations = strategy.allocate(total_budget, agents, history)

        alloc_map = {a["agent_id"]: a["amount"] for a in allocations}
        # agent1 should get more due to performance
        assert alloc_map["agent1"] > alloc_map["agent2"]
        # Both should have positive allocations
        assert alloc_map["agent2"] > 0


class TestRolloverAllocation:
    """Test rollover allocation strategy."""

    def test_rollover_with_unused(self):
        """Test rollover of unused budget."""
        strategy = RolloverAllocation(rollover_cap_pct=Decimal("0.25"))
        agents = [{"id": "agent1"}, {"id": "agent2"}]
        history = [
            {"agent_id": "agent1", "allocated": "500", "spent": "300"},  # 200 unused
            {"agent_id": "agent2", "allocated": "500", "spent": "500"},  # 0 unused
        ]
        total_budget = Decimal("1000")

        allocations = strategy.allocate(total_budget, agents, history)

        alloc_map = {a["agent_id"]: a["amount"] for a in allocations}
        # agent1 should get base + rollover (capped at 25% of 500 = 125)
        assert alloc_map["agent1"] > alloc_map["agent2"]

    def test_rollover_cap(self):
        """Test that rollover is capped."""
        strategy = RolloverAllocation(rollover_cap_pct=Decimal("0.25"))
        agents = [{"id": "agent1"}]
        history = [
            {"agent_id": "agent1", "allocated": "1000", "spent": "0"},  # All unused
        ]
        total_budget = Decimal("1000")

        allocations = strategy.allocate(total_budget, agents, history)

        # Rollover capped at 25% of 1000 = 250
        # Total = base (1000 - 250) + rollover (250) = 1000
        assert allocations[0]["amount"] == Decimal("1000")


class TestBudgetAllocator:
    """Test budget allocator orchestrator."""

    def test_create_cycle(self):
        """Test creating a budget cycle."""
        allocator = BudgetAllocator()
        agents = [{"id": "agent1", "weight": "1"}, {"id": "agent2", "weight": "1"}]

        cycle = allocator.create_cycle(
            org_id="org123",
            period=BudgetPeriod.MONTHLY,
            total_budget=Decimal("1000"),
            currency="USDC",
            strategy=AllocationStrategy.PROPORTIONAL,
            agent_configs=agents,
        )

        assert cycle.org_id == "org123"
        assert cycle.period == BudgetPeriod.MONTHLY
        assert cycle.total_budget == Decimal("1000")
        assert cycle.currency == "USDC"
        assert cycle.status == CycleStatus.ACTIVE
        assert len(cycle.allocations) == 2
        assert cycle.allocated_total == Decimal("1000")

    def test_get_current_cycle(self):
        """Test retrieving current active cycle."""
        allocator = BudgetAllocator()
        agents = [{"id": "agent1"}]

        cycle = allocator.create_cycle(
            org_id="org123",
            period=BudgetPeriod.WEEKLY,
            total_budget=Decimal("500"),
            currency="USDC",
            strategy=AllocationStrategy.FIXED,
            agent_configs=agents,
        )

        current = allocator.get_current_cycle("org123")
        assert current is not None
        assert current.id == cycle.id

    def test_close_cycle(self):
        """Test closing a budget cycle."""
        allocator = BudgetAllocator()
        agents = [{"id": "agent1"}]

        cycle = allocator.create_cycle(
            org_id="org123",
            period=BudgetPeriod.MONTHLY,
            total_budget=Decimal("1000"),
            currency="USDC",
            strategy=AllocationStrategy.FIXED,
            agent_configs=agents,
        )

        spending = [{"agent_id": "agent1", "spent": "600"}]
        closed = allocator.close_cycle(cycle.id, spending)

        assert closed.status == CycleStatus.CLOSED
        assert closed.closed_at is not None
        assert Decimal(closed.metadata["unspent_total"]) == Decimal("400")

    def test_get_agent_budget(self):
        """Test retrieving agent budget allocation."""
        allocator = BudgetAllocator()
        agents = [{"id": "agent1", "fixed_amount": "300"}, {"id": "agent2"}]

        cycle = allocator.create_cycle(
            org_id="org123",
            period=BudgetPeriod.MONTHLY,
            total_budget=Decimal("1000"),
            currency="USDC",
            strategy=AllocationStrategy.FIXED,
            agent_configs=agents,
        )

        allocation = allocator.get_agent_budget("agent1", cycle.id)
        assert allocation is not None
        assert allocation.agent_id == "agent1"
        assert allocation.amount == Decimal("300")

    def test_budget_utilization(self):
        """Test budget utilization calculation."""
        allocator = BudgetAllocator()
        agents = [{"id": "agent1"}]

        cycle = allocator.create_cycle(
            org_id="org123",
            period=BudgetPeriod.MONTHLY,
            total_budget=Decimal("1000"),
            currency="USDC",
            strategy=AllocationStrategy.FIXED,
            agent_configs=agents,
        )

        util = allocator.get_budget_utilization("agent1", cycle.id, Decimal("600"))

        assert util["allocated"] == Decimal("1000")
        assert util["spent"] == Decimal("600")
        assert util["remaining"] == Decimal("400")
        assert util["utilization_pct"] == Decimal("60")

    def test_adjust_allocation(self):
        """Test adjusting agent allocation."""
        allocator = BudgetAllocator()
        agents = [{"id": "agent1"}]

        cycle = allocator.create_cycle(
            org_id="org123",
            period=BudgetPeriod.MONTHLY,
            total_budget=Decimal("1000"),
            currency="USDC",
            strategy=AllocationStrategy.FIXED,
            agent_configs=agents,
        )

        adjusted = allocator.adjust_allocation(
            "agent1", cycle.id, Decimal("1200"), "Performance exceeded expectations"
        )

        assert adjusted.amount == Decimal("1200")
        assert "adjustments" in adjusted.metadata
        assert len(adjusted.metadata["adjustments"]) == 1

    def test_auto_rollover(self):
        """Test automatic rollover to new cycle."""
        allocator = BudgetAllocator()
        agents = [{"id": "agent1"}]

        # Create initial cycle
        cycle1 = allocator.create_cycle(
            org_id="org123",
            period=BudgetPeriod.MONTHLY,
            total_budget=Decimal("1000"),
            currency="USDC",
            strategy=AllocationStrategy.FIXED,
            agent_configs=agents,
        )

        # Rollover with spending data
        spending = [{"agent_id": "agent1", "spent": "600"}]
        cycle2 = allocator.auto_rollover(
            org_id="org123",
            new_total_budget=Decimal("1000"),
            currency="USDC",
            agent_configs=agents,
            spending_data=spending,
        )

        # Check that cycle1 is closed
        assert cycle1.status == CycleStatus.CLOSED

        # Check that cycle2 includes rollover
        assert cycle2.rollover_from == cycle1.id
        assert cycle2.rollover_amount > 0
        assert cycle2.total_budget > Decimal("1000")  # Has rollover added

    def test_get_available_strategies(self):
        """Test listing available strategies."""
        allocator = BudgetAllocator()
        strategies = allocator.get_available_strategies()

        assert len(strategies) == 4
        strategy_names = [s["name"] for s in strategies]
        assert "fixed" in strategy_names
        assert "proportional" in strategy_names
        assert "performance_based" in strategy_names
        assert "rollover" in strategy_names
