"""
SardisToolkit -- one-line setup for all Sardis LangChain tools.

Usage::

    from sardis import SardisClient
    from sardis_langchain import SardisToolkit

    client = SardisClient(api_key="sk_...")
    wallet = client.wallets.create(name="agent", chain="base", policy="Max $100/day")

    toolkit = SardisToolkit(client=client, wallet_id=wallet.id)
    tools = toolkit.get_tools()

    # Pass `tools` to any LangChain agent (ReAct, OpenAI Functions, etc.)
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool

from .tools import (
    SardisCheckBalanceTool,
    SardisCheckPolicyTool,
    SardisListTransactionsTool,
    SardisPayTool,
    SardisSetPolicyTool,
)


class SardisToolkit:
    """Create a full set of Sardis LangChain tools for an agent wallet.

    The toolkit bundles five tools that cover the core payment lifecycle:

    1. **sardis_pay** -- execute a policy-enforced payment
    2. **sardis_check_balance** -- inspect wallet balance and limits
    3. **sardis_check_policy** -- dry-run a payment against policy
    4. **sardis_set_policy** -- update spending limits from natural language
    5. **sardis_list_transactions** -- view recent transaction history

    Args:
        client: An initialised :class:`sardis.SardisClient` instance.
        wallet_id: The wallet ID that all tools will operate on.

    Example::

        from langchain.agents import AgentExecutor, create_react_agent
        from langchain_openai import ChatOpenAI

        toolkit = SardisToolkit(client=client, wallet_id=wallet.id)
        tools = toolkit.get_tools()

        agent = create_react_agent(ChatOpenAI(), tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools)
        result = executor.invoke({"input": "Pay $50 to OpenAI for API credits"})
    """

    def __init__(self, client: Any, wallet_id: str) -> None:
        self.client = client
        self.wallet_id = wallet_id

    def get_tools(self) -> list[BaseTool]:
        """Return all Sardis tools configured for the wallet.

        Returns:
            A list of LangChain ``BaseTool`` instances ready to be passed
            to any LangChain agent framework.
        """
        kwargs: dict[str, Any] = {
            "client": self.client,
            "wallet_id": self.wallet_id,
        }
        return [
            SardisPayTool(**kwargs),
            SardisCheckBalanceTool(**kwargs),
            SardisCheckPolicyTool(**kwargs),
            SardisSetPolicyTool(**kwargs),
            SardisListTransactionsTool(**kwargs),
        ]

    def get_payment_tools(self) -> list[BaseTool]:
        """Return only the payment-related tools (pay + balance + policy check).

        Useful when you want a minimal tool set without policy management
        or transaction history.
        """
        kwargs: dict[str, Any] = {
            "client": self.client,
            "wallet_id": self.wallet_id,
        }
        return [
            SardisPayTool(**kwargs),
            SardisCheckBalanceTool(**kwargs),
            SardisCheckPolicyTool(**kwargs),
        ]

    def __repr__(self) -> str:
        return f"SardisToolkit(wallet_id={self.wallet_id!r})"
