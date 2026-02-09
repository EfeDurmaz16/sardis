"""Authentication commands."""
from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.group()
def auth():
    """Authentication management."""
    pass


@auth.command()
@click.pass_context
def status(ctx):
    """Check authentication status."""
    config = ctx.obj["config"]
    
    api_key = config.get("api_key")
    if api_key:
        console.print("[green]✓ Authenticated[/green]")
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        console.print(f"  API Key: {masked}")
    else:
        console.print("[yellow]Not authenticated[/yellow]")
        console.print("  Run 'sardis login' to authenticate")


@auth.command()
@click.pass_context
def whoami(ctx):
    """Show current user information."""
    from ..api import SardisAPIClient, APIError
    
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    
    if not api_key:
        console.print("[yellow]Not authenticated[/yellow]")
        return
    
    client = SardisAPIClient(
        base_url=config.get("api_base_url", "https://api.sardis.sh"),
        api_key=api_key,
    )
    
    try:
        result = client.get("/api/v2/auth/me")
        console.print(f"\n[bold]User Information[/bold]")
        console.print(f"  Organization: {result.get('organization_id', 'N/A')}")
        console.print(f"  Scopes: {', '.join(result.get('scopes', []))}")
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()

