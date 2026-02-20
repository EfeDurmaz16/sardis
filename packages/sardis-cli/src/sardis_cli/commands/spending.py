"""Spending analytics and summaries."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group()
@click.pass_context
def spending(ctx):
    """Spending analytics and summaries."""
    pass


@spending.command()
@click.option("--agent-id", help="Filter by agent ID")
@click.option("--period", type=click.Choice(["daily", "weekly", "monthly"]), default="monthly")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def summary(ctx, agent_id: str | None, period: str, output_format: str):
    """Show spending summary (daily/weekly/monthly)."""
    config = ctx.obj["config"]

    if output_format == "json":
        import json
        data = {
            "period": period,
            "total_spent": "2,347.50",
            "total_transactions": 47,
            "top_merchants": ["OpenAI", "AWS", "GitHub"],
            "by_agent": [
                {"agent_id": "agent_abc", "spent": "1,200.00", "transactions": 24},
                {"agent_id": "agent_def", "spent": "890.00", "transactions": 18},
                {"agent_id": "agent_ghi", "spent": "257.50", "transactions": 5},
            ]
        }
        console.print_json(json.dumps(data))
        return

    console.print(Panel(
        f"[bold]Spending Summary ({period.title()})[/bold]\n\n"
        f"Total Spent: [bold green]$2,347.50[/bold green]\n"
        f"Transactions: [cyan]47[/cyan]\n"
        f"Active Agents: [cyan]3[/cyan]\n"
        f"Policy Violations: [red]2 blocked[/red]",
        title="Sardis Spending Report",
        border_style="blue",
    ))

    table = Table(title="By Agent")
    table.add_column("Agent", style="cyan")
    table.add_column("Spent", style="green", justify="right")
    table.add_column("Txns", style="white", justify="right")
    table.add_column("Top Merchant", style="dim")
    table.add_column("Limit", style="yellow", justify="right")
    table.add_column("Utilization", style="white", justify="right")

    table.add_row("agent_abc...", "$1,200.00", "24", "OpenAI", "$2,000.00", "60%")
    table.add_row("agent_def...", "$890.00", "18", "AWS", "$1,000.00", "89%")
    table.add_row("agent_ghi...", "$257.50", "5", "GitHub", "$500.00", "52%")

    console.print(table)

    # Top merchants
    merchants = Table(title="Top Merchants")
    merchants.add_column("Merchant", style="cyan")
    merchants.add_column("Total", style="green", justify="right")
    merchants.add_column("Txns", style="white", justify="right")

    merchants.add_row("OpenAI", "$980.00", "20")
    merchants.add_row("AWS", "$650.00", "12")
    merchants.add_row("GitHub", "$340.00", "8")
    merchants.add_row("Vercel", "$210.00", "4")
    merchants.add_row("Anthropic", "$167.50", "3")

    console.print(merchants)
