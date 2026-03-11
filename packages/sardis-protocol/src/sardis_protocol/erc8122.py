"""ERC-8122: Minimal Agent Registry.

Implements a curated, gas-efficient agent registry built on ERC-6909.
Each agent is a singleton token with fully on-chain metadata per ERC-8048.

Key features:
- Agent registration with on-chain metadata (name, service, type)
- Batch registration for bulk onboarding
- Display format: [alias.]agentId@registry (per ERC-8127)
- Service type categorization (MCP, A2A, custom)
- Cross-chain agent identification via ERC-7930

Reference: https://eips.ethereum.org/EIPS/eip-8122
Depends on: ERC-6909, ERC-7930, ERC-8048, ERC-8049
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


# ============ Enums ============


class ServiceType(str, Enum):
    """Standard agent service types."""
    MCP = "mcp"                    # Model Context Protocol server
    A2A = "a2a"                    # Agent-to-Agent protocol
    SARDIS_MCP = "sardis-mcp"     # Sardis MCP server
    SARDIS_API = "sardis-api"     # Sardis API agent
    BROWSER_USE = "browser-use"   # Browser automation agent
    CREW_AI = "crewai"            # CrewAI multi-agent
    OPENAI_AGENT = "openai-agent" # OpenAI Agents SDK
    CUSTOM = "custom"


class RegistryStatus(str, Enum):
    """Agent registration status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


# ============ Constants ============

# Standard metadata keys (per ERC-8048)
METADATA_NAME = "name"
METADATA_DESCRIPTION = "description"
METADATA_SERVICE_TYPE = "service_type"
METADATA_SERVICE = "service"
METADATA_AGENT_ACCOUNT = "agent_account"
METADATA_ENS_NAME = "ens_name"
METADATA_ERC8004_IDENTITY = "erc8004_identity"
METADATA_VERSION = "version"
METADATA_CAPABILITIES = "capabilities"

STANDARD_METADATA_KEYS: frozenset[str] = frozenset({
    METADATA_NAME,
    METADATA_DESCRIPTION,
    METADATA_SERVICE_TYPE,
    METADATA_SERVICE,
    METADATA_AGENT_ACCOUNT,
    METADATA_ENS_NAME,
    METADATA_ERC8004_IDENTITY,
    METADATA_VERSION,
    METADATA_CAPABILITIES,
})


# ============ Data Classes ============


@dataclass
class MetadataEntry:
    """A key-value metadata pair per ERC-8048."""
    key: str
    value: str  # Stored as string; encode to bytes on-chain

    def to_bytes(self) -> tuple[bytes, bytes]:
        """Encode for on-chain storage."""
        return self.key.encode("utf-8"), self.value.encode("utf-8")


@dataclass
class AgentRegistration:
    """A registered agent in the ERC-8122 registry."""
    agent_id: int
    owner: str  # Owner address
    metadata: dict[str, str] = field(default_factory=dict)
    status: RegistryStatus = RegistryStatus.ACTIVE
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Convenience properties
    @property
    def name(self) -> str:
        return self.metadata.get(METADATA_NAME, "")

    @property
    def description(self) -> str:
        return self.metadata.get(METADATA_DESCRIPTION, "")

    @property
    def service_type(self) -> str:
        return self.metadata.get(METADATA_SERVICE_TYPE, "")

    @property
    def service_uri(self) -> str:
        return self.metadata.get(METADATA_SERVICE, "")

    @property
    def agent_account(self) -> str:
        return self.metadata.get(METADATA_AGENT_ACCOUNT, "")

    @property
    def display_name(self) -> str:
        """Human-readable display per ERC-8127: name.agentId@registry."""
        name = self.name.lower().replace(" ", "-") if self.name else ""
        if name:
            return f"{name}.{self.agent_id}"
        return str(self.agent_id)

    @property
    def is_active(self) -> bool:
        return self.status == RegistryStatus.ACTIVE

    def get_metadata_entries(self) -> list[MetadataEntry]:
        """Convert metadata dict to MetadataEntry list."""
        return [MetadataEntry(k, v) for k, v in self.metadata.items()]


@dataclass
class RegistryInfo:
    """Information about an ERC-8122 registry deployment."""
    name: str
    address: str
    chain: str
    chain_id: int
    total_agents: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def display_format(self) -> str:
        """Registry display: address@chain."""
        short = self.address[:10] if self.address else "0x"
        return f"{short}@{self.chain}"


# ============ Calldata Builders ============


def build_register_calldata(
    owner: str,
    service_type: str,
    service: str,
    agent_account: str,
) -> bytes:
    """Build calldata for register(address, string, string, address).

    Args:
        owner: Owner address
        service_type: Agent service type
        service: Service URI
        agent_account: Agent's transaction account

    Returns:
        ABI-encoded calldata
    """
    selector = bytes.fromhex("f2c298be")  # register(address,string,string,address)
    owner_bytes = owner.encode("utf-8").ljust(32, b"\x00")[:32]
    account_bytes = agent_account.encode("utf-8").ljust(32, b"\x00")[:32]

    # Simplified ABI encoding
    type_bytes = service_type.encode("utf-8")
    service_bytes = service.encode("utf-8")

    # Pack with length prefixes
    data = (
        owner_bytes
        + account_bytes
        + len(type_bytes).to_bytes(32, "big")
        + type_bytes.ljust(32, b"\x00")
        + len(service_bytes).to_bytes(32, "big")
        + service_bytes.ljust(((len(service_bytes) + 31) // 32) * 32, b"\x00")
    )
    return selector + data


def build_register_with_metadata_calldata(
    owner: str,
    metadata: list[MetadataEntry],
) -> bytes:
    """Build calldata for register(address, MetadataEntry[]).

    Args:
        owner: Owner address
        metadata: List of metadata entries

    Returns:
        ABI-encoded calldata
    """
    selector = bytes.fromhex("a1b2c3d4")  # register(address,MetadataEntry[])
    owner_bytes = owner.encode("utf-8").ljust(32, b"\x00")[:32]
    count = len(metadata).to_bytes(32, "big")

    entries = b""
    for entry in metadata:
        key_bytes = entry.key.encode("utf-8")
        val_bytes = entry.value.encode("utf-8")
        entries += (
            len(key_bytes).to_bytes(32, "big")
            + key_bytes.ljust(32, b"\x00")
            + len(val_bytes).to_bytes(32, "big")
            + val_bytes.ljust(((len(val_bytes) + 31) // 32) * 32, b"\x00")
        )

    return selector + owner_bytes + count + entries


def build_owner_of_calldata(agent_id: int) -> bytes:
    """Build calldata for ownerOf(uint256).

    Args:
        agent_id: Agent token ID

    Returns:
        ABI-encoded calldata
    """
    selector = bytes.fromhex("6352211e")  # ownerOf(uint256)
    return selector + agent_id.to_bytes(32, "big")


# ============ Registry Manager ============


class AgentRegistryManager:
    """Manages ERC-8122 agent registrations.

    Off-chain manager for curating and querying agent registries.
    Coordinates with on-chain contract for actual registration.
    """

    def __init__(
        self,
        registry_name: str = "SardisAgentRegistry",
        registry_address: str = "",
        chain: str = "base",
    ):
        self._name = registry_name
        self._address = registry_address
        self._chain = chain
        self._agents: dict[int, AgentRegistration] = {}
        self._next_id = 1

    @property
    def registry_info(self) -> RegistryInfo:
        return RegistryInfo(
            name=self._name,
            address=self._address,
            chain=self._chain,
            chain_id={"base": 8453, "ethereum": 1, "polygon": 137}.get(self._chain, 8453),
            total_agents=len(self._agents),
        )

    def register(
        self,
        owner: str,
        name: str = "",
        description: str = "",
        service_type: ServiceType = ServiceType.CUSTOM,
        service_uri: str = "",
        agent_account: str = "",
        additional_metadata: dict[str, str] | None = None,
    ) -> AgentRegistration:
        """Register a new agent in the registry.

        Args:
            owner: Owner address
            name: Agent name
            description: Agent description
            service_type: Service type
            service_uri: Service endpoint URI
            agent_account: Agent's on-chain account
            additional_metadata: Extra metadata entries
        """
        metadata: dict[str, str] = {}
        if name:
            metadata[METADATA_NAME] = name
        if description:
            metadata[METADATA_DESCRIPTION] = description
        metadata[METADATA_SERVICE_TYPE] = service_type.value
        if service_uri:
            metadata[METADATA_SERVICE] = service_uri
        if agent_account:
            metadata[METADATA_AGENT_ACCOUNT] = agent_account
        if additional_metadata:
            metadata.update(additional_metadata)

        agent_id = self._next_id
        self._next_id += 1

        registration = AgentRegistration(
            agent_id=agent_id,
            owner=owner,
            metadata=metadata,
        )

        self._agents[agent_id] = registration
        return registration

    def register_batch(
        self,
        registrations: list[dict[str, Any]],
    ) -> list[AgentRegistration]:
        """Batch register multiple agents.

        Args:
            registrations: List of dicts with register() params

        Returns:
            List of created registrations
        """
        results: list[AgentRegistration] = []
        for params in registrations:
            reg = self.register(**params)
            results.append(reg)
        return results

    def get_agent(self, agent_id: int) -> AgentRegistration | None:
        return self._agents.get(agent_id)

    def owner_of(self, agent_id: int) -> str | None:
        """Get the owner of an agent token."""
        agent = self._agents.get(agent_id)
        return agent.owner if agent else None

    def find_by_service_type(self, service_type: ServiceType) -> list[AgentRegistration]:
        """Find agents by service type."""
        return [
            a for a in self._agents.values()
            if a.service_type == service_type.value and a.is_active
        ]

    def find_by_owner(self, owner: str) -> list[AgentRegistration]:
        """Find agents owned by a specific address."""
        return [
            a for a in self._agents.values()
            if a.owner == owner and a.is_active
        ]

    def find_by_name(self, name: str) -> list[AgentRegistration]:
        """Find agents by name (case-insensitive substring)."""
        name_lower = name.lower()
        return [
            a for a in self._agents.values()
            if name_lower in a.name.lower() and a.is_active
        ]

    def update_metadata(
        self,
        agent_id: int,
        metadata: dict[str, str],
    ) -> AgentRegistration:
        """Update an agent's metadata.

        Args:
            agent_id: Agent to update
            metadata: New/updated metadata entries

        Raises:
            ValueError: If agent not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        agent.metadata.update(metadata)
        agent.updated_at = datetime.now(UTC)
        return agent

    def suspend(self, agent_id: int) -> AgentRegistration:
        """Suspend an agent registration.

        Raises:
            ValueError: If agent not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        agent.status = RegistryStatus.SUSPENDED
        agent.updated_at = datetime.now(UTC)
        return agent

    def revoke(self, agent_id: int) -> AgentRegistration:
        """Revoke an agent registration.

        Raises:
            ValueError: If agent not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        agent.status = RegistryStatus.REVOKED
        agent.updated_at = datetime.now(UTC)
        return agent

    def format_display(self, agent_id: int) -> str:
        """Format agent display per ERC-8127: name.agentId@registry.

        Args:
            agent_id: Agent to format

        Returns:
            Display string
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return f"{agent_id}@{self._address or 'unknown'}"
        base = agent.display_name
        registry = self._address[:10] if self._address else self._name
        return f"{base}@{registry}"

    def total_agents(self) -> int:
        return len(self._agents)


def create_agent_registry(
    registry_name: str = "SardisAgentRegistry",
    registry_address: str = "",
    chain: str = "base",
) -> AgentRegistryManager:
    """Factory function to create an AgentRegistryManager."""
    return AgentRegistryManager(
        registry_name=registry_name,
        registry_address=registry_address,
        chain=chain,
    )
