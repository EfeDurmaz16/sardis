"""Raw Gemini function calling declarations for Sardis.

For use with the Google Generative AI SDK (google-generativeai) directly,
without the ADK framework. If you're using Google ADK, use the SardisToolkit
from sardis_adk.toolkit instead.

Usage:
    import google.generativeai as genai
    from sardis_adk.gemini_functions import get_sardis_gemini_tools, handle_function_call

    model = genai.GenerativeModel("gemini-2.0-flash", tools=[get_sardis_gemini_tools()])
    chat = model.start_chat()
    response = chat.send_message("Pay $25 to OpenAI for API credits")

    for part in response.parts:
        if part.function_call:
            result = await handle_function_call(part.function_call, api_key="sk_...")
            response = chat.send_message(
                genai.protos.Content(parts=[genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=part.function_call.name, response=result
                    )
                )])
            )
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_sardis_gemini_tools() -> dict:
    """Get Gemini-compatible function declarations for Sardis.

    Returns a Tool dict that can be passed to GenerativeModel or
    converted to genai.protos.Tool.

    Returns:
        Dict with function_declarations list, compatible with Gemini API.

    Example:
        model = genai.GenerativeModel("gemini-2.0-flash", tools=[get_sardis_gemini_tools()])
    """
    return {
        "function_declarations": [
            {
                "name": "sardis_pay",
                "description": (
                    "Execute a payment from an AI agent's wallet. "
                    "Automatically enforces spending policies (daily limits, vendor restrictions). "
                    "Returns transaction hash and status."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "wallet_id": {
                            "type": "STRING",
                            "description": "The agent wallet ID (e.g., 'wallet_abc123')",
                        },
                        "to": {
                            "type": "STRING",
                            "description": "Recipient address (0x...) or merchant identifier",
                        },
                        "amount": {
                            "type": "STRING",
                            "description": "Payment amount as string (e.g., '25.00')",
                        },
                        "token": {
                            "type": "STRING",
                            "enum": ["USDC", "USDT", "EURC", "PYUSD"],
                            "description": "Token to use for payment",
                        },
                        "purpose": {
                            "type": "STRING",
                            "description": "Payment purpose for audit trail",
                        },
                    },
                    "required": ["wallet_id", "to", "amount", "token", "purpose"],
                },
            },
            {
                "name": "sardis_check_balance",
                "description": (
                    "Check an agent wallet's current balance, spending limits, "
                    "and remaining daily budget."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "wallet_id": {
                            "type": "STRING",
                            "description": "The agent wallet ID",
                        },
                    },
                    "required": ["wallet_id"],
                },
            },
            {
                "name": "sardis_check_policy",
                "description": (
                    "Dry-run a policy check before executing payment. "
                    "Returns whether the payment would be allowed."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "wallet_id": {
                            "type": "STRING",
                            "description": "The agent wallet ID",
                        },
                        "amount": {
                            "type": "STRING",
                            "description": "Amount to check",
                        },
                        "vendor": {
                            "type": "STRING",
                            "description": "Merchant/vendor name",
                        },
                    },
                    "required": ["wallet_id", "amount"],
                },
            },
            {
                "name": "sardis_issue_card",
                "description": (
                    "Issue a virtual card for real-world purchases with "
                    "programmable spending controls."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "agent_id": {
                            "type": "STRING",
                            "description": "The agent ID",
                        },
                        "spending_limit": {
                            "type": "STRING",
                            "description": "Monthly spending limit (e.g., '500.00')",
                        },
                        "merchant_categories": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                            "description": "Allowed merchant categories",
                        },
                    },
                    "required": ["agent_id", "spending_limit", "merchant_categories"],
                },
            },
            {
                "name": "sardis_get_spending_summary",
                "description": "Get spending analytics for an agent by time period.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "agent_id": {
                            "type": "STRING",
                            "description": "The agent ID",
                        },
                        "period": {
                            "type": "STRING",
                            "enum": ["day", "week", "month"],
                            "description": "Time period for summary",
                        },
                    },
                    "required": ["agent_id", "period"],
                },
            },
        ]
    }


async def handle_function_call(
    function_call: Any,
    api_key: Optional[str] = None,
    wallet_id: Optional[str] = None,
) -> dict:
    """Handle a Gemini function call response.

    Args:
        function_call: Gemini FunctionCall object with .name and .args
        api_key: Sardis API key
        wallet_id: Default wallet ID

    Returns:
        Dict result to send back as FunctionResponse
    """
    name = function_call.name
    args = dict(function_call.args) if hasattr(function_call, 'args') else {}

    logger.info("Handling Gemini function call: %s(%s)", name, args)

    try:
        # Lazy import to avoid circular deps
        from sardis_openai.handler import SardisToolHandler

        class _GeminiToolCall:
            """Adapter to match OpenAI tool_call interface."""
            def __init__(self, fn_name, fn_args):
                self.function = type("Function", (), {
                    "name": fn_name,
                    "arguments": json.dumps(fn_args),
                })()

        handler = SardisToolHandler(api_key=api_key, wallet_id=wallet_id)
        result_str = await handler.handle(_GeminiToolCall(name, args))
        return json.loads(result_str)

    except ImportError:
        logger.warning("sardis-openai not installed, using basic handler")
        return {"error": "Install sardis-openai for full function handling", "tool": name}
