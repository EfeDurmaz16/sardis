"""Policy management commands."""
from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from ..api import SardisAPIClient, APIError

console = Console()


@click.group()
def policies():
    """Spending policy management commands."""
    pass


@policies.command("list")
@click.option("--agent", required=True, help="Agent ID")
@click.pass_context
def list_policies(ctx, agent: str):
    """List policies for an agent."""
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
        result = client.get(f"/api/v2/policies/{agent}")
        policies_list = result.get("policies", [result] if "policy_id" in result else [])

        if not policies_list:
            console.print("[dim]No policies found for this agent[/dim]")
            return

        table = Table(title=f"Policies for Agent {agent}")
        table.add_column("Policy ID", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Per-TX Limit", justify="right", style="yellow")
        table.add_column("Total Limit", justify="right", style="yellow")
        table.add_column("Allowed Destinations")
        table.add_column("Status")

        for policy in policies_list:
            allowed_dests = policy.get("allowed_destinations", [])
            dests_display = ", ".join(allowed_dests) if allowed_dests else "Any"

            status = policy.get("status", "active")
            status_style = "[green]Active[/green]" if status == "active" else f"[dim]{status}[/dim]"

            table.add_row(
                policy.get("policy_id", ""),
                policy.get("agent_id", agent),
                str(policy.get("max_per_tx", "Unlimited")),
                str(policy.get("max_total", "Unlimited")),
                dests_display,
                status_style,
            )

        console.print(table)

    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@policies.command()
@click.option("--agent", required=True, help="Agent ID")
@click.option("--amount", required=True, type=float, help="Transaction amount")
@click.option("--to", "destination", default=None, help="Destination address")
@click.option("--token", default="USDC", help="Token (default: USDC)")
@click.option("--purpose", default=None, help="Payment purpose/description")
@click.pass_context
def check(ctx, agent: str, amount: float, destination: str | None, token: str, purpose: str | None):
    """Check if a payment would be allowed by policy."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")

    if not api_key:
        console.print("[yellow]Not authenticated[/yellow]")
        return

    client = SardisAPIClient(
        base_url=config.get("api_base_url"),
        api_key=api_key,
    )

    payload: dict = {
        "agent_id": agent,
        "amount": amount,
        "token": token,
    }
    if destination:
        payload["destination"] = destination
    if purpose:
        payload["purpose"] = purpose

    try:
        result = client.post("/api/v2/policies/check", payload)

        allowed = result.get("allowed", False)
        reason = result.get("reason", "")
        checks_passed = result.get("checks_passed", [])
        checks_failed = result.get("checks_failed", [])

        console.print(f"\n[bold blue]Policy Check Result[/bold blue]\n")

        if allowed:
            console.print("[bold green]ALLOWED[/bold green]")
        else:
            console.print("[bold red]DENIED[/bold red]")

        if reason:
            console.print(f"Reason: {reason}")

        if checks_passed:
            console.print(f"\n[green]Checks Passed ({len(checks_passed)}):[/green]")
            for c in checks_passed:
                console.print(f"  [green]+ {c}[/green]")

        if checks_failed:
            console.print(f"\n[red]Checks Failed ({len(checks_failed)}):[/red]")
            for c in checks_failed:
                console.print(f"  [red]- {c}[/red]")

        console.print()

    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@policies.command("set")
@click.option("--agent", required=True, help="Agent ID")
@click.option("--max-per-tx", type=float, default=None, help="Maximum amount per transaction")
@click.option("--max-total", type=float, default=None, help="Maximum total spend")
@click.option("--allowed-destinations", default=None, help="Comma-separated allowed destination addresses")
@click.option("--blocked-destinations", default=None, help="Comma-separated blocked destination addresses")
@click.option("--allowed-tokens", default=None, help="Comma-separated allowed tokens")
@click.option("--require-purpose", is_flag=True, default=False, help="Require a purpose for every payment")
@click.option("--approval-threshold", type=float, default=None, help="Amount above which manual approval is required")
@click.option("--policy", "policy_text", default=None, help="Natural language policy description")
@click.pass_context
def set_policy(
    ctx,
    agent: str,
    max_per_tx: float | None,
    max_total: float | None,
    allowed_destinations: str | None,
    blocked_destinations: str | None,
    allowed_tokens: str | None,
    require_purpose: bool,
    approval_threshold: float | None,
    policy_text: str | None,
):
    """Set or update an agent's spending policy."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")

    if not api_key:
        console.print("[yellow]Not authenticated[/yellow]")
        return

    client = SardisAPIClient(
        base_url=config.get("api_base_url"),
        api_key=api_key,
    )

    payload: dict = {"agent_id": agent}

    if max_per_tx is not None:
        payload["max_per_tx"] = max_per_tx
    if max_total is not None:
        payload["max_total"] = max_total
    if allowed_destinations is not None:
        payload["allowed_destinations"] = [d.strip() for d in allowed_destinations.split(",") if d.strip()]
    if blocked_destinations is not None:
        payload["blocked_destinations"] = [d.strip() for d in blocked_destinations.split(",") if d.strip()]
    if allowed_tokens is not None:
        payload["allowed_tokens"] = [t.strip() for t in allowed_tokens.split(",") if t.strip()]
    if require_purpose:
        payload["require_purpose"] = True
    if approval_threshold is not None:
        payload["approval_threshold"] = approval_threshold
    if policy_text is not None:
        payload["policy"] = policy_text

    try:
        result = client.post("/api/v2/policies/apply", payload)

        console.print(f"\n[green]Policy applied successfully[/green]")
        console.print(f"  Agent: [cyan]{agent}[/cyan]")
        console.print(f"  Policy ID: [cyan]{result.get('policy_id', 'N/A')}[/cyan]")

        if max_per_tx is not None:
            console.print(f"  Max Per TX: {max_per_tx}")
        if max_total is not None:
            console.print(f"  Max Total: {max_total}")
        if allowed_destinations is not None:
            console.print(f"  Allowed Destinations: {allowed_destinations}")
        if blocked_destinations is not None:
            console.print(f"  Blocked Destinations: {blocked_destinations}")
        if allowed_tokens is not None:
            console.print(f"  Allowed Tokens: {allowed_tokens}")
        if require_purpose:
            console.print(f"  Require Purpose: Yes")
        if approval_threshold is not None:
            console.print(f"  Approval Threshold: {approval_threshold}")
        if policy_text is not None:
            console.print(f"  Policy: {policy_text}")

        console.print()

    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@policies.command()
@click.option("--agent", required=True, help="Agent ID")
@click.option("--file", "file_path", default=None, type=click.Path(exists=True), help="JSON file with transactions array")
@click.pass_context
def simulate(ctx, agent: str, file_path: str | None):
    """Simulate a series of transactions against a policy."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")

    if not api_key:
        console.print("[yellow]Not authenticated[/yellow]")
        return

    client = SardisAPIClient(
        base_url=config.get("api_base_url"),
        api_key=api_key,
    )

    transactions: list[dict] = []

    if file_path:
        with open(file_path) as f:
            data = json.load(f)
        if isinstance(data, list):
            transactions = data
        elif isinstance(data, dict) and "transactions" in data:
            transactions = data["transactions"]
        else:
            console.print("[red]Error: JSON file must contain an array or {\"transactions\": [...]}[/red]")
            client.close()
            return
    else:
        console.print("[bold blue]Interactive Simulation Mode[/bold blue]")
        console.print("Enter transactions one by one. Type 'done' to finish.\n")

        while True:
            amount_str = click.prompt("Amount (or 'done')", default="done")
            if amount_str.lower() == "done":
                break

            try:
                amount = float(amount_str)
            except ValueError:
                console.print("[red]Invalid amount, skipping[/red]")
                continue

            destination = click.prompt("Destination (optional, press Enter to skip)", default="", show_default=False)
            token = click.prompt("Token", default="USDC")
            purpose = click.prompt("Purpose (optional, press Enter to skip)", default="", show_default=False)

            tx: dict = {"amount": amount, "token": token}
            if destination:
                tx["destination"] = destination
            if purpose:
                tx["purpose"] = purpose

            transactions.append(tx)
            console.print(f"  [dim]Added transaction #{len(transactions)}[/dim]\n")

    if not transactions:
        console.print("[dim]No transactions to simulate[/dim]")
        client.close()
        return

    table = Table(title=f"Policy Simulation for Agent {agent}")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Amount", justify="right", style="yellow")
    table.add_column("Token")
    table.add_column("Destination")
    table.add_column("Purpose")
    table.add_column("Result")
    table.add_column("Reason")

    try:
        for i, tx in enumerate(transactions, 1):
            payload: dict = {
                "agent_id": agent,
                "amount": tx.get("amount", 0),
                "token": tx.get("token", "USDC"),
            }
            if tx.get("destination"):
                payload["destination"] = tx["destination"]
            if tx.get("purpose"):
                payload["purpose"] = tx["purpose"]

            try:
                result = client.post("/api/v2/policies/check", payload)
                allowed = result.get("allowed", False)
                reason = result.get("reason", "")

                result_display = "[green]PASS[/green]" if allowed else "[red]FAIL[/red]"
            except APIError as e:
                result_display = "[red]ERROR[/red]"
                reason = e.message

            table.add_row(
                str(i),
                str(tx.get("amount", 0)),
                tx.get("token", "USDC"),
                tx.get("destination", "-"),
                tx.get("purpose", "-"),
                result_display,
                reason,
            )

        console.print(table)

    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()
