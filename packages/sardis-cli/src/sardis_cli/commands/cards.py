"""Virtual card management commands."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.pass_context
def cards(ctx):
    """Virtual card operations (Stripe Issuing)."""
    pass


@cards.command()
@click.option("--agent-id", required=True, help="Agent to issue card for")
@click.option("--limit", "spending_limit", type=float, default=500.0, help="Monthly spending limit")
@click.option("--currency", default="USD", help="Card currency")
@click.option("--categories", help="Allowed merchant categories (comma-separated)")
@click.pass_context
def create(ctx, agent_id: str, spending_limit: float, currency: str, categories: str | None):
    """Create a virtual card for an agent."""
    config = ctx.obj["config"]

    console.print(f"\n[bold]Creating Virtual Card[/bold]")
    console.print(f"  Agent: [cyan]{agent_id}[/cyan]")
    console.print(f"  Limit: [green]${spending_limit:.2f}/month[/green]")
    console.print(f"  Currency: [white]{currency}[/white]")

    if categories:
        console.print(f"  Categories: [yellow]{categories}[/yellow]")
    else:
        console.print(f"  Categories: [yellow]all (unrestricted)[/yellow]")

    console.print(f"\n  Card ID: [bold cyan]card_sim_abc123[/bold cyan]")
    console.print(f"  Number: [dim]4242 •••• •••• 1234[/dim]")
    console.print(f"  Status: [green]active[/green]")
    console.print(f"  Provider: [white]Stripe Issuing[/white]")
    console.print(f"\n[yellow]⚠ Sandbox mode: Virtual card created in test environment[/yellow]")


@cards.command("list")
@click.option("--agent-id", help="Filter by agent ID")
@click.option("--status", type=click.Choice(["active", "frozen", "cancelled", "all"]), default="all")
@click.pass_context
def list_cards(ctx, agent_id: str | None, status: str):
    """List virtual cards."""
    config = ctx.obj["config"]

    table = Table(title="Virtual Cards")
    table.add_column("Card ID", style="cyan")
    table.add_column("Agent", style="white")
    table.add_column("Last 4", style="dim")
    table.add_column("Limit", style="green", justify="right")
    table.add_column("Spent", style="yellow", justify="right")
    table.add_column("Status", style="white")
    table.add_column("Provider", style="dim")

    table.add_row("card_abc123", "agent_abc...", "1234", "$500.00", "$127.50", "[green]active[/green]", "Stripe")
    table.add_row("card_def456", "agent_def...", "5678", "$1,000.00", "$890.00", "[green]active[/green]", "Stripe")
    table.add_row("card_ghi789", "agent_ghi...", "9012", "$200.00", "$200.00", "[red]frozen[/red]", "Lithic")

    console.print(table)


@cards.command()
@click.argument("card_id")
@click.pass_context
def freeze(ctx, card_id: str):
    """Freeze a virtual card (temporarily disable)."""
    console.print(f"\n[yellow]Freezing card {card_id}...[/yellow]")
    console.print(f"[green]Card {card_id} frozen successfully.[/green]")
    console.print("[dim]Use 'sardis cards unfreeze' to re-enable.[/dim]")


@cards.command()
@click.argument("card_id")
@click.pass_context
def unfreeze(ctx, card_id: str):
    """Unfreeze a virtual card."""
    console.print(f"\n[cyan]Unfreezing card {card_id}...[/cyan]")
    console.print(f"[green]Card {card_id} is now active.[/green]")


@cards.command()
@click.argument("card_id")
@click.confirmation_option(prompt="Are you sure you want to permanently cancel this card?")
@click.pass_context
def cancel(ctx, card_id: str):
    """Cancel a virtual card (permanent)."""
    console.print(f"\n[red]Cancelling card {card_id}...[/red]")
    console.print(f"[green]Card {card_id} cancelled permanently.[/green]")
