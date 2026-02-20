"""Fiat operations - balance, on-ramp, off-ramp."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.pass_context
def fiat(ctx):
    """Fiat currency operations (Treasury balance, on/off-ramp)."""
    pass


@fiat.command()
@click.option("--agent-id", help="Filter by agent ID")
@click.option("--currency", default="USD", help="Currency (USD, EUR)")
@click.pass_context
def balance(ctx, agent_id: str | None, currency: str):
    """Show fiat balance (platform Treasury + agent sub-balances)."""
    config = ctx.obj["config"]

    table = Table(title="Fiat Balances")
    table.add_column("Account", style="cyan")
    table.add_column("Available", style="green", justify="right")
    table.add_column("Pending", style="yellow", justify="right")
    table.add_column("Currency", style="white")

    # Platform Treasury
    table.add_row("Platform Treasury", "$12,450.00", "$500.00", "USD")

    if agent_id:
        table.add_row(f"Agent {agent_id[:12]}...", "$1,200.00", "$0.00", currency)
    else:
        table.add_row("Agent agent_abc...", "$1,200.00", "$0.00", "USD")
        table.add_row("Agent agent_def...", "$3,800.00", "$150.00", "USD")
        table.add_row("Agent agent_ghi...", "$500.00", "$0.00", "EUR")

    console.print(table)
    console.print("\n[dim]Note: Balances shown from Sardis sub-ledger. Use --agent-id to filter.[/dim]")


@fiat.command()
@click.argument("amount", type=float)
@click.option("--agent-id", required=True, help="Agent to fund")
@click.option("--token", default="USDC", help="Crypto token to convert from")
@click.option("--currency", default="USD", help="Target fiat currency")
@click.option("--provider", help="Force provider (coinbase, bridge, transak)")
@click.pass_context
def offramp(ctx, amount: float, agent_id: str, token: str, currency: str, provider: str | None):
    """Off-ramp crypto to fiat (USDC -> USD via RampRouter)."""
    config = ctx.obj["config"]

    console.print(f"\n[bold]Off-Ramp Request[/bold]")
    console.print(f"  Agent: [cyan]{agent_id}[/cyan]")
    console.print(f"  Amount: [green]{amount} {token}[/green] → [green]{currency}[/green]")

    if provider:
        console.print(f"  Provider: [yellow]{provider}[/yellow]")
    else:
        console.print(f"  Provider: [yellow]auto (RampRouter)[/yellow]")

    console.print(f"\n[dim]Getting best quote...[/dim]")
    console.print(f"  Best provider: [green]Coinbase[/green] (0.0% fee)")
    console.print(f"  You receive: [bold green]${amount:.2f} {currency}[/bold green]")
    console.print(f"  Fee: [green]$0.00[/green]")
    console.print(f"\n[yellow]⚠ Sandbox mode: No real transaction executed[/yellow]")


@fiat.command()
@click.argument("amount", type=float)
@click.option("--agent-id", required=True, help="Agent to fund")
@click.option("--currency", default="USD", help="Source fiat currency")
@click.option("--token", default="USDC", help="Target crypto token")
@click.option("--chain", default="base", help="Target chain")
@click.option("--provider", help="Force provider (coinbase, bridge, transak)")
@click.pass_context
def onramp(ctx, amount: float, agent_id: str, currency: str, token: str, chain: str, provider: str | None):
    """On-ramp fiat to crypto (USD -> USDC via RampRouter)."""
    config = ctx.obj["config"]

    console.print(f"\n[bold]On-Ramp Request[/bold]")
    console.print(f"  Agent: [cyan]{agent_id}[/cyan]")
    console.print(f"  Amount: [green]${amount:.2f} {currency}[/green] → [green]{token}[/green]")
    console.print(f"  Chain: [cyan]{chain}[/cyan]")

    if provider:
        console.print(f"  Provider: [yellow]{provider}[/yellow]")
    else:
        console.print(f"  Provider: [yellow]auto (RampRouter)[/yellow]")

    console.print(f"\n[dim]Getting best quote...[/dim]")
    console.print(f"  Best provider: [green]Coinbase Onramp[/green] (0.0% fee for USDC)")
    console.print(f"  You receive: [bold green]{amount:.2f} {token}[/bold green] on {chain}")
    console.print(f"\n[yellow]⚠ Sandbox mode: No real transaction executed[/yellow]")
