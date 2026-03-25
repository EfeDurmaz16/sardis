"""Sardis payment blocks for AutoGPT.

Addresses PR review feedback:
- str (not float) for all monetary amounts (IEEE 754 safety)
- Literal types for token/chain, regex validation for wallet_id/destination
- Block categories: Balance/PolicyCheck → BlockCategory.DATA
- Singleton HTTP client with connection pooling and retry
- Explicit status mapping from API responses
"""
from __future__ import annotations

import os
import re
import time
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from sardis import SardisClient

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_TOKENS = ("USDC", "USDT", "EURC", "PYUSD")
SUPPORTED_CHAINS = ("base", "ethereum", "polygon", "arbitrum", "optimism", "tempo")

_WALLET_ID_RE = re.compile(r"^wal_[a-zA-Z0-9]+$")
_HEX_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

# Token/chain literal types for schema-level validation
TokenType = Literal["USDC", "USDT", "EURC", "PYUSD"]
ChainType = Literal["base", "ethereum", "polygon", "arbitrum", "optimism", "tempo"]


# ---------------------------------------------------------------------------
# Block categories (mirrors autogpt_libs.suites.io.BlockCategory)
# We define our own enum so the package works without autogpt installed.
# ---------------------------------------------------------------------------

class BlockCategory(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    DATA = "data"
    TRANSFORM = "transform"
    LOGIC = "logic"


# ---------------------------------------------------------------------------
# Singleton client with retry
# ---------------------------------------------------------------------------

_cached_clients: dict[str, SardisClient] = {}

# Retry config
_MAX_RETRIES = 3
_INITIAL_BACKOFF_S = 0.5


def _get_client(api_key: str | None = None, wallet_id: str | None = None):
    """Return (SardisClient, wallet_id), reusing clients per API key."""
    key = api_key or os.getenv("SARDIS_API_KEY") or ""
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    if key not in _cached_clients:
        _cached_clients[key] = SardisClient(api_key=key or None)
    return _cached_clients[key], wid


def _with_retry(fn, *args, **kwargs):
    """Execute *fn* with exponential backoff on transient errors."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except (ConnectionError, TimeoutError, OSError) as exc:
            last_exc = exc
            time.sleep(_INITIAL_BACKOFF_S * (2 ** attempt))
        except Exception:
            raise
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Validators (reusable)
# ---------------------------------------------------------------------------

def _validate_wallet_id(v: str) -> str:
    """Validate wallet_id matches ``wal_<alphanum>`` pattern."""
    if v and not _WALLET_ID_RE.match(v):
        raise ValueError(
            f"Invalid wallet_id '{v}': must match pattern wal_<alphanumeric>"
        )
    return v


def _validate_hex_address(v: str) -> str:
    """Validate Ethereum-style hex address (0x + 40 hex chars)."""
    if v and not _HEX_ADDRESS_RE.match(v):
        raise ValueError(
            f"Invalid address '{v}': must be 0x followed by 40 hex characters"
        )
    return v


def _validate_amount_str(v: str) -> str:
    """Ensure amount is a valid positive decimal string."""
    if not v:
        raise ValueError("Amount is required")
    try:
        d = Decimal(v)
    except InvalidOperation:
        raise ValueError(f"Invalid amount '{v}': must be a decimal number string")
    if d <= 0:
        raise ValueError(f"Amount must be positive, got '{v}'")
    if d != d.quantize(Decimal("0.000001")):
        raise ValueError(f"Amount '{v}' has too many decimal places (max 6)")
    return v


# ---------------------------------------------------------------------------
# Status mapping
# ---------------------------------------------------------------------------

# The Sardis API returns a result object with:
#   result.status  - canonical status string (preferred)
#   result.success - boolean fallback
#
# Status values from the Sardis API:
#   "approved"  → payment succeeded, tx on-chain
#   "blocked"   → policy engine denied the payment
#   "pending"   → payment submitted, awaiting confirmation
#   "failed"    → on-chain tx failed or RPC error
#   "error"     → internal error (should not happen in production)

_STATUS_MAP: dict[str, str] = {
    "approved": "APPROVED",
    "blocked": "BLOCKED",
    "pending": "PENDING",
    "failed": "FAILED",
    "error": "ERROR",
}


def _normalize_status(result) -> str:
    """Derive block-level status from an API response object.

    Prefers ``result.status`` (explicit string), falls back to
    ``result.success`` (boolean) for backward compatibility.
    """
    raw_status = getattr(result, "status", None)
    if isinstance(raw_status, str) and raw_status.lower() in _STATUS_MAP:
        return _STATUS_MAP[raw_status.lower()]
    # Fallback: boolean success field
    success = getattr(result, "success", None)
    if success is True:
        return "APPROVED"
    if success is False:
        return "BLOCKED"
    return "ERROR"


def _normalize_response(result, input_amount: str, merchant: str) -> dict:
    """Build a normalized response dict from an API result object."""
    return {
        "status": _normalize_status(result),
        "tx_id": str(getattr(result, "tx_id", "") or ""),
        "message": str(getattr(result, "message", "") or ""),
        "amount": str(getattr(result, "amount", input_amount)),
        "merchant": merchant,
    }


# ---------------------------------------------------------------------------
# Block Schemas
# ---------------------------------------------------------------------------

class SardisPayBlockInput(BaseModel):
    api_key: str = Field(
        default="",
        description="Sardis API key (or use SARDIS_API_KEY env var)",
    )
    wallet_id: str = Field(
        default="",
        description="Wallet ID (e.g. wal_abc123) or use SARDIS_WALLET_ID env var",
    )
    amount: str = Field(
        description="Payment amount as a decimal string (e.g. '25.00'). Never use float for money.",
    )
    merchant: str = Field(
        description="Merchant or recipient identifier",
    )
    destination: str = Field(
        default="",
        description="On-chain destination address (0x...)",
    )
    purpose: str = Field(default="Payment", description="Reason for payment")
    token: TokenType = Field(default="USDC", description="Token to use for payment")
    chain: ChainType = Field(default="base", description="Target chain")

    @field_validator("wallet_id")
    @classmethod
    def check_wallet_id(cls, v: str) -> str:
        return _validate_wallet_id(v)

    @field_validator("destination")
    @classmethod
    def check_destination(cls, v: str) -> str:
        return _validate_hex_address(v)

    @field_validator("amount")
    @classmethod
    def check_amount(cls, v: str) -> str:
        return _validate_amount_str(v)


class SardisPayBlockOutput(BaseModel):
    status: str = Field(
        description="APPROVED, BLOCKED, PENDING, FAILED, or ERROR",
    )
    tx_id: str = Field(default="", description="Transaction ID if approved")
    message: str = Field(default="", description="Status message")
    amount: str = Field(default="0", description="Payment amount (decimal string)")
    merchant: str = Field(default="", description="Merchant name")


class SardisBalanceBlockInput(BaseModel):
    api_key: str = Field(default="", description="Sardis API key")
    wallet_id: str = Field(default="", description="Wallet ID (e.g. wal_abc123)")
    token: TokenType = Field(default="USDC", description="Token to check")

    @field_validator("wallet_id")
    @classmethod
    def check_wallet_id(cls, v: str) -> str:
        return _validate_wallet_id(v)


class SardisBalanceBlockOutput(BaseModel):
    balance: str = Field(default="0", description="Current balance (decimal string)")
    remaining: str = Field(
        default="0",
        description="Remaining spending limit (decimal string)",
    )
    token: str = Field(default="USDC", description="Token type")


class SardisPolicyCheckBlockInput(BaseModel):
    api_key: str = Field(default="", description="Sardis API key")
    wallet_id: str = Field(default="", description="Wallet ID (e.g. wal_abc123)")
    amount: str = Field(
        description="Amount to check (decimal string)",
    )
    merchant: str = Field(description="Merchant to check")

    @field_validator("wallet_id")
    @classmethod
    def check_wallet_id(cls, v: str) -> str:
        return _validate_wallet_id(v)

    @field_validator("amount")
    @classmethod
    def check_amount(cls, v: str) -> str:
        return _validate_amount_str(v)


class SardisPolicyCheckBlockOutput(BaseModel):
    allowed: bool = Field(description="Whether payment would be allowed")
    reason: str = Field(default="", description="Explanation")


# ---------------------------------------------------------------------------
# Block implementations
# ---------------------------------------------------------------------------

class SardisPayBlock:
    """AutoGPT block for executing Sardis payments."""

    id = "sardis-pay-block"
    name = "Sardis Pay"
    description = "Execute a policy-controlled payment from a Sardis wallet"
    categories = [BlockCategory.OUTPUT]
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
            result = _with_retry(
                client.payments.send,
                wallet_id,
                to=input_data.destination or input_data.merchant,
                amount=input_data.amount,
                purpose=input_data.purpose,
                token=input_data.token,
            )
        except Exception as e:
            yield SardisPayBlockOutput(
                status="ERROR",
                message=str(e),
                amount=input_data.amount,
                merchant=input_data.merchant,
            )
            return

        resp = _normalize_response(result, input_data.amount, input_data.merchant)
        yield SardisPayBlockOutput(**resp)


class SardisBalanceBlock:
    """AutoGPT block for checking Sardis wallet balance."""

    id = "sardis-balance-block"
    name = "Sardis Balance"
    description = "Check the current balance and spending limits of a Sardis wallet"
    categories = [BlockCategory.DATA]
    input_schema = SardisBalanceBlockInput
    output_schema = SardisBalanceBlockOutput

    @staticmethod
    def run(input_data: SardisBalanceBlockInput) -> Iterator[SardisBalanceBlockOutput]:
        client, wallet_id = _get_client(
            api_key=input_data.api_key or None,
            wallet_id=input_data.wallet_id or None,
        )
        if not wallet_id:
            yield SardisBalanceBlockOutput(
                balance="0", remaining="0", token=input_data.token,
            )
            return

        balance_obj = _with_retry(
            client.wallets.get_balance, wallet_id, token=input_data.token,
        )
        remaining = getattr(balance_obj, "remaining", None)
        if remaining is None:
            remaining = getattr(
                balance_obj, "remaining_limit",
                getattr(balance_obj, "daily_remaining", 0),
            )
        yield SardisBalanceBlockOutput(
            balance=str(balance_obj.balance),
            remaining=str(remaining),
            token=input_data.token,
        )


class SardisPolicyCheckBlock:
    """AutoGPT block for checking if a payment would pass policy."""

    id = "sardis-policy-check-block"
    name = "Sardis Policy Check"
    description = "Check if a payment would be allowed by spending policy before executing"
    categories = [BlockCategory.DATA]
    input_schema = SardisPolicyCheckBlockInput
    output_schema = SardisPolicyCheckBlockOutput

    @staticmethod
    def run(
        input_data: SardisPolicyCheckBlockInput,
    ) -> Iterator[SardisPolicyCheckBlockOutput]:
        client, wallet_id = _get_client(
            api_key=input_data.api_key or None,
            wallet_id=input_data.wallet_id or None,
        )
        if not wallet_id:
            yield SardisPolicyCheckBlockOutput(
                allowed=False, reason="No wallet ID configured",
            )
            return

        balance_obj = _with_retry(client.wallets.get_balance, wallet_id)
        remaining = getattr(balance_obj, "remaining", None)
        if remaining is None:
            remaining = getattr(
                balance_obj, "remaining_limit",
                getattr(balance_obj, "daily_remaining", 0),
            )

        amount_d = Decimal(input_data.amount)
        remaining_d = Decimal(str(remaining))
        balance_d = Decimal(str(balance_obj.balance))

        if amount_d > remaining_d:
            yield SardisPolicyCheckBlockOutput(
                allowed=False,
                reason=f"Amount ${input_data.amount} exceeds remaining limit ${remaining}",
            )
        elif amount_d > balance_d:
            yield SardisPolicyCheckBlockOutput(
                allowed=False,
                reason=f"Amount ${input_data.amount} exceeds balance ${balance_obj.balance}",
            )
        else:
            yield SardisPolicyCheckBlockOutput(
                allowed=True,
                reason=f"Payment of ${input_data.amount} to {input_data.merchant} would be allowed",
            )


# Registry of all blocks
BLOCKS = [SardisPayBlock, SardisBalanceBlock, SardisPolicyCheckBlock]
