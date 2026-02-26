"""
sardis-langchain: LangChain integration for the Sardis Payment OS.

Provides LangChain-compatible tools that let AI agents execute real financial
transactions through Sardis MPC wallets with policy enforcement.

Quick start::

    from sardis import SardisClient
    from sardis_langchain import SardisToolkit

    client = SardisClient(api_key="sk_...")
    wallet = client.wallets.create(name="agent", chain="base", policy="Max $100/day")

    toolkit = SardisToolkit(client=client, wallet_id=wallet.id)
    tools = toolkit.get_tools()
    # Pass tools to any LangChain agent
"""

__version__ = "1.0.0"

from .callbacks import SardisCallbackHandler
from .toolkit import SardisToolkit
from .tools import (
    SardisCheckBalanceInput,
    SardisCheckBalanceTool,
    SardisCheckPolicyInput,
    SardisCheckPolicyTool,
    SardisListTransactionsInput,
    SardisListTransactionsTool,
    SardisPayInput,
    SardisPayTool,
    SardisSetPolicyInput,
    SardisSetPolicyTool,
)

__all__ = [
    # Toolkit
    "SardisToolkit",
    # Tools
    "SardisPayTool",
    "SardisCheckBalanceTool",
    "SardisCheckPolicyTool",
    "SardisSetPolicyTool",
    "SardisListTransactionsTool",
    # Input schemas
    "SardisPayInput",
    "SardisCheckBalanceInput",
    "SardisCheckPolicyInput",
    "SardisSetPolicyInput",
    "SardisListTransactionsInput",
    # Callbacks
    "SardisCallbackHandler",
]
