"""Sardis Agent Card for A2A protocol.

The agent card is published at /.well-known/agent-card.json and declares
the agent's capabilities for other agents to discover.

Sardis agent cards declare:
- Payment capabilities (tokens, chains, protocols)
- Service endpoints (REST, MCP, webhooks)
- Supported message types
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentCapability(str, Enum):
    """Capabilities that a Sardis agent supports."""

    # Payment capabilities
    PAYMENT_EXECUTE = "payment.execute"  # Execute AP2 payment mandates
    PAYMENT_VERIFY = "payment.verify"  # Verify mandate chains
    PAYMENT_REFUND = "payment.refund"  # Process refunds

    # Mandate capabilities
    MANDATE_INGEST = "mandate.ingest"  # Receive mandates
    MANDATE_SIGN = "mandate.sign"  # Sign mandates

    # Wallet capabilities
    WALLET_BALANCE = "wallet.balance"  # Check wallet balances
    WALLET_HOLD = "wallet.hold"  # Create/manage holds

    # Checkout capabilities (UCP)
    CHECKOUT_CREATE = "checkout.create"  # Create UCP checkouts
    CHECKOUT_COMPLETE = "checkout.complete"  # Complete checkouts

    # Micropayment capabilities
    X402_MICROPAY = "x402.micropay"  # x402 micropayments


@dataclass(slots=True)
class PaymentCapability:
    """Payment-specific capability declaration."""

    # Supported tokens
    supported_tokens: List[str] = field(
        default_factory=lambda: ["USDC", "USDT", "PYUSD", "EURC"]
    )

    # Supported chains
    supported_chains: List[str] = field(
        default_factory=lambda: ["base", "polygon", "ethereum", "arbitrum", "optimism"]
    )

    # Limits (in minor units)
    min_amount_minor: int = 100  # $1.00
    max_amount_minor: int = 100_000_00  # $100,000.00

    # Protocol compliance
    ap2_compliant: bool = True
    x402_compliant: bool = True
    ucp_compliant: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "supported_tokens": self.supported_tokens,
            "supported_chains": self.supported_chains,
            "min_amount_minor": self.min_amount_minor,
            "max_amount_minor": self.max_amount_minor,
            "ap2_compliant": self.ap2_compliant,
            "x402_compliant": self.x402_compliant,
            "ucp_compliant": self.ucp_compliant,
        }


@dataclass(slots=True)
class ServiceEndpoint:
    """Service endpoint for agent communication."""

    url: str
    protocol: str = "https"  # https, wss, mcp
    auth_required: bool = False
    auth_type: Optional[str] = None  # bearer, api_key, signature

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "url": self.url,
            "protocol": self.protocol,
            "auth_required": self.auth_required,
            "auth_type": self.auth_type,
        }


@dataclass(slots=True)
class SardisAgentCard:
    """
    Sardis Agent Card for A2A protocol.

    Published at /.well-known/agent-card.json to allow other agents
    to discover and interact with this Sardis instance.

    Conforms to the A2A agent card specification.
    """

    # Agent identity
    agent_id: str
    agent_name: str
    agent_version: str = "1.0.0"
    agent_description: str = ""

    # Operator information
    operator_name: str = "Sardis"
    operator_url: str = "https://sardis.sh"
    operator_contact: Optional[str] = None

    # Capabilities
    capabilities: List[AgentCapability] = field(
        default_factory=lambda: [
            AgentCapability.PAYMENT_EXECUTE,
            AgentCapability.PAYMENT_VERIFY,
            AgentCapability.MANDATE_INGEST,
            AgentCapability.WALLET_BALANCE,
            AgentCapability.CHECKOUT_CREATE,
            AgentCapability.CHECKOUT_COMPLETE,
            AgentCapability.X402_MICROPAY,
        ]
    )
    payment_capability: PaymentCapability = field(default_factory=PaymentCapability)

    # Service endpoints
    api_endpoint: Optional[ServiceEndpoint] = None
    mcp_endpoint: Optional[str] = None  # MCP server command/args
    webhook_endpoint: Optional[ServiceEndpoint] = None
    a2a_endpoint: Optional[ServiceEndpoint] = None

    # Verification
    signing_key_id: Optional[str] = None
    public_key: Optional[str] = None
    key_algorithm: str = "Ed25519"

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def supports_capability(self, capability: AgentCapability) -> bool:
        """Check if this agent supports a specific capability."""
        return capability in self.capabilities

    def supports_token(self, token: str) -> bool:
        """Check if this agent supports a specific token."""
        return token.upper() in self.payment_capability.supported_tokens

    def supports_chain(self, chain: str) -> bool:
        """Check if this agent supports a specific chain."""
        return chain.lower() in self.payment_capability.supported_chains

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        This is the format served at /.well-known/agent-card.json
        """
        card = {
            # A2A spec fields
            "agent_id": self.agent_id,
            "name": self.agent_name,
            "version": self.agent_version,
            "description": self.agent_description,
            # Operator
            "operator": {
                "name": self.operator_name,
                "url": self.operator_url,
                "contact": self.operator_contact,
            },
            # Capabilities
            "capabilities": [cap.value for cap in self.capabilities],
            "payment": self.payment_capability.to_dict(),
            # Endpoints
            "endpoints": {},
            # Verification
            "signing": {
                "key_id": self.signing_key_id,
                "public_key": self.public_key,
                "algorithm": self.key_algorithm,
            } if self.signing_key_id else None,
            # Metadata
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

        # Add endpoints
        if self.api_endpoint:
            card["endpoints"]["api"] = self.api_endpoint.to_dict()
        if self.mcp_endpoint:
            card["endpoints"]["mcp"] = self.mcp_endpoint
        if self.webhook_endpoint:
            card["endpoints"]["webhook"] = self.webhook_endpoint.to_dict()
        if self.a2a_endpoint:
            card["endpoints"]["a2a"] = self.a2a_endpoint.to_dict()

        return card


def create_sardis_agent_card(
    agent_id: str,
    agent_name: str,
    api_base_url: str,
    mcp_command: Optional[str] = None,
    signing_key_id: Optional[str] = None,
    public_key: Optional[str] = None,
) -> SardisAgentCard:
    """
    Create a standard Sardis agent card with default capabilities.

    Args:
        agent_id: Unique agent identifier
        agent_name: Display name for the agent
        api_base_url: Base URL for the Sardis API
        mcp_command: Optional MCP server command
        signing_key_id: Optional signing key ID
        public_key: Optional public key for verification

    Returns:
        Configured SardisAgentCard
    """
    return SardisAgentCard(
        agent_id=agent_id,
        agent_name=agent_name,
        agent_description="Sardis Payment Agent - secure AI payment infrastructure",
        api_endpoint=ServiceEndpoint(
            url=f"{api_base_url}/api/v2",
            protocol="https",
            auth_required=True,
            auth_type="bearer",
        ),
        mcp_endpoint=mcp_command,
        a2a_endpoint=ServiceEndpoint(
            url=f"{api_base_url}/api/v2/a2a",
            protocol="https",
            auth_required=True,
            auth_type="signature",
        ),
        signing_key_id=signing_key_id,
        public_key=public_key,
    )


__all__ = [
    "AgentCapability",
    "PaymentCapability",
    "ServiceEndpoint",
    "SardisAgentCard",
    "create_sardis_agent_card",
]
