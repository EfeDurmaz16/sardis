"""Sardis payment blocks for AutoGPT."""
from __future__ import annotations

import os
from typing import Any, Iterator, Optional

from pydantic import BaseModel, Field
from sardis import SardisClient


_cached_clients: dict[str, SardisClient] = {}


def _get_client(api_key: Optional[str] = None, wallet_id: Optional[str] = None):
    key = api_key or os.getenv("SARDIS_API_KEY") or ""
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    if key not in _cached_clients:
        _cached_clients[key] = SardisClient(api_key=key or None)
    return _cached_clients[key], wid


# --- Block Schemas ---

class SardisPayBlockInput(BaseModel):
    api_key: str = Field(default="", description="Sardis API key (or use SARDIS_API_KEY env var)")
    wallet_id: str = Field(default="", description="Wallet ID (or use SARDIS_WALLET_ID env var)")
    amount: float = Field(description="Payment amount in USD")
    merchant: str = Field(description="Merchant or recipient identifier")
    purpose: str = Field(default="Payment", description="Reason for payment")
    token: str = Field(default="USDC", description="Token to use for payment")


class SardisPayBlockOutput(BaseModel):
    status: str = Field(description="APPROVED or BLOCKED")
    tx_id: str = Field(default="", description="Transaction ID if approved")
    message: str = Field(default="", description="Status message")
    amount: float = Field(default=0, description="Payment amount")
    merchant: str = Field(default="", description="Merchant name")


class SardisBalanceBlockInput(BaseModel):
    api_key: str = Field(default="", description="Sardis API key")
    wallet_id: str = Field(default="", description="Wallet ID")
    token: str = Field(default="USDC", description="Token to check")


class SardisBalanceBlockOutput(BaseModel):
    balance: float = Field(default=0, description="Current balance")
    remaining: float = Field(default=0, description="Remaining spending limit")
    token: str = Field(default="USDC", description="Token type")


class SardisPolicyCheckBlockInput(BaseModel):
    api_key: str = Field(default="", description="Sardis API key")
    wallet_id: str = Field(default="", description="Wallet ID")
    amount: float = Field(description="Amount to check")
    merchant: str = Field(description="Merchant to check")


class SardisPolicyCheckBlockOutput(BaseModel):
    allowed: bool = Field(description="Whether payment would be allowed")
    reason: str = Field(default="", description="Explanation")


# --- Block implementations ---

class SardisPayBlock:
    """AutoGPT block for executing Sardis payments."""

    id = "sardis-pay-block"
    name = "Sardis Pay"
    description = "Execute a policy-controlled payment from a Sardis wallet"
    input_schema = SardisPayBlockInput
    output_schema = SardisPayBlockOutput

    @staticmethod
    def run(input_data: SardisPayBlockInput) -> Iterator[SardisPayBlockOutput]:
        client, wallet_id = _get_client(
            api_key=input_data.api_key or None,
            wallet_id=input_data.wallet_id or None,
        )
        if not wallet_id:
            yield SardisPayBlockOutput(
                status="ERROR",
                message="No wallet ID configured",
                amount=input_data.amount,
                merchant=input_data.merchant,
            )
            return

        result = client.payments.send(
            wallet_id,
            to=input_data.merchant,
            amount=input_data.amount,
            purpose=input_data.purpose,
            token=input_data.token,
        )
        yield SardisPayBlockOutput(
            status="APPROVED" if result.success else "BLOCKED",
            tx_id=result.tx_id,
            message=result.message or "",
            amount=float(result.amount),
            merchant=input_data.merchant,
        )


class SardisBalanceBlock:
    """AutoGPT block for checking Sardis wallet balance."""

    id = "sardis-balance-block"
    name = "Sardis Balance"
    description = "Check the current balance and spending limits of a Sardis wallet"
    input_schema = SardisBalanceBlockInput
    output_schema = SardisBalanceBlockOutput

    @staticmethod
    def run(input_data: SardisBalanceBlockInput) -> Iterator[SardisBalanceBlockOutput]:
        client, wallet_id = _get_client(
            api_key=input_data.api_key or None,
            wallet_id=input_data.wallet_id or None,
        )
        if not wallet_id:
            yield SardisBalanceBlockOutput(balance=0, remaining=0, token=input_data.token)
            return

        balance = client.wallets.get_balance(wallet_id, token=input_data.token)
        yield SardisBalanceBlockOutput(
            balance=float(balance.balance),
            remaining=float(balance.remaining),
            token=input_data.token,
        )


class SardisPolicyCheckBlock:
    """AutoGPT block for checking if a payment would pass policy."""

    id = "sardis-policy-check-block"
    name = "Sardis Policy Check"
    description = "Check if a payment would be allowed by spending policy before executing"
    input_schema = SardisPolicyCheckBlockInput
    output_schema = SardisPolicyCheckBlockOutput

    @staticmethod
    def run(input_data: SardisPolicyCheckBlockInput) -> Iterator[SardisPolicyCheckBlockOutput]:
        client, wallet_id = _get_client(
            api_key=input_data.api_key or None,
            wallet_id=input_data.wallet_id or None,
        )
        if not wallet_id:
            yield SardisPolicyCheckBlockOutput(allowed=False, reason="No wallet ID configured")
            return

        balance = client.wallets.get_balance(wallet_id)
        if input_data.amount > balance.remaining:
            yield SardisPolicyCheckBlockOutput(
                allowed=False,
                reason=f"Amount ${input_data.amount} exceeds remaining limit ${balance.remaining}",
            )
        elif input_data.amount > balance.balance:
            yield SardisPolicyCheckBlockOutput(
                allowed=False,
                reason=f"Amount ${input_data.amount} exceeds balance ${balance.balance}",
            )
        else:
            yield SardisPolicyCheckBlockOutput(
                allowed=True,
                reason=f"Payment of ${input_data.amount} to {input_data.merchant} would be allowed",
            )


# Registry of all blocks
BLOCKS = [SardisPayBlock, SardisBalanceBlock, SardisPolicyCheckBlock]
