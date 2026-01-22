"""
Sardis Demo Agent

A LangChain-powered AI agent with Sardis payment capabilities.
Demonstrates policy-enforced autonomous spending.
"""
import os
import asyncio
from typing import Any
from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class SardisAgent:
    """
    AI Agent with Sardis payment capabilities.

    This agent can:
    - Execute payments through Sardis
    - Check spending policy before payments
    - Query wallet balances
    - Maintain transaction history
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        wallet_id: str | None = None,
        agent_id: str | None = None,
    ):
        self.api_key = api_key or os.getenv("SARDIS_API_KEY", "sk_test_demo")
        self.api_url = api_url or os.getenv("SARDIS_API_URL", "http://localhost:8000")
        self.wallet_id = wallet_id
        self.agent_id = agent_id or f"demo_agent_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.transaction_history: list[dict[str, Any]] = []
        self._client = None
        self._tools = None

    async def initialize(self) -> None:
        """Initialize the agent with Sardis client and tools."""
        try:
            from sardis_sdk import SardisClient
            from sardis_sdk.integrations.langchain import create_sardis_tools

            self._client = SardisClient(
                api_key=self.api_key,
                base_url=self.api_url,
            )

            # Create wallet if not provided
            if not self.wallet_id:
                console.print("[yellow]Creating demo wallet...[/yellow]")
                wallet = await self._client.wallets.create(
                    agent_id=self.agent_id,
                    mpc_provider="turnkey",
                    currency="USDC",
                )
                self.wallet_id = wallet.wallet_id
                # Set address for base_sepolia chain
                await self._client.wallets.set_address(
                    wallet_id=self.wallet_id,
                    chain="base_sepolia",
                    address="0x" + "0" * 40,  # Placeholder address for demo
                )
                console.print(f"[green]Created wallet: {self.wallet_id}[/green]")

            # Create LangChain tools
            self._tools = create_sardis_tools(
                self._client,
                wallet_id=self.wallet_id,
                agent_id=self.agent_id,
            )

            console.print(f"[green]Agent initialized with {len(self._tools)} tools[/green]")

        except ImportError as e:
            console.print(f"[red]Failed to import Sardis SDK: {e}[/red]")
            console.print("[yellow]Running in simulation mode[/yellow]")
            self._client = None
            self._tools = None

    async def check_policy(self, vendor: str, amount: float, category: str) -> dict[str, Any]:
        """Check if a payment would be allowed by policy."""
        if self._client and self._tools:
            try:
                policy_tool = next(t for t in self._tools if t.name == "sardis_check_policy")
                result = await policy_tool._arun(merchant=vendor, amount=amount)
                return {
                    "allowed": "ALLOWED" in result,
                    "message": result,
                }
            except Exception as e:
                return {"allowed": False, "message": f"Policy check failed: {e}"}
        else:
            # Simulation mode - use local policy
            from scenarios import DEFAULT_POLICY

            # Check category
            if category not in DEFAULT_POLICY["allowed_categories"]:
                return {
                    "allowed": False,
                    "message": f"Category '{category}' not in allowed list",
                }

            # Check amount limits
            if amount > DEFAULT_POLICY["per_transaction_limit"]:
                return {
                    "allowed": False,
                    "message": f"Amount ${amount:.2f} exceeds per-transaction limit",
                }

            # Check blocked merchants
            if any(blocked in vendor.lower() for blocked in DEFAULT_POLICY["blocked_merchants"]):
                return {
                    "allowed": False,
                    "message": f"Merchant '{vendor}' is blocked",
                }

            return {
                "allowed": True,
                "message": f"Payment of ${amount:.2f} to {vendor} allowed by policy",
            }

    async def execute_payment(
        self,
        vendor: str,
        amount: float,
        purpose: str,
        category: str,
    ) -> dict[str, Any]:
        """Execute a payment through Sardis."""
        timestamp = datetime.now(timezone.utc)

        # First check policy
        policy_result = await self.check_policy(vendor, amount, category)

        if not policy_result["allowed"]:
            result = {
                "status": "BLOCKED",
                "vendor": vendor,
                "amount": amount,
                "purpose": purpose,
                "category": category,
                "reason": policy_result["message"],
                "timestamp": timestamp.isoformat(),
            }
            self.transaction_history.append(result)
            return result

        # Execute payment
        if self._client and self._tools:
            try:
                pay_tool = next(t for t in self._tools if t.name == "sardis_pay")
                tool_result = await pay_tool._arun(
                    amount=amount,
                    merchant=vendor,
                    purpose=purpose,
                )

                status = "APPROVED" if "APPROVED" in tool_result else "BLOCKED"
                result = {
                    "status": status,
                    "vendor": vendor,
                    "amount": amount,
                    "purpose": purpose,
                    "category": category,
                    "response": tool_result,
                    "timestamp": timestamp.isoformat(),
                }
            except Exception as e:
                result = {
                    "status": "BLOCKED",
                    "vendor": vendor,
                    "amount": amount,
                    "purpose": purpose,
                    "category": category,
                    "reason": str(e),
                    "timestamp": timestamp.isoformat(),
                }
        else:
            # Simulation mode
            result = {
                "status": "APPROVED",
                "vendor": vendor,
                "amount": amount,
                "purpose": purpose,
                "category": category,
                "tx_id": f"sim_tx_{timestamp.strftime('%Y%m%d%H%M%S')}",
                "timestamp": timestamp.isoformat(),
            }

        self.transaction_history.append(result)
        return result

    async def get_balance(self) -> dict[str, Any]:
        """Get current wallet balance."""
        if self._client and self._tools:
            try:
                balance_tool = next(t for t in self._tools if t.name == "sardis_check_balance")
                result = await balance_tool._arun()
                return {"balance": result, "source": "api"}
            except Exception as e:
                return {"balance": "Unknown", "error": str(e)}
        else:
            # Simulation mode
            total_spent = sum(
                tx["amount"]
                for tx in self.transaction_history
                if tx["status"] == "APPROVED"
            )
            return {
                "balance": f"${1000.00 - total_spent:.2f}",
                "source": "simulation",
                "initial": "$1000.00",
                "spent": f"${total_spent:.2f}",
            }

    def get_transaction_summary(self) -> dict[str, Any]:
        """Get summary of all transactions."""
        approved = [tx for tx in self.transaction_history if tx["status"] == "APPROVED"]
        blocked = [tx for tx in self.transaction_history if tx["status"] == "BLOCKED"]

        return {
            "total_transactions": len(self.transaction_history),
            "approved_count": len(approved),
            "blocked_count": len(blocked),
            "total_spent": sum(tx["amount"] for tx in approved),
            "total_blocked": sum(tx["amount"] for tx in blocked),
        }

    def display_transaction_history(self) -> None:
        """Display transaction history in a formatted table."""
        table = Table(title="Transaction History")
        table.add_column("Time", style="dim")
        table.add_column("Vendor", style="cyan")
        table.add_column("Amount", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Category")

        for tx in self.transaction_history:
            timestamp = datetime.fromisoformat(tx["timestamp"])
            time_str = timestamp.strftime("%H:%M:%S")
            amount_str = f"${tx['amount']:.2f}"
            status_style = "green" if tx["status"] == "APPROVED" else "red"

            table.add_row(
                time_str,
                tx["vendor"],
                amount_str,
                f"[{status_style}]{tx['status']}[/{status_style}]",
                tx.get("category", "-"),
            )

        console.print(table)

    async def close(self) -> None:
        """Close the agent and cleanup resources."""
        if self._client:
            await self._client.close()
