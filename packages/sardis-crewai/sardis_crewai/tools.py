"""Sardis payment tools for CrewAI agents."""
from __future__ import annotations

import os

from pydantic import BaseModel, Field

from sardis import SardisClient


def _get_client(api_key: str | None = None, wallet_id: str | None = None):
    key = api_key or os.getenv("SARDIS_API_KEY")
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    client = SardisClient(api_key=key)
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

        def __init__(self, api_key: str | None = None, wallet_id: str | None = None, **kwargs):
            super().__init__(**kwargs)
            self._client, self._wallet_id = _get_client(api_key, wallet_id)

        def _run(self, amount: float, merchant: str, purpose: str = "Payment") -> str:
            wid = self._wallet_id
            if not wid:
                return "Error: No wallet ID configured. Set SARDIS_WALLET_ID env var."
            result = self._client.payments.send(wid, to=merchant, amount=amount, purpose=purpose)
            if result.success:
                return f"APPROVED: ${amount} to {merchant} (tx: {result.tx_id})"
            return f"BLOCKED by policy: {result.message}"

    class SardisBalanceTool(BaseTool):
        name: str = "sardis_balance"
        description: str = "Check the current wallet balance and remaining spending limits."
        args_schema: type[BaseModel] = SardisBalanceInput

        _client: SardisClient | None = None
        _wallet_id: str | None = None

        def __init__(self, api_key: str | None = None, wallet_id: str | None = None, **kwargs):
            super().__init__(**kwargs)
            self._client, self._wallet_id = _get_client(api_key, wallet_id)

        def _run(self, token: str = "USDC") -> str:
            wid = self._wallet_id
            if not wid:
                return "Error: No wallet ID configured."
            balance = self._client.wallets.get_balance(wid, token=token)
            return f"Balance: ${balance.balance} {token} | Remaining limit: ${balance.remaining}"

    class SardisPolicyCheckTool(BaseTool):
        name: str = "sardis_check_policy"
        description: str = "Check if a payment would be allowed by spending policy before executing it."
        args_schema: type[BaseModel] = SardisPolicyCheckInput

        _client: SardisClient | None = None
        _wallet_id: str | None = None

        def __init__(self, api_key: str | None = None, wallet_id: str | None = None, **kwargs):
            super().__init__(**kwargs)
            self._client, self._wallet_id = _get_client(api_key, wallet_id)

        def _run(self, amount: float, merchant: str) -> str:
            wid = self._wallet_id
            if not wid:
                return "Error: No wallet ID configured."
            balance = self._client.wallets.get_balance(wid)
            if amount > balance.remaining:
                return f"WOULD BE BLOCKED: ${amount} exceeds remaining limit ${balance.remaining}"
            if amount > balance.balance:
                return f"WOULD BE BLOCKED: ${amount} exceeds balance ${balance.balance}"
            return f"WOULD BE ALLOWED: ${amount} to {merchant} (balance: ${balance.balance}, remaining: ${balance.remaining})"

except ImportError:
    # crewai_tools not installed - provide stubs
    class SardisPaymentTool:  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            raise ImportError("crewai_tools is required: pip install crewai-tools")

    class SardisBalanceTool:  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            raise ImportError("crewai_tools is required: pip install crewai-tools")

    class SardisPolicyCheckTool:  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            raise ImportError("crewai_tools is required: pip install crewai-tools")


def create_sardis_toolkit(api_key: str | None = None, wallet_id: str | None = None) -> list:
    """Create all Sardis tools for a CrewAI agent."""
    return [
        SardisPaymentTool(api_key=api_key, wallet_id=wallet_id),
        SardisBalanceTool(api_key=api_key, wallet_id=wallet_id),
        SardisPolicyCheckTool(api_key=api_key, wallet_id=wallet_id),
    ]
