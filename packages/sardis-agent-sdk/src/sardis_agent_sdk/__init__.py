"""Anthropic Claude Agent SDK integration for Sardis payments.

Provides tool definitions and handlers that let Claude agents make
payments, check balances, and manage spending policies through Sardis.

Quick start::

    from sardis import SardisClient
    from sardis_agent_sdk import SardisToolkit

    sardis = SardisClient(api_key="sk_test_demo")
    wallet = sardis.wallets.create(name="agent-wallet", chain="base")
    toolkit = SardisToolkit(client=sardis, wallet_id=wallet.id)

    # Get tool definitions for the Claude API
    tools = toolkit.get_tools()

    # Process tool calls from Claude responses
    for block in response.content:
        if block.type == "tool_use":
            result = toolkit.handle_tool_call(block)
"""

from .toolkit import SardisToolkit
from .handlers import SardisToolHandler
from .tools import (
    ALL_TOOLS,
    READ_ONLY_TOOLS,
    TOOL_NAMES,
    SARDIS_PAY_TOOL,
    SARDIS_CHECK_BALANCE_TOOL,
    SARDIS_CHECK_POLICY_TOOL,
    SARDIS_SET_POLICY_TOOL,
    SARDIS_LIST_TRANSACTIONS_TOOL,
    SARDIS_CREATE_HOLD_TOOL,
)

__version__ = "1.0.0"

__all__ = [
    # Main entry points
    "SardisToolkit",
    "SardisToolHandler",
    # Tool collections
    "ALL_TOOLS",
    "READ_ONLY_TOOLS",
    "TOOL_NAMES",
    # Individual tool definitions
    "SARDIS_PAY_TOOL",
    "SARDIS_CHECK_BALANCE_TOOL",
    "SARDIS_CHECK_POLICY_TOOL",
    "SARDIS_SET_POLICY_TOOL",
    "SARDIS_LIST_TRANSACTIONS_TOOL",
    "SARDIS_CREATE_HOLD_TOOL",
]
