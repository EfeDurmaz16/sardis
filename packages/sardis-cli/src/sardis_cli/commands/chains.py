"""Chain and gas commands."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..api import SardisAPIClient, APIError

console = Console()


@click.group()
def chains():
    """Chain and gas management."""
    pass


@chains.command()
@click.pass_context
def list(ctx):
    """List supported chains."""
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
        result = client.get("/api/v2/transactions/chains")
        chains_list = result.get("chains", [])
        
        table = Table(title="Supported Chains")
        table.add_column("Chain", style="cyan")
        table.add_column("Chain ID", justify="right")
        table.add_column("Native Token")
        table.add_column("Explorer")
        table.add_column("Status")
        
        for chain in chains_list:
            status = "[green]Active[/green]" if chain.get("is_active", True) else "[red]Inactive[/red]"
            table.add_row(
                chain.get("name", ""),
                str(chain.get("chain_id", "")),
                chain.get("native_token", ""),
                chain.get("explorer", "")[:40] + "...",
                status,
            )
        
        console.print(table)
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@chains.command()
@click.option("--chain", default="base_sepolia", help="Chain name")
@click.option("--amount", default=100.0, type=float, help="Transaction amount")
@click.option("--token", default="USDC", help="Token")
@click.pass_context
def gas(ctx, chain: str, amount: float, token: str):
    """Estimate gas for a transaction."""
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
        result = client.post("/api/v2/transactions/estimate-gas", {
            "chain": chain,
            "amount_minor": int(amount * 100),
            "token": token,
        })
        
        console.print(f"\n[bold blue]Gas Estimate[/bold blue]\n")
        console.print(f"Chain: [cyan]{chain}[/cyan]")
        console.print(f"Amount: {amount} {token}")
        console.print(f"\n[bold]Estimate:[/bold]")
        console.print(f"  Gas Limit: {result.get('gas_limit', 'N/A')}")
        console.print(f"  Gas Price: {result.get('gas_price_gwei', 'N/A')} gwei")
        console.print(f"  Max Fee: {result.get('max_fee_gwei', 'N/A')} gwei")
        console.print(f"  Priority Fee: {result.get('max_priority_fee_gwei', 'N/A')} gwei")
        console.print(f"  Estimated Cost: {result.get('estimated_cost_wei', 'N/A')} wei")
        
        if result.get("estimated_cost_usd"):
            console.print(f"  USD Cost: ${result.get('estimated_cost_usd')}")
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@chains.command()
@click.argument("chain")
@click.pass_context
def tokens(ctx, chain: str):
    """List tokens available on a chain."""
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
        result = client.get(f"/api/v2/transactions/tokens/{chain}")
        tokens_list = result.get("tokens", [])
        
        console.print(f"\n[bold blue]Tokens on {chain}[/bold blue]\n")
        
        table = Table()
        table.add_column("Token", style="cyan")
        table.add_column("Address")
        table.add_column("Decimals", justify="right")
        
        for token in tokens_list:
            table.add_row(
                token.get("symbol", ""),
                token.get("address", ""),
                str(token.get("decimals", 6)),
            )
        
        console.print(table)
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@chains.command()
@click.option("--from", "from_chain", required=True, help="Source chain")
@click.option("--to", "to_chain", required=True, help="Destination chain")
@click.option("--amount", default=100.0, type=float, help="Amount")
@click.option("--token", default="USDC", help="Token")
@click.pass_context
def route(ctx, from_chain: str, to_chain: str, amount: float, token: str):
    """Analyze cross-chain route."""
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
        # Note: This is a placeholder - cross-chain routing may not be implemented yet
        result = client.post("/api/v2/transactions/route", {
            "from_chain": from_chain,
            "to_chain": to_chain,
            "amount_minor": int(amount * 100),
            "token": token,
        })
        
        console.print(f"\n[bold blue]Route Analysis[/bold blue]\n")
        console.print(f"From: [cyan]{from_chain}[/cyan]")
        console.print(f"To: [cyan]{to_chain}[/cyan]")
        console.print(f"Amount: {amount} {token}")
        
        if result.get("bridges"):
            console.print(f"\n[bold]Available Bridges:[/bold]")
            for bridge in result.get("bridges", []):
                console.print(f"  - {bridge.get('name')}: ~{bridge.get('estimated_time')} mins, ${bridge.get('fee')}")
        else:
            console.print("\n[yellow]Cross-chain routing not yet implemented[/yellow]")
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()

