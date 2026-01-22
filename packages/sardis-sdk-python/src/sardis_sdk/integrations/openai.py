"""
OpenAI Function Calling / Swarm Integration for Sardis SDK.

Provides function schemas and handlers for OpenAI's function calling feature,
enabling AI agents to execute payments through Sardis MPC wallets.

Example:
    ```python
    import openai
    from sardis_sdk import SardisClient
    from sardis_sdk.integrations.openai import (
        get_openai_tools,
        handle_function_call,
    )

    async with SardisClient(api_key="sk_...") as client:
        tools = get_openai_tools()

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Pay $50 to OpenAI"}],
            tools=tools,
        )

        # Handle tool calls
        for tool_call in response.choices[0].message.tool_calls:
            result = await handle_function_call(
                client,
                tool_call.function.name,
                json.loads(tool_call.function.arguments),
                wallet_id="wallet_123",
            )
    ```
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import SardisClient


def get_openai_function_schema() -> dict[str, Any]:
    """
    Returns the JSON schema for sardis_pay function (legacy format).

    Use get_openai_tools() for the newer tools format.
    """
    return {
        "name": "sardis_pay",
        "description": (
            "Executes a secure payment using Sardis MPC wallet. "
            "Validates against spending policy before processing. "
            "Use this when the user needs to pay for APIs, SaaS, or services."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "The amount to pay in USD (or token units)."
                },
                "merchant": {
                    "type": "string",
                    "description": "The name of the merchant or service provider."
                },
                "merchant_address": {
                    "type": "string",
                    "description": "The wallet address of the merchant (0x...). Optional."
                },
                "purpose": {
                    "type": "string",
                    "description": "The reason for the payment (e.g. 'API Credits')."
                },
                "token": {
                    "type": "string",
                    "enum": ["USDC", "USDT", "PYUSD", "EURC"],
                    "description": "The stablecoin to use. Defaults to USDC."
                }
            },
            "required": ["amount", "merchant"]
        }
    }


def get_openai_tools() -> list[dict[str, Any]]:
    """
    Returns OpenAI-compatible tool definitions for all Sardis functions.

    Use with OpenAI's Chat Completions API with tools parameter.

    Example:
        ```python
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=get_openai_tools(),
        )
        ```
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "sardis_pay",
                "description": (
                    "Execute a secure payment using Sardis MPC wallet. "
                    "Validates against spending policies before execution. "
                    "Returns transaction details on success or error if blocked by policy."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "number",
                            "description": "The amount to pay in USD (or token units)"
                        },
                        "merchant": {
                            "type": "string",
                            "description": "The name of the merchant or service provider"
                        },
                        "merchant_address": {
                            "type": "string",
                            "description": "The wallet address of the merchant (0x...). Optional."
                        },
                        "purpose": {
                            "type": "string",
                            "description": "The reason for the payment, used for policy validation"
                        },
                        "token": {
                            "type": "string",
                            "enum": ["USDC", "USDT", "PYUSD", "EURC"],
                            "description": "The stablecoin to use. Defaults to USDC."
                        }
                    },
                    "required": ["amount", "merchant"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "sardis_check_balance",
                "description": (
                    "Check the current balance of the Sardis wallet. "
                    "Use before making payments to ensure sufficient funds."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "enum": ["USDC", "USDT", "PYUSD", "EURC"],
                            "description": "The token to check balance for. Defaults to USDC."
                        },
                        "chain": {
                            "type": "string",
                            "description": "The blockchain to check balance on."
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "sardis_get_wallet",
                "description": (
                    "Get information about the Sardis wallet including spending limits."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "sardis_check_policy",
                "description": (
                    "Check if a payment would be allowed by the spending policy "
                    "without executing it. Use to validate before payment."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "number",
                            "description": "The amount to pay in USD"
                        },
                        "merchant": {
                            "type": "string",
                            "description": "The name of the merchant"
                        },
                        "purpose": {
                            "type": "string",
                            "description": "The reason for the payment"
                        }
                    },
                    "required": ["amount", "merchant"]
                }
            }
        }
    ]


def _generate_mandate_id() -> str:
    """Generate a unique mandate ID."""
    timestamp = hex(int(datetime.now(timezone.utc).timestamp() * 1000))[2:]
    random_part = uuid.uuid4().hex[:8]
    return f"mnd_{timestamp}{random_part}"


def _create_audit_hash(data: str) -> str:
    """Create SHA-256 hash for audit purposes."""
    return hashlib.sha256(data.encode()).hexdigest()


async def handle_function_call(
    client: "SardisClient",
    function_name: str,
    arguments: dict[str, Any],
    wallet_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    chain: str = "base_sepolia",
) -> str:
    """
    Handle an OpenAI function call and execute the corresponding Sardis operation.

    Args:
        client: Initialized SardisClient instance
        function_name: The name of the function to call
        arguments: The function arguments from OpenAI
        wallet_id: Wallet ID to use for operations
        agent_id: Agent ID for attribution
        chain: Default blockchain

    Returns:
        JSON string with the result

    Example:
        ```python
        async with SardisClient(api_key="sk_...") as client:
            result = await handle_function_call(
                client,
                "sardis_pay",
                {"amount": 50, "merchant": "OpenAI", "purpose": "API credits"},
                wallet_id="wallet_123",
            )
            print(result)
        ```
    """
    wallet_id = wallet_id or os.getenv("SARDIS_WALLET_ID", "")
    agent_id = agent_id or os.getenv("SARDIS_AGENT_ID", "")

    if function_name == "sardis_pay":
        return await _handle_payment(client, arguments, wallet_id, agent_id, chain)
    elif function_name == "sardis_check_balance":
        return await _handle_check_balance(client, arguments, wallet_id, chain)
    elif function_name == "sardis_get_wallet":
        return await _handle_get_wallet(client, wallet_id)
    elif function_name == "sardis_check_policy":
        return await _handle_check_policy(client, arguments, wallet_id)
    else:
        return json.dumps({"success": False, "error": f"Unknown function: {function_name}"})


async def _handle_payment(
    client: "SardisClient",
    args: dict[str, Any],
    wallet_id: str,
    agent_id: str,
    chain: str,
) -> str:
    """Handle sardis_pay function call."""
    if not wallet_id:
        return json.dumps({
            "success": False,
            "error": "No wallet ID configured. Set wallet_id or SARDIS_WALLET_ID env var."
        })

    amount = args.get("amount", 0)
    merchant = args.get("merchant", "")
    merchant_address = args.get("merchant_address")
    purpose = args.get("purpose", "Service payment")
    token = args.get("token", "USDC")

    if amount <= 0:
        return json.dumps({"success": False, "error": "Amount must be positive"})

    try:
        mandate_id = _generate_mandate_id()
        timestamp = datetime.now(timezone.utc).isoformat()
        amount_minor = str(int(amount * 1_000_000))

        audit_data = f"{mandate_id}:{wallet_id}:{merchant_address or merchant}:{amount_minor}:{token}:{timestamp}"
        audit_hash = _create_audit_hash(audit_data)

        mandate = {
            "mandate_id": mandate_id,
            "subject": wallet_id,
            "destination": merchant_address or f"pending:{merchant}",
            "amount_minor": amount_minor,
            "token": token,
            "chain": chain,
            "purpose": purpose,
            "vendor_name": merchant,
            "agent_id": agent_id,
            "timestamp": timestamp,
            "audit_hash": audit_hash,
            "metadata": {
                "vendor": merchant,
                "category": "saas",
                "initiated_by": "ai_agent",
                "tool": "openai_function_calling",
            },
        }

        result = await client.payments.execute_mandate(mandate)

        return json.dumps({
            "success": True,
            "status": result.status,
            "payment_id": result.payment_id,
            "transaction_hash": result.tx_hash,
            "chain": result.chain,
            "ledger_tx_id": result.ledger_tx_id,
            "audit_anchor": result.audit_anchor,
            "message": f"Payment of ${amount} {token} to {merchant} {result.status}.",
        })

    except Exception as e:
        error_msg = str(e)
        if any(kw in error_msg.lower() for kw in ["policy", "blocked", "limit", "denied"]):
            return json.dumps({
                "success": False,
                "blocked": True,
                "error": error_msg,
                "message": f"Payment to {merchant} blocked by policy: {error_msg}",
            })
        return json.dumps({"success": False, "error": error_msg})


async def _handle_check_balance(
    client: "SardisClient",
    args: dict[str, Any],
    wallet_id: str,
    chain: str,
) -> str:
    """Handle sardis_check_balance function call."""
    if not wallet_id:
        return json.dumps({"success": False, "error": "No wallet ID configured"})

    token = args.get("token", "USDC")
    chain = args.get("chain", chain)

    try:
        balance = await client.wallets.get_balance(wallet_id, chain, token)
        return json.dumps({
            "success": True,
            "wallet_id": balance.wallet_id,
            "balance": balance.balance,
            "token": balance.token,
            "chain": balance.chain,
            "address": balance.address,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _handle_get_wallet(client: "SardisClient", wallet_id: str) -> str:
    """Handle sardis_get_wallet function call."""
    if not wallet_id:
        return json.dumps({"success": False, "error": "No wallet ID configured"})

    try:
        wallet = await client.wallets.get(wallet_id)
        return json.dumps({
            "success": True,
            "wallet": {
                "id": wallet.id,
                "agent_id": wallet.agent_id,
                "currency": wallet.currency,
                "limit_per_tx": wallet.limit_per_tx,
                "limit_total": wallet.limit_total,
                "is_active": wallet.is_active,
                "addresses": wallet.addresses,
            }
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _handle_check_policy(
    client: "SardisClient",
    args: dict[str, Any],
    wallet_id: str,
) -> str:
    """Handle sardis_check_policy function call."""
    if not wallet_id:
        return json.dumps({"success": False, "error": "No wallet ID configured"})

    amount = args.get("amount", 0)
    merchant = args.get("merchant", "")

    try:
        wallet = await client.wallets.get(wallet_id)
        limit_per_tx = float(wallet.limit_per_tx) if wallet.limit_per_tx else float('inf')

        checks = []
        all_passed = True

        if amount <= limit_per_tx:
            checks.append({"name": "per_transaction_limit", "passed": True})
        else:
            checks.append({
                "name": "per_transaction_limit",
                "passed": False,
                "reason": f"Amount ${amount} exceeds limit of ${limit_per_tx}"
            })
            all_passed = False

        if wallet.is_active:
            checks.append({"name": "wallet_active", "passed": True})
        else:
            checks.append({
                "name": "wallet_active",
                "passed": False,
                "reason": "Wallet is not active"
            })
            all_passed = False

        return json.dumps({
            "success": True,
            "allowed": all_passed,
            "checks": checks,
            "summary": (
                f"Payment of ${amount} to {merchant} would be allowed"
                if all_passed else
                f"Payment of ${amount} to {merchant} would be blocked"
            ),
        })

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# Convenience function to create a tool response for OpenAI
def create_tool_response(tool_call_id: str, content: str) -> dict[str, Any]:
    """
    Create a tool response message for OpenAI conversation.

    Args:
        tool_call_id: The ID from the tool call
        content: The result content (JSON string)

    Returns:
        Dict formatted as an OpenAI tool message
    """
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }
