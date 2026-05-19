"""
Structured error types for the Sardis SDK.

Every error includes:
- ``code``:       Machine-readable error code (e.g. "INSUFFICIENT_FUNDS")
- ``message``:    Human-readable description
- ``suggestion``: Actionable fix the developer can try
- ``docs_url``:   Link to relevant documentation

Usage::

    from sardis.errors import SardisError, ErrorCode

    try:
        result = wallet.pay(to="openai.com", amount=500)
    except SardisError as e:
        print(e.code)        # "POLICY_AMOUNT_EXCEEDED"
        print(e.suggestion)  # "Reduce amount below $100.00 or update policy..."
        print(e.docs_url)    # "https://sardis.sh/docs/policies"
"""
from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Machine-readable error codes for Sardis SDK errors."""

    # Policy violations
    POLICY_AMOUNT_EXCEEDED = "POLICY_AMOUNT_EXCEEDED"
    POLICY_MERCHANT_BLOCKED = "POLICY_MERCHANT_BLOCKED"
    POLICY_MERCHANT_NOT_ALLOWED = "POLICY_MERCHANT_NOT_ALLOWED"
    POLICY_TOKEN_NOT_ALLOWED = "POLICY_TOKEN_NOT_ALLOWED"
    POLICY_PURPOSE_REQUIRED = "POLICY_PURPOSE_REQUIRED"
    POLICY_WALLET_LIMIT = "POLICY_WALLET_LIMIT"

    # Financial
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    GROUP_BUDGET_EXCEEDED = "GROUP_BUDGET_EXCEEDED"

    # Configuration
    WALLET_NOT_FOUND = "WALLET_NOT_FOUND"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    SIMULATION_MODE = "SIMULATION_MODE"

    # Execution
    TRANSACTION_FAILED = "TRANSACTION_FAILED"
    CHAIN_ERROR = "CHAIN_ERROR"


# Maps each error code to (suggestion_template, docs_url)
ERROR_SUGGESTIONS: dict[str, tuple[str, str]] = {
    ErrorCode.POLICY_AMOUNT_EXCEEDED: (
        "Reduce the amount below the per-transaction limit, or update the policy with a higher max_per_tx.",
        "https://sardis.sh/docs/policies",
    ),
    ErrorCode.POLICY_MERCHANT_BLOCKED: (
        "The destination is on the blocklist. Remove it from blocked_destinations in your policy.",
        "https://sardis.sh/docs/policies",
    ),
    ErrorCode.POLICY_MERCHANT_NOT_ALLOWED: (
        "The destination is not in the allowlist. Add it to allowed_destinations in your policy.",
        "https://sardis.sh/docs/policies",
    ),
    ErrorCode.POLICY_TOKEN_NOT_ALLOWED: (
        "This token is not in the allowed set. Add it to allowed_tokens in your policy.",
        "https://sardis.sh/docs/policies",
    ),
    ErrorCode.POLICY_PURPOSE_REQUIRED: (
        "This policy requires a purpose for every payment. Add purpose='...' to your pay() call.",
        "https://sardis.sh/docs/policies",
    ),
    ErrorCode.POLICY_WALLET_LIMIT: (
        "The wallet's total spending limit has been reached. Create a new wallet or increase max_total.",
        "https://sardis.sh/docs/wallets",
    ),
    ErrorCode.INSUFFICIENT_FUNDS: (
        "Fund the wallet with wallet.deposit(amount) in simulation, or transfer USDC to the wallet address in production.",
        "https://sardis.sh/docs/wallets",
    ),
    ErrorCode.APPROVAL_REQUIRED: (
        "This payment needs human approval. Approve it in the dashboard or via the Approvals API.",
        "https://sardis.sh/docs/payments",
    ),
    ErrorCode.GROUP_BUDGET_EXCEEDED: (
        "The agent group's shared budget is exhausted. Top up the group budget or adjust spending limits.",
        "https://sardis.sh/docs/policies",
    ),
    ErrorCode.WALLET_NOT_FOUND: (
        "Check the wallet ID. List available wallets with client.wallets.list().",
        "https://sardis.sh/docs/wallets",
    ),
    ErrorCode.AGENT_NOT_FOUND: (
        "Check the agent ID. List available agents with client.agents.list().",
        "https://sardis.sh/docs/quickstart",
    ),
    ErrorCode.CONFIGURATION_ERROR: (
        "Check your API key and configuration. See the production guide for setup.",
        "https://sardis.sh/docs/production-guide",
    ),
    ErrorCode.SIMULATION_MODE: (
        "You are in simulation mode. No real payments will execute. Provide a production API key to go live.",
        "https://sardis.sh/docs/production-guide",
    ),
    ErrorCode.TRANSACTION_FAILED: (
        "The transaction could not be completed. Check the error details and try again.",
        "https://sardis.sh/docs/payments",
    ),
    ErrorCode.CHAIN_ERROR: (
        "The on-chain transaction failed. This could be a gas issue, RPC timeout, or nonce conflict. Retry the payment.",
        "https://sardis.sh/docs/payments",
    ),
}


def _get_suggestion(code: str | ErrorCode) -> str:
    """Get the suggestion text for an error code."""
    key = code.value if isinstance(code, ErrorCode) else code
    entry = ERROR_SUGGESTIONS.get(key, ERROR_SUGGESTIONS.get(ErrorCode(key), ("", "")))
    return entry[0]


def _get_docs_url(code: str | ErrorCode) -> str:
    """Get the docs URL for an error code."""
    key = code.value if isinstance(code, ErrorCode) else code
    entry = ERROR_SUGGESTIONS.get(key, ERROR_SUGGESTIONS.get(ErrorCode(key), ("", "")))
    return entry[1]


class SardisError(Exception):
    """Base error for all Sardis SDK errors.

    Attributes:
        code: Machine-readable error code
        message: Human-readable description
        suggestion: Actionable fix
        docs_url: Link to relevant docs
    """

    def __init__(
        self,
        message: str,
        *,
        code: str | ErrorCode = ErrorCode.TRANSACTION_FAILED,
        suggestion: str | None = None,
        docs_url: str | None = None,
    ):
        self.code = code.value if isinstance(code, ErrorCode) else code
        self.message = message
        self.suggestion = suggestion or _get_suggestion(code)
        self.docs_url = docs_url or _get_docs_url(code)
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.suggestion:
            parts.append(f"  Suggestion: {self.suggestion}")
        if self.docs_url:
            parts.append(f"  Docs: {self.docs_url}")
        return "\n".join(parts)


class PolicyViolationError(SardisError):
    """A payment was rejected by the spending policy."""

    pass


class InsufficientFundsError(SardisError):
    """The wallet does not have enough funds."""

    def __init__(self, message: str = "Insufficient funds", **kwargs):
        super().__init__(message, code=ErrorCode.INSUFFICIENT_FUNDS, **kwargs)


class WalletNotFoundError(SardisError):
    """The specified wallet was not found."""

    def __init__(self, wallet_id: str = "", **kwargs):
        msg = f"Wallet '{wallet_id}' not found" if wallet_id else "Wallet not found"
        super().__init__(msg, code=ErrorCode.WALLET_NOT_FOUND, **kwargs)


class ConfigurationError(SardisError):
    """SDK configuration is invalid or incomplete."""

    def __init__(self, message: str = "Configuration error", **kwargs):
        super().__init__(message, code=ErrorCode.CONFIGURATION_ERROR, **kwargs)
