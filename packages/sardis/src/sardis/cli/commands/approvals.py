"""Approval management commands."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..api import APIError, SardisAPIClient

console = Console()


@click.group()
def approvals():
    """Manage payment approval requests."""
    pass


@approvals.command("list")
@click.option("--status", type=click.Choice(["pending", "approved", "denied"]), default="pending")
@click.pass_context
def list_approvals(ctx, status: str):
    """List approval requests."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    if not api_key:
        console.print("[yellow]Not authenticated. Run 'sardis login' first.[/yellow]")
        return

    client = SardisAPIClient(base_url=config.get("api_base_url"), api_key=api_key)
    try:
        result = client.get("/api/v2/approvals", params={"status": status})
        items = result.get("approvals", [])
        if not items:
            console.print(f"[dim]No {status} approvals found.[/dim]")
            return

        table = Table(title=f"Approvals ({status})")
        table.add_column("ID", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Amount", justify="right", style="yellow")
        table.add_column("Merchant")
        table.add_column("Reason")

        for a in items:
            table.add_row(
                a.get("approval_id", ""),
                a.get("agent_id", ""),
                f"${a.get('amount', '0')}",
                a.get("merchant", ""),
                (a.get("reason", "") or "")[:40],
            )
        console.print(table)
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@approvals.command()
@click.argument("approval_id")
@click.option("--note", default="", help="Approval note")
@click.pass_context
def approve(ctx, approval_id: str, note: str):
    """Approve a pending payment request."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    if not api_key:
        console.print("[yellow]Not authenticated.[/yellow]")
        return

    client = SardisAPIClient(base_url=config.get("api_base_url"), api_key=api_key)
    try:
        client.post(f"/api/v2/approvals/{approval_id}/approve", {"note": note})
        console.print(f"[green]Approval {approval_id} approved.[/green]")
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@approvals.command()
@click.argument("approval_id")
@click.option("--reason", required=True, help="Reason for denial")
@click.pass_context
def deny(ctx, approval_id: str, reason: str):
    """Deny a pending payment request."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    if not api_key:
        console.print("[yellow]Not authenticated.[/yellow]")
        return

    client = SardisAPIClient(base_url=config.get("api_base_url"), api_key=api_key)
    try:
        client.post(f"/api/v2/approvals/{approval_id}/deny", {"reason": reason})
        console.print(f"[red]Approval {approval_id} denied.[/red]")
        console.print(f"  Reason: {reason}")
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()
