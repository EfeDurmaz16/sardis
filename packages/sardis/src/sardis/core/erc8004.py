"""ERC-8004: Trustless Agents — on-chain identity, reputation, and validation.

Integrates with the ERC-8004 Identity Registry and Reputation Registry for
agent discovery and trust scoring. Each Sardis-managed agent is registered as
an ERC-721 identity NFT with a bound MPC wallet address.

Three on-chain registries (singleton per chain):
- Identity Registry: ERC-721 agent NFTs with agentURI and wallet binding
- Reputation Registry: Bounded feedback scores with tags and evidence
- Validation Registry: Independent validator attestations (zkML, TEE, etc.)

Spec: https://eips.ethereum.org/EIPS/eip-8004
Ref impl: https://github.com/erc-8004/erc-8004-contracts
Deployed: 2026-01-29 (Ethereum, Base, Polygon, Arbitrum, + 10 more chains)

Issue: #137
"""
from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from eth_abi import encode
from web3 import Web3

logger = logging.getLogger(__name__)

# ============ Deployed Contract Addresses ============
# Vanity-prefix addresses, deterministic across all chains

ERC8004_ADDRESSES = {
    "identity_registry": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
    "reputation_registry": "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
}

# ============ Service Types ============

SERVICE_TYPE_A2A = "A2A"
SERVICE_TYPE_MCP = "MCP"
SERVICE_TYPE_WEB = "web"
SERVICE_TYPE_OASF = "OASF"

# ============ Trust Models ============

TRUST_REPUTATION = "reputation"
TRUST_CRYPTO_ECONOMIC = "crypto-economic"
TRUST_TEE_ATTESTATION = "tee-attestation"

# ============ Function Selectors ============

REGISTER_SELECTOR = Web3.keccak(text="register(string,(string,bytes)[])")[:4]
SET_AGENT_URI_SELECTOR = Web3.keccak(text="setAgentURI(uint256,string)")[:4]
SET_AGENT_WALLET_SELECTOR = Web3.keccak(
    text="setAgentWallet(uint256,address,uint256,bytes)"
)[:4]
UNSET_AGENT_WALLET_SELECTOR = Web3.keccak(text="unsetAgentWallet(uint256)")[:4]
SET_METADATA_SELECTOR = Web3.keccak(text="setMetadata(uint256,string,bytes)")[:4]
GIVE_FEEDBACK_SELECTOR = Web3.keccak(
    text="giveFeedback(uint256,int128,uint8,string,string,string,string,bytes32)"
)[:4]
REVOKE_FEEDBACK_SELECTOR = Web3.keccak(text="revokeFeedback(uint256,uint64)")[:4]
GET_SUMMARY_SELECTOR = Web3.keccak(
    text="getSummary(uint256,address[],string,string)"
)[:4]

# EIP-712 type hashes for wallet binding
EIP712_DOMAIN_TYPEHASH = Web3.keccak(
    text="EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
)
WALLET_BINDING_TYPEHASH = Web3.keccak(
    text="SetAgentWallet(uint256 agentId,address wallet,uint256 deadline)"
)


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


# ============ ERC-8004 Spec-Compliant Types ============


@dataclass
class AgentService:
    """A service endpoint advertised by an agent per ERC-8004 spec."""
    name: str  # A2A, MCP, web, OASF, etc.
    endpoint: str  # URL to service

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "endpoint": self.endpoint}


@dataclass
class AgentRegistrationFile:
    """Off-chain agent registration file (agentURI JSON).

    Conforms to the ERC-8004 registration-v1 schema. This is the JSON
    document that the agentURI points to.
    """
    name: str
    description: str
    services: list[AgentService] = field(default_factory=list)
    image: str | None = None
    x402_support: bool = True  # Sardis agents support x402
    active: bool = True
    supported_trust: list[str] = field(
        default_factory=lambda: [TRUST_REPUTATION]
    )
    registrations: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize to ERC-8004 registration-v1 JSON."""
        data: dict[str, Any] = {
            "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
            "name": self.name,
            "description": self.description,
            "active": self.active,
            "x402Support": self.x402_support,
            "services": [s.to_dict() for s in self.services],
            "supportedTrust": self.supported_trust,
        }
        if self.image:
            data["image"] = self.image
        if self.registrations:
            data["registrations"] = self.registrations
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, raw: str) -> AgentRegistrationFile:
        """Parse an ERC-8004 registration JSON."""
        data = json.loads(raw)
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            services=[
                AgentService(name=s["name"], endpoint=s["endpoint"])
                for s in data.get("services", [])
            ],
            image=data.get("image"),
            x402_support=data.get("x402Support", False),
            active=data.get("active", True),
            supported_trust=data.get("supportedTrust", []),
            registrations=data.get("registrations", []),
        )


@dataclass
class ReputationFeedback:
    """Feedback to submit to the ERC-8004 Reputation Registry."""
    agent_id: int
    value: int  # int128 score (can be negative)
    value_decimals: int = 2
    tag1: str = ""
    tag2: str = ""
    endpoint: str = ""
    feedback_uri: str = ""
    feedback_hash: bytes = field(default_factory=lambda: b"\x00" * 32)


@dataclass
class ReputationSummary:
    """Aggregated reputation summary from the Reputation Registry."""
    agent_id: int
    count: int
    value: int  # int128 aggregate score
    value_decimals: int

    @property
    def normalized_score(self) -> float:
        """Score normalized to 0.0-1.0 range (from -100 to +100)."""
        raw = self.value / (10 ** self.value_decimals)
        return max(0.0, min(1.0, (raw + 100) / 200))


# ============ Registration File Builder ============


def build_sardis_agent_registration(
    agent_name: str,
    description: str,
    api_endpoint: str | None = None,
    a2a_endpoint: str | None = None,
    mcp_endpoint: str | None = None,
    image_url: str | None = None,
    agent_id: int | None = None,
    chain_id: int = 8453,
) -> AgentRegistrationFile:
    """Build an ERC-8004 registration for a Sardis-managed agent.

    Sardis agents advertise x402 support by default and use the
    reputation trust model.

    Args:
        agent_name: Human-readable agent name.
        description: Agent description.
        api_endpoint: Web API endpoint URL.
        a2a_endpoint: Agent-to-Agent protocol endpoint.
        mcp_endpoint: MCP server endpoint.
        image_url: Agent avatar URL.
        agent_id: On-chain agent ID (if already registered).
        chain_id: Chain where agent is registered.

    Returns:
        AgentRegistrationFile ready for JSON serialization and upload.
    """
    services: list[AgentService] = []
    if api_endpoint:
        services.append(AgentService(name=SERVICE_TYPE_WEB, endpoint=api_endpoint))
    if a2a_endpoint:
        services.append(AgentService(name=SERVICE_TYPE_A2A, endpoint=a2a_endpoint))
    if mcp_endpoint:
        services.append(AgentService(name=SERVICE_TYPE_MCP, endpoint=mcp_endpoint))

    registrations: list[dict[str, Any]] = []
    if agent_id is not None:
        identity_addr = ERC8004_ADDRESSES["identity_registry"]
        registrations.append({
            "agentId": agent_id,
            "agentRegistry": f"erc8004:{chain_id}:{identity_addr}",
        })

    return AgentRegistrationFile(
        name=agent_name,
        description=description,
        services=services,
        image=image_url,
        x402_support=True,
        active=True,
        supported_trust=[TRUST_REPUTATION],
        registrations=registrations,
    )


# ============ Calldata Builders ============


def build_register_calldata(
    agent_uri: str,
    metadata: list[tuple[str, bytes]] | None = None,
) -> bytes:
    """Build register(string,(string,bytes)[]) calldata for Identity Registry."""
    meta = metadata or []
    params = encode(["string", "(string,bytes)[]"], [agent_uri, meta])
    return REGISTER_SELECTOR + params


def build_set_agent_uri_calldata(agent_id: int, new_uri: str) -> bytes:
    """Build setAgentURI(uint256,string) calldata."""
    params = encode(["uint256", "string"], [agent_id, new_uri])
    return SET_AGENT_URI_SELECTOR + params


def build_set_agent_wallet_calldata(
    agent_id: int,
    wallet_address: str,
    deadline: int,
    signature: bytes,
) -> bytes:
    """Build setAgentWallet(uint256,address,uint256,bytes) calldata.

    Binds a wallet address to an agent identity. The wallet must prove
    control via EIP-712 (EOA) or ERC-1271 (smart contract) signature.
    """
    params = encode(
        ["uint256", "address", "uint256", "bytes"],
        [agent_id, Web3.to_checksum_address(wallet_address), deadline, signature],
    )
    return SET_AGENT_WALLET_SELECTOR + params


def build_unset_agent_wallet_calldata(agent_id: int) -> bytes:
    """Build unsetAgentWallet(uint256) calldata."""
    return UNSET_AGENT_WALLET_SELECTOR + encode(["uint256"], [agent_id])


def build_set_metadata_calldata(
    agent_id: int, key: str, value: bytes
) -> bytes:
    """Build setMetadata(uint256,string,bytes) calldata."""
    params = encode(["uint256", "string", "bytes"], [agent_id, key, value])
    return SET_METADATA_SELECTOR + params


def build_give_feedback_calldata(feedback: ReputationFeedback) -> bytes:
    """Build giveFeedback calldata for Reputation Registry."""
    params = encode(
        ["uint256", "int128", "uint8", "string", "string", "string", "string", "bytes32"],
        [
            feedback.agent_id, feedback.value, feedback.value_decimals,
            feedback.tag1, feedback.tag2, feedback.endpoint,
            feedback.feedback_uri, feedback.feedback_hash,
        ],
    )
    return GIVE_FEEDBACK_SELECTOR + params


def build_revoke_feedback_calldata(agent_id: int, feedback_index: int) -> bytes:
    """Build revokeFeedback(uint256,uint64) calldata."""
    return REVOKE_FEEDBACK_SELECTOR + encode(
        ["uint256", "uint64"], [agent_id, feedback_index]
    )


def build_get_summary_calldata(
    agent_id: int,
    client_addresses: list[str] | None = None,
    tag1: str = "",
    tag2: str = "",
) -> bytes:
    """Build getSummary(uint256,address[],string,string) calldata."""
    addrs = [Web3.to_checksum_address(a) for a in (client_addresses or [])]
    params = encode(
        ["uint256", "address[]", "string", "string"],
        [agent_id, addrs, tag1, tag2],
    )
    return GET_SUMMARY_SELECTOR + params


# ============ EIP-712 Wallet Binding ============


def build_wallet_binding_digest(
    agent_id: int,
    wallet_address: str,
    deadline: int,
    chain_id: int,
    identity_registry: str | None = None,
) -> bytes:
    """Build EIP-712 digest for setAgentWallet signature proof.

    The wallet owner must sign this to prove they control the address
    being bound to the agent identity.

    Args:
        agent_id: On-chain agent NFT ID.
        wallet_address: Wallet address to bind.
        deadline: Signature expiry timestamp.
        chain_id: Chain ID for EIP-712 domain.
        identity_registry: Override registry address.

    Returns:
        32-byte EIP-712 digest to be signed.
    """
    registry = identity_registry or ERC8004_ADDRESSES["identity_registry"]

    domain_separator = Web3.keccak(
        EIP712_DOMAIN_TYPEHASH
        + Web3.keccak(text="ERC8004IdentityRegistry")
        + Web3.keccak(text="1")
        + encode(["uint256"], [chain_id])
        + encode(["address"], [Web3.to_checksum_address(registry)])
    )

    struct_hash = Web3.keccak(
        WALLET_BINDING_TYPEHASH
        + encode(["uint256"], [agent_id])
        + encode(["address"], [Web3.to_checksum_address(wallet_address)])
        + encode(["uint256"], [deadline])
    )

    return Web3.keccak(b"\x19\x01" + domain_separator + struct_hash)


# ============ Namespace & Global ID ============


def build_agent_namespace(
    chain_id: int,
    identity_registry: str | None = None,
) -> str:
    """Build the ERC-8004 agent namespace: erc8004:{chainId}:{registryAddr}."""
    registry = identity_registry or ERC8004_ADDRESSES["identity_registry"]
    return f"erc8004:{chain_id}:{registry}"


def build_agent_global_id(
    agent_id: int,
    chain_id: int,
    identity_registry: str | None = None,
) -> str:
    """Build globally unique agent ID: erc8004:{chainId}:{registry}:{agentId}."""
    return f"{build_agent_namespace(chain_id, identity_registry)}:{agent_id}"
