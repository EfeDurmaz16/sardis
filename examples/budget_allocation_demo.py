"""
Budget Allocation System Demo

Demonstrates all allocation strategies and key features of the budget allocation system.
"""

import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add sardis-core to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "sardis-core" / "src"))

from sardis_v2_core.budget_allocator import (
    AllocationStrategy,
    BudgetAllocator,
    BudgetPeriod,
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_cycle(cycle):
    """Pretty print a budget cycle."""
    print(f"Cycle ID: {cycle.id}")
    print(f"Organization: {cycle.org_id}")
    print(f"Period: {cycle.period.value}")
    print(f"Total Budget: {cycle.total_budget} {cycle.currency}")
    print(f"Status: {cycle.status.value}")
    print(f"Duration: {cycle.start_date.date()} to {cycle.end_date.date()}")
    print(f"\nAllocations ({len(cycle.allocations)} agents):")
    print(f"{'Agent ID':<20} {'Amount':<15} {'Percentage':<10}")
    print("-" * 50)
    for alloc in cycle.allocations:
        pct = (alloc.amount / cycle.total_budget * 100) if cycle.total_budget > 0 else 0
        print(f"{alloc.agent_id:<20} {str(alloc.amount)[:13]:<15} {pct:.2f}%")
    print(f"\nAllocated Total: {cycle.allocated_total} {cycle.currency}")
    print(f"Unallocated: {cycle.unallocated_amount} {cycle.currency}")
    if cycle.rollover_amount > 0:
        print(f"Rollover Amount: {cycle.rollover_amount} {cycle.currency}")


def demo_fixed_allocation():
    """Demonstrate fixed allocation strategy."""
    print_section("Demo 1: Fixed Allocation")

    allocator = BudgetAllocator()

    # Scenario: 3 agents, 2 with fixed amounts, 1 gets remaining
    agents = [
        {"id": "marketing_agent", "fixed_amount": "4000"},
        {"id": "sales_agent", "fixed_amount": "3000"},
        {"id": "support_agent"},  # Gets remaining
    ]

    cycle = allocator.create_cycle(
        org_id="acme_corp",
        period=BudgetPeriod.MONTHLY,
        total_budget=Decimal("10000"),
        currency="USDC",
        strategy=AllocationStrategy.FIXED,
        agent_configs=agents,
    )

    print_cycle(cycle)


def demo_proportional_allocation():
    """Demonstrate proportional allocation strategy."""
    print_section("Demo 2: Proportional Allocation")

    allocator = BudgetAllocator()

    # Scenario: 3 agents with different weights
    agents = [
        {"id": "high_priority_agent", "weight": "3"},
        {"id": "medium_priority_agent", "weight": "2"},
        {"id": "low_priority_agent", "weight": "1"},
    ]

    cycle = allocator.create_cycle(
        org_id="acme_corp",
        period=BudgetPeriod.WEEKLY,
        total_budget=Decimal("6000"),
        currency="USDC",
        strategy=AllocationStrategy.PROPORTIONAL,
        agent_configs=agents,
    )

    print_cycle(cycle)


def demo_performance_based_allocation():
    """Demonstrate performance-based allocation strategy."""
    print_section("Demo 3: Performance-Based Allocation")

    allocator = BudgetAllocator()

    # Scenario: 3 agents with different ROI histories
    agents = [
        {"id": "high_roi_agent"},
        {"id": "medium_roi_agent"},
        {"id": "low_roi_agent"},
    ]

    # Historical performance data
    history = [
        # High ROI: spent 1000, generated 5000 value (5x ROI)
        {"agent_id": "high_roi_agent", "spent": "1000", "value_generated": "5000"},
        # Medium ROI: spent 1000, generated 3000 value (3x ROI)
        {"agent_id": "medium_roi_agent", "spent": "1000", "value_generated": "3000"},
        # Low ROI: spent 1000, generated 1500 value (1.5x ROI)
        {"agent_id": "low_roi_agent", "spent": "1000", "value_generated": "1500"},
    ]

    cycle = allocator.create_cycle(
        org_id="acme_corp",
        period=BudgetPeriod.MONTHLY,
        total_budget=Decimal("15000"),
        currency="USDC",
        strategy=AllocationStrategy.PERFORMANCE_BASED,
        agent_configs=agents,
        history=history,
    )

    print_cycle(cycle)
    print("\nNote: Agents with higher ROI receive larger allocations")


def demo_rollover_allocation():
    """Demonstrate rollover allocation strategy."""
    print_section("Demo 4: Rollover Allocation")

    allocator = BudgetAllocator()

    # Scenario: 2 agents, one spent less than allocated
    agents = [
        {"id": "efficient_agent"},
        {"id": "heavy_spender_agent"},
    ]

    # Previous cycle spending data
    history = [
        # Efficient agent: allocated 5000, spent only 3000 (2000 unused)
        {"agent_id": "efficient_agent", "allocated": "5000", "spent": "3000"},
        # Heavy spender: allocated 5000, spent all 5000 (0 unused)
        {"agent_id": "heavy_spender_agent", "allocated": "5000", "spent": "5000"},
    ]

    cycle = allocator.create_cycle(
        org_id="acme_corp",
        period=BudgetPeriod.MONTHLY,
        total_budget=Decimal("10000"),
        currency="USDC",
        strategy=AllocationStrategy.ROLLOVER,
        agent_configs=agents,
        history=history,
    )

    print_cycle(cycle)
    print("\nNote: Efficient agent gets bonus allocation from unused budget (capped at 25%)")


def demo_budget_utilization():
    """Demonstrate budget utilization tracking."""
    print_section("Demo 5: Budget Utilization Tracking")

    allocator = BudgetAllocator()

    agents = [{"id": "sales_agent"}]

    cycle = allocator.create_cycle(
        org_id="acme_corp",
        period=BudgetPeriod.MONTHLY,
        total_budget=Decimal("5000"),
        currency="USDC",
        strategy=AllocationStrategy.FIXED,
        agent_configs=agents,
    )

    print(f"Allocated Budget: {cycle.allocations[0].amount} USDC\n")

    # Simulate different spending levels
    spending_levels = [
        Decimal("1000"),
        Decimal("2500"),
        Decimal("4000"),
        Decimal("4900"),
    ]

    for spent in spending_levels:
        util = allocator.get_budget_utilization("sales_agent", cycle.id, spent)
        status = "🟢" if util["utilization_pct"] < 70 else "🟡" if util["utilization_pct"] < 90 else "🔴"
        print(f"{status} Spent: {util['spent']:<6} | Remaining: {util['remaining']:<6} | Utilization: {util['utilization_pct']:.1f}%")


def demo_budget_adjustment():
    """Demonstrate budget adjustment."""
    print_section("Demo 6: Budget Adjustment")

    allocator = BudgetAllocator()

    agents = [
        {"id": "agent_a"},
        {"id": "agent_b"},
    ]

    cycle = allocator.create_cycle(
        org_id="acme_corp",
        period=BudgetPeriod.MONTHLY,
        total_budget=Decimal("10000"),
        currency="USDC",
        strategy=AllocationStrategy.FIXED,
        agent_configs=agents,
    )

    print("Initial Allocations:")
    for alloc in cycle.allocations:
        print(f"  {alloc.agent_id}: {alloc.amount} USDC")

    # Adjust agent_a's budget due to exceptional performance
    print("\nAdjusting agent_a budget from 5000 to 7000 USDC...")
    adjusted = allocator.adjust_allocation(
        agent_id="agent_a",
        cycle_id=cycle.id,
        new_amount=Decimal("7000"),
        reason="Exceptional performance - exceeded targets by 40%"
    )

    print(f"\nNew Allocation for agent_a: {adjusted.amount} USDC")
    print(f"Adjustment History: {len(adjusted.metadata.get('adjustments', []))} adjustment(s)")
    if adjusted.metadata.get('adjustments'):
        adj = adjusted.metadata['adjustments'][0]
        print(f"  - Old: {adj['old_amount']} → New: {adj['new_amount']}")
        print(f"  - Reason: {adj['reason']}")


def demo_auto_rollover():
    """Demonstrate automatic rollover to new cycle."""
    print_section("Demo 7: Auto Rollover")

    allocator = BudgetAllocator()

    agents = [
        {"id": "agent_x"},
        {"id": "agent_y"},
    ]

    # Create initial cycle
    cycle1 = allocator.create_cycle(
        org_id="acme_corp",
        period=BudgetPeriod.MONTHLY,
        total_budget=Decimal("10000"),
        currency="USDC",
        strategy=AllocationStrategy.FIXED,
        agent_configs=agents,
    )

    print("Cycle 1 - Initial:")
    print_cycle(cycle1)

    # Simulate spending
    spending_data = [
        {"agent_id": "agent_x", "spent": "4000"},  # Spent 4k of 5k
        {"agent_id": "agent_y", "spent": "3500"},  # Spent 3.5k of 5k
    ]

    print("\n" + "-" * 70)
    print("Spending in Cycle 1:")
    for spend in spending_data:
        print(f"  {spend['agent_id']}: {spend['spent']} USDC spent")

    # Auto rollover
    cycle2 = allocator.auto_rollover(
        org_id="acme_corp",
        new_total_budget=Decimal("10000"),
        currency="USDC",
        agent_configs=agents,
        spending_data=spending_data,
    )

    print("\n" + "-" * 70)
    print("\nCycle 2 - After Rollover:")
    print_cycle(cycle2)
    print(f"\nNote: Unused budget from Cycle 1 (2500 USDC) rolled over to Cycle 2")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("  SARDIS BUDGET ALLOCATION SYSTEM - DEMONSTRATION")
    print("=" * 70)

    demo_fixed_allocation()
    demo_proportional_allocation()
    demo_performance_based_allocation()
    demo_rollover_allocation()
    demo_budget_utilization()
    demo_budget_adjustment()
    demo_auto_rollover()

    print("\n" + "=" * 70)
    print("  All demonstrations completed successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
