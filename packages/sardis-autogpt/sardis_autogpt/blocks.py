"""Sardis payment blocks for AutoGPT.

Provides three blocks for the AutoGPT block system that enable AI agents
to execute policy-controlled stablecoin payments through Sardis non-custodial
MPC wallets:

- ``SardisPayBlock`` — execute a payment (OUTPUT category)
- ``SardisBalanceBlock`` — check wallet balance (DATA category)
- ``SardisPolicyCheckBlock`` — pre-validate a payment (DATA category)

All monetary values use ``str`` (never ``float``) to avoid IEEE 754
rounding issues.  Token and chain fields use ``Literal`` types so the
AutoGPT UI renders dropdowns.  Wallet IDs and destination addresses are
regex-validated to prevent path-injection attacks.
"""
from __future__ import annotations

import os
import re
import time
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from sardis import SardisClient

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_TOKENS = ("USDC", "USDT", "EURC", "PYUSD")
"""Stablecoin tokens supported by the Sardis platform."""

SUPPORTED_CHAINS = ("base", "ethereum", "polygon", "arbitrum", "optimism", "tempo")
"""Blockchain networks supported by the Sardis platform."""

_WALLET_ID_RE = re.compile(r"^wal_[a-zA-Z0-9]+$")
_HEX_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

# Token/chain literal types for schema-level validation
TokenType = Literal["USDC", "USDT", "EURC", "PYUSD"]
"""Literal union of supported stablecoin token symbols."""

ChainType = Literal["base", "ethereum", "polygon", "arbitrum", "optimism", "tempo"]
"""Literal union of supported blockchain network identifiers."""


# ---------------------------------------------------------------------------
# Block categories (mirrors autogpt_libs.suites.io.BlockCategory)
# We define our own enum so the package works without autogpt installed.
# ---------------------------------------------------------------------------

class BlockCategory(str, Enum):
    """AutoGPT block category labels.

    Mirrors ``autogpt_libs.suites.io.BlockCategory`` so that the Sardis
    blocks can be used both inside and outside the full AutoGPT runtime.
    """

    INPUT = "input"
    OUTPUT = "output"
    DATA = "data"
    TRANSFORM = "transform"
    LOGIC = "logic"


# ---------------------------------------------------------------------------
# Shared HTTP headers helper
# ---------------------------------------------------------------------------

_DEFAULT_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "User-Agent": "sardis-autogpt/2.0",
}


def _build_headers(api_key: str) -> dict[str, str]:
    """Build HTTP headers for Sardis API requests.

    Consolidates header construction in a single place so that both the
    primary and retry HTTP clients share the same configuration.

    Args:
        api_key: The Sardis API key to include in the ``X-API-Key`` header.

    Returns:
        A dict of HTTP headers ready for use with ``httpx`` or ``requests``.
    """
    headers = dict(_DEFAULT_HEADERS)
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


# ---------------------------------------------------------------------------
# Singleton client with retry
# ---------------------------------------------------------------------------

_cached_clients: dict[str, SardisClient] = {}
"""Per-API-key cache of ``SardisClient`` instances for connection reuse."""

# Retry config
_MAX_RETRIES = 3
_INITIAL_BACKOFF_S = 0.5


def _get_client(api_key: str | None = None, wallet_id: str | None = None) -> tuple[SardisClient, str | None]:
    """Return a ``(SardisClient, wallet_id)`` tuple, reusing clients per API key.

    Clients are cached in ``_cached_clients`` so that connection pools and
    authentication state are shared across block invocations.

    Args:
        api_key: Sardis API key.  Falls back to ``SARDIS_API_KEY`` env var.
        wallet_id: Wallet identifier.  Falls back to ``SARDIS_WALLET_ID`` env var.

    Returns:
        A two-tuple of ``(client, wallet_id)`` where *wallet_id* may be
        ``None`` if neither the argument nor the environment variable is set.
    """
    key = api_key or os.getenv("SARDIS_API_KEY") or ""
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    if key not in _cached_clients:
        _cached_clients[key] = SardisClient(api_key=key or None)
    return _cached_clients[key], wid


def _with_retry(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Execute *fn* with exponential backoff on transient network errors.

    Retries up to ``_MAX_RETRIES`` times (default 3) for
    ``ConnectionError``, ``TimeoutError``, and ``OSError``.  All other
    exceptions propagate immediately.

    Args:
        fn: The callable to execute.
        *args: Positional arguments forwarded to *fn*.
        **kwargs: Keyword arguments forwarded to *fn*.

    Returns:
        The return value of *fn* on success.

    Raises:
        The last transient exception if all retries are exhausted.
    """
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
    """Validate that *v* matches the ``wal_<alphanumeric>`` pattern.

    An empty string is allowed (indicates the env var should be used).

    Args:
        v: The wallet ID string to validate.

    Returns:
        The validated wallet ID (unchanged).

    Raises:
        ValueError: If the format does not match ``wal_[a-zA-Z0-9]+``.
    """
    if v and not _WALLET_ID_RE.match(v):
        raise ValueError(
            f"Invalid wallet_id '{v}': must match pattern wal_<alphanumeric>"
        )
    return v


def _validate_hex_address(v: str) -> str:
    """Validate an Ethereum-style hex address (``0x`` + 40 hex characters).

    An empty string is allowed (destination is optional).

    Args:
        v: The address string to validate.

    Returns:
        The validated address (unchanged).

    Raises:
        ValueError: If the format does not match ``0x[a-fA-F0-9]{40}``.
    """
    if v and not _HEX_ADDRESS_RE.match(v):
        raise ValueError(
            f"Invalid address '{v}': must be 0x followed by 40 hex characters"
        )
    return v


def _validate_amount_str(v: str) -> str:
    """Validate that *v* is a positive decimal string with at most 6 decimal places.

    Args:
        v: The amount string to validate (e.g. ``"25.00"``).

    Returns:
        The validated amount string (unchanged).

    Raises:
        ValueError: If *v* is empty, non-numeric, zero/negative, or has
            more than 6 decimal places.
    """
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

_STATUS_MAP: dict[str, str] = {
    "approved": "APPROVED",
    "blocked": "BLOCKED",
    "pending": "PENDING",
    "failed": "FAILED",
    "error": "ERROR",
}
"""Maps lowercase Sardis API status strings to uppercase block-level constants."""


def _normalize_status(result: Any) -> str:
    """Derive a block-level status string from a Sardis API response object.

    Resolution order:

    1. ``result.status`` — the canonical status string returned by the
       Sardis API (``"approved"``, ``"blocked"``, ``"pending"``,
       ``"failed"``, ``"error"``).  Matched case-insensitively.
    2. ``result.success`` — boolean fallback for older API versions.
       ``True`` → ``"APPROVED"``, ``False`` → ``"BLOCKED"``.
    3. If neither field is present or recognised, returns ``"ERROR"``.

    Args:
        result: The API response object (any object with ``.status``
            and/or ``.success`` attributes).

    Returns:
        One of ``"APPROVED"``, ``"BLOCKED"``, ``"PENDING"``, ``"FAILED"``,
        or ``"ERROR"``.
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


def _normalize_response(result: Any, input_amount: str, merchant: str) -> dict[str, str]:
    """Build a normalized response dict from a Sardis API result object.

    Extracts ``status``, ``tx_id``, ``message``, ``amount``, and
    ``merchant`` from the result, applying safe defaults for missing or
    ``None`` fields.  The ``amount`` falls back to *input_amount* when
    the API response does not include one.

    Args:
        result: The API response object.
        input_amount: The original payment amount (used as fallback).
        merchant: The merchant identifier to include in the response.

    Returns:
        A dict suitable for unpacking into ``SardisPayBlockOutput``.
    """
    return {
        "status": _normalize_status(result),
        "tx_id": str(getattr(result, "tx_id", "") or ""),
        "message": str(getattr(result, "message", "") or ""),
        "amount": str(getattr(result, "amount", None) or input_amount),
        "merchant": merchant,
    }


# ---------------------------------------------------------------------------
# Block Schemas
# ---------------------------------------------------------------------------

class SardisPayBlockInput(BaseModel):
    """Input schema for the Sardis Pay block."""

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
        """Validate wallet_id format."""
        return _validate_wallet_id(v)

    @field_validator("destination")
    @classmethod
    def check_destination(cls, v: str) -> str:
        """Validate destination address format."""
        return _validate_hex_address(v)

    @field_validator("amount")
    @classmethod
    def check_amount(cls, v: str) -> str:
        """Validate amount is a positive decimal string."""
        return _validate_amount_str(v)


class SardisPayBlockOutput(BaseModel):
    """Output schema for the Sardis Pay block."""

    status: str = Field(
        description="APPROVED, BLOCKED, PENDING, FAILED, or ERROR",
    )
    tx_id: str = Field(default="", description="Transaction ID if approved")
    message: str = Field(default="", description="Status message")
    amount: str = Field(default="0", description="Payment amount (decimal string)")
    merchant: str = Field(default="", description="Merchant name")


class SardisBalanceBlockInput(BaseModel):
    """Input schema for the Sardis Balance block."""

    api_key: str = Field(default="", description="Sardis API key")
    wallet_id: str = Field(default="", description="Wallet ID (e.g. wal_abc123)")
    token: TokenType = Field(default="USDC", description="Token to check")

    @field_validator("wallet_id")
    @classmethod
    def check_wallet_id(cls, v: str) -> str:
        """Validate wallet_id format."""
        return _validate_wallet_id(v)


class SardisBalanceBlockOutput(BaseModel):
    """Output schema for the Sardis Balance block."""

    balance: str = Field(default="0", description="Current balance (decimal string)")
    remaining: str = Field(
        default="0",
        description="Remaining spending limit (decimal string)",
    )
    token: str = Field(default="USDC", description="Token type")


class SardisPolicyCheckBlockInput(BaseModel):
    """Input schema for the Sardis Policy Check block."""

    api_key: str = Field(default="", description="Sardis API key")
    wallet_id: str = Field(default="", description="Wallet ID (e.g. wal_abc123)")
    amount: str = Field(
        description="Amount to check (decimal string)",
    )
    merchant: str = Field(description="Merchant to check")

    @field_validator("wallet_id")
    @classmethod
    def check_wallet_id(cls, v: str) -> str:
        """Validate wallet_id format."""
        return _validate_wallet_id(v)

    @field_validator("amount")
    @classmethod
    def check_amount(cls, v: str) -> str:
        """Validate amount is a positive decimal string."""
        return _validate_amount_str(v)


class SardisPolicyCheckBlockOutput(BaseModel):
    """Output schema for the Sardis Policy Check block."""

    allowed: bool = Field(description="Whether payment would be allowed")
    reason: str = Field(default="", description="Explanation")


# ---------------------------------------------------------------------------
# Block implementations
# ---------------------------------------------------------------------------

class SardisPayBlock:
    """AutoGPT block for executing policy-controlled Sardis payments.

    Sends a stablecoin payment from the configured Sardis wallet, subject
    to the wallet's spending policy.  On success the block yields a single
    ``SardisPayBlockOutput`` with ``status="APPROVED"`` and a transaction
    ID; on policy denial or error it yields the appropriate status.

    Category: OUTPUT (mutates external state).
    """

    id = "sardis-pay-block"
    name = "Sardis Pay"
    description = "Execute a policy-controlled payment from a Sardis wallet"
    categories = [BlockCategory.OUTPUT]
    input_schema = SardisPayBlockInput
    output_schema = SardisPayBlockOutput

    @staticmethod
    def run(input_data: SardisPayBlockInput) -> Iterator[SardisPayBlockOutput]:
        """Execute a payment and yield the result.

        Args:
            input_data: Validated payment parameters.

        Yields:
            A single ``SardisPayBlockOutput`` with the payment outcome.
        """
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
    """AutoGPT block for checking Sardis wallet balance and spending limits.

    Queries the current token balance and remaining spending limit for the
    configured wallet.  This is a read-only operation that does not move
    funds.

    Category: DATA (read-only query).
    """

    id = "sardis-balance-block"
    name = "Sardis Balance"
    description = "Check the current balance and spending limits of a Sardis wallet"
    categories = [BlockCategory.DATA]
    input_schema = SardisBalanceBlockInput
    output_schema = SardisBalanceBlockOutput

    @staticmethod
    def run(input_data: SardisBalanceBlockInput) -> Iterator[SardisBalanceBlockOutput]:
        """Query wallet balance and yield the result.

        Args:
            input_data: Validated balance query parameters.

        Yields:
            A single ``SardisBalanceBlockOutput`` with balance details.
        """
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
    """AutoGPT block for pre-validating payments against spending policy.

    Checks whether a hypothetical payment of the given amount to the given
    merchant would be allowed by the wallet's spending policy and balance,
    *without* actually moving funds.  Useful for agents that want to
    confirm affordability before committing.

    Category: DATA (read-only query).
    """

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
        """Check policy and yield the result.

        Compares the requested amount against both the remaining spending
        limit and the current balance using ``Decimal`` arithmetic to
        avoid IEEE 754 rounding errors.

        Args:
            input_data: Validated policy check parameters.

        Yields:
            A single ``SardisPolicyCheckBlockOutput`` indicating whether
            the payment would be allowed.
        """
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
"""All Sardis blocks available for registration with the AutoGPT runtime."""
