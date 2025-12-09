"""Agent management commands."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..api import SardisAPIClient, APIError

console = Console()


@click.group()
def agents():
    """Agent management commands."""
    pass


@agents.command()
@click.pass_context
def list(ctx):
    """List all agents."""
    config = ctx.obj["config"]
    api_key = config.get("api_key")
    
    if not api_key:
        console.print("[yellow]Not authenticated. Run 'sardis login' first.[/yellow]")
        return
    
    client = SardisAPIClient(
        base_url=config.get("api_base_url"),
        api_key=api_key,
    )
    
    try:
        result = client.get("/api/v2/agents")
        agents_list = result.get("agents", [])
        
        if not agents_list:
            console.print("[dim]No agents found[/dim]")
            return
        
        table = Table(title="Agents")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created")
        
        for agent in agents_list:
            status = "Active" if agent.get("is_active") else "Inactive"
            table.add_row(
                agent.get("external_id", ""),
                agent.get("name", ""),
                status,
                agent.get("created_at", "")[:10],
            )
        
        console.print(table)
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@agents.command()
@click.argument("agent_id")
@click.pass_context
def get(ctx, agent_id: str):
    """Get agent details."""
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
        agent = client.get(f"/api/v2/agents/{agent_id}")
        
        console.print(f"\n[bold blue]Agent Details[/bold blue]\n")
        console.print(f"ID: [cyan]{agent.get('external_id')}[/cyan]")
        console.print(f"Name: {agent.get('name')}")
        console.print(f"Description: {agent.get('description', 'N/A')}")
        console.print(f"Status: {'Active' if agent.get('is_active') else 'Inactive'}")
        console.print(f"Created: {agent.get('created_at')}")
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()


@agents.command()
@click.option("--name", required=True, help="Agent name")
@click.option("--description", help="Agent description")
@click.pass_context
def create(ctx, name: str, description: str | None):
    """Create a new agent."""
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
        data = {"name": name}
        if description:
            data["description"] = description
        
        agent = client.post("/api/v2/agents", data)
        
        console.print(f"\n[green]✓ Agent created successfully[/green]")
        console.print(f"  ID: [cyan]{agent.get('external_id')}[/cyan]")
        console.print(f"  Name: {agent.get('name')}")
        
    except APIError as e:
        console.print(f"[red]Error: {e.message}[/red]")
    finally:
        client.close()

