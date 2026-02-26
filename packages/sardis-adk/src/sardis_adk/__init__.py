"""
sardis-adk -- Google Agent Development Kit integration for Sardis.

Provides FunctionTool wrappers around Sardis payment operations so that
Google ADK agents can make payments, check balances, enforce spending
policies, and review transaction history.

Quick start::

    from sardis_adk import SardisToolkit, create_sardis_agent

    # Option 1: Get tools for your own agent
    toolkit = SardisToolkit(api_key="sk_test_...", wallet_id="wallet_abc")
    tools = toolkit.get_tools()

    # Option 2: Use the pre-configured agent
    agent = create_sardis_agent(api_key="sk_test_...", wallet_id="wallet_abc")
"""

__version__ = "1.0.0"

from .toolkit import SardisToolkit
from .agent import create_sardis_agent
from .tools import (
    sardis_pay,
    sardis_check_balance,
    sardis_check_policy,
    sardis_set_policy,
    sardis_list_transactions,
)

__all__ = [
    "SardisToolkit",
    "create_sardis_agent",
    "sardis_pay",
    "sardis_check_balance",
    "sardis_check_policy",
    "sardis_set_policy",
    "sardis_list_transactions",
]
