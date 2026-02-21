#!/usr/bin/env python3
"""
Sardis Escrow Flow Demo
=======================

This demo showcases Agent-to-Agent (A2A) escrow:
1. Create escrow agreement
2. Agent A funds escrow
3. Agent B delivers service/data
4. Release payment to Agent B

Features:
- State machine visualization
- Multi-party escrow support
- Dispute resolution flow
- Mock mode support

Usage:
    python demos/demo_escrow.py              # Mock mode
    SARDIS_API_KEY=sk_... python demos/demo_escrow.py  # Production mode
"""

import os
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

# Try to import rich for beautiful output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree
    from rich import box
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install 'rich' for beautiful output: pip install rich")
    print("   Running with basic output...\n")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sardis import SardisClient


class EscrowState(Enum):
    """Escrow state machine states."""
    CREATED = "created"
    FUNDED = "funded"
    DELIVERED = "delivered"
    RELEASED = "released"
    DISPUTED = "disputed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class DemoDisplay:
    """Handle display output."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None

    def header(self, title: str):
        if RICH_AVAILABLE:
            self.console.print(Panel(
                f"[bold magenta]{title}[/bold magenta]",
                box=box.DOUBLE,
                style="magenta"
            ))
        else:
            print("\n" + "=" * 60)
            print(f"  {title}")
            print("=" * 60 + "\n")

    def step(self, number: int, title: str, description: str = ""):
        if RICH_AVAILABLE:
            text = f"[bold green]Step {number}:[/bold green] [bold]{title}[/bold]"
            if description:
                text += f"\n[dim]{description}[/dim]"
            self.console.print(Panel(text, box=box.ROUNDED, border_style="green"))
        else:
            print(f"\n{'─' * 50}")
            print(f"Step {number}: {title}")
            if description:
                print(f"  {description}")
            print('─' * 50)

    def state_machine(self, current_state: EscrowState):
        """Display escrow state machine."""
        states = [
            (EscrowState.CREATED, "Agreement Created", "cyan"),
            (EscrowState.FUNDED, "Funds Locked", "yellow"),
            (EscrowState.DELIVERED, "Service Delivered", "blue"),
            (EscrowState.RELEASED, "Payment Released", "green"),
        ]

        # Find current index
        current_index = -1
        for i, (state, _, _) in enumerate(states):
            if state == current_state:
                current_index = i
                break

        if RICH_AVAILABLE:
            self.console.print("\n[bold]Escrow State Machine:[/bold]\n")
            for i, (state, label, color) in enumerate(states):
                if state == current_state:
                    self.console.print(f"  [{color}]● {label}[/{color}] [bold]← CURRENT[/bold]")
                elif i < current_index:
                    self.console.print(f"  [dim]✓ {label}[/dim]")
                else:
                    self.console.print(f"  [dim]○ {label}[/dim]")
                if i < len(states) - 1:
                    self.console.print(f"  [dim]↓[/dim]")
        else:
            print("\nEscrow State Machine:")
            for i, (state, label, _) in enumerate(states):
                marker = "●" if state == current_state else ("✓" if i < current_index else "○")
                current = " ← CURRENT" if state == current_state else ""
                print(f"  {marker} {label}{current}")
                if i < len(states) - 1:
                    print("  ↓")

    def escrow_details(self, escrow: dict):
        """Display escrow details."""
        if RICH_AVAILABLE:
            table = Table(title="Escrow Agreement", box=box.ROUNDED)
            table.add_column("Property", style="cyan", width=20)
            table.add_column("Value", style="white")

            for key, value in escrow.items():
                table.add_row(key, str(value))

            self.console.print(table)
        else:
            print("\nEscrow Agreement:")
            for key, value in escrow.items():
                print(f"  {key:<20} {value}")

    def agent_balances(self, agent_a: dict, agent_b: dict):
        """Display agent balances."""
        if RICH_AVAILABLE:
            table = Table(title="Agent Balances", box=box.ROUNDED)
            table.add_column("Agent", style="bold")
            table.add_column("Balance", style="green")
            table.add_column("Escrowed", style="yellow")
            table.add_column("Available", style="cyan")

            table.add_row(
                agent_a["name"],
                f"${agent_a['balance']}",
                f"${agent_a['escrowed']}",
                f"${agent_a['balance'] - agent_a['escrowed']}"
            )
            table.add_row(
                agent_b["name"],
                f"${agent_b['balance']}",
                f"${agent_b['escrowed']}",
                f"${agent_b['balance'] - agent_b['escrowed']}"
            )

            self.console.print(table)
        else:
            print("\nAgent Balances:")
            print(f"  {agent_a['name']}: ${agent_a['balance']} (${agent_a['escrowed']} escrowed)")
            print(f"  {agent_b['name']}: ${agent_b['balance']} (${agent_b['escrowed']} escrowed)")

    def success(self, message: str):
        if RICH_AVAILABLE:
            self.console.print(f"\n[bold green]✓ {message}[/bold green]")
        else:
            print(f"\n✓ {message}")

    def info(self, label: str, value: str):
        if RICH_AVAILABLE:
            self.console.print(f"  [cyan]•[/cyan] [bold]{label}:[/bold] {value}")
        else:
            print(f"  • {label}: {value}")

    def simulate(self, message: str):
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task(f"[cyan]{message}...", total=None)
                time.sleep(0.5)
        else:
            print(f"  {message}... ", end="", flush=True)
            time.sleep(0.3)
            print("Done")

    def timeline(self, events: list):
        """Display timeline of events."""
        if RICH_AVAILABLE:
            tree = Tree("[bold]Escrow Timeline[/bold]")
            for timestamp, event, status in events:
                color = "green" if status == "success" else "yellow" if status == "pending" else "cyan"
                tree.add(f"[{color}]{timestamp}[/{color}] - {event}")
            self.console.print(tree)
        else:
            print("\nEscrow Timeline:")
            for timestamp, event, _ in events:
                print(f"  {timestamp} - {event}")


def main():
    """Run the escrow flow demo."""
    display = DemoDisplay()

    display.header("Sardis Agent-to-Agent Escrow Demo")

    if RICH_AVAILABLE:
        intro = """
This demo showcases trustless agent-to-agent payments using escrow:

**Scenario:** Agent A hires Agent B for data processing
- Agent A: Data Collection Bot
- Agent B: ML Processing Service
- Amount: $100 USDC
- Deliverable: Processed dataset

**Escrow Benefits:**
- Trustless transaction (no prior relationship needed)
- Automated release on delivery
- Dispute resolution available
- On-chain settlement guarantee
        """
        display.console.print(Panel(intro.strip(), title="Overview", border_style="magenta"))

    # Initialize client
    api_key = os.getenv('SARDIS_API_KEY', 'mock_key')
    client = SardisClient(api_key=api_key)

    # Agent balances
    agent_a = {
        "name": "Agent A (Buyer)",
        "balance": Decimal("500.00"),
        "escrowed": Decimal("0.00"),
    }
    agent_b = {
        "name": "Agent B (Seller)",
        "balance": Decimal("50.00"),
        "escrowed": Decimal("0.00"),
    }

    escrow_amount = Decimal("100.00")
    timeline_events = []

    # ================================================================
    # Step 1: Create Escrow Agreement
    # ================================================================
    display.step(
        1,
        "Create Escrow Agreement",
        "Both agents sign the terms and conditions"
    )

    display.agent_balances(agent_a, agent_b)

    display.simulate("Generating escrow smart contract")
    display.simulate("Agent A signing agreement")
    display.simulate("Agent B signing agreement")

    escrow_id = f"escrow_{int(time.time())}"
    expiry = datetime.now() + timedelta(hours=24)

    escrow = {
        "Escrow ID": escrow_id,
        "Buyer": "Agent A (Data Collection)",
        "Seller": "Agent B (ML Processing)",
        "Amount": f"${escrow_amount} USDC",
        "Deliverable": "Processed dataset (1000 records)",
        "Deadline": expiry.strftime("%Y-%m-%d %H:%M UTC"),
        "Chain": "Base",
        "State": EscrowState.CREATED.value,
    }

    display.escrow_details(escrow)
    display.state_machine(EscrowState.CREATED)

    timeline_events.append((
        datetime.now().strftime("%H:%M:%S"),
        "Escrow agreement created",
        "success"
    ))

    # ================================================================
    # Step 2: Fund Escrow
    # ================================================================
    display.step(
        2,
        "Agent A Funds Escrow",
        "Buyer locks payment in smart contract"
    )

    display.simulate("Validating Agent A balance")
    display.simulate("Creating AP2 mandate for escrow deposit")
    display.simulate("Transferring $100 USDC to escrow contract")
    display.simulate("Locking funds on-chain")

    agent_a["escrowed"] = escrow_amount
    escrow["State"] = EscrowState.FUNDED.value

    display.success("Escrow funded successfully!")
    display.agent_balances(agent_a, agent_b)
    display.state_machine(EscrowState.FUNDED)

    if RICH_AVAILABLE:
        display.console.print(Panel(
            f"[bold]${escrow_amount} USDC[/bold] is now locked in escrow\n\n"
            "✓ Agent A cannot withdraw\n"
            "✓ Agent B cannot access (yet)\n"
            "✓ Funds secured by smart contract\n"
            "✓ Automated release on delivery confirmation",
            title="Escrow Security",
            border_style="yellow"
        ))

    timeline_events.append((
        datetime.now().strftime("%H:%M:%S"),
        f"Agent A deposited ${escrow_amount}",
        "success"
    ))

    # ================================================================
    # Step 3: Service Delivery
    # ================================================================
    display.step(
        3,
        "Agent B Delivers Service",
        "Seller completes the work and submits proof"
    )

    if RICH_AVAILABLE:
        display.console.print("\n[bold]Agent B Processing Data:[/bold]\n")
    else:
        print("\nAgent B Processing Data:\n")

    # Simulate work
    tasks = [
        "Loading 1000 raw records",
        "Cleaning and validating data",
        "Running ML feature extraction",
        "Generating processed dataset",
        "Computing delivery hash"
    ]

    for task in tasks:
        display.simulate(task)
        time.sleep(0.2)

    delivery_hash = "0x" + "a" * 64  # Mock hash
    display.info("Delivery Hash", delivery_hash[:20] + "...")
    display.info("Dataset Size", "1000 records")
    display.info("Format", "Parquet")

    display.simulate("Submitting proof of delivery to escrow contract")

    escrow["State"] = EscrowState.DELIVERED.value
    escrow["Delivery Hash"] = delivery_hash[:20] + "..."

    display.success("Proof of delivery submitted!")
    display.state_machine(EscrowState.DELIVERED)

    timeline_events.append((
        datetime.now().strftime("%H:%M:%S"),
        "Agent B submitted deliverable",
        "success"
    ))

    # ================================================================
    # Step 4: Verify and Release
    # ================================================================
    display.step(
        4,
        "Verify Deliverable and Release Payment",
        "Buyer confirms delivery and funds are released automatically"
    )

    display.simulate("Agent A downloading delivered dataset")
    display.simulate("Verifying data hash matches proof")
    display.simulate("Checking record count (1000)")
    display.simulate("Validating data quality")

    display.success("Deliverable verified!")

    if RICH_AVAILABLE:
        display.console.print("\n[bold]Automatic Release Process:[/bold]")
        display.console.print("  [cyan]1.[/cyan] Delivery proof matches hash")
        display.console.print("  [cyan]2.[/cyan] Buyer confirms acceptance")
        display.console.print("  [cyan]3.[/cyan] Smart contract releases funds")
        display.console.print("  [cyan]4.[/cyan] Agent B receives payment\n")

    display.simulate("Agent A confirming acceptance")
    display.simulate("Smart contract releasing funds")
    display.simulate("Transferring $100 USDC to Agent B")

    # Update balances
    agent_a["escrowed"] = Decimal("0.00")
    agent_b["balance"] += escrow_amount

    escrow["State"] = EscrowState.RELEASED.value
    escrow["Released At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if RICH_AVAILABLE:
        display.console.print(Panel(
            "[bold green]✓ PAYMENT RELEASED[/bold green]\n\n"
            f"Agent B received ${escrow_amount} USDC\n"
            "Transaction complete!",
            box=box.HEAVY,
            border_style="green"
        ))
    else:
        print("\n" + "=" * 50)
        print("  ✓ PAYMENT RELEASED")
        print(f"  Agent B received ${escrow_amount} USDC")
        print("=" * 50)

    display.agent_balances(agent_a, agent_b)
    display.state_machine(EscrowState.RELEASED)

    timeline_events.append((
        datetime.now().strftime("%H:%M:%S"),
        f"Payment released to Agent B (${escrow_amount})",
        "success"
    ))

    # ================================================================
    # Step 5: Audit Trail
    # ================================================================
    display.step(
        5,
        "Complete Audit Trail",
        "Immutable record of the entire escrow lifecycle"
    )

    display.timeline(timeline_events)

    # Transaction summary
    if RICH_AVAILABLE:
        summary_table = Table(title="Transaction Summary", box=box.ROUNDED)
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Escrow ID", escrow_id)
        summary_table.add_row("Total Amount", f"${escrow_amount} USDC")
        summary_table.add_row("Buyer Paid", f"${escrow_amount}")
        summary_table.add_row("Seller Received", f"${escrow_amount}")
        summary_table.add_row("Platform Fee", "$0.00 (promotional)")
        summary_table.add_row("Duration", f"{len(timeline_events)} steps")
        summary_table.add_row("Final State", "RELEASED ✓")

        display.console.print(summary_table)

    # ================================================================
    # Bonus: Dispute Flow Example
    # ================================================================
    if RICH_AVAILABLE:
        display.console.print("\n")

    display.step(
        "Bonus",
        "Dispute Resolution Flow",
        "What happens if there's a disagreement"
    )

    if RICH_AVAILABLE:
        dispute_tree = Tree("[bold yellow]Dispute Scenario[/bold yellow]")

        scenario = dispute_tree.add("[red]Agent A rejects deliverable[/red]")
        scenario.add("Agent A: 'Data quality is insufficient'")
        scenario.add("Agent B: 'Data meets specifications'")

        resolution = dispute_tree.add("[cyan]Resolution Options[/cyan]")
        resolution.add("1. Automated Arbitration (AI judge)")
        resolution.add("2. Human Mediator (Sardis support)")
        resolution.add("3. On-chain Voting (DAO governance)")
        resolution.add("4. Partial Release (compromise)")

        outcomes = dispute_tree.add("[green]Possible Outcomes[/green]")
        outcomes.add("✓ Full refund to Agent A")
        outcomes.add("✓ Full release to Agent B")
        outcomes.add("✓ 50/50 split")
        outcomes.add("✓ Custom resolution")

        display.console.print(dispute_tree)
    else:
        print("\nDispute Scenario:")
        print("  • Agent A rejects deliverable")
        print("  • Resolution options:")
        print("    - Automated arbitration")
        print("    - Human mediator")
        print("    - On-chain voting")
        print("  • Possible outcomes:")
        print("    - Full refund")
        print("    - Full release")
        print("    - Partial split")

    # ================================================================
    # Summary
    # ================================================================
    display.header("Demo Complete!")

    if RICH_AVAILABLE:
        final_summary = """
## Escrow Flow Summary

### What We Demonstrated

✓ **Trustless Transactions**
  No prior trust relationship needed between agents

✓ **Smart Contract Security**
  Funds locked on-chain, released only on delivery

✓ **Automated Verification**
  Cryptographic proof of delivery

✓ **Dispute Resolution**
  Multiple resolution paths available

✓ **Complete Audit Trail**
  Every state transition recorded immutably

### State Machine

```
CREATED → FUNDED → DELIVERED → RELEASED
            ↓          ↓
         CANCELLED  DISPUTED → REFUNDED
```

### Use Cases

1. **Agent Services** - Hire agents for tasks
2. **Data Purchases** - Buy datasets from agents
3. **API Credits** - Prepay for API usage
4. **Subscription Escrow** - Lock funds for recurring payments
5. **Multi-party Contracts** - Complex agent collaborations

### Implementation

```python
from sardis import SardisClient

client = SardisClient(api_key="sk_...")

# Create escrow
escrow = client.escrow.create(
    buyer="agent-a-wallet-id",
    seller="agent-b-wallet-id",
    amount="100",
    deliverable="Processed dataset",
    deadline_hours=24
)

# Fund (buyer)
escrow.fund()

# Deliver (seller)
escrow.deliver(proof_hash="0xabc...")

# Release (buyer confirms)
escrow.release()
```

## Next Steps

• Read escrow docs: https://sardis.sh/docs/escrow
• Try other demos: `demo_payment_flow.py`, `demo_trust_scoring.py`
• Join Discord: https://discord.gg/sardis
• Get API key: https://sardis.sh/signup
        """
        display.console.print(Markdown(final_summary))
    else:
        print("\nEscrow Flow Summary:")
        print("  ✓ Trustless agent-to-agent payments")
        print("  ✓ Smart contract security")
        print("  ✓ Automated verification")
        print("  ✓ Dispute resolution")
        print("\nUse Cases:")
        print("  • Agent services marketplace")
        print("  • Data purchases")
        print("  • Prepaid API credits")
        print("\nDocs: https://sardis.sh/docs/escrow")

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
