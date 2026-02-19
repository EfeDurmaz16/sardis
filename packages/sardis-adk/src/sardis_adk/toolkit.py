"""
SardisToolkit -- bundles all Sardis ADK tools with shared client configuration.

Usage::

    from sardis_adk import SardisToolkit

    toolkit = SardisToolkit(api_key="sk_test_...", wallet_id="wallet_abc123")
    tools = toolkit.get_tools()       # list[FunctionTool]

    # Pass to a Google ADK Agent
    from google.adk import Agent
    agent = Agent(name="pay-agent", model="gemini-2.0-flash", tools=tools)
"""
from __future__ import annotations

from typing import Any, List

from sardis import SardisClient

from . import tools as _tools


class SardisToolkit:
    """Configure and bundle Sardis payment tools for Google ADK agents.

    The toolkit creates a ``SardisClient``, binds it (along with a default
    wallet) to the module-level tool functions, and wraps each function as
    a Google ADK ``FunctionTool``.

    Args:
        api_key: Sardis API key.  Use ``"sk_test_..."`` for simulation mode.
        wallet_id: Default wallet to operate on.  If empty, you must create
            a wallet via ``toolkit.client`` before using payment tools.
        base_url: Optional API base URL override.
    """

    def __init__(
        self,
        api_key: str = "",
        wallet_id: str = "",
        *,
        base_url: str | None = None,
    ) -> None:
        client_kwargs: dict[str, Any] = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = SardisClient(**client_kwargs)
        self.wallet_id = wallet_id

        # Bind the shared state so tool functions can access it
        _tools.configure(self.client, self.wallet_id)

    def get_tools(self) -> List[Any]:
        """Return a list of Google ADK ``FunctionTool`` instances.

        Each tool wraps one of the Sardis tool functions defined in
        ``sardis_adk.tools``.  The returned list can be passed directly
        to ``google.adk.Agent(tools=...)``.

        Returns:
            List of ``FunctionTool`` objects.
        """
        from google.adk.tools import FunctionTool

        return [
            FunctionTool(_tools.sardis_pay),
            FunctionTool(_tools.sardis_check_balance),
            FunctionTool(_tools.sardis_check_policy),
            FunctionTool(_tools.sardis_set_policy),
            FunctionTool(_tools.sardis_list_transactions),
        ]
