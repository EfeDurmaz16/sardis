"""
LangChain tool implementations for Sardis payment operations.

Each tool wraps a specific Sardis capability and exposes it as a LangChain
``BaseTool`` with structured input schemas.  Tools perform fail-closed error
handling: any exception is caught and returned as a JSON error payload so the
LLM can reason about the failure without crashing the agent loop.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class SardisPayInput(BaseModel):
    """Input schema for the sardis_pay tool."""

    to: str = Field(description="Recipient wallet address or merchant identifier (e.g. 'openai.com')")
    amount: str = Field(description="Payment amount in token units (e.g. '25.00')")
    token: str = Field(default="USDC", description="Stablecoin to use: USDC, USDT, PYUSD, or EURC")
    purpose: str = Field(default="", description="Reason for the payment (used for policy audit)")


class SardisCheckBalanceInput(BaseModel):
    """Input schema for the sardis_check_balance tool."""

    token: str = Field(default="USDC", description="Token to check balance for")
    chain: str = Field(default="base", description="Blockchain to query")


class SardisCheckPolicyInput(BaseModel):
    """Input schema for the sardis_check_policy tool."""

    to: str = Field(description="Recipient wallet address or merchant identifier")
    amount: str = Field(description="Payment amount to validate")
    token: str = Field(default="USDC", description="Token type for the payment")
    purpose: str = Field(default="", description="Payment purpose for policy evaluation")


class SardisSetPolicyInput(BaseModel):
    """Input schema for the sardis_set_policy tool."""

    policy: str = Field(
        description=(
            "Natural-language spending policy. Examples: "
            "'Max $100 per transaction', 'Max $500/day', "
            "'Daily limit $1000, max $200 per tx'"
        )
    )


class SardisListTransactionsInput(BaseModel):
    """Input schema for the sardis_list_transactions tool."""

    limit: int = Field(default=10, description="Maximum number of transactions to return")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _error_response(error: str) -> str:
    """Return a consistent JSON error payload."""
    return json.dumps({"success": False, "error": error})


def _safe_decimal(value: str, field_name: str = "amount") -> Decimal | None:
    """Parse a string into Decimal, returning None on failure."""
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class SardisPayTool(BaseTool):
    """Execute a payment through Sardis with automatic policy enforcement.

    The payment is validated against the wallet's spending policy before
    execution.  If the policy rejects the payment, no funds move and the
    rejection reason is returned.
    """

    name: str = "sardis_pay"
    description: str = (
        "Execute a payment through a Sardis MPC wallet with automatic policy "
        "enforcement.  Use this when you need to send stablecoins to a vendor, "
        "service provider, or wallet address."
    )
    args_schema: type[BaseModel] = SardisPayInput

    client: Any = None  # SardisClient
    wallet_id: str = ""

    def _run(
        self,
        to: str,
        amount: str,
        token: str = "USDC",
        purpose: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        amount_d = _safe_decimal(amount)
        if amount_d is None:
            return _error_response(f"Invalid amount: {amount!r}")

        if not self.wallet_id:
            return _error_response("No wallet_id configured on SardisPayTool")

        try:
            wallet = self.client.wallets.get(self.wallet_id)
            result = wallet.pay(to=to, amount=amount_d, token=token, purpose=purpose or None)

            return json.dumps({
                "success": result.success,
                "status": result.status.value if hasattr(result.status, "value") else str(result.status),
                "tx_id": result.tx_id,
                "tx_hash": result.tx_hash,
                "amount": str(result.amount),
                "currency": result.currency,
                "to": result.to,
                "message": result.message,
            })
        except Exception as exc:
            logger.exception("sardis_pay failed")
            error_msg = str(exc)
            if any(kw in error_msg.lower() for kw in ("policy", "blocked", "limit", "rejected")):
                return json.dumps({
                    "success": False,
                    "blocked": True,
                    "error": error_msg,
                    "message": f"Payment to {to} blocked by policy: {error_msg}",
                })
            return _error_response(error_msg)


class SardisCheckBalanceTool(BaseTool):
    """Check the current wallet balance, spending limits, and remaining budget."""

    name: str = "sardis_check_balance"
    description: str = (
        "Check the current balance and spending limits of the Sardis wallet. "
        "Use this before making payments to verify sufficient funds."
    )
    args_schema: type[BaseModel] = SardisCheckBalanceInput

    client: Any = None  # SardisClient
    wallet_id: str = ""

    def _run(
        self,
        token: str = "USDC",
        chain: str = "base",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        if not self.wallet_id:
            return _error_response("No wallet_id configured on SardisCheckBalanceTool")

        try:
            info = self.client.wallets.get_balance(self.wallet_id, chain=chain, token=token)

            return json.dumps({
                "success": True,
                "wallet_id": info.wallet_id,
                "chain": info.chain,
                "token": info.token,
                "balance": str(info.balance),
                "spent_total": str(info.spent_total),
                "limit_per_tx": str(info.limit_per_tx),
                "limit_total": str(info.limit_total),
                "remaining": str(info.remaining),
            })
        except Exception as exc:
            logger.exception("sardis_check_balance failed")
            return _error_response(str(exc))


class SardisCheckPolicyTool(BaseTool):
    """Validate a payment against the wallet's spending policy without executing it.

    Returns which policy checks pass or fail so the agent can decide whether
    to proceed or adjust the payment parameters.
    """

    name: str = "sardis_check_policy"
    description: str = (
        "Validate whether a payment would be allowed by the wallet's spending "
        "policy WITHOUT actually executing it.  Use this to pre-check a payment "
        "before calling sardis_pay."
    )
    args_schema: type[BaseModel] = SardisCheckPolicyInput

    client: Any = None  # SardisClient
    wallet_id: str = ""

    def _run(
        self,
        to: str,
        amount: str,
        token: str = "USDC",
        purpose: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        amount_d = _safe_decimal(amount)
        if amount_d is None:
            return _error_response(f"Invalid amount: {amount!r}")

        if not self.wallet_id:
            return _error_response("No wallet_id configured on SardisCheckPolicyTool")

        try:
            wallet = self.client.wallets.get(self.wallet_id)

            # Build policy checks based on wallet limits
            checks: list[dict[str, Any]] = []

            # Per-transaction limit
            if amount_d <= wallet.limit_per_tx:
                checks.append({"name": "per_transaction_limit", "passed": True})
            else:
                checks.append({
                    "name": "per_transaction_limit",
                    "passed": False,
                    "reason": (
                        f"Amount ${amount} exceeds per-transaction limit "
                        f"of ${wallet.limit_per_tx}"
                    ),
                })

            # Balance check
            if amount_d <= wallet.balance:
                checks.append({"name": "sufficient_balance", "passed": True})
            else:
                checks.append({
                    "name": "sufficient_balance",
                    "passed": False,
                    "reason": f"Amount ${amount} exceeds balance of ${wallet.balance}",
                })

            # Total spending limit
            remaining = wallet.remaining_limit()
            if amount_d <= remaining:
                checks.append({"name": "total_spending_limit", "passed": True})
            else:
                checks.append({
                    "name": "total_spending_limit",
                    "passed": False,
                    "reason": f"Amount ${amount} exceeds remaining limit of ${remaining}",
                })

            # Wallet active
            if wallet.is_active:
                checks.append({"name": "wallet_active", "passed": True})
            else:
                checks.append({
                    "name": "wallet_active",
                    "passed": False,
                    "reason": "Wallet is not active",
                })

            all_passed = all(c["passed"] for c in checks)
            failed_reasons = [c["reason"] for c in checks if not c["passed"]]

            return json.dumps({
                "success": True,
                "allowed": all_passed,
                "checks": checks,
                "summary": (
                    f"Payment of ${amount} to {to} would be allowed"
                    if all_passed
                    else f"Payment of ${amount} to {to} would be blocked: {'; '.join(failed_reasons)}"
                ),
            })
        except Exception as exc:
            logger.exception("sardis_check_policy failed")
            return _error_response(str(exc))


class SardisSetPolicyTool(BaseTool):
    """Set the wallet's spending policy from a natural-language description.

    Parses the description into per-transaction and daily limits, then applies
    them to the wallet.
    """

    name: str = "sardis_set_policy"
    description: str = (
        "Set or update the wallet's spending policy using natural language. "
        "Examples: 'Max $100 per transaction', 'Max $500/day', "
        "'Daily limit $1000, max $200 per tx'."
    )
    args_schema: type[BaseModel] = SardisSetPolicyInput

    client: Any = None  # SardisClient
    wallet_id: str = ""

    def _run(
        self,
        policy: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        if not self.wallet_id:
            return _error_response("No wallet_id configured on SardisSetPolicyTool")

        try:
            wallet = self.client.wallets.get(self.wallet_id)

            # Use the same natural-language parser as SardisClient
            from sardis.client import _parse_policy

            parsed = _parse_policy(policy)

            old_limit_per_tx = wallet.limit_per_tx
            old_limit_total = wallet.limit_total

            if "max_per_tx" in parsed:
                wallet.limit_per_tx = Decimal(str(parsed["max_per_tx"]))
            if "max_total" in parsed:
                wallet.limit_total = Decimal(str(parsed["max_total"]))

            return json.dumps({
                "success": True,
                "policy_text": policy,
                "applied": {
                    "limit_per_tx": {
                        "old": str(old_limit_per_tx),
                        "new": str(wallet.limit_per_tx),
                    },
                    "limit_total": {
                        "old": str(old_limit_total),
                        "new": str(wallet.limit_total),
                    },
                },
                "message": f"Policy updated: {policy}",
            })
        except Exception as exc:
            logger.exception("sardis_set_policy failed")
            return _error_response(str(exc))


class SardisListTransactionsTool(BaseTool):
    """List recent transactions from the wallet's ledger."""

    name: str = "sardis_list_transactions"
    description: str = (
        "View recent transactions from the Sardis wallet. "
        "Returns transaction history including amounts, merchants, and statuses."
    )
    args_schema: type[BaseModel] = SardisListTransactionsInput

    client: Any = None  # SardisClient
    wallet_id: str = ""

    def _run(
        self,
        limit: int = 10,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        if not self.wallet_id:
            return _error_response("No wallet_id configured on SardisListTransactionsTool")

        try:
            entries = self.client.ledger.list(wallet_id=self.wallet_id, limit=limit)

            transactions = []
            for entry in entries:
                transactions.append({
                    "tx_id": entry.tx_id,
                    "timestamp": entry.timestamp.isoformat(),
                    "amount": str(entry.amount),
                    "currency": entry.currency,
                    "merchant": entry.merchant,
                    "status": entry.status,
                    "purpose": entry.purpose,
                })

            return json.dumps({
                "success": True,
                "wallet_id": self.wallet_id,
                "count": len(transactions),
                "transactions": transactions,
            })
        except Exception as exc:
            logger.exception("sardis_list_transactions failed")
            return _error_response(str(exc))
