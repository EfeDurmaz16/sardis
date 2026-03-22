"""Guided setup wizard for Sardis CLI."""
from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel

from ..api import APIError, SardisAPIClient
from ..config import save_config

console = Console()


@click.command("init")
@click.pass_context
def init_cmd(ctx):
    """Guided setup wizard for Sardis CLI."""
    config = ctx.obj["config"]

    console.print(Panel(
        "[bold blue]Sardis CLI Setup Wizard[/bold blue]\n\n"
        "This will configure your CLI with API credentials,\n"
        "default chain, and an initial spending policy.",
        expand=False,
    ))

    # Step 1: API Key
    console.print("\n[bold]Step 1:[/bold] API Credentials\n")
    api_key = click.prompt("Enter your Sardis API key", hide_input=True)
    api_url = click.prompt("API base URL", default=config.get("api_base_url", "https://api.sardis.sh"))

    config["api_key"] = api_key
    config["api_base_url"] = api_url

    # Validate the API key by making a test request
    client = SardisAPIClient(base_url=api_url, api_key=api_key)
    try:
        client.get("/api/v2/health")
        console.print("[green]API key validated successfully[/green]")
    except APIError:
        console.print("[yellow]Warning: Could not validate API key (server may be unreachable)[/yellow]")
    except Exception:
        console.print("[yellow]Warning: Could not reach API server[/yellow]")

    # Step 2: Default Chain
    console.print("\n[bold]Step 2:[/bold] Default Chain\n")
    chains = ["base_sepolia", "base", "polygon", "ethereum", "arbitrum", "optimism"]
    for i, chain in enumerate(chains, 1):
        console.print(f"  {i}. {chain}")

    chain_choice = click.prompt("\nSelect default chain", default="1")
    try:
        chain_idx = int(chain_choice) - 1
        if 0 <= chain_idx < len(chains):
            default_chain = chains[chain_idx]
        else:
            default_chain = "base_sepolia"
    except ValueError:
        # Allow typing the chain name directly
        default_chain = chain_choice if chain_choice in chains else "base_sepolia"

    config["default_chain"] = default_chain
    console.print(f"[green]Default chain set to {default_chain}[/green]")

    # Step 3: Default Policy
    console.print("\n[bold]Step 3:[/bold] Default Spending Policy\n")
    console.print("Describe your default spending policy in natural language.")
    console.print("[dim]Example: Allow up to $100 per transaction, $1000 total, only USDC on Base[/dim]\n")

    policy_text = click.prompt("Policy", default="Allow up to $100 per transaction, $1000 total per day")

    max_per_tx = click.prompt("Max amount per transaction (USD)", default=100.0, type=float)
    max_total = click.prompt("Max total spend (USD)", default=1000.0, type=float)

    # Step 4: Create wallet and apply policy
    console.print("\n[bold]Step 4:[/bold] Creating initial wallet and applying policy...\n")

    agent_id = click.prompt("Agent ID for initial wallet", default="default-agent")

    wallet_id = "N/A"
    try:
        # Create wallet
        wallet_result = client.post("/api/v2/wallets", {
            "agent_id": agent_id,
            "currency": "USDC",
        })
        wallet_id = wallet_result.get("wallet_id", "N/A")
        console.print(f"[green]Wallet created: {wallet_id}[/green]")

        # Apply policy
        client.post("/api/v2/policies/apply", {
            "agent_id": agent_id,
            "max_per_tx": max_per_tx,
            "max_total": max_total,
            "policy": policy_text,
        })
        console.print("[green]Policy applied successfully[/green]")

    except APIError as e:
        console.print(f"[yellow]Warning: {e.message}[/yellow]")
        console.print("[dim]You can create wallets and policies later with 'sardis wallets create' and 'sardis policies set'[/dim]")

    # Step 5: Test payment (sandbox)
    console.print("\n[bold]Step 5:[/bold] Making a test payment...\n")

    tx_id = None
    try:
        # Request testnet USDC from faucet first
        try:
            client.post("/api/v2/faucet/drip", {
                "wallet_id": wallet_id,
                "amount": 100,
            })
            console.print("[green]Faucet: 100 test USDC credited[/green]")
        except APIError:
            console.print("[dim]Faucet unavailable — skipping (you can fund manually)[/dim]")

        # Run sandbox policy check to verify everything works
        check_result = client.post("/api/v2/sandbox/policy-check", {
            "agent_id": agent_id,
            "amount": 10.0,
            "currency": "USDC",
            "recipient": "merchant_demo",
            "memo": "sardis init test",
        })
        decision = check_result.get("decision", "unknown")
        tx_id = check_result.get("transaction_id") or check_result.get("check_id")

        if decision in ("allow", "approved"):
            console.print(f"[bold green]Test payment approved![/bold green] Transaction: {tx_id or 'N/A'}")
        else:
            console.print(f"[yellow]Policy check returned: {decision}[/yellow]")

    except APIError as e:
        console.print(f"[yellow]Test payment skipped: {e.message}[/yellow]")
    except Exception:
        console.print("[dim]Test payment skipped (sandbox endpoint unavailable)[/dim]")

    client.close()

    # Save configuration
    save_config(config)

    # Success summary
    summary = (
        "[bold green]Setup Complete[/bold green]\n\n"
        f"API URL:        {api_url}\n"
        f"Default Chain:  {default_chain}\n"
        f"Agent:          {agent_id}\n"
        f"Wallet:         {wallet_id}\n"
        f"Policy:         {policy_text}\n"
        f"Per-TX Limit:   ${max_per_tx}\n"
        f"Total Limit:    ${max_total}\n"
    )
    if tx_id:
        summary += f"Test Payment:   {tx_id}\n"
    summary += (
        "\n[bold]Next steps:[/bold]\n"
        "  sardis status            - Verify your configuration\n"
        "  sardis wallets list      - View your wallets\n"
        "  sardis policies list     - View your policies\n"
        "  sardis payments execute  - Make a real payment"
    )
    console.print(Panel(summary, title="Sardis CLI", expand=False))
