"""Tool call handler for Sardis OpenAI integration.

Processes OpenAI function call results and executes corresponding
Sardis operations via the SDK.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SardisToolHandler:
    """Handles OpenAI tool calls for Sardis operations.

    Usage:
        handler = SardisToolHandler(api_key="sk_...")

        for tool_call in response.choices[0].message.tool_calls:
            result = await handler.handle(tool_call)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        wallet_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ):
        self._api_key = api_key
        self._default_wallet_id = wallet_id
        self._default_agent_id = agent_id
        self._client = None

    def _get_client(self):
        """Lazily initialize the Sardis client."""
        if self._client is None:
            try:
                from sardis_sdk import AsyncSardisClient
                self._client = AsyncSardisClient(api_key=self._api_key)
            except ImportError:
                from sardis import SardisClient
                self._client = SardisClient(api_key=self._api_key)
        return self._client

    async def handle(self, tool_call: Any) -> str:
        """Handle a single OpenAI tool call.

        Args:
            tool_call: OpenAI tool call object with .function.name and .function.arguments

        Returns:
            JSON string result to include in the conversation
        """
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        logger.info("Handling Sardis tool call: %s(%s)", name, args)

        handlers = {
            "sardis_pay": self._handle_pay,
            "sardis_check_balance": self._handle_check_balance,
            "sardis_check_policy": self._handle_check_policy,
            "sardis_issue_card": self._handle_issue_card,
            "sardis_get_spending_summary": self._handle_spending_summary,
        }

        handler = handlers.get(name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            result = await handler(args)
            return json.dumps(result)
        except Exception as e:
            logger.error("Tool call failed: %s - %s", name, str(e))
            return json.dumps({"error": str(e), "tool": name})

    async def _handle_pay(self, args: dict) -> dict:
        """Execute payment via Sardis."""
        client = self._get_client()
        wallet_id = args.get("wallet_id", self._default_wallet_id)

        try:
            result = await client.payments.execute(
                wallet_id=wallet_id,
                to=args["to"],
                amount=args["amount"],
                token=args["token"],
                purpose=args["purpose"],
            )
            return {
                "status": "success",
                "tx_hash": getattr(result, "tx_hash", "simulated"),
                "amount": args["amount"],
                "token": args["token"],
                "to": args["to"],
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _handle_check_balance(self, args: dict) -> dict:
        """Check wallet balance."""
        client = self._get_client()
        wallet_id = args.get("wallet_id", self._default_wallet_id)

        try:
            balance = await client.wallets.balance(wallet_id)
            return {
                "wallet_id": wallet_id,
                "available": str(getattr(balance, "available", "0")),
                "token": getattr(balance, "token", "USDC"),
                "daily_spent": str(getattr(balance, "spent_daily", "0")),
                "daily_remaining": str(getattr(balance, "daily_remaining", "0")),
            }
        except Exception as e:
            return {"error": str(e)}

    async def _handle_check_policy(self, args: dict) -> dict:
        """Dry-run policy check."""
        client = self._get_client()
        wallet_id = args.get("wallet_id", self._default_wallet_id)

        try:
            result = await client.policies.check(
                wallet_id=wallet_id,
                amount=args["amount"],
                vendor=args.get("vendor"),
            )
            return {
                "allowed": getattr(result, "allowed", True),
                "reason": getattr(result, "reason", ""),
                "rules_applied": getattr(result, "rules_applied", []),
            }
        except Exception as e:
            return {"allowed": False, "reason": str(e)}

    async def _handle_issue_card(self, args: dict) -> dict:
        """Issue virtual card."""
        client = self._get_client()
        agent_id = args.get("agent_id", self._default_agent_id)

        try:
            card = await client.cards.create(
                agent_id=agent_id,
                spending_limit=args["spending_limit"],
                merchant_categories=args.get("merchant_categories", []),
            )
            return {
                "status": "created",
                "card_id": getattr(card, "card_id", "simulated"),
                "last_four": getattr(card, "last_four", "0000"),
                "spending_limit": args["spending_limit"],
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _handle_spending_summary(self, args: dict) -> dict:
        """Get spending analytics."""
        client = self._get_client()
        agent_id = args.get("agent_id", self._default_agent_id)

        try:
            summary = await client.spending.summary(
                agent_id=agent_id,
                period=args["period"],
            )
            return {
                "agent_id": agent_id,
                "period": args["period"],
                "total_spent": str(getattr(summary, "total", "0")),
                "by_category": getattr(summary, "by_category", {}),
                "by_vendor": getattr(summary, "by_vendor", {}),
            }
        except Exception as e:
            return {"error": str(e)}


async def handle_tool_call(
    tool_call: Any,
    api_key: Optional[str] = None,
    wallet_id: Optional[str] = None,
) -> str:
    """Convenience function to handle a single tool call.

    Args:
        tool_call: OpenAI tool call object
        api_key: Sardis API key
        wallet_id: Default wallet ID

    Returns:
        JSON string result
    """
    handler = SardisToolHandler(api_key=api_key, wallet_id=wallet_id)
    return await handler.handle(tool_call)
