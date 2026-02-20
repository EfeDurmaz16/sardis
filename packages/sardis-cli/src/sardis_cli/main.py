"""
Sardis CLI main entry point.

Usage:
    sardis [OPTIONS] COMMAND [ARGS]...
"""
from __future__ import annotations

import click
from rich.console import Console

from .commands import agents, auth, chains, holds, init, payments, policies, wallets
from .commands import fiat, cards, spending, demo
from .config import load_config

console = Console()


@click.group()
@click.version_option(message="%(prog)s %(version)s")
@click.option("--api-url", envvar="SARDIS_API_BASE_URL", help="API base URL")
@click.option("--api-key", envvar="SARDIS_API_KEY", help="API key")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, api_url: str | None, api_key: str | None, verbose: bool):
    """Sardis CLI - Command-line interface for agent payments."""
    ctx.ensure_object(dict)
    
    # Load configuration
    config = load_config()
    
    # Override with CLI options
    if api_url:
        config["api_base_url"] = api_url
    if api_key:
        config["api_key"] = api_key
    
    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose


@cli.command()
@click.pass_context
def status(ctx):
    """Show current status and configuration."""
    config = ctx.obj["config"]
    
    console.print("\n[bold blue]Sardis CLI Status[/bold blue]\n")
    
    # API configuration
    api_url = config.get("api_base_url", "Not configured")
    console.print(f"API URL: [cyan]{api_url}[/cyan]")
    
    # Authentication
    api_key = config.get("api_key")
    if api_key:
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        console.print(f"API Key: [green]{masked}[/green]")
    else:
        console.print("API Key: [yellow]Not configured[/yellow]")
    
    # Default chain
    default_chain = config.get("default_chain", "base_sepolia")
    console.print(f"Default Chain: [cyan]{default_chain}[/cyan]")
    
    console.print()


@cli.command()
@click.pass_context
def login(ctx):
    """Configure API credentials."""
    console.print("\n[bold blue]Sardis Login[/bold blue]\n")
    
    # Prompt for API key
    api_key = click.prompt("Enter your API key", hide_input=True)
    
    # Prompt for API URL (optional)
    default_url = "https://api.sardis.sh"
    api_url = click.prompt("API URL", default=default_url)
    
    # Save configuration
    from .config import save_config
    
    config = ctx.obj["config"]
    config["api_key"] = api_key
    config["api_base_url"] = api_url
    
    save_config(config)
    
    console.print("\n[green]✓ Credentials saved successfully[/green]\n")


@cli.command()
@click.pass_context
def logout(ctx):
    """Remove stored credentials."""
    from .config import save_config
    
    config = ctx.obj["config"]
    config.pop("api_key", None)
    
    save_config(config)
    
    console.print("[green]✓ Logged out successfully[/green]")


# Register command groups
cli.add_command(agents.agents)
cli.add_command(wallets.wallets)
cli.add_command(payments.payments)
cli.add_command(holds.holds)
cli.add_command(chains.chains)
cli.add_command(auth.auth)
cli.add_command(policies.policies)
cli.add_command(init.init_cmd)
cli.add_command(fiat.fiat)
cli.add_command(cards.cards)
cli.add_command(spending.spending)
cli.add_command(demo.demo)


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()

