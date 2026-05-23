"""Payment commands."""
from __future__ import annotations

import time

import click
from rich.console import Console
from rich.progress import Progress

from ..api import APIError, SardisAPIClient

console = Console()


def _check_mandate(
    client: SardisAPIClient,
    from_wallet: str,
    destination: str,
    amount: float,
    token: str,
    chain: str,
) -> bool:
    """Check active spending mandate before payment execution.

    Looks up the active mandate for the agent/wallet and validates the
    payment against mandate limits, merchant scope, and rail permissions.

    Returns True if payment should proceed, False if it should be blocked.
    """
    try:
        mandates_resp = client.get(
            "/api/v2/spending-mandates",
            params={"status_filter": "active"},
        )
    except APIError:
        # Don't block payment on mandate lookup failure
        return True

    # The API may return a list directly or wrapped in a response object
    if isinstance(mandates_resp, dict):
        mandates = mandates_resp.get("mandates", mandates_resp.get("data", []))
    elif isinstance(mandates_resp, list):
        mandates = mandates_resp
    else:
        return True

    if not mandates:
        return True

    # Find mandate matching this wallet (prefer wallet_id match, fall back to first)
    mandate = None
    for m in mandates:
        if m.get("wallet_id") == from_wallet or m.get("agent_id") == from_wallet:
            mandate = m
            break
    if mandate is None:
        mandate = mandates[0]

    mandate_id = mandate.get("id", "unknown")
    purpose_scope = mandate.get("purpose_scope")
    status = mandate.get("status", "unknown")
    per_tx = mandate.get("amount_per_tx")
    daily = mandate.get("amount_daily")
    monthly = mandate.get("amount_monthly")
    total = mandate.get("amount_total")
    spent = mandate.get("spent_total", "0")
    allowed_rails = mandate.get("allowed_rails", [])
    allowed_chains = mandate.get("allowed_chains")
    allowed_tokens = mandate.get("allowed_tokens")
    merchant_scope = mandate.get("merchant_scope") or {}
    approval_threshold = mandate.get("approval_threshold")
    approval_mode = mandate.get("approval_mode", "auto")

    # Display mandate info header
    console.print(f"\n[bold blue]Spending Mandate[/bold blue]: [cyan]{mandate_id}[/cyan]")
    if purpose_scope:
        console.print(f"  Purpose: {purpose_scope}")
    console.print(f"  Status: {status}")

    # Show limits summary
    if per_tx:
        console.print(f"  Per-transaction limit: ${per_tx}")
    if daily:
        console.print(f"  Daily limit: ${daily}")
    if monthly:
        console.print(f"  Monthly limit: ${monthly}")
    if total:
        remaining = float(total) - float(spent)
        console.print(f"  Total budget: ${spent} / ${total} ([green]${remaining:.2f} remaining[/green])")
    if allowed_rails:
        console.print(f"  Allowed rails: {', '.join(allowed_rails)}")

    # --- Validation checks ---

    # Check mandate is active
    if status != "active":
        console.print(
            f"\n[red]Error: Mandate {mandate_id} is {status}, not active.[/red]"
        )
        console.print(
            "[yellow]Suggestion: Ask the mandate owner to activate or create a new mandate.[/yellow]"
        )
        return False

    # Check per-transaction limit
    if per_tx and amount > float(per_tx):
        console.print(
            f"\n[red]Error: Amount ${amount:.2f} exceeds per-transaction limit ${per_tx}.[/red]"
        )
        console.print(
            f"[yellow]Suggestion: Reduce payment to at most ${per_tx} "
            f"or request a higher per-tx limit.[/yellow]"
        )
        return False

    # Check total remaining budget
    if total:
        remaining = float(total) - float(spent)
        if amount > remaining:
            console.print(
                f"\n[red]Error: Amount ${amount:.2f} exceeds remaining mandate budget "
                f"${remaining:.2f} (${spent} of ${total} spent).[/red]"
            )
            console.print(
                "[yellow]Suggestion: Request a budget increase or create a new mandate.[/yellow]"
            )
            return False

    # Check merchant scope
    allowed_merchants = merchant_scope.get("allowed")
    blocked_merchants = merchant_scope.get("blocked", [])
    if destination in blocked_merchants:
        console.print(
            f"\n[red]Error: Destination {destination} is blocked by mandate merchant scope.[/red]"
        )
        console.print(
            "[yellow]Suggestion: Use a different destination or update the mandate scope.[/yellow]"
        )
        return False
    if allowed_merchants and destination not in allowed_merchants:
        # Check wildcard patterns
        matched = any(
            destination.endswith(a.lstrip("*")) if a.startswith("*") else destination == a
            for a in allowed_merchants
        )
        if not matched:
            console.print(
                f"\n[red]Error: Destination {destination} is not in the mandate's "
                f"allowed merchant list.[/red]"
            )
            console.print(
                f"[yellow]Suggestion: Allowed merchants: {', '.join(allowed_merchants)}[/yellow]"
            )
            return False

    # Check rail/chain/token permissions
    if allowed_chains and chain not in allowed_chains:
        console.print(
            f"\n[red]Error: Chain '{chain}' is not permitted by mandate "
            f"(allowed: {', '.join(allowed_chains)}).[/red]"
        )
        console.print(
            f"[yellow]Suggestion: Use one of: {', '.join(allowed_chains)}[/yellow]"
        )
        return False

    if allowed_tokens and token not in allowed_tokens:
        console.print(
            f"\n[red]Error: Token '{token}' is not permitted by mandate "
            f"(allowed: {', '.join(allowed_tokens)}).[/red]"
        )
        console.print(
            f"[yellow]Suggestion: Use one of: {', '.join(allowed_tokens)}[/yellow]"
        )
        return False

    # Check approval threshold
    if approval_mode == "always_human":
        console.print(
            "\n[yellow]Approval required: This mandate requires human approval "
            "for every payment.[/yellow]"
        )
        console.print(
            "[yellow]The payment will be routed for approval. "
            "You will be notified once approved.[/yellow]"
        )
    elif approval_mode == "threshold" and approval_threshold:
        if amount > float(approval_threshold):
            console.print(
                f"\n[yellow]Approval required: Amount ${amount:.2f} exceeds "
                f"approval threshold ${approval_threshold}.[/yellow]"
            )
            console.print(
                "[yellow]The payment will be routed for human approval. "
                "You will be notified once approved.[/yellow]"
            )

    # All checks passed
    console.print("[green]  Mandate check: passed[/green]")
    return True


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
@click.option("--skip-mandate-check", is_flag=True, default=False, help="Skip mandate pre-check")
@click.pass_context
def execute(
    ctx,
    from_wallet: str,
    destination: str,
    amount: float,
    token: str,
    chain: str,
    purpose: str | None,
    skip_mandate_check: bool,
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

    try:
        # Pre-check: validate payment against active spending mandate
        if not skip_mandate_check:
            should_proceed = _check_mandate(
                client, from_wallet, destination, amount, token, chain,
            )
            if not should_proceed:
                return

        # Convert amount to minor units (cents)
        amount_minor = int(amount * 100)

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

        with Progress() as progress:
            task = progress.add_task("Processing payment...", total=None)

            result = client.post("/api/v2/mandates/execute", {"mandate": mandate})

            progress.update(task, completed=True)

        console.print("\n[green]Payment executed successfully[/green]")
        console.print(f"  Ledger TX: [cyan]{result.get('ledger_tx_id')}[/cyan]")
        console.print(f"  Chain TX: [cyan]{result.get('chain_tx_hash')}[/cyan]")
        console.print(f"  Chain: {result.get('chain')}")
        console.print(f"  Amount: {amount} {token}")

        spending_mandate_id = result.get("spending_mandate_id")
        if spending_mandate_id:
            console.print(f"  Mandate: [cyan]{spending_mandate_id}[/cyan]")

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
            "pending": "...",
            "submitted": ">>",
            "confirming": "<>",
            "confirmed": "OK",
            "failed": "XX",
        }

        tx_status = result.get("status", "unknown")
        indicator = status_emoji.get(tx_status, "??")

        console.print("\n[bold blue]Transaction Status[/bold blue]\n")
        console.print(f"TX Hash: [cyan]{tx_id}[/cyan]")
        console.print(f"Status: [{indicator}] {tx_status}")

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
