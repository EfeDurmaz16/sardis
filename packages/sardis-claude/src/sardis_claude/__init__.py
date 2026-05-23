"""sardis-claude — Anthropic Claude integration for Sardis payments.

This package is a thin alias of `sardis-agent-sdk`. It exists to provide a
clearer install name (`pip install sardis-claude`) that does not collide with
the main `sardis` SDK. All symbols are re-exported from `sardis_agent_sdk`.

In Sardis v2.0 the canonical home for this integration will be
`sardis.integrations.anthropic`; this package will keep working as an alias.

Quick start::

    from sardis import SardisClient
    from sardis_claude import SardisToolkit

    sardis = SardisClient(api_key="your-api-key")
    wallet = sardis.wallets.create(name="agent-wallet", chain="base")
    toolkit = SardisToolkit(client=sardis, wallet_id=wallet.id)
    tools = toolkit.get_tools()
"""

import warnings as _warnings

with _warnings.catch_warnings():
    _warnings.simplefilter("ignore", DeprecationWarning)
    from sardis_agent_sdk import (  # noqa: F401
        ALL_TOOLS,
        READ_ONLY_TOOLS,
        SARDIS_CHECK_BALANCE_TOOL,
        SARDIS_CHECK_POLICY_TOOL,
        SARDIS_CREATE_ESCROW_TOOL,
        SARDIS_CREATE_HOLD_TOOL,
        SARDIS_CREATE_SUBSCRIPTION_TOOL,
        SARDIS_GET_FX_QUOTE_TOOL,
        SARDIS_LIST_TRANSACTIONS_TOOL,
        SARDIS_MINT_PAYMENT_TOOL,
        SARDIS_PAY_TOOL,
        SARDIS_SET_POLICY_TOOL,
        TOOL_NAMES,
        SardisToolHandler,
        SardisToolkit,
    )

__version__ = "0.1.0"

__all__ = [
    "SardisToolkit",
    "SardisToolHandler",
    "ALL_TOOLS",
    "READ_ONLY_TOOLS",
    "TOOL_NAMES",
    "SARDIS_PAY_TOOL",
    "SARDIS_CHECK_BALANCE_TOOL",
    "SARDIS_CHECK_POLICY_TOOL",
    "SARDIS_SET_POLICY_TOOL",
    "SARDIS_LIST_TRANSACTIONS_TOOL",
    "SARDIS_CREATE_HOLD_TOOL",
    "SARDIS_MINT_PAYMENT_TOOL",
    "SARDIS_GET_FX_QUOTE_TOOL",
    "SARDIS_CREATE_SUBSCRIPTION_TOOL",
    "SARDIS_CREATE_ESCROW_TOOL",
]
