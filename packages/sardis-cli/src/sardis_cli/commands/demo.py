"""Interactive demo command for Sardis."""
from __future__ import annotations

import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

console = Console()


@click.command()
@click.option("--scenario", type=click.Choice(["payment", "fiat", "card", "full"]), default="full")
@click.pass_context
def demo(ctx, scenario: str):
    """Run an interactive Sardis demo (simulation mode)."""
    console.print(Panel(
        "[bold blue]Sardis Interactive Demo[/bold blue]\n\n"
        "This demo simulates agent payment flows in sandbox mode.\n"
        "No real transactions are executed.",
        border_style="blue",
    ))

    if scenario in ("payment", "full"):
        _demo_payment()

    if scenario in ("fiat", "full"):
        _demo_fiat()

    if scenario in ("card", "full"):
        _demo_card()

    console.print(Panel(
        "[bold green]Demo Complete![/bold green]\n\n"
        "To get started with real transactions:\n"
        "  1. [cyan]sardis init[/cyan] - Configure your API key\n"
        "  2. [cyan]sardis wallets create --name my-agent --chain base[/cyan]\n"
        "  3. [cyan]sardis payments execute --wallet <id> --to <address> --amount 10 --token USDC[/cyan]\n\n"
        "Documentation: [link]https://sardis.sh/docs[/link]",
        border_style="green",
    ))


def _demo_payment():
    console.print("\n[bold]Step 1: On-Chain Payment[/bold]\n")

    code = '''from sardis import SardisClient

client = SardisClient(api_key="sk_test_...")
wallet = client.wallets.create(
    name="demo-agent",
    chain="base",
    policy="Max $100/day, only OpenAI and AWS"
)

# Agent makes a payment
result = client.payments.execute(
    wallet_id=wallet.id,
    to="0x1234...merchant",
    amount=50,
    token="USDC",
    purpose="OpenAI API credits"
)'''
    console.print(Syntax(code, "python", theme="monokai"))

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Creating MPC wallet via Turnkey...", total=None)
        time.sleep(1)
        progress.update(task, description="[green]Wallet created: wallet_demo_abc123")

        task = progress.add_task("Checking spending policy...", total=None)
        time.sleep(0.5)
        progress.update(task, description="[green]Policy check passed (within $100/day limit)")

        task = progress.add_task("Executing USDC transfer on Base...", total=None)
        time.sleep(1.5)
        progress.update(task, description="[green]Payment complete! TX: 0xabcd...ef12")

    table = Table(title="Transaction Receipt")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Status", "[green]confirmed[/green]")
    table.add_row("Amount", "50.00 USDC")
    table.add_row("Chain", "Base")
    table.add_row("TX Hash", "0xabcd...ef12")
    table.add_row("Gas", "0.0002 ETH")
    table.add_row("Ledger Entry", "LE-2026-001")
    console.print(table)


def _demo_fiat():
    console.print("\n[bold]Step 2: Fiat Off-Ramp (USDC -> USD)[/bold]\n")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("RampRouter: Getting best quote...", total=None)
        time.sleep(1)
        progress.update(task, description="[green]Best: Coinbase Onramp (0.0% fee for USDC)")

        task = progress.add_task("Off-ramping 100 USDC to USD...", total=None)
        time.sleep(1.5)
        progress.update(task, description="[green]$100.00 deposited to Stripe Treasury")

        task = progress.add_task("Recording in sub-ledger...", total=None)
        time.sleep(0.5)
        progress.update(task, description="[green]Double-entry recorded: DR Assets/Fiat, CR Liabilities")

    console.print("[green]Fiat balance updated: $100.00 available[/green]\n")


def _demo_card():
    console.print("\n[bold]Step 3: Virtual Card Payment[/bold]\n")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Creating virtual card via Stripe Issuing...", total=None)
        time.sleep(1)
        progress.update(task, description="[green]Card created: 4242 **** **** 1234 ($0.10)")

        task = progress.add_task("Funding card from Treasury balance...", total=None)
        time.sleep(0.5)
        progress.update(task, description="[green]Card funded: $100.00")

        task = progress.add_task("Agent purchasing OpenAI credits...", total=None)
        time.sleep(1)

        task = progress.add_task("Authorization webhook -> Policy check...", total=None)
        time.sleep(0.5)
        progress.update(task, description="[green]Authorized: merchant=OpenAI, amount=$50.00")

        task = progress.add_task("Recording card purchase in ledger...", total=None)
        time.sleep(0.5)
        progress.update(task, description="[green]Ledger entry: DR Expenses/Purchases, CR Assets/Cards")

    table = Table(title="Card Transaction")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Card", "4242 •••• •••• 1234")
    table.add_row("Merchant", "OpenAI")
    table.add_row("Amount", "$50.00")
    table.add_row("Status", "[green]approved[/green]")
    table.add_row("Remaining", "$50.00")
    console.print(table)
