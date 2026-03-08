"""Sardis payment tools for CrewAI.

These tools enable CrewAI agents to make policy-controlled payments
through Sardis non-custodial MPC wallets.

Installation:
    pip install sardis-crewai

Or install the tools directly:
    pip install sardis crewai-tools
"""

from __future__ import annotations

import os
from typing import Optional, Type

from crewai_tools import BaseTool
from pydantic import BaseModel, Field


class SardisPaymentToolInput(BaseModel):
    """Input for SardisPaymentTool."""

    amount: float = Field(description="Payment amount in USD")
    merchant: str = Field(description="Merchant or recipient identifier")
    purpose: str = Field(default="Payment", description="Reason for payment")


class SardisPaymentTool(BaseTool):
    """Execute policy-controlled payments from a Sardis wallet.

    This tool enables AI agents to make real financial transactions
    with spending policy guardrails. Every payment is checked against
    configurable policies before execution.

    Attributes:
        api_key: Sardis API key. Defaults to SARDIS_API_KEY env var.
        wallet_id: Wallet ID to use. Defaults to SARDIS_WALLET_ID env var.

    Example:
        ```python
        from crewai_tools import SardisPaymentTool

        tool = SardisPaymentTool()
        result = tool.run(amount=25.0, merchant="openai", purpose="API credits")
        ```
    """

    name: str = "sardis_pay"
    description: str = (
        "Execute a policy-controlled payment from a Sardis wallet. "
        "Checks spending limits and policies before executing. "
        "Supports USDC payments on Base, Polygon, Ethereum, Arbitrum, and Optimism."
    )
    args_schema: Type[BaseModel] = SardisPaymentToolInput

    api_key: Optional[str] = None
    wallet_id: Optional[str] = None

    def __init__(self, api_key: Optional[str] = None, wallet_id: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("SARDIS_API_KEY")
        self.wallet_id = wallet_id or os.getenv("SARDIS_WALLET_ID")

    def _run(self, amount: float, merchant: str, purpose: str = "Payment") -> str:
        try:
            from sardis import SardisClient
        except ImportError:
            return "Error: sardis package required. Install with: pip install sardis"

        if not self.wallet_id:
            return "Error: No wallet ID configured. Set SARDIS_WALLET_ID env var."

        client = SardisClient(api_key=self.api_key)
        result = client.payments.send(
            self.wallet_id, to=merchant, amount=amount, purpose=purpose
        )

        if result.success:
            return f"APPROVED: ${amount} to {merchant} (tx: {result.tx_id})"
        return f"BLOCKED by policy: {result.message}"
