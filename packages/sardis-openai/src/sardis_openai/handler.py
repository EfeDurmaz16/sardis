"""Tool call handler for Sardis OpenAI integration.

Processes OpenAI function call results and executes corresponding
Sardis operations via the SDK.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


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
        api_key: str | None = None,
        wallet_id: str | None = None,
        agent_id: str | None = None,
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

    async def _get_wallet(self, wallet_id: str) -> Any:
        return await _maybe_await(self._get_client().wallets.get(wallet_id))

    async def _resolve_agent_id_from_wallet(self, wallet_id: str) -> str:
        wallet = await self._get_wallet(wallet_id)
        agent_id = getattr(wallet, "agent_id", None)
        if not agent_id:
            raise ValueError(
                f"Wallet {wallet_id} is not linked to an agent; cannot run canonical policy check"
            )
        return str(agent_id)

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
        if not wallet_id:
            return {"status": "failed", "error": "wallet_id is required"}

        try:
            result = await _maybe_await(
                client.wallets.transfer(
                    wallet_id,
                    destination=args["to"],
                    amount=Decimal(str(args["amount"])),
                    token=args["token"],
                    memo=args["purpose"],
                )
            )
            return {
                "status": "success",
                "tx_hash": getattr(result, "tx_hash", None),
                "chain": getattr(result, "chain", None),
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
        if not wallet_id:
            return {"error": "wallet_id is required"}

        try:
            balance = await _maybe_await(client.wallets.get_balance(wallet_id))
            return {
                "wallet_id": wallet_id,
                "balance": str(getattr(balance, "balance", "0")),
                "token": getattr(balance, "token", "USDC"),
                "chain": getattr(balance, "chain", None),
                "address": getattr(balance, "address", None),
            }
        except Exception as e:
            return {"error": str(e)}

    async def _handle_check_policy(self, args: dict) -> dict:
        """Dry-run policy check."""
        client = self._get_client()
        wallet_id = args.get("wallet_id", self._default_wallet_id)
        if not wallet_id:
            return {"allowed": False, "reason": "wallet_id is required"}

        try:
            agent_id = await self._resolve_agent_id_from_wallet(wallet_id)
            result = await _maybe_await(
                client.policies.check(
                    agent_id=agent_id,
                    amount=Decimal(str(args["amount"])),
                    currency="USD",
                    merchant_id=args.get("vendor"),
                )
            )
            return {
                "allowed": getattr(result, "allowed", False),
                "reason": getattr(result, "reason", ""),
                "policy_id": getattr(result, "policy_id", None),
                "wallet_id": wallet_id,
                "agent_id": agent_id,
            }
        except Exception as e:
            return {"allowed": False, "reason": str(e)}

    async def _handle_issue_card(self, args: dict) -> dict:
        """Issue virtual card."""
        client = self._get_client()
        agent_id = args.get("agent_id", self._default_agent_id)
        if not agent_id:
            return {"status": "failed", "error": "agent_id is required"}

        try:
            agent = await _maybe_await(client.agents.get(agent_id))
            wallet_id = getattr(agent, "wallet_id", None)
            if not wallet_id:
                return {
                    "status": "failed",
                    "error": f"Agent {agent_id} has no wallet_id; cannot issue a card",
                }

            card = await _maybe_await(
                client.cards.issue(
                    wallet_id=wallet_id,
                    limit_per_tx=Decimal(str(args["spending_limit"])),
                    limit_daily=Decimal(str(args["spending_limit"])),
                    limit_monthly=Decimal(str(args["spending_limit"])),
                )
            )
            return {
                "status": "created",
                "card_id": getattr(card, "card_id", getattr(card, "id", None)),
                "last_four": getattr(card, "last_four", "0000"),
                "spending_limit": args["spending_limit"],
                "warning": (
                    "merchant_categories were requested but are not enforced by the current "
                    "cards.issue SDK method"
                    if args.get("merchant_categories")
                    else None
                ),
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _handle_spending_summary(self, args: dict) -> dict:
        """Get spending analytics."""
        agent_id = args.get("agent_id", self._default_agent_id)
        return {
            "error": (
                "Spending summary is unavailable: the current Sardis SDK does not expose "
                "a spending.summary resource"
            ),
            "agent_id": agent_id,
            "period": args.get("period"),
        }


async def handle_tool_call(
    tool_call: Any,
    api_key: str | None = None,
    wallet_id: str | None = None,
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
