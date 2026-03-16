"""Payment commands."""
from __future__ import annotations

import time

import click
from rich.console import Console
from rich.progress import Progress

from ..api import APIError, SardisAPIClient

console = Console()


@click.group()
def payments():
    """Payment management commands."""
    pass


@payments.command()
@click.option("--from", "from_wallet", required=True, help="Source wallet ID")
@click.option("--to", "destination", required=True, help="Destination address")
@click.option("--amount", required=True, type=float, help="Amount to send")
@click.option("--token", default="USDC", help="Token (default: USDC)")
@click.option("--chain", default="base_sepolia", help="Chain (default: base_sepolia)")
@click.option("--purpose", help="Payment purpose/description")
@click.pass_context
def execute(
    ctx,
    from_wallet: str,
    destination: str,
    amount: float,
    token: str,
    chain: str,
    purpose: str | None,
):
    """Execute a payment."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")

    if not api_key:
        console.print("[yellow]Not authenticated[/yellow]")
        return

    client = SardisAPIClient(
        base_url=config.get("api_base_url"),
        api_key=api_key,
    )

    # Convert amount to minor units (cents)
    amount_minor = int(amount * 100)

    # Pre-check: look up active spending mandate for context
    try:
        mandates_data = client.get("/api/v2/spending-mandates", params={"status_filter": "active"})
        if mandates_data and isinstance(mandates_data, list) and len(mandates_data) > 0:
            active_mandate = mandates_data[0]
            per_tx = active_mandate.get("amount_per_tx")
            spent = active_mandate.get("spent_total", "0")
            total = active_mandate.get("amount_total")
            purpose_scope = active_mandate.get("purpose_scope", "")

            console.print(f"\n[dim]Active mandate: {active_mandate.get('id')}[/dim]")
            if purpose_scope:
                console.print(f"[dim]  Purpose: {purpose_scope}[/dim]")
            if per_tx:
                if amount > float(per_tx):
                    console.print(f"[red]⚠ Amount ${amount} exceeds mandate per-tx limit ${per_tx}[/red]")
                    console.print("[red]  Payment will likely be rejected by mandate policy.[/red]")
                else:
                    console.print(f"[dim]  Per-tx limit: ${per_tx} (ok)[/dim]")
            if total:
                remaining = float(total) - float(spent)
                if amount > remaining:
                    console.print(f"[red]⚠ Amount ${amount} exceeds remaining mandate budget ${remaining:.2f}[/red]")
                else:
                    console.print(f"[dim]  Budget: ${spent} / ${total} ({remaining:.2f} remaining)[/dim]")
    except Exception:
        pass  # Don't block payment on mandate lookup failure

    mandate = {
        "mandate_id": f"cli_payment_{int(time.time())}",
        "issuer": "cli_user",
        "subject": from_wallet,
        "destination": destination,
        "amount_minor": amount_minor,
        "token": token,
        "chain": chain,
        "expires_at": int(time.time()) + 300,
    }

    if purpose:
        mandate["purpose"] = purpose

    try:
        with Progress() as progress:
            task = progress.add_task("Processing payment...", total=None)

            result = client.post("/api/v2/mandates/execute", {"mandate": mandate})

            progress.update(task, completed=True)

        console.print("\n[green]✓ Payment executed successfully[/green]")
        console.print(f"  Ledger TX: [cyan]{result.get('ledger_tx_id')}[/cyan]")
        console.print(f"  Chain TX: [cyan]{result.get('chain_tx_hash')}[/cyan]")
        console.print(f"  Chain: {result.get('chain')}")
        console.print(f"  Amount: {amount} {token}")

    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@payments.command()
@click.argument("tx_id")
@click.pass_context
def status(ctx, tx_id: str):
    """Get payment status."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")

    if not api_key:
        console.print("[yellow]Not authenticated[/yellow]")
        return

    client = SardisAPIClient(
        base_url=config.get("api_base_url"),
        api_key=api_key,
    )

    try:
        result = client.get(f"/api/v2/transactions/status/{tx_id}")

        status_emoji = {
            "pending": "⏳",
            "submitted": "📤",
            "confirming": "🔄",
            "confirmed": "✅",
            "failed": "❌",
        }

        tx_status = result.get("status", "unknown")
        emoji = status_emoji.get(tx_status, "❓")

        console.print("\n[bold blue]Transaction Status[/bold blue]\n")
        console.print(f"TX Hash: [cyan]{tx_id}[/cyan]")
        console.print(f"Status: {emoji} {tx_status}")

        if result.get("block_number"):
            console.print(f"Block: {result['block_number']}")
        if result.get("confirmations"):
            console.print(f"Confirmations: {result['confirmations']}")

    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@payments.command()
@click.option("--limit", default=10, help="Number of transactions")
@click.pass_context
def recent(ctx, limit: int):
    """List recent transactions."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")

    if not api_key:
        console.print("[yellow]Not authenticated[/yellow]")
        return

    client = SardisAPIClient(
        base_url=config.get("api_base_url"),
        api_key=api_key,
    )

    try:
        result = client.get(f"/api/v2/ledger/recent?limit={limit}")
        entries = result.get("entries", [])

        if not entries:
            console.print("[dim]No recent transactions[/dim]")
            return

        from rich.table import Table

        table = Table(title="Recent Transactions")
        table.add_column("TX ID", style="cyan")
        table.add_column("From")
        table.add_column("To")
        table.add_column("Amount", justify="right")
        table.add_column("Chain")
        table.add_column("Time")

        for entry in entries:
            table.add_row(
                entry.get("tx_id", "")[:16] + "...",
                entry.get("from_wallet", "")[:12] + "...",
                entry.get("to_wallet", "")[:12] + "...",
                f"{entry.get('amount', '0.00')} {entry.get('currency', 'USDC')}",
                entry.get("chain", ""),
                entry.get("created_at", "")[:19],
            )

        console.print(table)

    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()

