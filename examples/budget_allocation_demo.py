"""
Budget allocation across agents — public client SDK.

Allocate a shared budget across a team of agents using Sardis agent groups, then
read back live group spending. The group enforces a shared budget envelope
(total + per-transaction + daily caps); each agent additionally carries its own
natural-language policy for its slice.

Public surface only: the `sardis` client SDK talks to a hosted Sardis
deployment. The server owns budget tracking and enforcement.

    export SARDIS_API_KEY=sk_live_...
    # optional: export SARDIS_API_URL=https://your-sardis-api.example.com
    python examples/budget_allocation_demo.py
"""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal


def print_section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def main() -> None:
    from sardis import Sardis

    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    client = Sardis(api_key=api_key)

    print_section("SARDIS BUDGET ALLOCATION — agent groups")

    # 1. Create a group with a shared budget envelope.
    group = client.groups.create(
        name="growth-team",
        budget={
            "total": "10000.00",      # whole-team monthly envelope
            "monthly": "10000.00",
            "daily": "1000.00",
            "per_transaction": "500.00",
        },
        merchant_policy={
            "blocked_categories": ["gambling"],
        },
    )
    print(f"group:  {group.group_id} ({group.name})")
    if group.budget:
        print(
            f"budget: total={group.budget.total} "
            f"monthly={group.budget.monthly} daily={group.budget.daily} "
            f"per_tx={group.budget.per_transaction}"
        )

    # 2. Allocate slices by creating agents and adding them to the group. Each
    #    agent's slice is expressed as its own natural-language policy; the group
    #    budget is the hard cap they all share.
    allocations = [
        ("marketing-agent", Decimal("4000")),
        ("sales-agent", Decimal("3000")),
        ("support-agent", Decimal("3000")),
    ]

    print("\nallocations:")
    print(f"  {'agent':<18}{'slice':<12}{'% of total':<10}")
    print("  " + "-" * 40)
    total = Decimal("10000")
    for name, slice_amount in allocations:
        agent = client.agents.create(name=name)
        client.groups.add_agent(group.group_id, agent.id)
        client.policies.apply(
            agent_id=agent.id,
            natural_language=(
                f"Spend at most ${slice_amount} per month. "
                "Block gambling."
            ),
        )
        pct = slice_amount / total * 100
        print(f"  {name:<18}{str(slice_amount):<12}{pct:.1f}%")

    # 3. Read back live group spending (server-tracked).
    print_section("Live group spending")
    spending = client.groups.get_spending(group.group_id)
    print(json.dumps(spending, indent=2, default=str))

    print_section("Done")
    print("The group budget is the shared hard cap. Per-agent natural-language")
    print("policies carve it into slices. Strategy logic (proportional, ROI-")
    print("weighted, rollover) lives in the private backend; this client just")
    print("declares budgets and reads enforcement results.")


if __name__ == "__main__":
    main()
