"""Agent-to-Agent (A2A) protocol integration for Sardis.

A2A enables multi-agent communication with support for:
- Agent discovery via /.well-known/agent-card.json
- Structured message exchange (payment requests, credentials)
- Capability negotiation

This package provides Sardis's A2A implementation for agent interoperability.
"""

from .agent_card import (
    AgentCapability,
    PaymentCapability,
    SardisAgentCard,
    create_sardis_agent_card,
)
from .client import (
    A2AClient,
    A2AClientError,
)
from .discovery import (
    AgentDiscoveryService,
    DiscoveredAgent,
)
from .messages import (
    A2ACredentialRequest,
    A2ACredentialResponse,
    A2AMessage,
    A2AMessageType,
    A2APaymentRequest,
    A2APaymentResponse,
)

__all__ = [
    # Agent Card
    "SardisAgentCard",
    "AgentCapability",
    "PaymentCapability",
    "create_sardis_agent_card",
    # Messages
    "A2AMessageType",
    "A2AMessage",
    "A2APaymentRequest",
    "A2APaymentResponse",
    "A2ACredentialRequest",
    "A2ACredentialResponse",
    # Discovery
    "AgentDiscoveryService",
    "DiscoveredAgent",
    # Client
    "A2AClient",
    "A2AClientError",
]
