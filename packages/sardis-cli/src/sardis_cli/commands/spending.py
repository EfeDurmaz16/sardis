"""Spending analytics and summaries.

NOTE: Spending analytics are not yet connected to a live backend.
This module will query the ledger API once available.
See sardis --help for available commands.
"""
from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.group()
@click.pass_context
def spending(ctx):
    """Spending analytics and summaries. [Not yet implemented]"""
    pass


@spending.command()
@click.option("--agent-id", help="Filter by agent ID")
@click.option("--period", type=click.Choice(["daily", "weekly", "monthly"]), default="monthly")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def summary(ctx, agent_id: str | None, period: str, output_format: str):
    """Show spending summary (daily/weekly/monthly)."""
    click.echo("Command not yet implemented. See sardis --help for available commands.")
