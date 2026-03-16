"""CLI commands for spending mandate management."""
from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def mandates():
    """Manage spending mandates — scoped payment authorization for AI agents."""
    pass


@mandates.command("list")
@click.option("--status", type=click.Choice(["active", "draft", "suspended", "revoked", "expired", "consumed"]), help="Filter by status")
@click.option("--agent-id", help="Filter by agent ID")
@click.pass_context
def list_mandates(ctx, status, agent_id):
    """List spending mandates."""
    from sardis_cli.api import api_get

    params = {}
    if status:
        params["status_filter"] = status
    if agent_id:
        params["agent_id"] = agent_id

    data = api_get(ctx, "/api/v2/spending-mandates", params=params)
    if not data:
        console.print("[dim]No mandates found.[/dim]")
        return

    table = Table(title="Spending Mandates", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Purpose")
    table.add_column("Per-TX", justify="right")
    table.add_column("Spent", justify="right", style="yellow")
    table.add_column("Total", justify="right")
    table.add_column("Approval")

    status_colors = {
        "active": "green", "draft": "dim", "suspended": "yellow",
        "revoked": "red", "expired": "dim", "consumed": "blue",
    }

    for m in data:
        s = m.get("status", "?")
        color = status_colors.get(s, "white")
        table.add_row(
            m.get("id", "?"),
            f"[{color}]{s}[/{color}]",
            (m.get("purpose_scope") or "—")[:40],
            f"${m.get('amount_per_tx', '∞')}",
            f"${m.get('spent_total', '0')}",
            f"${m.get('amount_total', '∞')}",
            m.get("approval_mode", "auto"),
        )

    console.print(table)


@mandates.command("create")
@click.option("--purpose", "-p", required=True, help="Purpose description")
@click.option("--per-tx", type=float, required=True, help="Max amount per transaction")
@click.option("--daily", type=float, help="Max daily spending")
@click.option("--monthly", type=float, help="Max monthly spending")
@click.option("--total", type=float, help="Total budget")
@click.option("--merchants", help="Allowed merchants (comma-separated)")
@click.option("--approval-threshold", type=float, help="Amount above which human approval needed")
@click.option("--approval-mode", type=click.Choice(["auto", "threshold", "always_human"]), default="auto")
@click.pass_context
def create_mandate(ctx, purpose, per_tx, daily, monthly, total, merchants, approval_threshold, approval_mode):
    """Create a new spending mandate."""
    from sardis_cli.api import api_post

    body = {
        "purpose_scope": purpose,
        "amount_per_tx": per_tx,
        "amount_daily": daily,
        "amount_monthly": monthly,
        "amount_total": total,
        "approval_threshold": approval_threshold,
        "approval_mode": approval_mode,
    }

    if merchants:
        body["merchant_scope"] = {"allowed": [m.strip() for m in merchants.split(",")]}

    result = api_post(ctx, "/api/v2/spending-mandates", body)
    if result:
        console.print(Panel(
            f"[green]Mandate created:[/green] {result.get('id', '?')}\n"
            f"Purpose: {purpose}\n"
            f"Per-TX: ${per_tx}\n"
            f"Status: {result.get('status', '?')}",
            title="✅ Spending Mandate Created",
        ))
    else:
        console.print("[red]Failed to create mandate.[/red]")


@mandates.command("revoke")
@click.argument("mandate_id")
@click.option("--reason", "-r", default="Revoked via CLI", help="Reason for revocation")
@click.pass_context
def revoke_mandate(ctx, mandate_id, reason):
    """Permanently revoke a spending mandate."""
    from sardis_cli.api import api_post

    if not click.confirm(f"Permanently revoke mandate {mandate_id}? This cannot be undone."):
        console.print("[dim]Cancelled.[/dim]")
        return

    result = api_post(ctx, f"/api/v2/spending-mandates/{mandate_id}/revoke", {"reason": reason})
    if result:
        console.print(f"[red]🚫 Mandate {mandate_id} permanently revoked.[/red]")
        console.print(f"Reason: {reason}")
    else:
        console.print(f"[red]Failed to revoke mandate {mandate_id}.[/red]")


@mandates.command("suspend")
@click.argument("mandate_id")
@click.option("--reason", "-r", default="Suspended via CLI", help="Reason")
@click.pass_context
def suspend_mandate(ctx, mandate_id, reason):
    """Temporarily suspend a spending mandate."""
    from sardis_cli.api import api_post

    result = api_post(ctx, f"/api/v2/spending-mandates/{mandate_id}/suspend", {"reason": reason})
    if result:
        console.print(f"[yellow]⏸️  Mandate {mandate_id} suspended.[/yellow]")
    else:
        console.print(f"[red]Failed to suspend mandate {mandate_id}.[/red]")


@mandates.command("resume")
@click.argument("mandate_id")
@click.pass_context
def resume_mandate(ctx, mandate_id):
    """Resume a suspended spending mandate."""
    from sardis_cli.api import api_post

    result = api_post(ctx, f"/api/v2/spending-mandates/{mandate_id}/resume", {})
    if result:
        console.print(f"[green]▶️  Mandate {mandate_id} resumed.[/green]")
    else:
        console.print(f"[red]Failed to resume mandate {mandate_id}.[/red]")
