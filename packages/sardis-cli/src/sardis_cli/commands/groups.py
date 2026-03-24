"""Agent group management commands."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..api import APIError, SardisAPIClient

console = Console()


@click.group()
def groups():
    """Manage agent groups with shared budgets."""
    pass


@groups.command("list")
@click.pass_context
def list_groups(ctx):
    """List all agent groups."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    if not api_key:
        console.print("[yellow]Not authenticated. Run 'sardis login' first.[/yellow]")
        return

    client = SardisAPIClient(base_url=config.get("api_base_url"), api_key=api_key)
    try:
        result = client.get("/api/v2/groups")
        items = result.get("groups", [])
        if not items:
            console.print("[dim]No groups found.[/dim]")
            return

        table = Table(title="Agent Groups")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Budget/Day", justify="right", style="yellow")
        table.add_column("Spent/Day", justify="right")
        table.add_column("Agents", justify="right")

        for g in items:
            budget = g.get("budget", {})
            table.add_row(
                g.get("group_id", ""),
                g.get("name", ""),
                f"${budget.get('daily', 'N/A')}",
                f"${g.get('spent_daily', '0')}",
                str(g.get("agent_count", 0)),
            )
        console.print(table)
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@groups.command()
@click.option("--name", required=True, help="Group name")
@click.option("--budget-daily", type=float, default=5000, help="Daily budget (default: $5,000)")
@click.option("--budget-per-tx", type=float, default=500, help="Per-transaction limit (default: $500)")
@click.option("--budget-monthly", type=float, default=50000, help="Monthly budget (default: $50,000)")
@click.pass_context
def create(ctx, name: str, budget_daily: float, budget_per_tx: float, budget_monthly: float):
    """Create a new agent group."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    if not api_key:
        console.print("[yellow]Not authenticated.[/yellow]")
        return

    client = SardisAPIClient(base_url=config.get("api_base_url"), api_key=api_key)
    try:
        result = client.post("/api/v2/groups", {
            "name": name,
            "budget": {
                "daily": str(budget_daily),
                "per_transaction": str(budget_per_tx),
                "monthly": str(budget_monthly),
            },
        })
        console.print(f"[green]Group created: {result.get('group_id', '?')}[/green]")
        console.print(f"  Name: {name}")
        console.print(f"  Budget: ${budget_daily}/day, ${budget_per_tx}/tx")
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@groups.command("add-member")
@click.argument("group_id")
@click.option("--agent", required=True, help="Agent ID to add")
@click.pass_context
def add_member(ctx, group_id: str, agent: str):
    """Add an agent to a group."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    if not api_key:
        console.print("[yellow]Not authenticated.[/yellow]")
        return

    client = SardisAPIClient(base_url=config.get("api_base_url"), api_key=api_key)
    try:
        client.post(f"/api/v2/groups/{group_id}/agents", {"agent_id": agent})
        console.print(f"[green]Agent {agent} added to group {group_id}[/green]")
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()
