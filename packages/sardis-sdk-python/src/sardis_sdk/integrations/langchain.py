"""
LangChain integration for Sardis SDK.

DEPRECATED: This module is a compatibility shim. Use sardis-langchain directly:
    pip install sardis-langchain

    from sardis_langchain import SardisToolkit, SardisPayTool
"""
from __future__ import annotations

import os
import warnings
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

warnings.warn(
    "sardis_sdk.integrations.langchain is deprecated. "
    "Use sardis-langchain package directly: pip install sardis-langchain\n"
    "  from sardis_langchain import SardisToolkit",
    DeprecationWarning,
    stacklevel=2,
)

try:
    from sardis_langchain import SardisToolkit  # type: ignore
except ImportError:  # pragma: no cover - optional dependency bridge
    SardisToolkit = None  # type: ignore[assignment]


class PayInput(BaseModel):
    """Legacy payment input schema."""

    amount: float = Field(description="Payment amount")
    merchant: str = Field(description="Merchant identifier")
    merchant_address: Optional[str] = Field(default=None, description="Recipient wallet address")
    purpose: str = Field(default="Service payment", description="Reason for payment")
    token: str = Field(default="USDC", description="Token symbol")


class PolicyCheckInput(BaseModel):
    """Legacy policy-check input schema."""

    merchant: str = Field(description="Merchant identifier")
    amount: float = Field(description="Amount to validate")
    purpose: Optional[str] = Field(default=None, description="Optional purpose")


class BalanceCheckInput(BaseModel):
    """Legacy balance-check input schema."""

    token: str = Field(default="USDC", description="Token symbol")
    chain: str = Field(default="base_sepolia", description="Chain identifier")


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


class _BaseCompatibilityTool:
    name: str = ""
    description: str = ""
    args_schema: type[BaseModel] = BaseModel

    def __init__(
        self,
        *,
        client: Any = None,
        wallet_id: str | None = None,
        agent_id: str | None = None,
        chain: str = "base_sepolia",
        **_: Any,
    ) -> None:
        self.client = client
        self.wallet_id = wallet_id or os.getenv("SARDIS_WALLET_ID", "")
        self.agent_id = agent_id or os.getenv("SARDIS_AGENT_ID", "")
        self.chain = chain


class SardisTool(_BaseCompatibilityTool):
    """Legacy payment tool compatibility class."""

    name = "sardis_pay"
    description = "Execute policy-enforced payment from Sardis wallet."
    args_schema = PayInput

    async def _arun(
        self,
        amount: float,
        merchant: str,
        merchant_address: str | None = None,
        purpose: str = "Service payment",
        token: str = "USDC",
    ) -> str:
        if self.client is None:
            return "Error: Sardis client not initialized"
        if not self.wallet_id:
            return "Error: wallet ID is required"
        if amount <= 0:
            return "Error: amount must be positive"

        destination = merchant_address or merchant
        try:
            result = await _maybe_await(
                self.client.wallets.transfer(
                    self.wallet_id,
                    destination=destination,
                    amount=Decimal(str(amount)),
                    token=token,
                    chain=self.chain,
                    memo=purpose,
                )
            )
            tx_hash = getattr(result, "tx_hash", "")
            chain = getattr(result, "chain", self.chain)
            return f"APPROVED: Payment ${amount:g} to {merchant} submitted on {chain} (tx: {tx_hash})"
        except Exception as exc:
            message = str(exc)
            if any(marker in message.lower() for marker in ("blocked", "policy", "limit", "deny")):
                return f"BLOCKED: PREVENTED by policy - {message}"
            return f"Error: {message}"


class SardisPolicyCheckTool(_BaseCompatibilityTool):
    """Legacy policy-check tool compatibility class."""

    name = "sardis_check_policy"
    description = "Check whether a payment would pass policy."
    args_schema = PolicyCheckInput

    async def _arun(self, merchant: str, amount: float, purpose: str | None = None) -> str:
        if self.client is None:
            return "Error: Sardis client not initialized"
        if not self.wallet_id:
            return "Error: wallet ID is required"

        try:
            wallet = await _maybe_await(self.client.wallets.get(self.wallet_id))
            limit_raw = getattr(wallet, "limit_per_tx", None)
            active = bool(getattr(wallet, "is_active", True))
            limit = Decimal(str(limit_raw)) if limit_raw not in (None, "") else None
            amount_d = Decimal(str(amount))

            if not active:
                return f"WOULD BE BLOCKED (FAIL): wallet disabled for {merchant}"
            if limit is not None and amount_d > limit:
                return (
                    f"WOULD BE BLOCKED (FAIL): amount ${amount:g} exceeds per-tx limit "
                    f"${limit}"
                )
            return f"WOULD BE ALLOWED (PASS): ${amount:g} to {merchant}"
        except Exception as exc:
            return f"Error: {exc}"


class SardisBalanceCheckTool(_BaseCompatibilityTool):
    """Legacy balance tool compatibility class."""

    name = "sardis_check_balance"
    description = "Check current wallet balance."
    args_schema = BalanceCheckInput

    async def _arun(self, token: str = "USDC", chain: str = "base_sepolia") -> str:
        if self.client is None:
            return "Error: Sardis client not initialized"
        if not self.wallet_id:
            return "Error: wallet ID is required"

        try:
            balance = await _maybe_await(
                self.client.wallets.get_balance(self.wallet_id, token=token, chain=chain)
            )
            amount = getattr(balance, "balance", "0")
            return (
                "Wallet Balance\n"
                f"wallet={getattr(balance, 'wallet_id', self.wallet_id)}\n"
                f"token={getattr(balance, 'token', token)}\n"
                f"chain={getattr(balance, 'chain', chain)}\n"
                f"balance={amount}"
            )
        except Exception as exc:
            return f"Error: {exc}"


# Legacy aliases expected by historical integrations/tests
SardisPayTool = SardisTool
SardisCheckPolicyTool = SardisPolicyCheckTool
SardisCheckBalanceTool = SardisBalanceCheckTool


def create_sardis_tools(
    client: Any,
    wallet_id: str,
    *,
    agent_id: str | None = None,
    chain: str = "base_sepolia",
) -> list[_BaseCompatibilityTool]:
    """Legacy tool factory returning payment/policy/balance tools only."""
    common = {"client": client, "wallet_id": wallet_id, "agent_id": agent_id, "chain": chain}
    return [
        SardisTool(**common),
        SardisPolicyCheckTool(**common),
        SardisBalanceCheckTool(**common),
    ]


__all__ = [
    "BalanceCheckInput",
    "PayInput",
    "PolicyCheckInput",
    "SardisBalanceCheckTool",
    "SardisCheckBalanceTool",
    "SardisCheckPolicyTool",
    "SardisPayTool",
    "SardisPolicyCheckTool",
    "SardisTool",
    "SardisToolkit",
    "create_sardis_tools",
]
