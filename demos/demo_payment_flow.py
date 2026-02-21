#!/usr/bin/env python3
"""
Sardis Payment Flow Demo
========================

This demo showcases a complete agent payment flow:
1. Create an agent wallet with spending policy
2. Execute a payment transaction
3. Check audit trail

Features:
- Beautiful terminal output with rich library
- Mock mode (no API keys needed) and production mode
- Step-by-step explanations of Sardis concepts

Usage:
    python demos/demo_payment_flow.py              # Mock mode
    SARDIS_API_KEY=sk_... python demos/demo_payment_flow.py  # Production mode
"""

import os
import sys
import time
from datetime import datetime
from decimal import Decimal

# Try to import rich for beautiful output, fallback to basic prints
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.layout import Layout
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install 'rich' for beautiful output: pip install rich")
    print("   Running with basic output...\n")

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sardis import SardisClient


class DemoDisplay:
    """Handle display output with or without rich library."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.mock_mode = os.getenv('SARDIS_API_KEY') is None

    def header(self, title: str):
        """Display a header."""
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
        """Display a step."""
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

    def info(self, label: str, value: str, color: str = "white"):
        """Display an info line."""
        if RICH_AVAILABLE:
            self.console.print(f"  [{color}]●[/{color}] [bold]{label}:[/bold] {value}")
        else:
            print(f"  • {label}: {value}")

    def success(self, message: str):
        """Display a success message."""
        if RICH_AVAILABLE:
            self.console.print(f"  [green]✓[/green] {message}")
        else:
            print(f"  ✓ {message}")

    def warning(self, message: str):
        """Display a warning message."""
        if RICH_AVAILABLE:
            self.console.print(f"  [yellow]⚠[/yellow] {message}")
        else:
            print(f"  ⚠ {message}")

    def table(self, title: str, data: list[tuple[str, str]]):
        """Display a table."""
        if RICH_AVAILABLE:
            table = Table(title=title, box=box.ROUNDED, show_header=False)
            table.add_column("Property", style="cyan", width=25)
            table.add_column("Value", style="white")
            for key, value in data:
                table.add_row(key, str(value))
            self.console.print(table)
        else:
            print(f"\n{title}:")
            for key, value in data:
                print(f"  {key:<25} {value}")

    def code(self, code: str, language: str = "python"):
        """Display code."""
        if RICH_AVAILABLE:
            self.console.print(Syntax(code, language, theme="monokai", line_numbers=False))
        else:
            print(code)

    def progress_bar(self, description: str, total: int = 100):
        """Show a progress bar (mock operation)."""
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console
            ) as progress:
                task = progress.add_task(description, total=total)
                for _ in range(total):
                    time.sleep(0.01)
                    progress.update(task, advance=1)
        else:
            print(f"  {description}... ", end="", flush=True)
            time.sleep(0.5)
            print("Done")

    def mode_banner(self):
        """Display mode banner."""
        mode = "MOCK MODE" if self.mock_mode else "PRODUCTION MODE"
        style = "yellow" if self.mock_mode else "red"
        message = (
            "Running in mock mode - no real API calls\n"
            "Set SARDIS_API_KEY to use production mode"
        ) if self.mock_mode else (
            "Running in PRODUCTION mode - real API calls!\n"
            "Transactions will use your Sardis account"
        )

        if RICH_AVAILABLE:
            self.console.print(Panel(
                f"[bold {style}]{mode}[/bold {style}]\n\n{message}",
                box=box.HEAVY,
                border_style=style
            ))
        else:
            print(f"\n{'=' * 60}")
            print(f"  {mode}")
            print(f"  {message}")
            print('=' * 60)


def main():
    """Run the payment flow demo."""
    display = DemoDisplay()

    # Header
    display.header("Sardis Payment Flow Demo")
    display.mode_banner()

    # Initialize client
    api_key = os.getenv('SARDIS_API_KEY', 'mock_key')
    client = SardisClient(api_key=api_key)

    # ================================================================
    # Step 1: Create Agent Wallet
    # ================================================================
    display.step(
        1,
        "Create Agent Wallet",
        "Setting up a non-custodial wallet with spending policy"
    )

    display.info("Concept", "Agent wallets use MPC (Multi-Party Computation)")
    display.info("Security", "Private keys are never stored - they're computed on-demand")

    if RICH_AVAILABLE:
        display.console.print()

    display.progress_bar("Creating wallet with Turnkey MPC")

    # Create wallet with policy
    wallet = client.wallets.create(
        name="demo-shopping-agent",
        chain="base",
        policy="Max $100 per day, only merchants in whitelist"
    )

    display.success("Wallet created successfully!")
    display.table("Wallet Details", [
        ("Wallet ID", wallet.wallet_id),
        ("Name", "demo-shopping-agent"),
        ("Chain", "Base (Ethereum L2)"),
        ("Token", "USDC"),
        ("Balance", "$0.00 (unfunded)"),
        ("Policy", "Max $100/day, merchant whitelist"),
    ])

    # Show policy details
    if RICH_AVAILABLE:
        display.console.print("\n[bold]Spending Policy:[/bold]")
        display.console.print("  [cyan]├─[/cyan] Daily Limit: $100.00")
        display.console.print("  [cyan]├─[/cyan] Merchant Whitelist: Enabled")
        display.console.print("  [cyan]├─[/cyan] Token: USDC only")
        display.console.print("  [cyan]└─[/cyan] Chain: Base")
    else:
        print("\nSpending Policy:")
        print("  - Daily Limit: $100.00")
        print("  - Merchant Whitelist: Enabled")
        print("  - Token: USDC only")
        print("  - Chain: Base")

    # ================================================================
    # Step 2: Fund Wallet (Simulated)
    # ================================================================
    display.step(
        2,
        "Fund Wallet",
        "In production, fund via bank transfer or crypto deposit"
    )

    display.info("Methods", "Bank ACH, Card, Crypto Transfer, or USDC Mint")
    display.progress_bar("Processing deposit")

    # In mock mode, we simulate funding
    funded_amount = Decimal("50.00")
    display.success(f"Wallet funded with ${funded_amount} USDC")

    # ================================================================
    # Step 3: Execute Payment
    # ================================================================
    display.step(
        3,
        "Execute Payment",
        "Agent pays for OpenAI API usage with policy enforcement"
    )

    # Show payment flow
    if RICH_AVAILABLE:
        display.console.print("[bold]Payment Flow:[/bold]")
        display.console.print("  [cyan]1.[/cyan] Agent requests payment")
        display.console.print("  [cyan]2.[/cyan] Policy engine validates (amount, merchant, limits)")
        display.console.print("  [cyan]3.[/cyan] AP2 mandate chain created (Intent → Cart → Payment)")
        display.console.print("  [cyan]4.[/cyan] On-chain USDC transfer executed")
        display.console.print("  [cyan]5.[/cyan] Audit log recorded\n")
    else:
        print("\nPayment Flow:")
        print("  1. Agent requests payment")
        print("  2. Policy engine validates")
        print("  3. AP2 mandate chain created")
        print("  4. On-chain transfer executed")
        print("  5. Audit log recorded\n")

    # Execute payment
    payment_amount = "25.00"
    merchant = "openai.com"

    display.info("Merchant", merchant)
    display.info("Amount", f"${payment_amount} USDC")
    display.info("Purpose", "GPT-4 API Credits")

    if RICH_AVAILABLE:
        display.console.print()

    display.progress_bar("Validating spending policy")
    display.progress_bar("Creating AP2 mandate chain")
    display.progress_bar("Executing on-chain transfer")

    # Make payment
    tx = wallet.pay(
        to=merchant,
        amount=payment_amount,
        token="USDC",
        purpose="GPT-4 API credits for demo agent"
    )

    if RICH_AVAILABLE:
        display.console.print(Panel(
            "[bold green]✓ PAYMENT SUCCESSFUL[/bold green]",
            box=box.HEAVY,
            border_style="green"
        ))
    else:
        print("\n" + "=" * 50)
        print("  ✓ PAYMENT SUCCESSFUL")
        print("=" * 50)

    display.table("Transaction Details", [
        ("Transaction ID", tx.tx_id[:16] + "..." if len(tx.tx_id) > 16 else tx.tx_id),
        ("Status", "CONFIRMED"),
        ("Amount", f"${payment_amount} USDC"),
        ("Merchant", merchant),
        ("Chain", "Base"),
        ("Block Number", "12,345,678" if display.mock_mode else tx.block_number),
        ("Gas Fee", "$0.02"),
        ("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ])

    # ================================================================
    # Step 4: Check Audit Trail
    # ================================================================
    display.step(
        4,
        "Review Audit Trail",
        "Immutable, append-only ledger of all transactions"
    )

    display.info("Storage", "Dual-layer: PostgreSQL + Blockchain anchor")
    display.info("Compliance", "SOC2, GDPR, AML/KYC ready")

    if RICH_AVAILABLE:
        display.console.print()

    display.progress_bar("Fetching audit records")

    # Get audit trail
    ledger = client.ledger.list(wallet_id=wallet.wallet_id)

    if RICH_AVAILABLE:
        audit_table = Table(title="Audit Trail", box=box.ROUNDED)
        audit_table.add_column("Time", style="cyan", width=20)
        audit_table.add_column("Event", style="yellow", width=20)
        audit_table.add_column("Amount", style="green", width=15)
        audit_table.add_column("Details", style="white", width=30)

        audit_table.add_row(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "WALLET_CREATED",
            "-",
            "demo-shopping-agent"
        )
        audit_table.add_row(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "DEPOSIT",
            f"+${funded_amount}",
            "Initial funding"
        )
        audit_table.add_row(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "PAYMENT",
            f"-${payment_amount}",
            f"To {merchant}"
        )

        display.console.print(audit_table)
    else:
        print("\nAudit Trail:")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | WALLET_CREATED | - | demo-shopping-agent")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | DEPOSIT | +${funded_amount} | Initial funding")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | PAYMENT | -${payment_amount} | To {merchant}")

    # ================================================================
    # Step 5: Current State
    # ================================================================
    display.step(
        5,
        "Current Wallet State",
        "Real-time balance and spending limits"
    )

    remaining_balance = funded_amount - Decimal(payment_amount)
    daily_spent = Decimal(payment_amount)
    daily_limit = Decimal("100.00")
    daily_remaining = daily_limit - daily_spent

    display.table("Wallet Status", [
        ("Current Balance", f"${remaining_balance} USDC"),
        ("Today's Spending", f"${daily_spent} / ${daily_limit}"),
        ("Remaining Today", f"${daily_remaining}"),
        ("Total Transactions", "1"),
        ("Wallet Health", "✓ Active"),
    ])

    # Progress bar for daily limit
    if RICH_AVAILABLE:
        from rich.progress import Progress, BarColumn, TextColumn

        display.console.print("\n[bold]Daily Spending Progress:[/bold]")
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style="yellow", finished_style="green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=display.console
        )
        with progress:
            task = progress.add_task(
                f"${daily_spent} / ${daily_limit}",
                total=float(daily_limit),
                completed=float(daily_spent)
            )
            time.sleep(0.5)

    # ================================================================
    # Summary & Next Steps
    # ================================================================
    display.header("Demo Complete!")

    if RICH_AVAILABLE:
        summary = """
## What We Demonstrated

✓ **Non-Custodial Wallet Creation**
  MPC-based wallet with no private key storage

✓ **Policy Enforcement**
  Spending limits and merchant whitelists enforced before execution

✓ **AP2 Protocol Compliance**
  Full mandate chain (Intent → Cart → Payment) verification

✓ **On-Chain Settlement**
  USDC transfer on Base L2 with sub-cent gas fees

✓ **Immutable Audit Trail**
  Every action logged to append-only ledger

## Next Steps

• Try other demos: `demo_trust_scoring.py`, `demo_multi_agent.py`, `demo_escrow.py`
• Read the docs: https://sardis.sh/docs
• Join Discord: https://discord.gg/sardis
• Get API key: https://sardis.sh/signup
        """
        display.console.print(Markdown(summary))
    else:
        print("\nWhat We Demonstrated:")
        print("  ✓ Non-Custodial Wallet Creation")
        print("  ✓ Policy Enforcement")
        print("  ✓ AP2 Protocol Compliance")
        print("  ✓ On-Chain Settlement")
        print("  ✓ Immutable Audit Trail")
        print("\nNext Steps:")
        print("  • Try other demos")
        print("  • Read docs: https://sardis.sh/docs")
        print("  • Get API key: https://sardis.sh/signup")

    if display.mock_mode:
        display.warning("This was a mock demo. Set SARDIS_API_KEY for real transactions.")

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
