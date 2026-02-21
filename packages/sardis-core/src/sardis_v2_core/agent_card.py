"""Agent Card generation for A2A/AP2 protocol compatibility."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .erc8004 import AgentIdentity


@dataclass(slots=True)
class AgentCard:
    """
    Agent Card following A2A/AP2 agent card specification.

    Agent cards are discoverable identity documents that enable
    agent-to-agent communication and payment protocols.
    """

    agent_id: str
    name: str
    description: str
    version: str
    owner: str  # Ethereum address or DID
    capabilities: list[str] = field(default_factory=list)
    protocols: list[str] = field(default_factory=lambda: ["a2a", "ap2"])
    endpoints: dict[str, str] = field(default_factory=dict)
    public_key: str | None = None  # For signature verification
    ens_name: str | None = None
    chain_id: int = 1
    created_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Export as JSON-serializable dict."""
        card = {
            "@context": "https://sardis.sh/agent-card/v1",
            "type": "AgentCard",
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "owner": self.owner,
            "capabilities": self.capabilities,
            "protocols": self.protocols,
            "endpoints": self.endpoints,
            "chain_id": self.chain_id,
            "created_at": self.created_at,
        }

        if self.public_key:
            card["public_key"] = self.public_key

        if self.ens_name:
            card["ens_name"] = self.ens_name

        return card

    @property
    def fingerprint(self) -> str:
        """Generate card fingerprint (hash of canonical JSON)."""
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    @classmethod
    def from_dict(cls, data: dict) -> AgentCard:
        """Parse from JSON dict."""
        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            description=data["description"],
            version=data["version"],
            owner=data["owner"],
            capabilities=data.get("capabilities", []),
            protocols=data.get("protocols", ["a2a", "ap2"]),
            endpoints=data.get("endpoints", {}),
            public_key=data.get("public_key"),
            ens_name=data.get("ens_name"),
            chain_id=data.get("chain_id", 1),
            created_at=data.get("created_at", 0),
        )


def generate_agent_card(
    identity: AgentIdentity,
    capabilities: list[str] | None = None,
    public_key: str | None = None,
    endpoints: dict[str, str] | None = None,
) -> dict:
    """
    Generate A2A/AP2 agent card from ERC-8004 identity.

    Args:
        identity: ERC-8004 agent identity
        capabilities: Optional capability overrides
        public_key: Optional public key for signature verification
        endpoints: Optional service endpoints

    Returns:
        Agent card as JSON dict
    """
    metadata = identity.metadata

    card = AgentCard(
        agent_id=identity.agent_id,
        name=metadata.get("name", f"Agent {identity.agent_id}"),
        description=metadata.get("description", ""),
        version=metadata.get("version", "1.0.0"),
        owner=identity.owner_address,
        capabilities=capabilities or metadata.get("capabilities", []),
        protocols=metadata.get("protocols_supported", ["a2a", "ap2"]),
        endpoints=endpoints or metadata.get("service_endpoints", {}),
        public_key=public_key,
        ens_name=identity.ens_name,
        chain_id=identity.chain_id,
        created_at=identity.created_at,
    )

    return card.to_dict()


def verify_agent_card(card: dict) -> bool:
    """
    Verify agent card integrity and signature.

    Args:
        card: Agent card dict

    Returns:
        True if valid, False otherwise
    """
    # Basic structure validation
    required_fields = ["agent_id", "name", "description", "version", "owner"]
    if not all(field in card for field in required_fields):
        return False

    # Validate context
    if card.get("@context") != "https://sardis.sh/agent-card/v1":
        return False

    # Validate type
    if card.get("type") != "AgentCard":
        return False

    # Validate protocols
    protocols = card.get("protocols", [])
    if not isinstance(protocols, list) or not protocols:
        return False

    # TODO: Signature verification if public_key present
    # For now, just structural validation
    return True


def bind_ens_name(card: dict, ens_name: str) -> dict:
    """
    Bind ENS name to agent card.

    Args:
        card: Agent card dict
        ens_name: ENS name (e.g., "myagent.eth")

    Returns:
        Updated agent card with ENS binding
    """
    card["ens_name"] = ens_name

    # Add ENS resolution endpoint
    if "endpoints" not in card:
        card["endpoints"] = {}

    card["endpoints"]["ens_resolver"] = f"https://ens.eth/resolve/{ens_name}"

    return card


def resolve_agent_card_uri(agent_id: str, chain_id: int = 1) -> str:
    """
    Generate standard agent card URI.

    Args:
        agent_id: Agent token ID
        chain_id: Chain ID where agent is registered

    Returns:
        Agent card URI
    """
    return f"https://sardis.sh/api/v2/agents/identity/{agent_id}/card?chain={chain_id}"
