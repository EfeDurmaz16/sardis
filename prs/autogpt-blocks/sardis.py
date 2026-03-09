"""Sardis payment blocks for AutoGPT.

These blocks enable AutoGPT agents to make policy-controlled payments
through Sardis non-custodial MPC wallets.

Installation:
    pip install sardis
"""

from __future__ import annotations

import os

from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField
from pydantic import BaseModel


class SardisCredentials(BaseModel):
    api_key: str = SchemaField(
        description="Sardis API key (or set SARDIS_API_KEY env var)",
        default="",
    )
    wallet_id: str = SchemaField(
        description="Sardis wallet ID (or set SARDIS_WALLET_ID env var)",
        default="",
    )


class SardisPayBlockInput(BlockSchema):
    credentials: SardisCredentials = SchemaField(
        description="Sardis API credentials",
        default=SardisCredentials(),
    )
    amount: float = SchemaField(description="Payment amount in USD")
    merchant: str = SchemaField(description="Merchant or recipient identifier")
    purpose: str = SchemaField(
        description="Reason for payment", default="Payment"
    )
    token: str = SchemaField(
        description="Token to use (USDC, USDT, etc.)", default="USDC"
    )


class SardisPayBlockOutput(BlockSchema):
    status: str = SchemaField(description="APPROVED, BLOCKED, or ERROR")
    tx_id: str = SchemaField(description="Transaction ID if approved", default="")
    message: str = SchemaField(description="Status message", default="")
    amount: float = SchemaField(description="Payment amount", default=0)
    merchant: str = SchemaField(description="Merchant name", default="")
    error: str = SchemaField(description="Error message if failed", default="")


class SardisPayBlock(Block):
    """Execute a policy-controlled payment from a Sardis wallet.

    Every payment is checked against configurable spending policies before
    execution. Supports USDC/USDT on Base, Polygon, Ethereum, Arbitrum, Optimism.
    """

    id = "b1f2e3d4-5a6b-7c8d-9e0f-sardis-pay-01"
    input_schema = SardisPayBlockInput
    output_schema = SardisPayBlockOutput

    class Meta:
        name = "Sardis Pay"
        description = "Execute a policy-controlled payment from a Sardis wallet"
        category = BlockCategory.OUTPUT
        tags = ["payments", "fintech", "ai-agents", "sardis"]

    @staticmethod
    def run(input_data: SardisPayBlockInput, **kwargs) -> BlockOutput:
        try:
            from sardis import SardisClient
        except ImportError:
            yield "error", "sardis package required. Install with: pip install sardis"
            return

        api_key = input_data.credentials.api_key or os.getenv("SARDIS_API_KEY")
        wallet_id = input_data.credentials.wallet_id or os.getenv("SARDIS_WALLET_ID")

        if not wallet_id:
            yield "error", "No wallet ID configured. Set SARDIS_WALLET_ID env var."
            return

        client = SardisClient(api_key=api_key)
        result = client.payments.send(
            wallet_id,
            to=input_data.merchant,
            amount=input_data.amount,
            purpose=input_data.purpose,
            token=input_data.token,
        )

        yield "status", "APPROVED" if result.success else "BLOCKED"
        yield "tx_id", result.tx_id or ""
        yield "message", result.message or ""
        yield "amount", input_data.amount
        yield "merchant", input_data.merchant


class SardisBalanceBlockInput(BlockSchema):
    credentials: SardisCredentials = SchemaField(
        description="Sardis API credentials",
        default=SardisCredentials(),
    )
    token: str = SchemaField(description="Token to check", default="USDC")


class SardisBalanceBlockOutput(BlockSchema):
    balance: float = SchemaField(description="Current balance", default=0)
    remaining: float = SchemaField(description="Remaining spending limit", default=0)
    token: str = SchemaField(description="Token type", default="USDC")
    error: str = SchemaField(description="Error message if failed", default="")


class SardisBalanceBlock(Block):
    """Check the balance and spending limits of a Sardis wallet."""

    id = "b1f2e3d4-5a6b-7c8d-9e0f-sardis-bal-01"
    input_schema = SardisBalanceBlockInput
    output_schema = SardisBalanceBlockOutput

    class Meta:
        name = "Sardis Balance"
        description = "Check the balance and spending limits of a Sardis wallet"
        category = BlockCategory.OUTPUT
        tags = ["payments", "fintech", "ai-agents", "sardis"]

    @staticmethod
    def run(input_data: SardisBalanceBlockInput, **kwargs) -> BlockOutput:
        try:
            from sardis import SardisClient
        except ImportError:
            yield "error", "sardis package required. Install with: pip install sardis"
            return

        api_key = input_data.credentials.api_key or os.getenv("SARDIS_API_KEY")
        wallet_id = input_data.credentials.wallet_id or os.getenv("SARDIS_WALLET_ID")

        if not wallet_id:
            yield "error", "No wallet ID configured."
            return

        client = SardisClient(api_key=api_key)
        balance = client.wallets.get_balance(wallet_id, token=input_data.token)

        yield "balance", float(balance.balance)
        yield "remaining", float(balance.remaining)
        yield "token", input_data.token
