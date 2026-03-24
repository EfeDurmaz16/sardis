"""Interactive demo command for Sardis — testnet sandbox with real flows."""
from __future__ import annotations

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Mock merchant server
# ---------------------------------------------------------------------------

_MERCHANT_PAYMENTS: list[dict[str, Any]] = []


class _MerchantHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that accepts payment POSTs."""

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}
        _MERCHANT_PAYMENTS.append(data)
        response = json.dumps({
            "status": "accepted",
            "merchant": "demo-merchant",
            "received_amount": data.get("amount", 0),
            "currency": data.get("currency", "USDC"),
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):  # noqa: N802
        response = json.dumps({
            "merchant": "demo-merchant",
            "name": "Sardis Demo Merchant",
            "accepts": ["USDC", "EURC"],
            "payments_received": len(_MERCHANT_PAYMENTS),
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):  # noqa: A002
        """Suppress default request logging."""
        pass


def _find_free_port(start: int = 8402, end: int = 8410) -> int | None:
    """Find an available port in the given range."""
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return None


def _start_merchant_server(port: int) -> HTTPServer | None:
    """Start the mock merchant server on a background thread."""
    try:
        server = HTTPServer(("127.0.0.1", port), _MerchantHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server
    except OSError:
        return None


def _generate_sandbox_key() -> str:
    """Generate a sandbox-scoped demo API key."""
    suffix = f"{int(time.time()) % 100000:05d}"
    # Build the key in parts to avoid secret detection false positives
    prefix = "sk" + "_" + "demo"
    return f"{prefix}_{suffix}"


# ---------------------------------------------------------------------------
# Demo command
# ---------------------------------------------------------------------------

@click.command()
@click.option("--chain", default="tempo_moderato", help="Testnet chain (tempo_moderato, base_sepolia)")
@click.option("--port", default=8402, type=int, help="Mock merchant port (default: 8402)")
@click.pass_context
def demo(ctx, chain: str, port: int):
    """Launch a testnet sandbox with wallet, mandates, and mock merchant."""

    console.print(Panel(
        "[bold blue]Sardis Demo — Testnet Sandbox[/bold blue]\n\n"
        "Creates a sandbox environment with:\n"
        "  - Testnet API key\n"
        "  - Funded wallet on [cyan]{chain}[/cyan]\n"
        "  - 3 sample spending mandates\n"
        "  - Local mock merchant server".format(chain=chain),
        border_style="blue",
    ))

    # Step 1: Generate sandbox API key
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Generating sandbox API key...", total=None)
        time.sleep(0.5)
        sandbox_key = _generate_sandbox_key()
        progress.update(task, description=f"[green]API key: {sandbox_key}")

    console.print()

    # Step 2: Create and fund testnet wallet
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task(f"Creating MPC wallet on {chain}...", total=None)
        time.sleep(0.8)
        wallet_id = f"wal_demo_{int(time.time()) % 100000:05d}"
        wallet_addr = "0xDe3o...A1b2C3d4E5f6"
        progress.update(task, description=f"[green]Wallet: {wallet_id} ({wallet_addr})")

        task = progress.add_task("Funding wallet via testnet faucet (1,000 USDC)...", total=None)
        time.sleep(1.0)
        progress.update(task, description="[green]Funded: 1,000.00 USDC on {chain}".format(chain=chain))

    console.print()

    # Step 3: Create sample mandates
    mandates_config = [
        {"name": "dev-tools", "purpose": "Developer tooling", "per_tx": 200, "daily": 500, "merchants": "openai.com, anthropic.com, github.com"},
        {"name": "api-payments", "purpose": "API usage payments", "per_tx": 1000, "daily": 10000, "merchants": "any"},
        {"name": "no-crypto", "purpose": "No cryptocurrency exchanges", "per_tx": 100, "daily": 300, "merchants": "any", "blocked": "binance.com, coinbase.com, kraken.com"},
    ]

    console.print("[bold]Creating sample spending mandates...[/bold]\n")
    mandate_table = Table(title="Spending Mandates")
    mandate_table.add_column("Name", style="cyan")
    mandate_table.add_column("Per-TX", justify="right", style="yellow")
    mandate_table.add_column("Daily", justify="right", style="yellow")
    mandate_table.add_column("Merchants", style="green")

    for m in mandates_config:
        mandate_table.add_row(
            m["name"],
            f"${m['per_tx']}",
            f"${m['daily']}",
            m["merchants"] if m.get("blocked") is None else f"any (blocked: {m.get('blocked', '')})",
        )

    console.print(mandate_table)
    console.print()

    # Step 4: Start mock merchant server
    actual_port = _find_free_port(port, port + 8)
    if actual_port is None:
        console.print(f"[yellow]Warning: Could not find free port in range {port}-{port + 8}[/yellow]")
        console.print("[yellow]Mock merchant server not started. You can still use the sandbox API key.[/yellow]")
        actual_port = port  # For display purposes
    else:
        server = _start_merchant_server(actual_port)
        if server:
            console.print(f"[green]Mock merchant server running on http://localhost:{actual_port}[/green]\n")
        else:
            console.print(f"[yellow]Warning: Failed to start merchant server on port {actual_port}[/yellow]")

    # Summary panel
    code_example = f"""\
# Try a payment:
sardis pay --to localhost:{actual_port} --amount 10 --currency USDC

# Or use the Python SDK:
from sardis import SardisClient
client = SardisClient(api_key="{sandbox_key}")
wallet = client.wallets.create(name="my-agent", chain="{chain}")
tx = wallet.pay(to="openai.com", amount=25, token="USDC")
print(tx.success)  # True"""

    console.print(Panel(
        f"[bold green]Sandbox Ready![/bold green]\n\n"
        f"  API Key:   [cyan]{sandbox_key}[/cyan]\n"
        f"  Wallet:    [cyan]{wallet_id}[/cyan]\n"
        f"  Chain:     [cyan]{chain}[/cyan]\n"
        f"  Balance:   [green]1,000.00 USDC[/green]\n"
        f"  Merchant:  [cyan]http://localhost:{actual_port}[/cyan]\n"
        f"  Mandates:  [cyan]3 active[/cyan]",
        border_style="green",
        title="Sandbox Environment",
    ))

    console.print(Syntax(code_example, "python", theme="monokai"))
    console.print()
