"""Ledger / audit trail commands."""
from __future__ import annotations

import csv
import io
import sys

import click
from rich.console import Console
from rich.table import Table

from ..api import APIError, SardisAPIClient

console = Console()


@click.group()
def ledger():
    """View and export the append-only audit trail."""
    pass


@ledger.command("list")
@click.option("--wallet", help="Filter by wallet ID")
@click.option("--group", help="Filter by group ID")
@click.option("--limit", type=int, default=50, help="Max entries (default: 50)")
@click.pass_context
def list_entries(ctx, wallet: str | None, group: str | None, limit: int):
    """List ledger entries."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    if not api_key:
        console.print("[yellow]Not authenticated. Run 'sardis login' first.[/yellow]")
        return

    client = SardisAPIClient(base_url=config.get("api_base_url"), api_key=api_key)
    try:
        params: dict[str, str | int] = {"limit": limit}
        if wallet:
            params["wallet_id"] = wallet
        if group:
            params["group_id"] = group

        result = client.get("/api/v2/ledger", params=params)
        items = result.get("entries", [])
        if not items:
            console.print("[dim]No ledger entries found.[/dim]")
            return

        table = Table(title="Ledger Entries")
        table.add_column("TX ID", style="cyan")
        table.add_column("Time", style="dim")
        table.add_column("Agent", style="green")
        table.add_column("Amount", justify="right", style="yellow")
        table.add_column("Merchant")
        table.add_column("Status")

        status_colors = {"confirmed": "green", "rejected": "red", "pending": "yellow"}

        for entry in items:
            status = entry.get("status", "?")
            color = status_colors.get(status, "white")
            table.add_row(
                entry.get("tx_id", "")[:16],
                entry.get("timestamp", "")[:19],
                entry.get("agent_name", ""),
                f"${entry.get('amount', '0')} {entry.get('currency', 'USDC')}",
                entry.get("merchant", ""),
                f"[{color}]{status}[/{color}]",
            )
        console.print(table)
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@ledger.command()
@click.option("--wallet", help="Filter by wallet ID")
@click.option("--group", help="Filter by group ID")
@click.option("--format", "fmt", type=click.Choice(["csv", "json"]), default="csv", help="Export format")
@click.option("--output", "-o", type=click.Path(), help="Output file (default: stdout)")
@click.pass_context
def export(ctx, wallet: str | None, group: str | None, fmt: str, output: str | None):
    """Export ledger entries to CSV or JSON."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    if not api_key:
        console.print("[yellow]Not authenticated.[/yellow]")
        return

    client = SardisAPIClient(base_url=config.get("api_base_url"), api_key=api_key)
    try:
        params: dict[str, str | int] = {"limit": 10000}
        if wallet:
            params["wallet_id"] = wallet
        if group:
            params["group_id"] = group

        result = client.get("/api/v2/ledger", params=params)
        items = result.get("entries", [])
        if not items:
            console.print("[dim]No entries to export.[/dim]")
            return

        if fmt == "json":
            import json
            data = json.dumps(items, indent=2)
        else:
            buf = io.StringIO()
            fields = ["tx_id", "timestamp", "agent_name", "amount", "currency", "merchant", "status", "wallet_id", "group_id", "purpose"]
            writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(items)
            data = buf.getvalue()

        if output:
            with open(output, "w") as f:
                f.write(data)
            console.print(f"[green]Exported {len(items)} entries to {output}[/green]")
        else:
            sys.stdout.write(data)
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()
