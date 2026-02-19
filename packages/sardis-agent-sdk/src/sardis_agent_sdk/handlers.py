"""Tool call handlers for Sardis payment tools.

Processes Claude ``tool_use`` content blocks and returns ``tool_result``
blocks that can be sent back in the conversation.

Each handler method maps a tool name to the corresponding SardisClient
operation, formats the result as a human-readable string, and wraps
errors gracefully so the agent always receives useful feedback.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from uuid import uuid4

from sardis import SardisClient

from .tools import TOOL_NAMES


class SardisToolHandler:
    """Processes Claude tool_use calls and returns tool_result responses.

    Args:
        client: A configured :class:`sardis.SardisClient` instance.
        wallet_id: The wallet ID to operate on.
    """

    def __init__(self, client: SardisClient, wallet_id: str) -> None:
        self.client = client
        self.wallet_id = wallet_id
        self._handlers: dict[str, Any] = {
            "sardis_pay": self._handle_pay,
            "sardis_check_balance": self._handle_check_balance,
            "sardis_check_policy": self._handle_check_policy,
            "sardis_set_policy": self._handle_set_policy,
            "sardis_list_transactions": self._handle_list_transactions,
            "sardis_create_hold": self._handle_create_hold,
        }
        # Holds tracked in-memory (simulation); production would use the API.
        self._holds: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def handle(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Process a tool call and return the result as a dict.

        Args:
            tool_name: Name of the Sardis tool (e.g. ``"sardis_pay"``).
            tool_input: The ``input`` dict from the Claude tool_use block.

        Returns:
            A dict with ``"status"`` (``"success"`` or ``"error"``) and
            a ``"result"`` or ``"error"`` key with the details.

        Raises:
            ValueError: If *tool_name* is not a recognised Sardis tool.
        """
        if tool_name not in self._handlers:
            raise ValueError(
                f"Unknown tool '{tool_name}'. "
                f"Valid tools: {', '.join(sorted(TOOL_NAMES))}"
            )
        handler = self._handlers[tool_name]
        try:
            result = handler(tool_input)
            return {"status": "success", "result": result}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def process_tool_use_block(self, tool_use_block: dict[str, Any]) -> dict[str, Any]:
        """Process a Claude API tool_use content block directly.

        Takes a dict shaped like::

            {
                "type": "tool_use",
                "id": "toolu_...",
                "name": "sardis_pay",
                "input": {"to": "openai.com", "amount": "25.00"}
            }

        Returns a dict shaped like::

            {
                "type": "tool_result",
                "tool_use_id": "toolu_...",
                "content": "..."
            }

        If the tool call fails, the ``"is_error"`` key is set to ``True``.
        """
        tool_use_id = tool_use_block.get("id", "")
        tool_name = tool_use_block.get("name", "")
        tool_input = tool_use_block.get("input", {})

        result = self.handle(tool_name, tool_input)

        if result["status"] == "success":
            content = json.dumps(result["result"], default=str)
            return {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": content,
            }
        else:
            return {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": json.dumps({"error": result["error"]}),
                "is_error": True,
            }

    # ------------------------------------------------------------------
    # Individual tool handlers
    # ------------------------------------------------------------------

    def _handle_pay(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute a payment through the wallet."""
        to = input_data["to"]
        amount = self._parse_amount(input_data["amount"])
        token = input_data.get("token", "USDC")
        purpose = input_data.get("purpose")

        result = self.client.payments.send(
            wallet_id=self.wallet_id,
            to=to,
            amount=amount,
            token=token,
            memo=purpose,
        )

        return {
            "tx_id": result.tx_id,
            "status": result.status.value,
            "success": result.success,
            "amount": str(result.amount),
            "to": result.to,
            "currency": result.currency,
            "tx_hash": result.tx_hash,
            "message": result.message,
            "timestamp": result.timestamp.isoformat(),
        }

    def _handle_check_balance(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Return the wallet's current balance and limits."""
        token = input_data.get("token", "USDC")
        wallet = self.client.wallets.get(self.wallet_id)

        balance_info = self.client.wallets.get_balance(
            self.wallet_id,
            token=token,
        )

        return {
            "wallet_id": self.wallet_id,
            "balance": str(balance_info.balance),
            "currency": balance_info.currency,
            "token": token,
            "spent_total": str(balance_info.spent_total),
            "limit_per_tx": str(balance_info.limit_per_tx),
            "limit_total": str(balance_info.limit_total),
            "remaining": str(balance_info.remaining),
        }

    def _handle_check_policy(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Pre-check whether a payment would be allowed."""
        to = input_data["to"]
        amount = self._parse_amount(input_data["amount"])
        token = input_data.get("token", "USDC")
        purpose = input_data.get("purpose")

        wallet = self.client.wallets.get(self.wallet_id)

        # Use the wallet's policy if it's a ManagedWallet with policy,
        # otherwise create a default policy from wallet limits.
        from sardis import Policy

        policy = Policy(
            max_per_tx=float(wallet.limit_per_tx),
            max_total=float(wallet.limit_total),
        )

        policy_result = policy.check(
            amount=amount,
            wallet=wallet,
            destination=to,
            token=token,
            purpose=purpose,
        )

        return {
            "approved": policy_result.approved,
            "reason": policy_result.reason,
            "requires_approval": policy_result.requires_approval,
            "checks_passed": policy_result.checks_passed,
            "checks_failed": policy_result.checks_failed,
        }

    def _handle_set_policy(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Update the wallet's spending policy."""
        policy_text = input_data["policy"]
        max_per_tx = input_data.get("max_per_tx")
        max_total = input_data.get("max_total")
        allowed_destinations = input_data.get("allowed_destinations")
        blocked_destinations = input_data.get("blocked_destinations")

        wallet = self.client.wallets.get(self.wallet_id)

        # Parse natural language policy for limits
        parsed = _parse_natural_language_policy(policy_text)

        # Explicit parameters override natural language parse
        new_per_tx = Decimal(str(max_per_tx)) if max_per_tx is not None else parsed.get("max_per_tx")
        new_total = Decimal(str(max_total)) if max_total is not None else parsed.get("max_total")

        if new_per_tx is not None:
            wallet.limit_per_tx = Decimal(str(new_per_tx))
        if new_total is not None:
            wallet.limit_total = Decimal(str(new_total))

        # Store policy text on managed wallets
        if hasattr(wallet, "_policy_text"):
            wallet._policy_text = policy_text

        result: dict[str, Any] = {
            "wallet_id": self.wallet_id,
            "policy_text": policy_text,
            "limit_per_tx": str(wallet.limit_per_tx),
            "limit_total": str(wallet.limit_total),
        }

        if allowed_destinations is not None:
            result["allowed_destinations"] = allowed_destinations
        if blocked_destinations is not None:
            result["blocked_destinations"] = blocked_destinations

        return result

    def _handle_list_transactions(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Return recent transactions for this wallet."""
        limit = input_data.get("limit", 10)

        entries = self.client.ledger.list(
            wallet_id=self.wallet_id,
            limit=limit,
        )

        transactions = []
        for entry in entries:
            transactions.append({
                "tx_id": entry.tx_id,
                "amount": str(entry.amount),
                "to": entry.merchant,
                "status": entry.status,
                "currency": entry.currency,
                "purpose": entry.purpose,
                "timestamp": entry.timestamp.isoformat(),
            })

        return {
            "wallet_id": self.wallet_id,
            "count": len(transactions),
            "transactions": transactions,
        }

    def _handle_create_hold(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Create a payment hold (authorization)."""
        to = input_data["to"]
        amount = self._parse_amount(input_data["amount"])
        token = input_data.get("token", "USDC")
        purpose = input_data.get("purpose")
        expires_in = input_data.get("expires_in_seconds", 3600)

        wallet = self.client.wallets.get(self.wallet_id)

        # Check if wallet can cover the hold
        if not wallet.can_spend(amount):
            return {
                "hold_id": None,
                "status": "rejected",
                "reason": "Insufficient funds or spending limit exceeded",
                "amount": str(amount),
                "to": to,
            }

        # Reserve the funds (reduce balance without recording a spend)
        hold_id = f"hold_{uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)

        self._holds[hold_id] = {
            "hold_id": hold_id,
            "wallet_id": self.wallet_id,
            "to": to,
            "amount": amount,
            "token": token,
            "purpose": purpose,
            "status": "active",
            "created_at": now.isoformat(),
            "expires_at": (
                datetime.fromtimestamp(
                    now.timestamp() + expires_in, tz=timezone.utc
                ).isoformat()
            ),
        }

        # Deduct from available balance to reserve the amount
        wallet.balance -= amount

        return {
            "hold_id": hold_id,
            "status": "active",
            "amount": str(amount),
            "to": to,
            "token": token,
            "purpose": purpose,
            "expires_in_seconds": expires_in,
            "created_at": now.isoformat(),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_amount(raw: Any) -> Decimal:
        """Parse an amount string into a Decimal, stripping currency symbols."""
        if isinstance(raw, (int, float, Decimal)):
            return Decimal(str(raw))
        text = str(raw).strip().lstrip("$").replace(",", "")
        try:
            return Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid amount: {raw!r}") from exc


# ---------------------------------------------------------------------------
# Natural language policy parser (mirrors sardis.client._parse_policy)
# ---------------------------------------------------------------------------

def _parse_natural_language_policy(text: str) -> dict[str, Any]:
    """Parse natural language policy into structured limits.

    Handles patterns like:
      - "Max $100 per transaction"
      - "Max $100/day"
      - "Daily limit $500"
    """
    result: dict[str, Any] = {}
    text_lower = text.lower()

    # "Max $100 per transaction" / "Max $100/tx"
    m = re.search(
        r"max\s+\$?([\d,]+(?:\.\d+)?)\s*(?:per\s+(?:transaction|tx)|/tx)",
        text_lower,
    )
    if m:
        result["max_per_tx"] = Decimal(m.group(1).replace(",", ""))

    # "$200 per transaction" without "max" prefix
    if "max_per_tx" not in result:
        m = re.search(
            r"\$?([\d,]+(?:\.\d+)?)\s*per\s+(?:transaction|tx)",
            text_lower,
        )
        if m:
            result["max_per_tx"] = Decimal(m.group(1).replace(",", ""))

    # "Daily limit $500" / "Max $500/day"
    m = re.search(r"max\s+\$?([\d,]+(?:\.\d+)?)\s*/\s*day", text_lower)
    if m:
        result["max_total"] = Decimal(m.group(1).replace(",", ""))

    if "max_total" not in result:
        m = re.search(r"daily\s+limit\s+\$?([\d,]+(?:\.\d+)?)", text_lower)
        if m:
            result["max_total"] = Decimal(m.group(1).replace(",", ""))

    return result
