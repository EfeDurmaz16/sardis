"""
LangChain integration for Sardis SDK.

DEPRECATED: This module is a compatibility shim. Use sardis-langchain directly:
    pip install sardis-langchain

    from sardis_langchain import SardisToolkit, SardisPayTool
"""
from __future__ import annotations

import warnings

warnings.warn(
    "sardis_sdk.integrations.langchain is deprecated. "
    "Use sardis-langchain package directly: pip install sardis-langchain\n"
    "  from sardis_langchain import SardisToolkit",
    DeprecationWarning,
    stacklevel=2,
)

try:
    from sardis_langchain import (
        SardisToolkit,
        SardisPayTool,
        SardisCheckBalanceTool,
        SardisCheckPolicyTool,
        SardisSetPolicyTool,
        SardisListTransactionsTool,
        SardisPayInput,
        SardisCheckBalanceInput,
        SardisCheckPolicyInput,
        SardisSetPolicyInput,
        SardisListTransactionsInput,
        SardisCallbackHandler,
    )
except ImportError:
    raise ImportError(
        "sardis-langchain package is required for LangChain integration. "
        "Install it with: pip install sardis-langchain"
    )

# Backward compatibility aliases
SardisTool = SardisPayTool
SardisPolicyCheckTool = SardisCheckPolicyTool
SardisBalanceCheckTool = SardisCheckBalanceTool

def create_sardis_tools(client, wallet_id, **kwargs):
    """Backward compatible factory. Use SardisToolkit instead."""
    toolkit = SardisToolkit(client=client, wallet_id=wallet_id, **kwargs)
    return toolkit.get_tools()

__all__ = [
    # New canonical names
    "SardisToolkit",
    "SardisPayTool",
    "SardisCheckBalanceTool",
    "SardisCheckPolicyTool",
    "SardisSetPolicyTool",
    "SardisListTransactionsTool",
    "SardisPayInput",
    "SardisCheckBalanceInput",
    "SardisCheckPolicyInput",
    "SardisSetPolicyInput",
    "SardisListTransactionsInput",
    "SardisCallbackHandler",
    # Backward compat aliases
    "SardisTool",
    "SardisPolicyCheckTool",
    "SardisBalanceCheckTool",
    "create_sardis_tools",
]
