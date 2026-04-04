"""Sardis AgentKit — Coinbase AgentKit action provider for Sardis payments.

Usage:
    from sardis_agentkit import sardis_action_provider
    from coinbase_agentkit import AgentKit, AgentKitConfig

    agentkit = AgentKit(AgentKitConfig(
        action_providers=[sardis_action_provider(api_key="sk_test_...")]
    ))

    # With LangChain:
    from coinbase_agentkit_langchain import get_langchain_tools
    tools = get_langchain_tools(agentkit)

    # With OpenAI Agents SDK:
    from coinbase_agentkit_openai_agents_sdk import get_openai_agents_sdk_tools
    tools = get_openai_agents_sdk_tools(agentkit)
"""
from sardis_agentkit.provider import SardisActionProvider, sardis_action_provider

__all__ = ["SardisActionProvider", "sardis_action_provider"]
__version__ = "0.1.0"
