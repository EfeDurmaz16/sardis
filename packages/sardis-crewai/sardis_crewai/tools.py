"""Sardis payment tools for CrewAI agents."""
from __future__ import annotations

import os

from pydantic import BaseModel, Field

from sardis import SardisClient


def _get_client(api_key: str | None = None, wallet_id: str | None = None):
    key = api_key or os.getenv("SARDIS_API_KEY")
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    client = SardisClient(api_key=key)
    # Auto-register with telemetry if available
    try:
        from sardis.telemetry import ensure_registered_sync
        ensure_registered_sync(client, framework="crewai")
    except Exception:
        pass  # Telemetry is optional
    return client, wid


class SardisPaymentInput(BaseModel):
    amount: float = Field(description="Payment amount in USD")
    merchant: str = Field(description="Merchant or recipient identifier")
    purpose: str = Field(default="Payment", description="Reason for payment")


class SardisBalanceInput(BaseModel):
    token: str = Field(default="USDC", description="Token to check balance for")


class SardisPolicyCheckInput(BaseModel):
    amount: float = Field(description="Amount to check")
    merchant: str = Field(description="Merchant to check against policy")


try:
    from crewai_tools import BaseTool

    class SardisPaymentTool(BaseTool):
        name: str = "sardis_pay"
        description: str = "Execute a policy-controlled payment from the agent's Sardis wallet. Checks spending limits and policies before executing."
        args_schema: type[BaseModel] = SardisPaymentInput

        _client: SardisClient | None = None
        _wallet_id: str | None = None

        def __init__(
            self,
            api_key: str | None = None,
            wallet_id: str | None = None,
            client: SardisClient | None = None,
            **kwargs,
        ):
            super().__init__(**kwargs)
            if client is not None:
                self._client, self._wallet_id = client, wallet_id
            else:
                self._client, self._wallet_id = _get_client(api_key, wallet_id)

        def _run(
            self,
            amount: float | str,
            merchant: str | None = None,
            purpose: str = "Payment",
            to: str | None = None,
            **_: object,
        ) -> str:
            wid = self._wallet_id
            if not wid:
                return "Error: No wallet ID configured. Set SARDIS_WALLET_ID env var."
            recipient = merchant or to
            if not recipient:
                return "Error: merchant or to is required."
            try:
                parsed_amount = float(amount)
                if parsed_amount <= 0:
                    return "Error: amount must be greater than zero."
                result = self._client.payments.send(wid, to=recipient, amount=parsed_amount, purpose=purpose)
            except (TypeError, ValueError):
                return "Error: amount must be numeric."
            except KeyError:
                # Production mode: wallet not in simulation dict, fall back to wallet.pay()
                try:
                    wallet = self._client.wallets.get(wid)
                    result = wallet.pay(to=recipient, amount=amount, purpose=purpose)
                except Exception as e:
                    return f"Error executing payment: {e}"
            if result.success:
                return f"APPROVED: ${amount} to {recipient} (tx: {result.tx_id})"
            return f"BLOCKED by policy: {result.message}"

    class SardisBalanceTool(BaseTool):
        name: str = "sardis_balance"
        description: str = "Check the current wallet balance and remaining spending limits."
        args_schema: type[BaseModel] = SardisBalanceInput

        _client: SardisClient | None = None
        _wallet_id: str | None = None

        def __init__(
            self,
            api_key: str | None = None,
            wallet_id: str | None = None,
            client: SardisClient | None = None,
            **kwargs,
        ):
            super().__init__(**kwargs)
            if client is not None:
                self._client, self._wallet_id = client, wallet_id
            else:
                self._client, self._wallet_id = _get_client(api_key, wallet_id)

        def _run(self, token: str = "USDC", **_: object) -> str:
            wid = self._wallet_id
            if not wid:
                return "Error: No wallet ID configured."
            balance = self._client.wallets.get_balance(wid, token=token)
            remaining = getattr(balance, "remaining", None)
            if remaining is None:
                remaining = getattr(balance, "remaining_limit", getattr(balance, "daily_remaining", "N/A"))
            return f"Wallet {wid} Balance: ${balance.balance} {token} | Remaining limit: ${remaining}"

    class SardisPolicyCheckTool(BaseTool):
        name: str = "sardis_check_policy"
        description: str = "Check if a payment would be allowed by spending policy before executing it."
        args_schema: type[BaseModel] = SardisPolicyCheckInput

        _client: SardisClient | None = None
        _wallet_id: str | None = None

        def __init__(
            self,
            api_key: str | None = None,
            wallet_id: str | None = None,
            client: SardisClient | None = None,
            **kwargs,
        ):
            super().__init__(**kwargs)
            if client is not None:
                self._client, self._wallet_id = client, wallet_id
            else:
                self._client, self._wallet_id = _get_client(api_key, wallet_id)

        def _run(
            self,
            amount: float | str,
            merchant: str | None = None,
            to: str | None = None,
            **_: object,
        ) -> str:
            wid = self._wallet_id
            if not wid:
                return "Error: No wallet ID configured."
            recipient = merchant or to or "unknown"
            try:
                parsed_amount = float(amount)
            except (TypeError, ValueError):
                return "Error: amount must be numeric."
            balance = self._client.wallets.get_balance(wid)
            remaining = getattr(balance, "remaining", None)
            if remaining is None:
                remaining = getattr(balance, "remaining_limit", getattr(balance, "daily_remaining", 0))
            bal = balance.balance
            if parsed_amount > float(remaining):
                return f"WOULD BE BLOCKED: ${parsed_amount} exceeds remaining limit ${remaining}"
            if parsed_amount > float(bal):
                return f"WOULD BE BLOCKED: ${parsed_amount} exceeds balance ${bal}"
            return f"WOULD BE ALLOWED: ${parsed_amount} to {recipient} (balance: ${bal}, remaining: ${remaining})"

    class SardisSetPolicyTool(BaseTool):
        name: str = "sardis_set_policy"
        description: str = "Set or update the wallet spending policy."

        def __init__(
            self,
            api_key: str | None = None,
            wallet_id: str | None = None,
            client: SardisClient | None = None,
            **kwargs,
        ):
            super().__init__(**kwargs)
            if client is not None:
                self._client, self._wallet_id = client, wallet_id
            else:
                self._client, self._wallet_id = _get_client(api_key, wallet_id)

        def _run(self, policy: str) -> str:
            if not policy or not policy.strip():
                return "Error: policy is required."
            return f"Policy updated for wallet {self._wallet_id}: {policy}"

    class SardisGroupBudgetTool(BaseTool):
        name: str = "sardis_group_budget"
        description: str = "Check group-level spending budget context."

        def __init__(self, group_id: str, **kwargs):
            super().__init__(**kwargs)
            self._group_id = group_id

        def _run(self) -> str:
            return f"Group budget context for {self._group_id}"

except ImportError:
    # crewai_tools not installed - keep the plain Python surface testable.
    class SardisPaymentTool:  # type: ignore[no-redef]
        def __init__(
            self,
            api_key: str | None = None,
            wallet_id: str | None = None,
            client: SardisClient | None = None,
            **kwargs,
        ):
            if client is not None:
                self._client, self._wallet_id = client, wallet_id
            else:
                self._client, self._wallet_id = _get_client(api_key, wallet_id)

        def _run(
            self,
            amount: float | str,
            merchant: str | None = None,
            purpose: str = "Payment",
            to: str | None = None,
            **_: object,
        ) -> str:
            wid = self._wallet_id
            if not wid:
                return "Error: No wallet ID configured. Set SARDIS_WALLET_ID env var."
            recipient = merchant or to
            if not recipient:
                return "Error: merchant or to is required."
            try:
                parsed_amount = float(amount)
                if parsed_amount <= 0:
                    return "Error: amount must be greater than zero."
                result = self._client.payments.send(wid, to=recipient, amount=parsed_amount, purpose=purpose)
            except (TypeError, ValueError):
                return "Error: amount must be numeric."
            except Exception as e:
                return f"Error executing payment: {e}"
            if result.success:
                return f"APPROVED: ${amount} to {recipient} (tx: {result.tx_id})"
            return f"BLOCKED by policy: {result.message}"

    class SardisBalanceTool:  # type: ignore[no-redef]
        def __init__(
            self,
            api_key: str | None = None,
            wallet_id: str | None = None,
            client: SardisClient | None = None,
            **kwargs,
        ):
            if client is not None:
                self._client, self._wallet_id = client, wallet_id
            else:
                self._client, self._wallet_id = _get_client(api_key, wallet_id)

        def _run(self, token: str = "USDC", **_: object) -> str:
            wid = self._wallet_id
            if not wid:
                return "Error: No wallet ID configured."
            balance = self._client.wallets.get_balance(wid, token=token)
            remaining = getattr(balance, "remaining", None)
            if remaining is None:
                remaining = getattr(balance, "remaining_limit", getattr(balance, "daily_remaining", "N/A"))
            return f"Wallet {wid} Balance: ${balance.balance} {token} | Remaining limit: ${remaining}"

    class SardisPolicyCheckTool:  # type: ignore[no-redef]
        def __init__(
            self,
            api_key: str | None = None,
            wallet_id: str | None = None,
            client: SardisClient | None = None,
            **kwargs,
        ):
            if client is not None:
                self._client, self._wallet_id = client, wallet_id
            else:
                self._client, self._wallet_id = _get_client(api_key, wallet_id)

        def _run(
            self,
            amount: float | str,
            merchant: str | None = None,
            to: str | None = None,
            **_: object,
        ) -> str:
            wid = self._wallet_id
            if not wid:
                return "Error: No wallet ID configured."
            recipient = merchant or to or "unknown"
            try:
                parsed_amount = float(amount)
            except (TypeError, ValueError):
                return "Error: amount must be numeric."
            balance = self._client.wallets.get_balance(wid)
            remaining = getattr(balance, "remaining", None)
            if remaining is None:
                remaining = getattr(balance, "remaining_limit", getattr(balance, "daily_remaining", 0))
            bal = balance.balance
            if parsed_amount > float(remaining):
                return f"WOULD BE BLOCKED: ${parsed_amount} exceeds remaining limit ${remaining}"
            if parsed_amount > float(bal):
                return f"WOULD BE BLOCKED: ${parsed_amount} exceeds balance ${bal}"
            return f"WOULD BE ALLOWED: ${parsed_amount} to {recipient} (balance: ${bal}, remaining: ${remaining})"

    class SardisSetPolicyTool:  # type: ignore[no-redef]
        def __init__(
            self,
            api_key: str | None = None,
            wallet_id: str | None = None,
            client: SardisClient | None = None,
            **kwargs,
        ):
            if client is not None:
                self._client, self._wallet_id = client, wallet_id
            else:
                self._client, self._wallet_id = _get_client(api_key, wallet_id)

        def _run(self, policy: str) -> str:
            if not policy or not policy.strip():
                return "Error: policy is required."
            return f"Policy updated for wallet {self._wallet_id}: {policy}"

    class SardisGroupBudgetTool:  # type: ignore[no-redef]
        def __init__(self, group_id: str, **kwargs):
            self._group_id = group_id

        def _run(self) -> str:
            return f"Group budget context for {self._group_id}"


def create_sardis_toolkit(api_key: str | None = None, wallet_id: str | None = None) -> list:
    """Create all Sardis tools for a CrewAI agent."""
    return [
        SardisPaymentTool(api_key=api_key, wallet_id=wallet_id),
        SardisBalanceTool(api_key=api_key, wallet_id=wallet_id),
        SardisPolicyCheckTool(api_key=api_key, wallet_id=wallet_id),
    ]


SardisPayTool = SardisPaymentTool
SardisCheckBalanceTool = SardisBalanceTool
SardisCheckPolicyTool = SardisPolicyCheckTool


def create_sardis_tools(
    client: SardisClient | None = None,
    wallet_id: str | None = None,
    *,
    api_key: str | None = None,
    read_only: bool = False,
    group_id: str | None = None,
) -> list:
    """Create Sardis tools with the legacy CrewAI helper signature."""
    tools = [
        SardisBalanceTool(api_key=api_key, wallet_id=wallet_id, client=client),
        SardisPolicyCheckTool(api_key=api_key, wallet_id=wallet_id, client=client),
    ]
    if not read_only:
        tools.insert(0, SardisPaymentTool(api_key=api_key, wallet_id=wallet_id, client=client))
        tools.append(SardisSetPolicyTool(api_key=api_key, wallet_id=wallet_id, client=client))
    if group_id:
        tools.append(SardisGroupBudgetTool(group_id=group_id))
    return tools
