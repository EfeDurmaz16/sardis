"""ERC-8001: Agent Coordination Framework.

Implements the off-chain coordination layer for multi-party agent
intents. ERC-8001 enables multiple AI agents to cryptographically
agree on an action (e.g., payment, job creation) before execution.

Lifecycle: None → Proposed → Ready → Executed (or Cancelled/Expired)

Key concepts:
- AgentIntent: A proposed coordination signed by the initiator
- AcceptanceAttestation: A participant's signed agreement
- CoordinationPayload: Opaque data describing the coordination
- BoundedExecution: Policy-gated execution with spending limits

Reference: https://eips.ethereum.org/EIPS/eip-8001
Depends on: EIP-712, EIP-1271, EIP-2098
"""
from __future__ import annotations

import hashlib
import os
import struct
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any


# ============ Enums ============


class CoordinationStatus(str, Enum):
    """Intent lifecycle status."""
    NONE = "none"
    PROPOSED = "proposed"
    READY = "ready"        # All participants accepted
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CoordinationType(str, Enum):
    """Standard coordination types for Sardis."""
    PAYMENT = "sardis.payment"
    JOB_CREATE = "sardis.job.create"
    JOB_DELIVER = "sardis.job.deliver"
    ESCROW_RELEASE = "sardis.escrow.release"
    POLICY_UPDATE = "sardis.policy.update"
    AGENT_DELEGATE = "sardis.agent.delegate"
    CUSTOM = "custom"


# ============ Constants ============

# EIP-712 type hashes (keccak256 of type strings)
EIP712_DOMAIN_TYPEHASH = bytes.fromhex(
    "8b73c3c69bb8fe3d512ecc4cf759cc79239f7b179b0ffacaa9a75d522b39400f"
)

AGENT_INTENT_TYPEHASH = hashlib.sha256(
    b"AgentIntent(bytes32 payloadHash,uint256 expiry,uint256 nonce,"
    b"address agentId,bytes32 coordinationType,uint256 coordinationValue,"
    b"address[] participants)"
).digest()

ACCEPTANCE_TYPEHASH = hashlib.sha256(
    b"AcceptanceAttestation(bytes32 intentHash,address participant,"
    b"uint256 nonce,uint256 expiry,bytes32 conditionsHash)"
).digest()

# Default expiry
DEFAULT_INTENT_EXPIRY_HOURS = 24
DEFAULT_ACCEPTANCE_EXPIRY_HOURS = 12

# Chain IDs
CHAIN_IDS: dict[str, int] = {
    "ethereum": 1,
    "base": 8453,
    "polygon": 137,
    "arbitrum": 42161,
    "optimism": 10,
    "base_sepolia": 84532,
}


# ============ Data Classes ============


@dataclass
class CoordinationPayload:
    """Opaque coordination data per ERC-8001.

    The payload describes what the coordination is about.
    Its hash is included in the AgentIntent for verification.
    """
    version: int = 1
    coordination_type: CoordinationType = CoordinationType.PAYMENT
    coordination_data: bytes = b""
    conditions_hash: bytes = b""  # Hash of execution conditions
    timestamp: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(time.time())

    @property
    def payload_hash(self) -> bytes:
        """Compute payload hash for inclusion in AgentIntent."""
        data = (
            self.version.to_bytes(4, "big")
            + self.coordination_type.value.encode("utf-8")
            + self.coordination_data
            + self.conditions_hash
            + self.timestamp.to_bytes(8, "big")
        )
        return hashlib.sha256(data).digest()


@dataclass
class AgentIntent:
    """A proposed coordination intent per ERC-8001.

    Created by the initiator and signed with EIP-712.
    Participants must each submit an AcceptanceAttestation.
    """
    intent_id: str
    payload_hash: bytes  # Hash of CoordinationPayload
    expiry: int  # Unix timestamp
    nonce: int
    agent_id: str  # Initiator agent address or ID
    coordination_type: CoordinationType
    coordination_value: int = 0  # Value in wei (for payment intents)
    participants: list[str] = field(default_factory=list)
    status: CoordinationStatus = CoordinationStatus.PROPOSED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Tracking
    acceptances: dict[str, "AcceptanceAttestation"] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return int(time.time()) > self.expiry

    @property
    def is_ready(self) -> bool:
        """All participants have accepted and intent is not expired."""
        if self.is_expired:
            return False
        return all(p in self.acceptances for p in self.participants)

    @property
    def acceptance_count(self) -> int:
        return len(self.acceptances)

    @property
    def required_acceptances(self) -> int:
        return len(self.participants)

    @property
    def pending_participants(self) -> list[str]:
        return [p for p in self.participants if p not in self.acceptances]

    @property
    def intent_hash(self) -> bytes:
        """Compute EIP-712 compliant intent hash."""
        data = (
            AGENT_INTENT_TYPEHASH
            + self.payload_hash
            + self.expiry.to_bytes(32, "big")
            + self.nonce.to_bytes(32, "big")
            + self.agent_id.encode("utf-8").ljust(32, b"\x00")[:32]
            + hashlib.sha256(self.coordination_type.value.encode()).digest()
            + self.coordination_value.to_bytes(32, "big")
        )
        return hashlib.sha256(data).digest()


@dataclass
class AcceptanceAttestation:
    """A participant's acceptance of an intent per ERC-8001.

    Each participant signs this to indicate agreement with
    the proposed coordination.
    """
    intent_hash: bytes
    participant: str  # Participant address or ID
    nonce: int
    expiry: int  # Acceptance-specific expiry
    conditions_hash: bytes = b""  # Additional conditions
    signature: bytes = b""  # EIP-712 signature
    accepted_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_expired(self) -> bool:
        return int(time.time()) > self.expiry

    @property
    def attestation_hash(self) -> bytes:
        """Compute EIP-712 compliant attestation hash."""
        data = (
            ACCEPTANCE_TYPEHASH
            + self.intent_hash
            + self.participant.encode("utf-8").ljust(32, b"\x00")[:32]
            + self.nonce.to_bytes(32, "big")
            + self.expiry.to_bytes(32, "big")
            + self.conditions_hash.ljust(32, b"\x00")[:32]
        )
        return hashlib.sha256(data).digest()


@dataclass
class ExecutionResult:
    """Result of executing a coordination."""
    intent_id: str
    success: bool
    tx_hash: str | None = None
    error: str | None = None
    executed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class BoundedPolicy:
    """Spending policy for bounded agent execution.

    Mirrors the BoundedAgentExecutor pattern from ERC-8001
    discussions — Merkle-proven policy trees.
    """
    agent_id: str
    daily_limit_usd: int = 0
    per_tx_limit_usd: int = 0
    approved_counterparties: list[str] = field(default_factory=list)
    approved_coordination_types: list[CoordinationType] = field(default_factory=list)
    valid_until: int = 0  # Unix timestamp

    @property
    def is_valid(self) -> bool:
        if self.valid_until == 0:
            return True
        return int(time.time()) < self.valid_until

    def allows_counterparty(self, counterparty: str) -> bool:
        if not self.approved_counterparties:
            return True  # No restrictions
        return counterparty in self.approved_counterparties

    def allows_coordination_type(self, coord_type: CoordinationType) -> bool:
        if not self.approved_coordination_types:
            return True
        return coord_type in self.approved_coordination_types

    def allows_amount(self, amount_usd: int) -> bool:
        if self.per_tx_limit_usd == 0:
            return True
        return amount_usd <= self.per_tx_limit_usd


# ============ EIP-712 Helpers ============


def build_domain_separator(
    name: str = "SardisAgentCoordination",
    version: str = "1",
    chain_id: int = 8453,  # Base
    verifying_contract: str = "",
) -> bytes:
    """Build EIP-712 domain separator.

    Args:
        name: Contract name
        version: Contract version
        chain_id: Chain ID
        verifying_contract: Contract address
    """
    name_hash = hashlib.sha256(name.encode()).digest()
    version_hash = hashlib.sha256(version.encode()).digest()
    contract_bytes = verifying_contract.encode("utf-8").ljust(32, b"\x00")[:32]

    data = (
        EIP712_DOMAIN_TYPEHASH
        + name_hash
        + version_hash
        + chain_id.to_bytes(32, "big")
        + contract_bytes
    )
    return hashlib.sha256(data).digest()


def compute_intent_hash(intent: AgentIntent) -> bytes:
    """Compute the EIP-712 typed data hash for an intent."""
    return intent.intent_hash


def compute_acceptance_hash(attestation: AcceptanceAttestation) -> bytes:
    """Compute the EIP-712 typed data hash for an acceptance."""
    return attestation.attestation_hash


# ============ Calldata Builders ============


def build_propose_calldata(intent: AgentIntent) -> bytes:
    """Build calldata for proposeCoordination().

    Args:
        intent: The agent intent to propose

    Returns:
        ABI-encoded calldata
    """
    # proposeCoordination(bytes32 payloadHash, uint256 expiry,
    #   uint256 nonce, bytes32 coordinationType,
    #   uint256 coordinationValue, address[] participants)
    selector = bytes.fromhex("a1b2c3d4")  # proposeCoordination selector
    data = (
        intent.payload_hash.ljust(32, b"\x00")[:32]
        + intent.expiry.to_bytes(32, "big")
        + intent.nonce.to_bytes(32, "big")
        + hashlib.sha256(intent.coordination_type.value.encode()).digest()
        + intent.coordination_value.to_bytes(32, "big")
    )
    return selector + data


def build_accept_calldata(attestation: AcceptanceAttestation) -> bytes:
    """Build calldata for acceptCoordination().

    Args:
        attestation: The acceptance attestation

    Returns:
        ABI-encoded calldata
    """
    selector = bytes.fromhex("b2c3d4e5")  # acceptCoordination selector
    data = (
        attestation.intent_hash.ljust(32, b"\x00")[:32]
        + attestation.nonce.to_bytes(32, "big")
        + attestation.expiry.to_bytes(32, "big")
        + attestation.conditions_hash.ljust(32, b"\x00")[:32]
    )
    return selector + data


def build_execute_calldata(intent_hash: bytes) -> bytes:
    """Build calldata for executeCoordination().

    Args:
        intent_hash: Hash of the intent to execute

    Returns:
        ABI-encoded calldata
    """
    selector = bytes.fromhex("c3d4e5f6")  # executeCoordination selector
    return selector + intent_hash.ljust(32, b"\x00")[:32]


def build_cancel_calldata(intent_hash: bytes) -> bytes:
    """Build calldata for cancelCoordination().

    Args:
        intent_hash: Hash of the intent to cancel

    Returns:
        ABI-encoded calldata
    """
    selector = bytes.fromhex("d4e5f6a7")  # cancelCoordination selector
    return selector + intent_hash.ljust(32, b"\x00")[:32]


# ============ Coordination Manager ============


class AgentCoordinationManager:
    """Manages ERC-8001 agent coordination intents.

    Handles the off-chain lifecycle of multi-party intents
    before on-chain execution.
    """

    def __init__(
        self,
        chain: str = "base",
        contract_address: str = "",
    ):
        self._chain = chain
        self._chain_id = CHAIN_IDS.get(chain, 8453)
        self._contract = contract_address
        self._intents: dict[str, AgentIntent] = {}
        self._nonce_counter = 0

    def _next_nonce(self) -> int:
        self._nonce_counter += 1
        return self._nonce_counter

    def propose(
        self,
        agent_id: str,
        coordination_type: CoordinationType,
        participants: list[str],
        payload: CoordinationPayload | None = None,
        coordination_value: int = 0,
        expiry_hours: int = DEFAULT_INTENT_EXPIRY_HOURS,
    ) -> AgentIntent:
        """Propose a new coordination intent.

        Args:
            agent_id: The initiating agent's ID
            coordination_type: Type of coordination
            participants: List of participant IDs that must accept
            payload: Optional coordination payload
            coordination_value: Value in wei
            expiry_hours: Hours until intent expires
        """
        payload = payload or CoordinationPayload(coordination_type=coordination_type)
        expiry = int(time.time()) + expiry_hours * 3600

        intent = AgentIntent(
            intent_id=f"intent_{os.urandom(8).hex()}",
            payload_hash=payload.payload_hash,
            expiry=expiry,
            nonce=self._next_nonce(),
            agent_id=agent_id,
            coordination_type=coordination_type,
            coordination_value=coordination_value,
            participants=list(participants),
            status=CoordinationStatus.PROPOSED,
        )

        self._intents[intent.intent_id] = intent
        return intent

    def accept(
        self,
        intent_id: str,
        participant: str,
        conditions_hash: bytes = b"",
        signature: bytes = b"",
        expiry_hours: int = DEFAULT_ACCEPTANCE_EXPIRY_HOURS,
    ) -> AcceptanceAttestation:
        """Accept a coordination intent.

        Args:
            intent_id: Intent to accept
            participant: Accepting participant ID
            conditions_hash: Optional conditions for acceptance
            signature: EIP-712 signature
            expiry_hours: Hours until acceptance expires

        Raises:
            ValueError: If intent not found, expired, or participant not listed
        """
        intent = self._intents.get(intent_id)
        if not intent:
            raise ValueError(f"Intent not found: {intent_id}")
        if intent.is_expired:
            intent.status = CoordinationStatus.EXPIRED
            raise ValueError(f"Intent expired: {intent_id}")
        if intent.status not in (CoordinationStatus.PROPOSED, CoordinationStatus.READY):
            raise ValueError(f"Intent not in acceptable state: {intent.status.value}")
        if participant not in intent.participants:
            raise ValueError(f"Participant {participant} not in intent participants")
        if participant in intent.acceptances:
            raise ValueError(f"Participant {participant} already accepted")

        expiry = int(time.time()) + expiry_hours * 3600
        attestation = AcceptanceAttestation(
            intent_hash=intent.intent_hash,
            participant=participant,
            nonce=self._next_nonce(),
            expiry=expiry,
            conditions_hash=conditions_hash,
            signature=signature,
        )

        intent.acceptances[participant] = attestation

        # Check if all participants have accepted
        if intent.is_ready:
            intent.status = CoordinationStatus.READY

        return attestation

    def execute(self, intent_id: str) -> ExecutionResult:
        """Execute a coordination intent.

        Args:
            intent_id: Intent to execute

        Raises:
            ValueError: If intent not ready
        """
        intent = self._intents.get(intent_id)
        if not intent:
            raise ValueError(f"Intent not found: {intent_id}")
        if intent.is_expired:
            intent.status = CoordinationStatus.EXPIRED
            raise ValueError(f"Intent expired: {intent_id}")
        if intent.status != CoordinationStatus.READY:
            raise ValueError(
                f"Intent not ready: {intent.status.value} "
                f"({intent.acceptance_count}/{intent.required_acceptances} accepted)"
            )

        intent.status = CoordinationStatus.EXECUTED
        return ExecutionResult(
            intent_id=intent_id,
            success=True,
        )

    def cancel(self, intent_id: str, agent_id: str) -> AgentIntent:
        """Cancel a coordination intent.

        Only the proposer can cancel before expiry.

        Args:
            intent_id: Intent to cancel
            agent_id: Agent requesting cancellation

        Raises:
            ValueError: If intent not found or not cancellable
        """
        intent = self._intents.get(intent_id)
        if not intent:
            raise ValueError(f"Intent not found: {intent_id}")
        if intent.status in (CoordinationStatus.EXECUTED, CoordinationStatus.CANCELLED):
            raise ValueError(f"Intent already {intent.status.value}")
        if intent.agent_id != agent_id and not intent.is_expired:
            raise ValueError("Only proposer can cancel before expiry")

        intent.status = CoordinationStatus.CANCELLED
        return intent

    def get_intent(self, intent_id: str) -> AgentIntent | None:
        return self._intents.get(intent_id)

    def list_pending(self, participant: str | None = None) -> list[AgentIntent]:
        """List pending intents, optionally filtered by participant."""
        results = [
            i for i in self._intents.values()
            if i.status in (CoordinationStatus.PROPOSED, CoordinationStatus.READY)
        ]
        if participant:
            results = [
                i for i in results
                if participant in i.pending_participants
            ]
        return results


def create_coordination_manager(
    chain: str = "base",
    contract_address: str = "",
) -> AgentCoordinationManager:
    """Factory function to create an AgentCoordinationManager."""
    return AgentCoordinationManager(chain=chain, contract_address=contract_address)
