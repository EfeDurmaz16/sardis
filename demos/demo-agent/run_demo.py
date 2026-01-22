#!/usr/bin/env python3
"""
Sardis Demo Agent - Interactive CLI Runner

Demonstrates AI agent payment capabilities with policy enforcement.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich import box

from agent import SardisAgent
from scenarios import DEMO_SCENARIOS, DEFAULT_POLICY, PaymentScenario

console = Console()


def display_banner():
    """Display the demo banner."""
    banner = """
[bold cyan]  ____                  _ _
 / ___|  __ _ _ __ __| (_)___
 \\___ \\ / _` | '__/ _` | / __|
  ___) | (_| | | | (_| | \\__ \\
 |____/ \\__,_|_|  \\__,_|_|___/[/bold cyan]

[dim]AI Agent Payment Infrastructure Demo[/dim]
"""
    console.print(banner)


def display_policy():
    """Display the current spending policy."""
    table = Table(title="Spending Policy", box=box.ROUNDED)
    table.add_column("Rule", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Daily Limit", f"${DEFAULT_POLICY['daily_limit']:.2f}")
    table.add_row("Per-Transaction Limit", f"${DEFAULT_POLICY['per_transaction_limit']:.2f}")
    table.add_row("Monthly Limit", f"${DEFAULT_POLICY['monthly_limit']:.2f}")
    table.add_row("Allowed Categories", ", ".join(DEFAULT_POLICY["allowed_categories"]))
    table.add_row("Blocked Merchants", ", ".join(DEFAULT_POLICY["blocked_merchants"]))

    console.print(table)
    console.print()


def display_scenarios():
    """Display available demo scenarios."""
    table = Table(title="Demo Scenarios", box=box.ROUNDED)
    table.add_column("#", style="dim", width=3)
    table.add_column("Scenario", style="cyan")
    table.add_column("Vendor", style="white")
    table.add_column("Amount", justify="right")
    table.add_column("Expected", justify="center")

    for i, scenario in enumerate(DEMO_SCENARIOS, 1):
        expected_style = "green" if scenario.expected_result == "APPROVED" else "red"
        table.add_row(
            str(i),
            scenario.name,
            scenario.vendor,
            f"${scenario.amount:.2f}",
            f"[{expected_style}]{scenario.expected_result}[/{expected_style}]",
        )

    console.print(table)
    console.print()


async def run_scenario(agent: SardisAgent, scenario: PaymentScenario) -> None:
    """Run a single payment scenario."""
    console.print(f"\n[bold]Running: {scenario.name}[/bold]")
    console.print(f"[dim]{scenario.explanation}[/dim]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Check policy
        task = progress.add_task("Checking policy...", total=None)
        policy_result = await agent.check_policy(
            scenario.vendor,
            scenario.amount,
            scenario.category,
        )
        progress.update(task, description="Policy checked")
        await asyncio.sleep(0.5)

        # Execute payment
        progress.update(task, description="Executing payment...")
        result = await agent.execute_payment(
            vendor=scenario.vendor,
            amount=scenario.amount,
            purpose=scenario.purpose,
            category=scenario.category,
        )
        progress.update(task, description="Payment processed")

    # Display result
    if result["status"] == "APPROVED":
        console.print(Panel(
            f"[green bold]APPROVED[/green bold]\n\n"
            f"Vendor: {result['vendor']}\n"
            f"Amount: ${result['amount']:.2f}\n"
            f"Purpose: {result['purpose']}",
            title="Payment Result",
            border_style="green",
        ))
    else:
        reason = result.get("reason", "Policy violation")
        console.print(Panel(
            f"[red bold]BLOCKED[/red bold]\n\n"
            f"Vendor: {result['vendor']}\n"
            f"Amount: ${result['amount']:.2f}\n"
            f"Reason: {reason}",
            title="Payment Result",
            border_style="red",
        ))

    # Verify against expected
    if result["status"] == scenario.expected_result:
        console.print("[green]Result matches expected outcome[/green]")
    else:
        console.print(f"[yellow]Unexpected: got {result['status']}, expected {scenario.expected_result}[/yellow]")


async def run_all_scenarios(agent: SardisAgent) -> None:
    """Run all demo scenarios."""
    console.print("\n[bold cyan]Running all demo scenarios...[/bold cyan]\n")

    for i, scenario in enumerate(DEMO_SCENARIOS, 1):
        console.rule(f"[dim]Scenario {i}/{len(DEMO_SCENARIOS)}[/dim]")
        await run_scenario(agent, scenario)
        await asyncio.sleep(0.5)

    console.rule()
    console.print("\n[bold]Demo Complete![/bold]\n")

    # Display summary
    summary = agent.get_transaction_summary()
    summary_table = Table(title="Summary", box=box.ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", justify="right")

    summary_table.add_row("Total Transactions", str(summary["total_transactions"]))
    summary_table.add_row("Approved", f"[green]{summary['approved_count']}[/green]")
    summary_table.add_row("Blocked", f"[red]{summary['blocked_count']}[/red]")
    summary_table.add_row("Total Spent", f"${summary['total_spent']:.2f}")
    summary_table.add_row("Total Blocked", f"${summary['total_blocked']:.2f}")

    console.print(summary_table)


async def interactive_mode(agent: SardisAgent) -> None:
    """Run in interactive mode."""
    console.print("\n[bold cyan]Interactive Mode[/bold cyan]")
    console.print("[dim]Enter commands: pay, balance, history, scenarios, run, quit[/dim]\n")

    while True:
        command = Prompt.ask("\n[cyan]sardis>[/cyan]").strip().lower()

        if command in ("quit", "exit", "q"):
            break

        elif command == "balance":
            balance = await agent.get_balance()
            console.print(f"[green]Balance: {balance['balance']}[/green]")
            if balance.get("source") == "simulation":
                console.print(f"[dim]Spent: {balance['spent']}[/dim]")

        elif command == "history":
            agent.display_transaction_history()

        elif command == "scenarios":
            display_scenarios()

        elif command == "policy":
            display_policy()

        elif command == "run":
            await run_all_scenarios(agent)

        elif command.startswith("run "):
            try:
                num = int(command.split()[1])
                if 1 <= num <= len(DEMO_SCENARIOS):
                    await run_scenario(agent, DEMO_SCENARIOS[num - 1])
                else:
                    console.print(f"[red]Invalid scenario number. Use 1-{len(DEMO_SCENARIOS)}[/red]")
            except (ValueError, IndexError):
                console.print("[red]Usage: run <scenario_number>[/red]")

        elif command == "pay":
            vendor = Prompt.ask("Vendor")
            amount = float(Prompt.ask("Amount ($)"))
            purpose = Prompt.ask("Purpose")
            category = Prompt.ask("Category", choices=["saas", "cloud", "devtools", "api", "retail", "other"])

            result = await agent.execute_payment(vendor, amount, purpose, category)

            if result["status"] == "APPROVED":
                console.print(f"[green]Payment approved: ${amount:.2f} to {vendor}[/green]")
            else:
                console.print(f"[red]Payment blocked: {result.get('reason', 'Policy violation')}[/red]")

        elif command == "help":
            console.print("""
[bold]Available Commands:[/bold]
  pay        - Make a custom payment
  balance    - Check wallet balance
  history    - View transaction history
  scenarios  - List demo scenarios
  policy     - View spending policy
  run        - Run all scenarios
  run N      - Run scenario N
  quit       - Exit demo
""")

        else:
            console.print("[yellow]Unknown command. Type 'help' for available commands.[/yellow]")


@click.command()
@click.option("--api-key", envvar="SARDIS_API_KEY", help="Sardis API key")
@click.option("--api-url", envvar="SARDIS_API_URL", default="http://localhost:8000", help="Sardis API URL")
@click.option("--wallet-id", help="Existing wallet ID to use")
@click.option("--interactive", "-i", is_flag=True, help="Run in interactive mode")
@click.option("--run-all", "-a", is_flag=True, help="Run all scenarios automatically")
def main(api_key: str, api_url: str, wallet_id: str, interactive: bool, run_all: bool):
    """
    Sardis Demo Agent - AI Payment Infrastructure Demo

    Demonstrates policy-enforced autonomous spending for AI agents.
    """
    display_banner()

    async def run():
        # Initialize agent
        agent = SardisAgent(
            api_key=api_key,
            api_url=api_url,
            wallet_id=wallet_id,
        )

        console.print("[dim]Initializing agent...[/dim]")

        try:
            await agent.initialize()
        except Exception as e:
            console.print(f"[yellow]Running in simulation mode: {e}[/yellow]")

        # Display policy
        display_policy()

        try:
            if run_all:
                await run_all_scenarios(agent)
            elif interactive:
                await interactive_mode(agent)
            else:
                # Default: show menu
                display_scenarios()
                console.print("\n[bold]Options:[/bold]")
                console.print("  1. Run all scenarios")
                console.print("  2. Interactive mode")
                console.print("  3. Exit")

                choice = Prompt.ask("\nSelect option", choices=["1", "2", "3"])

                if choice == "1":
                    await run_all_scenarios(agent)
                elif choice == "2":
                    await interactive_mode(agent)

        finally:
            await agent.close()

        console.print("\n[dim]Demo complete. Thank you for trying Sardis![/dim]")

    asyncio.run(run())


if __name__ == "__main__":
    main()
