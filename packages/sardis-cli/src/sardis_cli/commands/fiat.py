"""Fiat operations - balance, on-ramp, off-ramp.

NOTE: Fiat operations are not yet connected to a live backend.
On/off-ramp integration is planned via Coinbase Onramp and RampRouter.
See sardis --help for available commands.
"""
from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.group()
@click.pass_context
def fiat(ctx):
    """Fiat currency operations (Treasury balance, on/off-ramp). [Not yet implemented]"""
    pass


@fiat.command()
@click.option("--agent-id", help="Filter by agent ID")
@click.option("--currency", default="USD", help="Currency (USD, EUR)")
@click.pass_context
def balance(ctx, agent_id: str | None, currency: str):
    """Show fiat balance (platform Treasury + agent sub-balances)."""
    click.echo("Command not yet implemented. See sardis --help for available commands.")


@fiat.command()
@click.argument("amount", type=float)
@click.option("--agent-id", required=True, help="Agent to fund")
@click.option("--token", default="USDC", help="Crypto token to convert from")
@click.option("--currency", default="USD", help="Target fiat currency")
@click.option("--provider", help="Force provider (coinbase, bridge, transak)")
@click.pass_context
def offramp(ctx, amount: float, agent_id: str, token: str, currency: str, provider: str | None):
    """Off-ramp crypto to fiat (USDC -> USD via RampRouter)."""
    click.echo("Command not yet implemented. See sardis --help for available commands.")


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
    click.echo("Command not yet implemented. See sardis --help for available commands.")
