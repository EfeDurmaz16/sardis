"""
CrewAI tool implementations for Sardis agent payments.

Each tool wraps a Sardis SDK operation and returns a human-readable string
that CrewAI agents can interpret and act on.  Tools are stateful: they hold
a reference to a ``SardisClient`` and a ``wallet_id`` so agents do not need
to manage credentials or wallet lookups themselves.

Example::

    from sardis import SardisClient
    from sardis_crewai.tools import SardisPayTool

    client = SardisClient(api_key="sk_test_...")
    wallet = client.wallets.create(name="buyer", chain="base")

    pay = SardisPayTool(client=client, wallet_id=wallet.wallet_id)
    result = pay._run(to="openai.com", amount="25.00")
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from sardis import SardisClient


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class SardisPayInput(BaseModel):
    """Input schema for the Sardis payment tool."""

    to: str = Field(description="Recipient address, merchant identifier, or agent ID")
    amount: str = Field(description="Payment amount as a decimal string (e.g. '25.00')")
    token: str = Field(default="USDC", description="Stablecoin to use: USDC, USDT, EURC, or PYUSD")
    purpose: str = Field(default="", description="Reason for the payment (recorded in audit log)")


class SardisCheckBalanceInput(BaseModel):
    """Input schema for the balance check tool."""

    token: str = Field(default="USDC", description="Token to check balance for")
    chain: str = Field(default="base", description="Chain to check balance on")


class SardisCheckPolicyInput(BaseModel):
    """Input schema for the policy check tool."""

    amount: str = Field(description="Amount to validate against policy")
    to: str = Field(default="", description="Destination address or merchant")
    token: str = Field(default="USDC", description="Token type")
    purpose: str = Field(default="", description="Payment purpose")


class SardisSetPolicyInput(BaseModel):
    """Input schema for the set-policy tool."""

    policy: str = Field(
        description=(
            "Natural language spending policy. Examples: "
            "'Max $100 per transaction', 'Max $500/day', "
            "'Daily limit $1000, max $200 per tx'"
        )
    )
    chain: str = Field(default="base", description="Chain for the new wallet")
    token: str = Field(default="USDC", description="Default token for the new wallet")


class SardisGroupBudgetInput(BaseModel):
    """Input schema for the group budget status tool."""

    group_id: str = Field(description="Group ID to check budget status for")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class SardisPayTool(BaseTool):
    """Execute a payment through Sardis with policy enforcement and audit logging.

    The payment is subject to wallet spending limits, group budget (if the
    wallet belongs to a group), and the Sardis policy engine.  Results are
    recorded in the append-only audit ledger automatically.
    """

    name: str = "sardis_pay"
    description: str = (
        "Execute a payment through Sardis with policy enforcement and audit logging. "
        "Provide recipient, amount, token type, and purpose."
    )
    args_schema: Type[BaseModel] = SardisPayInput

    client: Any = Field(exclude=True)
    wallet_id: str

    def _run(
        self,
        to: str,
        amount: str,
        token: str = "USDC",
        purpose: str = "",
    ) -> str:
        try:
            amount_d = Decimal(amount)
        except InvalidOperation:
            return f"Error: Invalid amount '{amount}'. Provide a decimal string like '25.00'."

        if amount_d <= 0:
            return "Error: Amount must be positive."

        try:
            result = self.client.payments.send(
                wallet_id=self.wallet_id,
                to=to,
                amount=amount_d,
                token=token,
                memo=purpose or None,
            )
        except ValueError as exc:
            return f"Error: {exc}"
        except Exception as exc:
            return f"Payment failed: {exc}"

        if result.success:
            parts = [
                f"Payment successful.",
                f"  TX ID: {result.tx_id}",
                f"  Amount: {result.amount} {token}",
                f"  To: {to}",
                f"  Status: {result.status.value}",
            ]
            if result.tx_hash:
                parts.append(f"  TX Hash: {result.tx_hash}")
            if hasattr(result, "group_remaining"):
                parts.append(f"  Group budget remaining: ${result.group_remaining}")
            return "\n".join(parts)

        reason = result.message or "Unknown reason"
        return f"Payment rejected: {reason} (Status: {result.status.value})"


class SardisCheckBalanceTool(BaseTool):
    """Check wallet balance, spending limits, and remaining budget."""

    name: str = "sardis_check_balance"
    description: str = (
        "Check wallet balance including available funds, spending limits, "
        "and remaining budget. Useful before making payments."
    )
    args_schema: Type[BaseModel] = SardisCheckBalanceInput

    client: Any = Field(exclude=True)
    wallet_id: str

    def _run(self, token: str = "USDC", chain: str = "base") -> str:
        try:
            info = self.client.wallets.get_balance(
                self.wallet_id,
                chain=chain,
                token=token,
            )
        except ValueError as exc:
            return f"Error: {exc}"
        except Exception as exc:
            return f"Balance check failed: {exc}"

        return (
            f"Wallet: {info.wallet_id}\n"
            f"  Balance: {info.balance} {info.currency}\n"
            f"  Spent total: {info.spent_total}\n"
            f"  Limit per tx: {info.limit_per_tx}\n"
            f"  Total limit: {info.limit_total}\n"
            f"  Remaining: {info.remaining}"
        )


class SardisCheckPolicyTool(BaseTool):
    """Validate a hypothetical payment against the wallet's policy without executing it.

    Use this to pre-check whether a payment would be approved before actually
    sending funds.
    """

    name: str = "sardis_check_policy"
    description: str = (
        "Validate a payment against spending policy without executing it. "
        "Returns whether the payment would be approved and why."
    )
    args_schema: Type[BaseModel] = SardisCheckPolicyInput

    client: Any = Field(exclude=True)
    wallet_id: str

    def _run(
        self,
        amount: str,
        to: str = "",
        token: str = "USDC",
        purpose: str = "",
    ) -> str:
        try:
            amount_d = Decimal(amount)
        except InvalidOperation:
            return f"Error: Invalid amount '{amount}'."

        try:
            wallet = self.client.wallets.get(self.wallet_id)
        except ValueError as exc:
            return f"Error: {exc}"

        # Use the wallet's built-in policy check
        from sardis import Policy

        policy = getattr(wallet, "default_policy", None) or Policy()
        result = policy.check(
            amount=amount_d,
            wallet=wallet,
            destination=to or None,
            token=token,
            purpose=purpose or None,
        )

        lines = [
            f"Policy check for {amount} {token} -> {to or '(any)'}:",
            f"  Approved: {result.approved}",
        ]
        if result.reason:
            lines.append(f"  Reason: {result.reason}")
        if result.requires_approval:
            lines.append(f"  Requires human approval: Yes")
            if result.approval_reason:
                lines.append(f"  Approval reason: {result.approval_reason}")
        if result.checks_passed:
            lines.append(f"  Checks passed: {', '.join(result.checks_passed)}")
        if result.checks_failed:
            lines.append(f"  Checks failed: {', '.join(result.checks_failed)}")
        return "\n".join(lines)


class SardisSetPolicyTool(BaseTool):
    """Set a spending policy from a natural language description.

    Creates a new wallet with the parsed policy applied and updates the
    tool's wallet reference.  The old wallet balance is preserved.
    """

    name: str = "sardis_set_policy"
    description: str = (
        "Set a spending policy using natural language. "
        "Examples: 'Max $100 per transaction', 'Max $500/day', "
        "'Daily limit $1000, max $200 per tx'. "
        "Creates a new wallet with the policy applied."
    )
    args_schema: Type[BaseModel] = SardisSetPolicyInput

    client: Any = Field(exclude=True)
    wallet_id: str

    def _run(
        self,
        policy: str,
        chain: str = "base",
        token: str = "USDC",
    ) -> str:
        if not policy.strip():
            return "Error: Policy description cannot be empty."

        try:
            old_wallet = self.client.wallets.get(self.wallet_id)
            old_balance = float(old_wallet.balance)
        except (ValueError, AttributeError):
            old_balance = 1000.0

        try:
            new_wallet = self.client.wallets.create(
                name=f"policy-wallet",
                chain=chain,
                token=token,
                policy=policy,
                initial_balance=old_balance,
            )
        except Exception as exc:
            return f"Failed to set policy: {exc}"

        self.wallet_id = new_wallet.wallet_id

        return (
            f"Policy applied successfully.\n"
            f"  Policy: {policy}\n"
            f"  New wallet: {new_wallet.wallet_id}\n"
            f"  Balance: {new_wallet.balance} {token}\n"
            f"  Limit per tx: {new_wallet.limit_per_tx}\n"
            f"  Total limit: {new_wallet.limit_total}"
        )


class SardisGroupBudgetTool(BaseTool):
    """Check the shared group budget status including spending across all agents."""

    name: str = "sardis_group_budget"
    description: str = (
        "Check group budget status including daily/monthly limits, "
        "current spending, and remaining budget across all agents in the group."
    )
    args_schema: Type[BaseModel] = SardisGroupBudgetInput

    client: Any = Field(exclude=True)

    def _run(self, group_id: str) -> str:
        try:
            info = self.client.groups.get(group_id)
            spending = self.client.groups.get_spending(group_id)
        except ValueError as exc:
            return f"Error: {exc}"
        except Exception as exc:
            return f"Group budget check failed: {exc}"

        budget = spending.get("budget", {}) if isinstance(spending, dict) else {}
        spend_info = spending.get("spending", {}) if isinstance(spending, dict) else {}
        daily_remaining = spending.get("daily_remaining", "n/a") if isinstance(spending, dict) else "n/a"
        agent_count = spending.get("agent_count", 0) if isinstance(spending, dict) else 0
        tx_count = spending.get("tx_count_daily", 0) if isinstance(spending, dict) else 0

        return (
            f"Group: {info.name}\n"
            f"  Group ID: {group_id}\n"
            f"  Agents: {agent_count}\n"
            f"  Budget (per tx): ${budget.get('per_transaction', 'n/a')}\n"
            f"  Budget (daily): ${budget.get('daily', 'n/a')}\n"
            f"  Budget (monthly): ${budget.get('monthly', 'n/a')}\n"
            f"  Spent today: ${spend_info.get('daily', '0')}\n"
            f"  Daily remaining: ${daily_remaining}\n"
            f"  Transactions today: {tx_count}"
        )


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def create_sardis_tools(
    client: SardisClient,
    wallet_id: str,
    *,
    group_id: Optional[str] = None,
    read_only: bool = False,
) -> list[BaseTool]:
    """Create a set of Sardis tools for a CrewAI agent.

    Args:
        client: Initialized SardisClient instance.
        wallet_id: Wallet ID the tools should operate on.
        group_id: Optional group ID for group budget checking.
        read_only: If True, only include read-only tools (balance, policy
            check, group budget). Useful for audit agents.

    Returns:
        List of configured BaseTool instances ready for CrewAI agents.
    """
    read_tools: list[BaseTool] = [
        SardisCheckBalanceTool(client=client, wallet_id=wallet_id),
        SardisCheckPolicyTool(client=client, wallet_id=wallet_id),
    ]

    if group_id:
        read_tools.append(SardisGroupBudgetTool(client=client))

    if read_only:
        return read_tools

    write_tools: list[BaseTool] = [
        SardisPayTool(client=client, wallet_id=wallet_id),
        SardisSetPolicyTool(client=client, wallet_id=wallet_id),
    ]

    return write_tools + read_tools
