"""ERC-8004 Trustless Agents on-chain identity registry support."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class AgentMetadata:
    """Agent metadata following ERC-8004 agentURI JSON schema."""

    name: str
    description: str
    version: str
    model_type: str  # e.g. "gpt-4", "claude-3-opus"
    capabilities: list[str] = field(default_factory=list)  # e.g. ["payment", "research", "trading"]
    service_endpoints: dict[str, str] = field(default_factory=dict)  # e.g. {"webhook": "https://..."}
    trust_config: dict[str, str] = field(default_factory=dict)  # e.g. {"policy_hash": "0x...", "verification": "..."}
    protocols_supported: list[str] = field(default_factory=lambda: ["a2a", "ap2"])  # ["a2a", "mcp", "ap2"]

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for agentURI."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "model_type": self.model_type,
            "capabilities": self.capabilities,
            "service_endpoints": self.service_endpoints,
            "trust_config": self.trust_config,
            "protocols_supported": self.protocols_supported,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentMetadata:
        """Parse from JSON dict."""
        return cls(
            name=data["name"],
            description=data["description"],
            version=data["version"],
            model_type=data["model_type"],
            capabilities=data.get("capabilities", []),
            service_endpoints=data.get("service_endpoints", {}),
            trust_config=data.get("trust_config", {}),
            protocols_supported=data.get("protocols_supported", ["a2a", "ap2"]),
        )


@dataclass(slots=True)
class AgentIdentity:
    """ERC-8004 Agent Identity record."""

    agent_id: str  # Token ID (uint256 as string)
    owner_address: str  # Ethereum address that owns this agent NFT
    agent_uri: str  # IPFS/HTTP URI pointing to AgentMetadata JSON
    metadata: dict  # Cached metadata from agentURI
    created_at: int
    chain_id: int  # Chain where this identity is registered

    @property
    def did(self) -> str:
        """Decentralized identifier for this agent."""
        return f"did:erc8004:{self.chain_id}:{self.agent_id}"

    @property
    def ens_name(self) -> str | None:
        """ENS name binding if available."""
        return self.metadata.get("ens_name")


@dataclass(slots=True)
class ReputationEntry:
    """On-chain reputation entry between agents."""

    from_agent: str  # Agent ID giving reputation
    to_agent: str  # Agent ID receiving reputation
    score: int  # 0-1000 reputation score
    category: str  # e.g. "reliability", "speed", "quality"
    timestamp: int
    transaction_hash: str


@dataclass(slots=True)
class ValidationResult:
    """Validation attestation from trusted validator."""

    validator_address: str  # Address of validator
    agent_id: str  # Agent being validated
    is_valid: bool
    validation_type: str  # e.g. "kyc", "certification", "audit"
    evidence_uri: str  # IPFS/HTTP URI to validation evidence
    timestamp: int
    transaction_hash: str | None = None


class ERC8004Registry(ABC):
    """
    Abstract interface for ERC-8004 agent identity registry.

    ERC-8004 defines three on-chain registries:
    1. Identity Registry (ERC-721 based)
    2. Reputation Registry
    3. Validation Registry

    Each agent gets a unique agentId (NFT token ID) with metadata URI.
    """

    @abstractmethod
    async def register_agent(self, owner: str, metadata: AgentMetadata) -> AgentIdentity:
        """
        Register a new agent identity on-chain.

        Args:
            owner: Ethereum address that will own the agent NFT
            metadata: Agent metadata (will be uploaded to IPFS/storage)

        Returns:
            AgentIdentity with assigned agent_id and agent_uri
        """
        ...

    @abstractmethod
    async def get_agent(self, agent_id: str) -> AgentIdentity | None:
        """
        Retrieve agent identity by ID.

        Args:
            agent_id: Agent token ID

        Returns:
            AgentIdentity or None if not found
        """
        ...

    @abstractmethod
    async def update_metadata(self, agent_id: str, metadata: AgentMetadata) -> bool:
        """
        Update agent metadata URI (only by owner).

        Args:
            agent_id: Agent token ID
            metadata: New metadata

        Returns:
            True if updated successfully
        """
        ...

    @abstractmethod
    async def submit_reputation(self, entry: ReputationEntry) -> str:
        """
        Submit reputation score for an agent.

        Args:
            entry: Reputation entry

        Returns:
            Transaction hash
        """
        ...

    @abstractmethod
    async def get_reputation(self, agent_id: str) -> list[ReputationEntry]:
        """
        Get all reputation entries for an agent.

        Args:
            agent_id: Agent token ID

        Returns:
            List of reputation entries
        """
        ...

    @abstractmethod
    async def get_reputation_score(self, agent_id: str) -> float:
        """
        Get aggregate reputation score (0-1000).

        Args:
            agent_id: Agent token ID

        Returns:
            Aggregated reputation score
        """
        ...

    @abstractmethod
    async def validate_agent(self, agent_id: str, validator: str, result: ValidationResult) -> str:
        """
        Submit validation attestation for an agent.

        Args:
            agent_id: Agent token ID
            validator: Validator address
            result: Validation result

        Returns:
            Transaction hash
        """
        ...

    @abstractmethod
    async def get_validations(self, agent_id: str) -> list[ValidationResult]:
        """
        Get all validation results for an agent.

        Args:
            agent_id: Agent token ID

        Returns:
            List of validation results
        """
        ...

    @abstractmethod
    async def resolve_agent_uri(self, agent_id: str) -> str:
        """
        Resolve agentURI for an agent.

        Args:
            agent_id: Agent token ID

        Returns:
            Agent URI (IPFS/HTTP)
        """
        ...


class InMemoryERC8004Registry(ERC8004Registry):
    """In-memory implementation for testing/development."""

    def __init__(self, chain_id: int = 1):
        self.chain_id = chain_id
        self._agents: dict[str, AgentIdentity] = {}
        self._reputation: dict[str, list[ReputationEntry]] = {}
        self._validations: dict[str, list[ValidationResult]] = {}
        self._next_id = 1

    async def register_agent(self, owner: str, metadata: AgentMetadata) -> AgentIdentity:
        agent_id = str(self._next_id)
        self._next_id += 1

        # Simulate IPFS upload
        agent_uri = f"ipfs://Qm{agent_id}{'0' * 40}"

        identity = AgentIdentity(
            agent_id=agent_id,
            owner_address=owner,
            agent_uri=agent_uri,
            metadata=metadata.to_dict(),
            created_at=int(time.time()),
            chain_id=self.chain_id,
        )
        self._agents[agent_id] = identity
        return identity

    async def get_agent(self, agent_id: str) -> AgentIdentity | None:
        return self._agents.get(agent_id)

    async def update_metadata(self, agent_id: str, metadata: AgentMetadata) -> bool:
        if agent_id not in self._agents:
            return False
        self._agents[agent_id].metadata = metadata.to_dict()
        self._agents[agent_id].agent_uri = f"ipfs://Qm{agent_id}{'1' * 40}"
        return True

    async def submit_reputation(self, entry: ReputationEntry) -> str:
        if entry.to_agent not in self._reputation:
            self._reputation[entry.to_agent] = []
        self._reputation[entry.to_agent].append(entry)
        return f"0x{'abc123' * 10}"

    async def get_reputation(self, agent_id: str) -> list[ReputationEntry]:
        return self._reputation.get(agent_id, [])

    async def get_reputation_score(self, agent_id: str) -> float:
        entries = await self.get_reputation(agent_id)
        if not entries:
            return 0.0
        return sum(e.score for e in entries) / len(entries)

    async def validate_agent(self, agent_id: str, validator: str, result: ValidationResult) -> str:
        if agent_id not in self._validations:
            self._validations[agent_id] = []
        self._validations[agent_id].append(result)
        return f"0x{'def456' * 10}"

    async def get_validations(self, agent_id: str) -> list[ValidationResult]:
        return self._validations.get(agent_id, [])

    async def resolve_agent_uri(self, agent_id: str) -> str:
        agent = await self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        return agent.agent_uri
