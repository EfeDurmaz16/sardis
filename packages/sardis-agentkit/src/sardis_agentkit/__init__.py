"""Sardis AgentKit — Coinbase AgentKit action provider for Sardis payments.

Enables Coinbase ecosystem agents to use Sardis for policy-enforced payments.

Usage with AgentKit:
    from sardis_agentkit import SardisActionProvider

    provider = SardisActionProvider(api_key="sk_test_...")
    agent = Agent(action_providers=[provider])
"""
from sardis_agentkit.provider import SardisActionProvider

__all__ = ["SardisActionProvider"]
__version__ = "0.1.0"
