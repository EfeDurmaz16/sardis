"""Anthropic tool_use definitions for Sardis payment tools.

Each tool is defined as a dict matching the Anthropic Messages API
``tools`` parameter schema.  Pass these directly to
``client.messages.create(tools=...)`` or use :class:`SardisToolkit`
for a batteries-included experience.

Example::

    import anthropic
    from sardis_agent_sdk.tools import ALL_TOOLS

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        tools=ALL_TOOLS,
        messages=[{"role": "user", "content": "Pay $10 USDC to openai.com"}],
    )
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# sardis_pay
# ---------------------------------------------------------------------------

SARDIS_PAY_TOOL: dict[str, Any] = {
    "name": "sardis_pay",
    "description": (
        "Execute a payment through Sardis with automatic policy enforcement. "
        "The payment is checked against the wallet's spending policy before "
        "execution. If the policy rejects the payment, no funds are moved and "
        "the rejection reason is returned."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": (
                    "Recipient address, merchant identifier, or agent ID. "
                    "Examples: '0x1234...', 'openai.com', 'agent_abc123'."
                ),
            },
            "amount": {
                "type": "string",
                "description": (
                    "Payment amount as a decimal string. Examples: '25.00', '0.50', '100'."
                ),
            },
            "token": {
                "type": "string",
                "description": "Stablecoin token to use for the payment.",
                "enum": ["USDC", "USDT", "PYUSD", "EURC"],
                "default": "USDC",
            },
            "purpose": {
                "type": "string",
                "description": (
                    "Human-readable reason for the payment. Required if the "
                    "wallet policy has require_purpose enabled."
                ),
            },
        },
        "required": ["to", "amount"],
    },
}

# ---------------------------------------------------------------------------
# sardis_check_balance
# ---------------------------------------------------------------------------

SARDIS_CHECK_BALANCE_TOOL: dict[str, Any] = {
    "name": "sardis_check_balance",
    "description": (
        "Check the current balance and spending limits of the Sardis wallet. "
        "Returns the available balance, total spent, per-transaction limit, "
        "total spending limit, and remaining allowance."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "token": {
                "type": "string",
                "description": "Token to check balance for.",
                "enum": ["USDC", "USDT", "PYUSD", "EURC"],
                "default": "USDC",
            },
        },
        "required": [],
    },
}

# ---------------------------------------------------------------------------
# sardis_check_policy
# ---------------------------------------------------------------------------

SARDIS_CHECK_POLICY_TOOL: dict[str, Any] = {
    "name": "sardis_check_policy",
    "description": (
        "Pre-check whether a payment would be allowed by the wallet's "
        "spending policy WITHOUT executing it. Use this to verify a payment "
        "will succeed before committing. Returns approval status, which "
        "checks passed/failed, and whether human approval is required."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient address or merchant identifier.",
            },
            "amount": {
                "type": "string",
                "description": "Payment amount as a decimal string.",
            },
            "token": {
                "type": "string",
                "description": "Token type for the payment.",
                "enum": ["USDC", "USDT", "PYUSD", "EURC"],
                "default": "USDC",
            },
            "purpose": {
                "type": "string",
                "description": "Payment purpose (checked if require_purpose is enabled).",
            },
        },
        "required": ["to", "amount"],
    },
}

# ---------------------------------------------------------------------------
# sardis_set_policy
# ---------------------------------------------------------------------------

SARDIS_SET_POLICY_TOOL: dict[str, Any] = {
    "name": "sardis_set_policy",
    "description": (
        "Set or update the spending policy for the wallet using natural "
        "language. The policy controls per-transaction limits, daily limits, "
        "allowed destinations, blocked destinations, and more. "
        "Examples: 'Max $50 per transaction', 'Daily limit $500', "
        "'Only allow payments to openai.com and anthropic.com'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "policy": {
                "type": "string",
                "description": (
                    "Natural language spending policy. Sardis will parse this "
                    "into structured rules. Examples: 'Max $100 per transaction, "
                    "daily limit $1000', 'Only allow USDC payments under $50'."
                ),
            },
            "max_per_tx": {
                "type": "number",
                "description": "Maximum amount per transaction (overrides natural language parse).",
            },
            "max_total": {
                "type": "number",
                "description": "Maximum total spending limit (overrides natural language parse).",
            },
            "allowed_destinations": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Allowlist of merchant/destination patterns. Supports wildcards: "
                    "'openai:*' matches any openai endpoint."
                ),
            },
            "blocked_destinations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Blocklist of merchant/destination patterns.",
            },
        },
        "required": ["policy"],
    },
}

# ---------------------------------------------------------------------------
# sardis_list_transactions
# ---------------------------------------------------------------------------

SARDIS_LIST_TRANSACTIONS_TOOL: dict[str, Any] = {
    "name": "sardis_list_transactions",
    "description": (
        "View the transaction history for this wallet. Returns recent "
        "transactions with their status, amounts, destinations, and "
        "timestamps. Useful for reviewing spending patterns and auditing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of transactions to return.",
                "default": 10,
            },
        },
        "required": [],
    },
}

# ---------------------------------------------------------------------------
# sardis_create_hold
# ---------------------------------------------------------------------------

SARDIS_CREATE_HOLD_TOOL: dict[str, Any] = {
    "name": "sardis_create_hold",
    "description": (
        "Create a payment hold (authorization) that reserves funds without "
        "transferring them. The hold locks the specified amount in the wallet, "
        "reducing the available balance. The hold can later be captured "
        "(finalized) or released. Useful for two-phase payments like hotel "
        "bookings or service deposits."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient for the eventual payment.",
            },
            "amount": {
                "type": "string",
                "description": "Amount to hold as a decimal string.",
            },
            "token": {
                "type": "string",
                "description": "Token type for the hold.",
                "enum": ["USDC", "USDT", "PYUSD", "EURC"],
                "default": "USDC",
            },
            "purpose": {
                "type": "string",
                "description": "Reason for the hold.",
            },
            "expires_in_seconds": {
                "type": "integer",
                "description": "Hold expiration in seconds. Default: 3600 (1 hour).",
                "default": 3600,
            },
        },
        "required": ["to", "amount"],
    },
}

# ---------------------------------------------------------------------------
# Convenience aggregates
# ---------------------------------------------------------------------------

ALL_TOOLS: list[dict[str, Any]] = [
    SARDIS_PAY_TOOL,
    SARDIS_CHECK_BALANCE_TOOL,
    SARDIS_CHECK_POLICY_TOOL,
    SARDIS_SET_POLICY_TOOL,
    SARDIS_LIST_TRANSACTIONS_TOOL,
    SARDIS_CREATE_HOLD_TOOL,
]

READ_ONLY_TOOLS: list[dict[str, Any]] = [
    SARDIS_CHECK_BALANCE_TOOL,
    SARDIS_CHECK_POLICY_TOOL,
    SARDIS_LIST_TRANSACTIONS_TOOL,
]

TOOL_NAMES: set[str] = {tool["name"] for tool in ALL_TOOLS}
