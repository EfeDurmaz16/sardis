#!/usr/bin/env python3
"""
Sardis Demo - Simulation Mode

Demonstrates the complete agent payment flow in simulation mode.
No API server required - simulates all Sardis functionality locally.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import hashlib
import uuid

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


# ============================================================================
# SIMULATED SARDIS MODELS
# ============================================================================

@dataclass
class Agent:
    """Simulated AI Agent."""
    agent_id: str
    name: str
    is_active: bool = True
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Wallet:
    """Simulated MPC Wallet."""
    wallet_id: str
    agent_id: str
    address: str
    chain: str = "base_sepolia"
    balance: float = 1000.00  # Starting balance in USDC
    limit_per_tx: float = 500.00
    limit_daily: float = 1000.00
    is_active: bool = True


@dataclass
class Policy:
    """Spending Policy Configuration."""
    allowed_categories: list
    blocked_merchants: list
    per_tx_limit: float
    daily_limit: float
    require_purpose: bool = True


@dataclass
class Transaction:
    """Payment Transaction Record."""
    tx_id: str
    wallet_id: str
    merchant: str
    amount: float
    purpose: str
    category: str
    status: str  # APPROVED, BLOCKED
    reason: str | None
    tx_hash: str | None
    timestamp: datetime


# ============================================================================
# POLICY ENGINE
# ============================================================================

DEFAULT_POLICY = Policy(
    allowed_categories=["saas", "cloud", "devtools", "api"],
    blocked_merchants=["gambling", "adult", "casino", "betting"],
    per_tx_limit=500.00,
    daily_limit=1000.00,
    require_purpose=True,
)


def check_policy(
    policy: Policy,
    merchant: str,
    amount: float,
    category: str,
    daily_spent: float = 0.0,
) -> tuple[bool, str]:
    """
    Check if payment is allowed by policy.

    Returns: (allowed, reason)
    """
    # Check blocked merchants
    merchant_lower = merchant.lower()
    for blocked in policy.blocked_merchants:
        if blocked.lower() in merchant_lower:
            return False, f"Merchant '{merchant}' is blocked by policy"

    # Check allowed categories
    if category.lower() not in [c.lower() for c in policy.allowed_categories]:
        return False, f"Category '{category}' not in allowed list: {policy.allowed_categories}"

    # Check per-transaction limit
    if amount > policy.per_tx_limit:
        return False, f"Amount ${amount:.2f} exceeds per-transaction limit of ${policy.per_tx_limit:.2f}"

    # Check daily limit
    if daily_spent + amount > policy.daily_limit:
        return False, f"Payment would exceed daily limit of ${policy.daily_limit:.2f} (already spent ${daily_spent:.2f})"

    return True, "Payment allowed by policy"


# ============================================================================
# SIMULATED SARDIS CLIENT
# ============================================================================

class SimulatedSardisClient:
    """Simulates Sardis API for demo purposes."""

    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self.wallets: dict[str, Wallet] = {}
        self.transactions: list[Transaction] = []
        self.policy = DEFAULT_POLICY

    def create_agent(self, name: str, metadata: dict = None) -> Agent:
        """Create a new AI agent."""
        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        agent = Agent(agent_id=agent_id, name=name, metadata=metadata or {})
        self.agents[agent_id] = agent
        return agent

    def create_wallet(self, agent_id: str, initial_balance: float = 1000.00) -> Wallet:
        """Create an MPC wallet for an agent."""
        wallet_id = f"wallet_{uuid.uuid4().hex[:12]}"
        address = "0x" + hashlib.sha256(wallet_id.encode()).hexdigest()[:40]

        wallet = Wallet(
            wallet_id=wallet_id,
            agent_id=agent_id,
            address=address,
            balance=initial_balance,
        )
        self.wallets[wallet_id] = wallet
        return wallet

    def get_daily_spent(self, wallet_id: str) -> float:
        """Get total spent today."""
        today = datetime.now(timezone.utc).date()
        return sum(
            tx.amount
            for tx in self.transactions
            if tx.wallet_id == wallet_id
            and tx.status == "APPROVED"
            and tx.timestamp.date() == today
        )

    def execute_payment(
        self,
        wallet_id: str,
        merchant: str,
        amount: float,
        purpose: str,
        category: str,
    ) -> Transaction:
        """Execute a payment through the policy engine."""
        wallet = self.wallets.get(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet {wallet_id} not found")

        if not wallet.is_active:
            raise ValueError("Wallet is disabled")

        if wallet.balance < amount:
            raise ValueError(f"Insufficient balance: ${wallet.balance:.2f} < ${amount:.2f}")

        # Check policy
        daily_spent = self.get_daily_spent(wallet_id)
        allowed, reason = check_policy(
            self.policy,
            merchant=merchant,
            amount=amount,
            category=category,
            daily_spent=daily_spent,
        )

        tx_id = f"tx_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc)

        if allowed:
            # Simulate on-chain transaction
            tx_hash = "0x" + hashlib.sha256(f"{tx_id}{timestamp}".encode()).hexdigest()
            wallet.balance -= amount
            status = "APPROVED"
        else:
            tx_hash = None
            status = "BLOCKED"

        tx = Transaction(
            tx_id=tx_id,
            wallet_id=wallet_id,
            merchant=merchant,
            amount=amount,
            purpose=purpose,
            category=category,
            status=status,
            reason=None if allowed else reason,
            tx_hash=tx_hash,
            timestamp=timestamp,
        )
        self.transactions.append(tx)
        return tx


# ============================================================================
# DEMO SCENARIOS
# ============================================================================

DEMO_SCENARIOS = [
    {
        "name": "SaaS Subscription - OpenAI",
        "merchant": "OpenAI",
        "amount": 20.00,
        "purpose": "API credits for GPT-4",
        "category": "saas",
        "expected": "APPROVED",
        "explanation": "Within limits, approved category",
    },
    {
        "name": "Cloud Infrastructure - Vercel",
        "merchant": "Vercel",
        "amount": 50.00,
        "purpose": "Pro plan subscription",
        "category": "cloud",
        "expected": "APPROVED",
        "explanation": "Cloud category allowed",
    },
    {
        "name": "Development Tools - GitHub",
        "merchant": "GitHub",
        "amount": 45.00,
        "purpose": "GitHub Copilot",
        "category": "devtools",
        "expected": "APPROVED",
        "explanation": "DevTools category allowed",
    },
    {
        "name": "Blocked Category - Amazon",
        "merchant": "Amazon",
        "amount": 150.00,
        "purpose": "Office supplies",
        "category": "retail",
        "expected": "BLOCKED",
        "explanation": "Retail not in allowed categories",
    },
    {
        "name": "Over Transaction Limit",
        "merchant": "Anthropic",
        "amount": 600.00,
        "purpose": "Claude API bulk",
        "category": "saas",
        "expected": "BLOCKED",
        "explanation": "Exceeds $500 per-tx limit",
    },
    {
        "name": "AWS Infrastructure",
        "merchant": "AWS",
        "amount": 200.00,
        "purpose": "EC2 and S3 usage",
        "category": "cloud",
        "expected": "APPROVED",
        "explanation": "Cloud infrastructure allowed",
    },
    {
        "name": "Blocked Merchant - Gambling",
        "merchant": "BetOnline Casino",
        "amount": 50.00,
        "purpose": "Entertainment",
        "category": "saas",
        "expected": "BLOCKED",
        "explanation": "Gambling merchants blocked",
    },
    {
        "name": "Small Purchase - Figma",
        "merchant": "Figma",
        "amount": 15.00,
        "purpose": "Design tool",
        "category": "saas",
        "expected": "APPROVED",
        "explanation": "Small SaaS purchase OK",
    },
]


# ============================================================================
# DEMO RUNNER
# ============================================================================

def display_banner():
    """Display demo banner."""
    banner = """
[bold cyan]  ____                  _ _
 / ___|  __ _ _ __ __| (_)___
 \\___ \\ / _` | '__/ _` | / __|
  ___) | (_| | | | (_| | \\__ \\
 |____/ \\__,_|_|  \\__,_|_|___/[/bold cyan]

[dim]AI Agent Payment Infrastructure - Simulation Demo[/dim]
"""
    console.print(banner)


def display_policy():
    """Display current policy."""
    table = Table(title="Spending Policy", box=box.ROUNDED)
    table.add_column("Rule", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Per-Transaction Limit", f"${DEFAULT_POLICY.per_tx_limit:.2f}")
    table.add_row("Daily Limit", f"${DEFAULT_POLICY.daily_limit:.2f}")
    table.add_row("Allowed Categories", ", ".join(DEFAULT_POLICY.allowed_categories))
    table.add_row("Blocked Merchants", ", ".join(DEFAULT_POLICY.blocked_merchants))

    console.print(table)
    console.print()


def run_demo():
    """Run the complete demo."""
    display_banner()

    # Step 1: Create Agent
    console.print("[bold]Step 1: Create AI Agent[/bold]")
    client = SimulatedSardisClient()
    agent = client.create_agent(
        name="Demo Agent",
        metadata={"purpose": "Investment demo", "version": "1.0"}
    )
    console.print(f"[green]Created agent: {agent.agent_id}[/green]")
    console.print(f"[dim]Name: {agent.name}[/dim]")
    console.print()

    # Step 2: Create MPC Wallet
    console.print("[bold]Step 2: Create MPC Wallet (via Turnkey)[/bold]")
    wallet = client.create_wallet(agent.agent_id, initial_balance=1000.00)
    console.print(f"[green]Created wallet: {wallet.wallet_id}[/green]")
    console.print(f"[dim]Address: {wallet.address}[/dim]")
    console.print(f"[dim]Balance: ${wallet.balance:.2f} USDC[/dim]")
    console.print()

    # Step 3: Display Policy
    console.print("[bold]Step 3: Policy Configuration[/bold]")
    display_policy()

    # Step 4: Run Payment Scenarios
    console.print("[bold]Step 4: Execute Payment Scenarios[/bold]\n")

    results = []
    for i, scenario in enumerate(DEMO_SCENARIOS, 1):
        console.rule(f"[dim]Scenario {i}/{len(DEMO_SCENARIOS)}[/dim]")
        console.print(f"[bold]{scenario['name']}[/bold]")
        console.print(f"[dim]{scenario['explanation']}[/dim]\n")

        # Execute payment
        tx = client.execute_payment(
            wallet_id=wallet.wallet_id,
            merchant=scenario["merchant"],
            amount=scenario["amount"],
            purpose=scenario["purpose"],
            category=scenario["category"],
        )

        # Display result
        if tx.status == "APPROVED":
            console.print(Panel(
                f"[green bold]APPROVED[/green bold]\n\n"
                f"Merchant: {tx.merchant}\n"
                f"Amount: ${tx.amount:.2f}\n"
                f"TX Hash: {tx.tx_hash[:20]}...",
                border_style="green",
            ))
        else:
            console.print(Panel(
                f"[red bold]BLOCKED[/red bold]\n\n"
                f"Merchant: {tx.merchant}\n"
                f"Amount: ${tx.amount:.2f}\n"
                f"Reason: {tx.reason}",
                border_style="red",
            ))

        # Verify
        match = tx.status == scenario["expected"]
        results.append(match)
        if match:
            console.print("[green]Result matches expected[/green]\n")
        else:
            console.print(f"[yellow]MISMATCH: got {tx.status}, expected {scenario['expected']}[/yellow]\n")

    # Step 5: Summary
    console.rule()
    console.print("\n[bold]Step 5: Transaction Summary[/bold]\n")

    approved = [tx for tx in client.transactions if tx.status == "APPROVED"]
    blocked = [tx for tx in client.transactions if tx.status == "BLOCKED"]

    summary_table = Table(title="Results", box=box.ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", justify="right")

    summary_table.add_row("Total Transactions", str(len(client.transactions)))
    summary_table.add_row("Approved", f"[green]{len(approved)}[/green]")
    summary_table.add_row("Blocked", f"[red]{len(blocked)}[/red]")
    summary_table.add_row("Total Spent", f"${sum(tx.amount for tx in approved):.2f}")
    summary_table.add_row("Total Blocked", f"${sum(tx.amount for tx in blocked):.2f}")
    summary_table.add_row("Final Balance", f"${wallet.balance:.2f}")

    console.print(summary_table)

    # Verification
    console.print()
    passed = sum(results)
    total = len(results)
    if passed == total:
        console.print(f"[green bold]All {total} scenarios passed![/green bold]")
    else:
        console.print(f"[yellow]{passed}/{total} scenarios passed[/yellow]")

    # Transaction history
    console.print("\n[bold]Transaction History[/bold]")
    history_table = Table(box=box.SIMPLE)
    history_table.add_column("Time", style="dim")
    history_table.add_column("Merchant")
    history_table.add_column("Amount", justify="right")
    history_table.add_column("Status")

    for tx in client.transactions:
        time_str = tx.timestamp.strftime("%H:%M:%S")
        status_style = "green" if tx.status == "APPROVED" else "red"
        history_table.add_row(
            time_str,
            tx.merchant,
            f"${tx.amount:.2f}",
            f"[{status_style}]{tx.status}[/{status_style}]",
        )

    console.print(history_table)

    console.print("\n[dim]Demo complete! This demonstrates Sardis policy enforcement.[/dim]")
    console.print("[dim]In production, wallets are real MPC wallets via Turnkey,[/dim]")
    console.print("[dim]and transactions execute on-chain (Base, Polygon, etc.)[/dim]")


if __name__ == "__main__":
    run_demo()
