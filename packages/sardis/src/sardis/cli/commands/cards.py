"""Virtual card management commands.

NOTE: Card operations are not yet connected to a live backend.
All subcommands in this module will display a 'not yet implemented' message.
Card issuance is planned via Stripe Issuing; see sardis --help for available commands.
"""
from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.group()
@click.pass_context
def cards(ctx):
    """Virtual card operations (Stripe Issuing). [Not yet implemented]"""
    pass


@cards.command()
@click.option("--agent-id", required=True, help="Agent to issue card for")
@click.option("--limit", "spending_limit", type=float, default=500.0, help="Monthly spending limit")
@click.option("--currency", default="USD", help="Card currency")
@click.option("--categories", help="Allowed merchant categories (comma-separated)")
@click.pass_context
def create(ctx, agent_id: str, spending_limit: float, currency: str, categories: str | None):
    """Create a virtual card for an agent."""
    click.echo("Command not yet implemented. See sardis --help for available commands.")


@cards.command("list")
@click.option("--agent-id", help="Filter by agent ID")
@click.option("--status", type=click.Choice(["active", "frozen", "cancelled", "all"]), default="all")
@click.pass_context
def list_cards(ctx, agent_id: str | None, status: str):
    """List virtual cards."""
    click.echo("Command not yet implemented. See sardis --help for available commands.")


@cards.command()
@click.argument("card_id")
@click.pass_context
def freeze(ctx, card_id: str):
    """Freeze a virtual card (temporarily disable)."""
    click.echo("Command not yet implemented. See sardis --help for available commands.")


@cards.command()
@click.argument("card_id")
@click.pass_context
def unfreeze(ctx, card_id: str):
    """Unfreeze a virtual card."""
    click.echo("Command not yet implemented. See sardis --help for available commands.")


@cards.command()
@click.argument("card_id")
@click.confirmation_option(prompt="Are you sure you want to permanently cancel this card?")
@click.pass_context
def cancel(ctx, card_id: str):
    """Cancel a virtual card (permanent)."""
    click.echo("Command not yet implemented. See sardis --help for available commands.")
