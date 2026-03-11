"""Paladin Privacy: Privacy-preserving transactions for AI agents.

Implements privacy domains inspired by the Paladin framework from
LF Decentralized Trust. Sardis acts as the notary for private agent
transactions using the Noto (notarized UTXO) model.

Key domains:
- Noto: Notarized UTXO tokens — notary validates transfers off-chain
- Zeto: ZK proof tokens — zero-knowledge proofs for confidential amounts
- Pente: Privacy groups — private state with endorsement policies

Lifecycle: UTXO created → included in PrivateTransfer → notary validates →
  inputs SPENT, outputs UNSPENT (approve) or inputs restored (reject)

Reference: https://lf-decentralized-trust-labs.github.io/paladin/
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


# ============ Enums ============


class PrivacyDomain(str, Enum):
    """Paladin privacy domain types."""
    NOTO = "noto"          # Notarized UTXO tokens
    ZETO = "zeto"          # ZK proof tokens
    PENTE = "pente"        # Privacy groups
    CUSTOM = "custom"


class PrivacyLevel(str, Enum):
    """Transaction privacy level."""
    PUBLIC = "public"              # Fully visible on-chain
    PRIVATE = "private"            # Hidden from non-participants
    CONFIDENTIAL = "confidential"  # Amounts hidden, parties visible
    ANONYMOUS = "anonymous"        # Both amounts and parties hidden


class NotaryDecision(str, Enum):
    """Notary validation decision."""
    APPROVE = "approve"
    REJECT = "reject"
    PENDING = "pending"


class UTXOState(str, Enum):
    """UTXO lifecycle state."""
    UNSPENT = "unspent"
    SPENT = "spent"
    LOCKED = "locked"


class PrivacyGroupStatus(str, Enum):
    """Privacy group lifecycle status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISSOLVED = "dissolved"


# ============ Constants ============

PALADIN_VERSION = "0.1.0"
DEFAULT_ENDORSEMENT_POLICY = "all"
SUPPORTED_PRIVACY_TOKENS = frozenset({"USDC", "EURC", "USDT"})
MAX_UTXO_INPUTS = 10


# ============ Data Classes ============


@dataclass
class UTXO:
    """An unspent transaction output in the Noto model.

    UTXOs are created during transfers and consumed (spent) when
    used as inputs to new transfers. The notary validates state
    transitions.
    """
    utxo_id: str
    owner: str
    amount: int
    token: str = "USDC"
    state: UTXOState = UTXOState.UNSPENT
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    spent_at: datetime | None = None

    @property
    def is_spendable(self) -> bool:
        """Only UNSPENT UTXOs can be used as transfer inputs."""
        return self.state == UTXOState.UNSPENT


@dataclass
class PrivacyGroup:
    """A Pente privacy group with endorsement policies.

    Members share private state and must endorse transactions
    according to the group's endorsement policy.
    """
    group_id: str
    name: str
    members: list[str] = field(default_factory=list)
    endorsement_policy: str = DEFAULT_ENDORSEMENT_POLICY
    status: PrivacyGroupStatus = PrivacyGroupStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_active(self) -> bool:
        return self.status == PrivacyGroupStatus.ACTIVE

    @property
    def member_count(self) -> int:
        return len(self.members)

    def is_member(self, address: str) -> bool:
        """Check if an address is a group member."""
        return address in self.members

    def add_member(self, address: str) -> None:
        """Add a member to the group."""
        if address not in self.members:
            self.members.append(address)

    def remove_member(self, address: str) -> None:
        """Remove a member from the group."""
        if address in self.members:
            self.members.remove(address)


@dataclass
class PrivateTransfer:
    """A private transfer between agents using the Noto model.

    The transfer selects input UTXOs from the sender, creates output
    UTXOs for the receiver (and change back to sender), and waits
    for notary validation before finalizing state transitions.
    """
    transfer_id: str
    domain: PrivacyDomain
    sender: str
    receiver: str
    amount: int
    token: str = "USDC"
    inputs: list[str] = field(default_factory=list)    # Input UTXO IDs
    outputs: list[str] = field(default_factory=list)   # Output UTXO IDs
    privacy_level: PrivacyLevel = PrivacyLevel.PRIVATE
    notary_decision: NotaryDecision = NotaryDecision.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_approved(self) -> bool:
        return self.notary_decision == NotaryDecision.APPROVE

    @property
    def is_pending(self) -> bool:
        return self.notary_decision == NotaryDecision.PENDING


@dataclass
class NotaryValidation:
    """Record of a notary's validation decision on a transfer."""
    transfer_id: str
    notary: str
    decision: NotaryDecision
    reason: str = ""
    validated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ZKProofRequest:
    """A zero-knowledge proof request for the Zeto domain."""
    proof_id: str
    prover: str
    statement: str
    domain: PrivacyDomain = PrivacyDomain.ZETO
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class PrivacyConfig:
    """Configuration for the Paladin privacy manager."""
    domain: PrivacyDomain = PrivacyDomain.NOTO
    notary_address: str = ""
    privacy_level: PrivacyLevel = PrivacyLevel.PRIVATE
    require_endorsement: bool = True


# ============ Privacy Manager ============


class PaladinPrivacyManager:
    """Manages privacy-preserving transactions using the Paladin model.

    Sardis acts as the notary for private agent transactions. The manager
    handles UTXO lifecycle, transfer creation/validation, and privacy
    group management.
    """

    def __init__(self, config: PrivacyConfig | None = None):
        self._config = config or PrivacyConfig()
        self._utxos: dict[str, UTXO] = {}
        self._transfers: dict[str, PrivateTransfer] = {}
        self._groups: dict[str, PrivacyGroup] = {}
        self._nonce_counter = 0

    def _next_id(self, prefix: str) -> str:
        self._nonce_counter += 1
        return f"{prefix}_{uuid.uuid4().hex[:16]}"

    # ---- UTXO management ----

    def create_utxo(self, owner: str, amount: int, token: str = "USDC") -> UTXO:
        """Create a new UTXO for the given owner.

        Args:
            owner: Owner address or agent ID
            amount: Token amount
            token: Token symbol (default USDC)

        Returns:
            The created UTXO in UNSPENT state
        """
        utxo = UTXO(
            utxo_id=self._next_id("utxo"),
            owner=owner,
            amount=amount,
            token=token,
        )
        self._utxos[utxo.utxo_id] = utxo
        return utxo

    def get_utxo(self, utxo_id: str) -> UTXO | None:
        """Get a UTXO by ID."""
        return self._utxos.get(utxo_id)

    def get_utxos_for_owner(self, owner: str) -> list[UTXO]:
        """Get all unspent UTXOs for an owner.

        Args:
            owner: Owner address or agent ID

        Returns:
            List of UNSPENT UTXOs owned by the address
        """
        return [
            u for u in self._utxos.values()
            if u.owner == owner and u.state == UTXOState.UNSPENT
        ]

    def get_balance(self, owner: str, token: str = "USDC") -> int:
        """Get the total balance for an owner and token.

        Args:
            owner: Owner address or agent ID
            token: Token symbol

        Returns:
            Sum of unspent UTXO amounts
        """
        return sum(
            u.amount for u in self._utxos.values()
            if u.owner == owner and u.token == token and u.state == UTXOState.UNSPENT
        )

    # ---- Transfer operations ----

    def create_private_transfer(
        self,
        sender: str,
        receiver: str,
        amount: int,
        token: str = "USDC",
        privacy_level: PrivacyLevel = PrivacyLevel.PRIVATE,
    ) -> PrivateTransfer:
        """Create a private transfer between agents.

        Selects input UTXOs from the sender using FIFO ordering,
        creates output UTXOs for the receiver (and change for sender),
        and returns the transfer in PENDING state awaiting notary validation.

        Args:
            sender: Sender address or agent ID
            receiver: Receiver address or agent ID
            amount: Transfer amount
            token: Token symbol
            privacy_level: Desired privacy level

        Returns:
            The created PrivateTransfer in PENDING state

        Raises:
            ValueError: If sender has insufficient balance
        """
        # Check balance
        balance = self.get_balance(sender, token)
        if balance < amount:
            raise ValueError(
                f"Insufficient balance: {sender} has {balance} {token}, "
                f"needs {amount}"
            )

        # Select input UTXOs (FIFO by creation time)
        sender_utxos = sorted(
            [
                u for u in self._utxos.values()
                if u.owner == sender and u.token == token and u.state == UTXOState.UNSPENT
            ],
            key=lambda u: u.created_at,
        )

        selected_inputs: list[UTXO] = []
        total_input = 0
        for utxo in sender_utxos:
            selected_inputs.append(utxo)
            total_input += utxo.amount
            if total_input >= amount:
                break

        # Lock selected inputs
        for utxo in selected_inputs:
            utxo.state = UTXOState.LOCKED

        # Create output UTXOs
        output_utxos: list[UTXO] = []

        # Receiver output
        receiver_utxo = UTXO(
            utxo_id=self._next_id("utxo"),
            owner=receiver,
            amount=amount,
            token=token,
            state=UTXOState.LOCKED,  # Locked until notary approves
        )
        self._utxos[receiver_utxo.utxo_id] = receiver_utxo
        output_utxos.append(receiver_utxo)

        # Change output (if any)
        change = total_input - amount
        if change > 0:
            change_utxo = UTXO(
                utxo_id=self._next_id("utxo"),
                owner=sender,
                amount=change,
                token=token,
                state=UTXOState.LOCKED,
            )
            self._utxos[change_utxo.utxo_id] = change_utxo
            output_utxos.append(change_utxo)

        # Create transfer record
        transfer = PrivateTransfer(
            transfer_id=self._next_id("txfr"),
            domain=self._config.domain,
            sender=sender,
            receiver=receiver,
            amount=amount,
            token=token,
            inputs=[u.utxo_id for u in selected_inputs],
            outputs=[u.utxo_id for u in output_utxos],
            privacy_level=privacy_level,
        )

        self._transfers[transfer.transfer_id] = transfer
        return transfer

    def validate_transfer(
        self,
        transfer_id: str,
        notary: str,
        decision: NotaryDecision,
        reason: str = "",
    ) -> NotaryValidation:
        """Validate a pending transfer as notary.

        If APPROVE: marks input UTXOs as SPENT, output UTXOs as UNSPENT.
        If REJECT: returns input UTXOs to UNSPENT, marks outputs as SPENT.

        Args:
            transfer_id: Transfer to validate
            notary: Notary address or ID
            decision: Approval or rejection
            reason: Optional reason for the decision

        Returns:
            The NotaryValidation record

        Raises:
            ValueError: If transfer not found or already decided
        """
        transfer = self._transfers.get(transfer_id)
        if not transfer:
            raise ValueError(f"Transfer not found: {transfer_id}")
        if not transfer.is_pending:
            raise ValueError(
                f"Transfer already decided: {transfer.notary_decision.value}"
            )

        transfer.notary_decision = decision

        if decision == NotaryDecision.APPROVE:
            # Spend inputs
            for utxo_id in transfer.inputs:
                utxo = self._utxos[utxo_id]
                utxo.state = UTXOState.SPENT
                utxo.spent_at = datetime.now(UTC)
            # Unlock outputs
            for utxo_id in transfer.outputs:
                utxo = self._utxos[utxo_id]
                utxo.state = UTXOState.UNSPENT
        elif decision == NotaryDecision.REJECT:
            # Return inputs to unspent
            for utxo_id in transfer.inputs:
                utxo = self._utxos[utxo_id]
                utxo.state = UTXOState.UNSPENT
            # Mark outputs as spent (invalidated)
            for utxo_id in transfer.outputs:
                utxo = self._utxos[utxo_id]
                utxo.state = UTXOState.SPENT

        validation = NotaryValidation(
            transfer_id=transfer_id,
            notary=notary,
            decision=decision,
            reason=reason,
        )
        return validation

    def get_transfer(self, transfer_id: str) -> PrivateTransfer | None:
        """Get a transfer by ID."""
        return self._transfers.get(transfer_id)

    # ---- Privacy groups (Pente domain) ----

    def create_privacy_group(
        self,
        name: str,
        members: list[str],
        endorsement_policy: str = DEFAULT_ENDORSEMENT_POLICY,
    ) -> PrivacyGroup:
        """Create a new privacy group.

        Args:
            name: Group name
            members: Initial member addresses
            endorsement_policy: Endorsement policy (default "all")

        Returns:
            The created PrivacyGroup
        """
        group = PrivacyGroup(
            group_id=self._next_id("grp"),
            name=name,
            members=list(members),
            endorsement_policy=endorsement_policy,
        )
        self._groups[group.group_id] = group
        return group

    def get_privacy_group(self, group_id: str) -> PrivacyGroup | None:
        """Get a privacy group by ID."""
        return self._groups.get(group_id)

    def dissolve_privacy_group(self, group_id: str) -> None:
        """Dissolve a privacy group.

        Args:
            group_id: Group to dissolve

        Raises:
            ValueError: If group not found
        """
        group = self._groups.get(group_id)
        if not group:
            raise ValueError(f"Privacy group not found: {group_id}")
        group.status = PrivacyGroupStatus.DISSOLVED

    # ---- Properties ----

    @property
    def total_utxos(self) -> int:
        """Total number of UTXOs tracked."""
        return len(self._utxos)

    @property
    def total_transfers(self) -> int:
        """Total number of transfers created."""
        return len(self._transfers)

    @property
    def active_groups(self) -> int:
        """Number of active privacy groups."""
        return sum(1 for g in self._groups.values() if g.is_active)


# ============ Calldata Builders ============


def build_notarized_transfer_calldata(
    sender: str,
    receiver: str,
    amount: int,
    notary_signature: bytes,
) -> bytes:
    """Build calldata for notarizedTransfer() on-chain.

    Args:
        sender: Sender address
        receiver: Receiver address
        amount: Transfer amount
        notary_signature: Notary's approval signature

    Returns:
        ABI-encoded calldata
    """
    selector = bytes.fromhex("a1b2c3d4")  # notarizedTransfer selector
    sender_bytes = sender.encode("utf-8").ljust(32, b"\x00")[:32]
    receiver_bytes = receiver.encode("utf-8").ljust(32, b"\x00")[:32]
    amount_bytes = amount.to_bytes(32, "big")
    sig_len = len(notary_signature).to_bytes(32, "big")
    sig_padded = notary_signature.ljust(((len(notary_signature) + 31) // 32) * 32, b"\x00")

    return selector + sender_bytes + receiver_bytes + amount_bytes + sig_len + sig_padded


def build_create_privacy_group_calldata(
    group_id: str,
    members: list[str],
) -> bytes:
    """Build calldata for createPrivacyGroup() on-chain.

    Args:
        group_id: Privacy group identifier
        members: List of member addresses

    Returns:
        ABI-encoded calldata
    """
    selector = bytes.fromhex("b2c3d4e5")  # createPrivacyGroup selector
    group_id_bytes = group_id.encode("utf-8").ljust(32, b"\x00")[:32]
    count = len(members).to_bytes(32, "big")

    member_data = b""
    for member in members:
        member_data += member.encode("utf-8").ljust(32, b"\x00")[:32]

    return selector + group_id_bytes + count + member_data


# ============ Factory ============


def create_privacy_manager(
    domain: PrivacyDomain = PrivacyDomain.NOTO,
    notary_address: str = "",
    privacy_level: PrivacyLevel = PrivacyLevel.PRIVATE,
) -> PaladinPrivacyManager:
    """Factory function to create a PaladinPrivacyManager.

    Args:
        domain: Privacy domain to use
        notary_address: Address of the notary
        privacy_level: Default privacy level

    Returns:
        Configured PaladinPrivacyManager instance
    """
    config = PrivacyConfig(
        domain=domain,
        notary_address=notary_address,
        privacy_level=privacy_level,
    )
    return PaladinPrivacyManager(config=config)
