"""Wallet management commands."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..api import SardisAPIClient, APIError

console = Console()


@click.group()
def wallets():
    """Wallet management commands."""
    pass


@wallets.command()
@click.option("--agent", help="Filter by agent ID")
@click.pass_context
def list(ctx, agent: str | None):
    """List all wallets."""
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
        params = {}
        if agent:
            params["agent_id"] = agent
        
        result = client.get("/api/v2/wallets", params=params)
        wallets_list = result.get("wallets", [])
        
        if not wallets_list:
            console.print("[dim]No wallets found[/dim]")
            return
        
        table = Table(title="Wallets")
        table.add_column("ID", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Balance", style="yellow", justify="right")
        table.add_column("Currency")
        table.add_column("Status")
        
        for wallet in wallets_list:
            status = "Active" if wallet.get("is_active") else "Inactive"
            table.add_row(
                wallet.get("wallet_id", ""),
                wallet.get("agent_id", ""),
                str(wallet.get("balance", "0.00")),
                wallet.get("currency", "USDC"),
                status,
            )
        
        console.print(table)
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@wallets.command()
@click.argument("wallet_id")
@click.pass_context
def balance(ctx, wallet_id: str):
    """Get wallet balance."""
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
        wallet = client.get(f"/api/v2/wallets/{wallet_id}")
        
        console.print(f"\n[bold blue]Wallet Balance[/bold blue]\n")
        console.print(f"Wallet ID: [cyan]{wallet.get('wallet_id')}[/cyan]")
        console.print(f"Balance: [green]{wallet.get('balance', '0.00')} {wallet.get('currency', 'USDC')}[/green]")
        console.print(f"Spent Total: {wallet.get('spent_total', '0.00')} {wallet.get('currency', 'USDC')}")
        console.print(f"Limit/Tx: {wallet.get('limit_per_tx', 'N/A')}")
        console.print(f"Limit Total: {wallet.get('limit_total', 'N/A')}")
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@wallets.command()
@click.option("--agent", required=True, help="Agent ID")
@click.option("--currency", default="USDC", help="Currency (default: USDC)")
@click.pass_context
def create(ctx, agent: str, currency: str):
    """Create a new wallet."""
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
        wallet = client.post("/api/v2/wallets", {
            "agent_id": agent,
            "currency": currency,
        })
        
        console.print(f"\n[green]✓ Wallet created successfully[/green]")
        console.print(f"  ID: [cyan]{wallet.get('wallet_id')}[/cyan]")
        console.print(f"  Agent: {wallet.get('agent_id')}")
        console.print(f"  Currency: {wallet.get('currency')}")
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()

