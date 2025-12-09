"""Hold (pre-authorization) commands."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..api import SardisAPIClient, APIError

console = Console()


@click.group()
def holds():
    """Hold (pre-authorization) management."""
    pass


@holds.command()
@click.option("--wallet", required=True, help="Wallet ID")
@click.option("--amount", required=True, type=float, help="Hold amount")
@click.option("--token", default="USDC", help="Token (default: USDC)")
@click.option("--merchant", help="Merchant ID")
@click.option("--purpose", help="Hold purpose")
@click.option("--hours", default=24, type=int, help="Expiration hours (default: 24)")
@click.pass_context
def create(
    ctx,
    wallet: str,
    amount: float,
    token: str,
    merchant: str | None,
    purpose: str | None,
    hours: int,
):
    """Create a hold (pre-authorization)."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    
    if not api_key:
        console.print("[yellow]Not authenticated[/yellow]")
        return
    
    client = SardisAPIClient(
        base_url=config.get("api_base_url"),
        api_key=api_key,
    )
    
    data = {
        "wallet_id": wallet,
        "amount": f"{amount:.2f}",
        "token": token,
        "expiration_hours": hours,
    }
    
    if merchant:
        data["merchant_id"] = merchant
    if purpose:
        data["purpose"] = purpose
    
    try:
        result = client.post("/api/v2/holds", data)
        
        console.print(f"\n[green]✓ Hold created successfully[/green]")
        console.print(f"  Hold ID: [cyan]{result.get('hold_id')}[/cyan]")
        console.print(f"  Amount: {result.get('amount')} {result.get('token')}")
        console.print(f"  Expires: {result.get('expires_at')}")
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@holds.command()
@click.argument("hold_id")
@click.option("--amount", type=float, help="Capture amount (defaults to full hold)")
@click.pass_context
def capture(ctx, hold_id: str, amount: float | None):
    """Capture a hold."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    
    if not api_key:
        console.print("[yellow]Not authenticated[/yellow]")
        return
    
    client = SardisAPIClient(
        base_url=config.get("api_base_url"),
        api_key=api_key,
    )
    
    data = {}
    if amount is not None:
        data["amount"] = f"{amount:.2f}"
    
    try:
        result = client.post(f"/api/v2/holds/{hold_id}/capture", data)
        
        console.print(f"\n[green]✓ Hold captured successfully[/green]")
        console.print(f"  Hold ID: [cyan]{hold_id}[/cyan]")
        console.print(f"  Captured: {result.get('captured_amount')}")
        console.print(f"  Status: {result.get('status')}")
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@holds.command()
@click.argument("hold_id")
@click.pass_context
def void(ctx, hold_id: str):
    """Void a hold."""
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
        result = client.post(f"/api/v2/holds/{hold_id}/void")
        
        console.print(f"\n[green]✓ Hold voided successfully[/green]")
        console.print(f"  Hold ID: [cyan]{hold_id}[/cyan]")
        console.print(f"  Status: {result.get('status')}")
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@holds.command()
@click.argument("hold_id")
@click.pass_context
def get(ctx, hold_id: str):
    """Get hold details."""
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
        hold = client.get(f"/api/v2/holds/{hold_id}")
        
        status_emoji = {
            "active": "🔵",
            "captured": "✅",
            "voided": "⚪",
            "expired": "⏰",
        }
        
        status = hold.get("status", "unknown")
        emoji = status_emoji.get(status, "❓")
        
        console.print(f"\n[bold blue]Hold Details[/bold blue]\n")
        console.print(f"Hold ID: [cyan]{hold.get('hold_id')}[/cyan]")
        console.print(f"Wallet: {hold.get('wallet_id')}")
        console.print(f"Amount: {hold.get('amount')} {hold.get('token')}")
        console.print(f"Status: {emoji} {status}")
        console.print(f"Expires: {hold.get('expires_at')}")
        
        if hold.get("captured_amount"):
            console.print(f"Captured: {hold.get('captured_amount')}")
        if hold.get("merchant_id"):
            console.print(f"Merchant: {hold.get('merchant_id')}")
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@holds.command()
@click.option("--wallet", help="Filter by wallet ID")
@click.pass_context
def list(ctx, wallet: str | None):
    """List holds."""
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
        if wallet:
            result = client.get(f"/api/v2/holds/wallet/{wallet}")
        else:
            result = client.get("/api/v2/holds")
        
        holds_list = result.get("holds", [])
        
        if not holds_list:
            console.print("[dim]No holds found[/dim]")
            return
        
        table = Table(title="Holds")
        table.add_column("Hold ID", style="cyan")
        table.add_column("Wallet")
        table.add_column("Amount", justify="right")
        table.add_column("Status")
        table.add_column("Expires")
        
        for hold in holds_list:
            table.add_row(
                hold.get("hold_id", "")[:16] + "...",
                hold.get("wallet_id", "")[:16] + "...",
                f"{hold.get('amount', '0.00')} {hold.get('token', 'USDC')}",
                hold.get("status", ""),
                hold.get("expires_at", "")[:19],
            )
        
        console.print(table)
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()

