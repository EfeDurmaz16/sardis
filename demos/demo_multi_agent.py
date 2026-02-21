#!/usr/bin/env python3
"""
Sardis Multi-Agent Payment Demo
================================

This demo showcases multi-agent payment scenarios:
1. Split Payment - Multiple agents share a purchase
2. Group Payment - Agent group with shared budget
3. Cascade Payment - Primary agent with fallback agents

Features:
- Visual flow diagrams in terminal
- Multiple payment coordination patterns
- Agent group management
- Mock mode support

Usage:
    python demos/demo_multi_agent.py              # Mock mode
    SARDIS_API_KEY=sk_... python demos/demo_multi_agent.py  # Production mode
"""

import os
import sys
import time
from decimal import Decimal
from typing import List

# Try to import rich for beautiful output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree
    from rich import box
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install 'rich' for beautiful output: pip install rich")
    print("   Running with basic output...\n")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sardis import SardisClient


class DemoDisplay:
    """Handle display output."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None

    def header(self, title: str):
        if RICH_AVAILABLE:
            self.console.print(Panel(
                f"[bold cyan]{title}[/bold cyan]",
                box=box.DOUBLE,
                style="cyan"
            ))
        else:
            print("\n" + "=" * 60)
            print(f"  {title}")
            print("=" * 60 + "\n")

    def step(self, number: int, title: str, description: str = ""):
        if RICH_AVAILABLE:
            text = f"[bold green]Scenario {number}:[/bold green] [bold]{title}[/bold]"
            if description:
                text += f"\n[dim]{description}[/dim]"
            self.console.print(Panel(text, box=box.ROUNDED, border_style="green"))
        else:
            print(f"\n{'─' * 50}")
            print(f"Scenario {number}: {title}")
            if description:
                print(f"  {description}")
            print('─' * 50)

    def flow_diagram(self, title: str, nodes: List[tuple]):
        """Display a flow diagram."""
        if RICH_AVAILABLE:
            tree = Tree(f"[bold cyan]{title}[/bold cyan]")
            for node_text, children in nodes:
                if children:
                    branch = tree.add(node_text)
                    for child in children:
                        branch.add(child)
                else:
                    tree.add(node_text)
            self.console.print(tree)
        else:
            print(f"\n{title}:")
            for node_text, children in nodes:
                print(f"  • {node_text}")
                for child in children:
                    print(f"    → {child}")

    def agent_table(self, agents: List[dict]):
        """Display agent information table."""
        if RICH_AVAILABLE:
            table = Table(title="Agent Details", box=box.ROUNDED)
            table.add_column("Agent", style="cyan")
            table.add_column("Balance", style="green")
            table.add_column("Contribution", style="yellow")
            table.add_column("Status", style="white")

            for agent in agents:
                table.add_row(
                    agent["name"],
                    f"${agent['balance']}",
                    f"${agent.get('contribution', '-')}",
                    agent.get("status", "Active")
                )
            self.console.print(table)
        else:
            print("\nAgent Details:")
            for agent in agents:
                print(f"  {agent['name']}: ${agent['balance']} (contributing ${agent.get('contribution', 0)})")

    def success(self, message: str):
        if RICH_AVAILABLE:
            self.console.print(f"\n[bold green]✓ {message}[/bold green]")
        else:
            print(f"\n✓ {message}")

    def info(self, message: str):
        if RICH_AVAILABLE:
            self.console.print(f"  [cyan]•[/cyan] {message}")
        else:
            print(f"  • {message}")

    def simulate(self, message: str):
        if RICH_AVAILABLE:
            self.console.print(f"  [dim]{message}...[/dim]", end="")
            time.sleep(0.3)
            self.console.print(" [green]✓[/green]")
        else:
            print(f"  {message}... Done")
            time.sleep(0.2)


def scenario_split_payment(display: DemoDisplay, client: SardisClient):
    """Scenario 1: Split Payment - Multiple agents share a purchase."""
    display.step(
        1,
        "Split Payment",
        "Three agents share the cost of a data processing service"
    )

    # Create three agents
    display.info("Creating three agent wallets")

    agents = [
        {"name": "Agent-A (Data Collection)", "balance": Decimal("50.00")},
        {"name": "Agent-B (Data Processing)", "balance": Decimal("50.00")},
        {"name": "Agent-C (Data Analysis)", "balance": Decimal("50.00")},
    ]

    display.agent_table(agents)

    # Show flow
    display.flow_diagram(
        "Split Payment Flow",
        [
            ("[bold]Purchase:[/bold] $75 Data API Subscription", []),
            ("[bold]Split Strategy:[/bold] Equal 3-way split", [
                "Agent-A pays $25.00",
                "Agent-B pays $25.00",
                "Agent-C pays $25.00"
            ]),
            ("[bold]Merchant:[/bold] data-api.example.com", []),
        ]
    )

    # Execute split payment
    display.info("Coordinating multi-agent payment")

    total_amount = Decimal("75.00")
    split_amount = total_amount / 3

    display.simulate("Agent-A authorizing $25.00")
    display.simulate("Agent-B authorizing $25.00")
    display.simulate("Agent-C authorizing $25.00")
    display.simulate("Creating combined mandate chain")
    display.simulate("Executing atomic payment")

    display.success("Split payment completed successfully!")

    # Update balances
    for agent in agents:
        agent["contribution"] = split_amount
        agent["balance"] -= split_amount
        agent["status"] = "✓ Paid"

    display.agent_table(agents)

    if RICH_AVAILABLE:
        display.console.print(Panel(
            "[bold]Benefits:[/bold]\n"
            "✓ Atomic execution - all or nothing\n"
            "✓ Fair cost distribution\n"
            "✓ Individual spending limits respected\n"
            "✓ Separate audit trails per agent",
            title="Split Payment Advantages",
            border_style="blue"
        ))


def scenario_group_payment(display: DemoDisplay, client: SardisClient):
    """Scenario 2: Group Payment - Agent group with shared budget."""
    display.step(
        2,
        "Group Payment",
        "A team of agents shares a common budget pool"
    )

    display.info("Creating agent group with shared treasury")

    # Create group
    group_budget = Decimal("500.00")

    if RICH_AVAILABLE:
        display.console.print(f"\n[bold]Group:[/bold] Marketing Team")
        display.console.print(f"[bold]Shared Budget:[/bold] [green]${group_budget}[/green]")
        display.console.print(f"[bold]Daily Limit:[/bold] $200")
        display.console.print(f"[bold]Members:[/bold] 4 agents\n")
    else:
        print("\nGroup: Marketing Team")
        print(f"Shared Budget: ${group_budget}")
        print("Daily Limit: $200")
        print("Members: 4 agents\n")

    # Show group structure
    display.flow_diagram(
        "Group Payment Architecture",
        [
            ("[bold]Group Treasury[/bold] - $500 USDC", [
                "Social Media Agent - Posts/Ads",
                "Content Agent - Image Generation",
                "Analytics Agent - Metrics API",
                "Email Agent - Newsletter Service"
            ]),
            ("[bold]Governance:[/bold] Any member can spend", []),
            ("[bold]Policy:[/bold] $50 per transaction, $200 daily total", []),
        ]
    )

    # Simulate group transactions
    transactions = [
        {"agent": "Social Media Agent", "merchant": "twitter-ads.com", "amount": Decimal("45.00"), "purpose": "Ad campaign"},
        {"agent": "Content Agent", "merchant": "openai.com", "amount": Decimal("30.00"), "purpose": "DALL-E images"},
        {"agent": "Analytics Agent", "merchant": "analytics-api.com", "amount": Decimal("25.00"), "purpose": "Usage metrics"},
        {"agent": "Email Agent", "merchant": "sendgrid.com", "amount": Decimal("40.00"), "purpose": "Newsletter"},
    ]

    if RICH_AVAILABLE:
        display.console.print("\n[bold]Group Activity:[/bold]\n")
    else:
        print("\nGroup Activity:\n")

    total_spent = Decimal("0")
    for tx in transactions:
        display.simulate(f"{tx['agent']}: ${tx['amount']} to {tx['merchant']}")
        total_spent += tx["amount"]
        time.sleep(0.2)

    remaining = group_budget - total_spent

    # Summary table
    if RICH_AVAILABLE:
        summary = Table(title="Group Budget Summary", box=box.ROUNDED)
        summary.add_column("Metric", style="bold")
        summary.add_column("Value", style="white")
        summary.add_row("Initial Budget", f"${group_budget}")
        summary.add_row("Total Spent", f"[red]${total_spent}[/red]")
        summary.add_row("Remaining", f"[green]${remaining}[/green]")
        summary.add_row("Transactions", str(len(transactions)))
        summary.add_row("Daily Limit Used", f"{(total_spent/200*100):.0f}%")
        display.console.print(summary)
    else:
        print(f"\nGroup Budget Summary:")
        print(f"  Initial Budget: ${group_budget}")
        print(f"  Total Spent: ${total_spent}")
        print(f"  Remaining: ${remaining}")
        print(f"  Transactions: {len(transactions)}")

    if RICH_AVAILABLE:
        display.console.print(Panel(
            "[bold]Benefits:[/bold]\n"
            "✓ Shared treasury management\n"
            "✓ Group spending policies\n"
            "✓ Per-member transaction limits\n"
            "✓ Unified audit trail\n"
            "✓ Easy budget tracking",
            title="Group Payment Advantages",
            border_style="blue"
        ))


def scenario_cascade_payment(display: DemoDisplay, client: SardisClient):
    """Scenario 3: Cascade Payment - Primary agent with fallback agents."""
    display.step(
        3,
        "Cascade Payment",
        "Automatic failover to backup agents if primary agent cannot pay"
    )

    display.info("Setting up cascade payment with 3-tier fallback")

    # Agent hierarchy
    agents = [
        {"name": "Primary Agent", "balance": Decimal("15.00"), "priority": 1, "status": "Standby"},
        {"name": "Secondary Agent", "balance": Decimal("100.00"), "priority": 2, "status": "Standby"},
        {"name": "Tertiary Agent", "balance": Decimal("200.00"), "priority": 3, "status": "Standby"},
    ]

    display.agent_table(agents)

    # Show cascade flow
    display.flow_diagram(
        "Cascade Payment Decision Tree",
        [
            ("[bold]Payment Required:[/bold] $50 to claude.ai", []),
            ("Priority 1: Primary Agent ($15)", [
                "[red]✗ Insufficient balance[/red]",
                "→ Cascade to Priority 2"
            ]),
            ("Priority 2: Secondary Agent ($100)", [
                "[green]✓ Sufficient balance[/green]",
                "→ Execute payment"
            ]),
            ("Priority 3: Tertiary Agent ($200)", [
                "[dim]Not needed - backup only[/dim]"
            ]),
        ]
    )

    # Execute cascade
    payment_amount = Decimal("50.00")
    merchant = "claude.ai"

    if RICH_AVAILABLE:
        display.console.print("\n[bold]Executing Cascade Payment:[/bold]\n")
    else:
        print("\nExecuting Cascade Payment:\n")

    # Try primary
    display.info(f"Trying Primary Agent (balance: ${agents[0]['balance']})")
    time.sleep(0.3)
    agents[0]["status"] = "✗ Insufficient"
    if RICH_AVAILABLE:
        display.console.print("  [red]✗ Failed: Balance too low[/red]")
    else:
        print("  ✗ Failed: Balance too low")

    # Try secondary
    display.info(f"Trying Secondary Agent (balance: ${agents[1]['balance']})")
    time.sleep(0.3)
    agents[1]["status"] = "✓ Success"
    if RICH_AVAILABLE:
        display.console.print("  [green]✓ Success: Payment executed[/green]")
    else:
        print("  ✓ Success: Payment executed")

    agents[1]["balance"] -= payment_amount
    agents[1]["contribution"] = payment_amount

    display.success(f"Cascade payment completed via Secondary Agent!")

    # Final state
    display.agent_table(agents)

    if RICH_AVAILABLE:
        display.console.print(Panel(
            "[bold]Benefits:[/bold]\n"
            "✓ Automatic failover - no downtime\n"
            "✓ Priority-based routing\n"
            "✓ High availability for critical agents\n"
            "✓ Cost optimization (use cheaper source first)\n"
            "✓ Emergency backup funding",
            title="Cascade Payment Advantages",
            border_style="blue"
        ))

    # Use case examples
    if RICH_AVAILABLE:
        display.console.print("\n[bold]Real-World Use Cases:[/bold]")
        display.console.print("  • Production agent → Development budget fallback")
        display.console.print("  • Department budget → Company treasury fallback")
        display.console.print("  • Agent wallet → Human wallet fallback")
        display.console.print("  • Primary chain → L2 chain fallback (gas optimization)")


def main():
    """Run the multi-agent payment demo."""
    display = DemoDisplay()

    display.header("Sardis Multi-Agent Payment Patterns")

    if RICH_AVAILABLE:
        intro = """
This demo showcases three advanced multi-agent payment patterns:

1. **Split Payment** - Multiple agents share purchase costs
2. **Group Payment** - Agent teams with shared budgets
3. **Cascade Payment** - Automatic failover between agents

All patterns maintain:
- Individual policy enforcement
- Atomic transaction execution
- Complete audit trails
- Secure mandate verification
        """
        display.console.print(Panel(intro.strip(), title="Overview", border_style="cyan"))

    # Initialize client
    api_key = os.getenv('SARDIS_API_KEY', 'mock_key')
    client = SardisClient(api_key=api_key)

    # Run scenarios
    scenario_split_payment(display, client)
    print("\n")

    scenario_group_payment(display, client)
    print("\n")

    scenario_cascade_payment(display, client)

    # Summary
    display.header("Demo Complete!")

    if RICH_AVAILABLE:
        summary = """
## Multi-Agent Payment Patterns

### 1. Split Payment
**Use Case:** Shared resource costs
- Equal or custom split ratios
- Atomic all-or-nothing execution
- Individual spending limit enforcement

### 2. Group Payment
**Use Case:** Team budgets
- Shared treasury pool
- Group spending policies
- Per-member transaction limits
- Unified audit trail

### 3. Cascade Payment
**Use Case:** High availability & cost optimization
- Priority-based routing
- Automatic failover
- Zero downtime for critical agents
- Multi-tier backup funding

## Implementation

```python
from sardis import SardisClient

client = SardisClient(api_key="sk_...")

# Split payment
group = client.groups.create(name="data-team")
group.add_agents(["agent-a", "agent-b", "agent-c"])
tx = group.split_pay(to="api.com", amount="75", strategy="equal")

# Group payment
treasury = client.groups.create(
    name="marketing",
    shared_budget=500,
    policy="$50/tx, $200/day"
)
tx = treasury.pay(to="twitter-ads.com", amount="45")

# Cascade payment
cascade = client.cascades.create(
    agents=["primary", "secondary", "tertiary"]
)
tx = cascade.pay(to="claude.ai", amount="50")  # Auto-routes to first available
```

## Next Steps

• Try `demo_escrow.py` for agent-to-agent escrow flows
• Read multi-agent docs: https://sardis.sh/docs/multi-agent
• Join Discord: https://discord.gg/sardis
        """
        display.console.print(Markdown(summary))
    else:
        print("\nMulti-Agent Payment Patterns Summary:")
        print("  1. Split Payment - Shared costs")
        print("  2. Group Payment - Team budgets")
        print("  3. Cascade Payment - High availability")
        print("\nDocs: https://sardis.sh/docs/multi-agent")

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
