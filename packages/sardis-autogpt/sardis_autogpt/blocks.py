"""Sardis payment blocks for AutoGPT."""
from __future__ import annotations

import os
from collections.abc import Iterator

from pydantic import BaseModel, Field

from sardis import SardisClient

_cached_clients: dict[str, SardisClient] = {}


def _get_client(api_key: str | None = None, wallet_id: str | None = None):
    key = api_key or os.getenv("SARDIS_API_KEY") or ""
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    if key not in _cached_clients:
        _cached_clients[key] = SardisClient(api_key=key or None)
    return _cached_clients[key], wid


def _execute_payment(client: SardisClient, wallet_id: str, merchant: str,
                     amount: float, purpose: str, token: str):
    """Execute payment with fallback for production mode compatibility."""
    try:
        return client.payments.send(
            wallet_id,
            to=merchant,
            amount=amount,
            purpose=purpose,
            token=token,
        )
    except (ValueError, KeyError):
        # Production mode: wallet not in simulation dict, fall back to wallet.pay()
        wallet = client.wallets.get(wallet_id)
        return wallet.pay(to=merchant, amount=amount, purpose=purpose)


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

        try:
            result = _execute_payment(
                client, wallet_id, input_data.merchant,
                input_data.amount, input_data.purpose, input_data.token,
            )
        except Exception as e:
            yield SardisPayBlockOutput(
                status="ERROR",
                message=str(e),
                amount=input_data.amount,
                merchant=input_data.merchant,
            )
            return

        yield SardisPayBlockOutput(
            status="APPROVED" if result.success else "BLOCKED",
            tx_id=getattr(result, "tx_id", ""),
            message=getattr(result, "message", "") or "",
            amount=float(getattr(result, "amount", input_data.amount)),
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
        remaining = getattr(balance, "remaining", None)
        if remaining is None:
            remaining = getattr(balance, "remaining_limit", getattr(balance, "daily_remaining", 0))
        yield SardisBalanceBlockOutput(
            balance=float(balance.balance),
            remaining=float(remaining),
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
        remaining = getattr(balance, "remaining", None)
        if remaining is None:
            remaining = getattr(balance, "remaining_limit", getattr(balance, "daily_remaining", 0))
        if input_data.amount > float(remaining):
            yield SardisPolicyCheckBlockOutput(
                allowed=False,
                reason=f"Amount ${input_data.amount} exceeds remaining limit ${remaining}",
            )
        elif input_data.amount > float(balance.balance):
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
