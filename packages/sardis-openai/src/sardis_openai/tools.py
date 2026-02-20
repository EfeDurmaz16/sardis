"""OpenAI function calling tool definitions for Sardis.

Defines 5 tools with strict mode enabled to prevent hallucination:
- sardis_pay: Execute payment with policy enforcement
- sardis_check_balance: Check wallet balance and limits
- sardis_check_policy: Dry-run policy validation
- sardis_issue_card: Issue virtual card for agent
- sardis_get_spending_summary: Get spending analytics
"""

from __future__ import annotations

from typing import Any


SARDIS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "sardis_pay",
            "description": (
                "Execute a payment from an AI agent's wallet. "
                "Automatically enforces spending policies (daily limits, vendor restrictions, KYA level). "
                "Returns transaction hash and status."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_id": {
                        "type": "string",
                        "description": "The agent wallet ID (e.g., 'wallet_abc123')",
                    },
                    "to": {
                        "type": "string",
                        "description": "Recipient address (0x...) or merchant identifier",
                    },
                    "amount": {
                        "type": "string",
                        "description": "Payment amount as string (e.g., '25.00')",
                    },
                    "token": {
                        "type": "string",
                        "enum": ["USDC", "USDT", "EURC", "PYUSD"],
                        "description": "Token to use for payment",
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Payment purpose for audit trail (e.g., 'Monthly API subscription')",
                    },
                },
                "required": ["wallet_id", "to", "amount", "token", "purpose"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sardis_check_balance",
            "description": (
                "Check an agent wallet's current balance, spending limits, and remaining daily budget. "
                "Returns available balance, daily/monthly spent, and remaining limits."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_id": {
                        "type": "string",
                        "description": "The agent wallet ID",
                    },
                },
                "required": ["wallet_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sardis_check_policy",
            "description": (
                "Dry-run a policy check before executing payment. "
                "Returns whether the payment would be allowed and which rules apply. "
                "Use this to verify before calling sardis_pay."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_id": {
                        "type": "string",
                        "description": "The agent wallet ID",
                    },
                    "amount": {
                        "type": "string",
                        "description": "Amount to check",
                    },
                    "vendor": {
                        "type": "string",
                        "description": "Merchant/vendor name to check against allowlist",
                    },
                },
                "required": ["wallet_id", "amount"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sardis_issue_card",
            "description": (
                "Issue a virtual card for real-world purchases. "
                "Card has programmable spending controls enforced by policy engine. "
                "Uses Stripe Issuing ($0.10 per card)."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The agent ID to issue card for",
                    },
                    "spending_limit": {
                        "type": "string",
                        "description": "Monthly spending limit (e.g., '500.00')",
                    },
                    "merchant_categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Allowed merchant categories (e.g., ['software', 'cloud_services'])",
                    },
                },
                "required": ["agent_id", "spending_limit", "merchant_categories"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sardis_get_spending_summary",
            "description": (
                "Get spending analytics for an agent. "
                "Returns totals by category and vendor for the specified period."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The agent ID",
                    },
                    "period": {
                        "type": "string",
                        "enum": ["day", "week", "month"],
                        "description": "Time period for summary",
                    },
                },
                "required": ["agent_id", "period"],
                "additionalProperties": False,
            },
        },
    },
]


def get_sardis_tools() -> list[dict[str, Any]]:
    """Get OpenAI-compatible tool definitions for Sardis.

    Returns a list of function tool definitions that can be passed
    directly to the OpenAI Chat Completions or Assistants API.

    Returns:
        List of tool definitions with strict mode enabled.

    Example:
        tools = get_sardis_tools()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Pay $25 to OpenAI"}],
            tools=tools,
        )
    """
    return SARDIS_TOOL_DEFINITIONS.copy()
