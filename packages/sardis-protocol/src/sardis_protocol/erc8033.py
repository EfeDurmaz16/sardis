"""ERC-8033: Paymaster Protocol for Agent Payment Channels.

Implements gasless transaction infrastructure through paymaster sponsorship
with spending limits and session-based authorization for AI agents.

Key features:
- Gas session management with per-agent spending limits
- Multiple paymaster types (verifying, depositor, token, sponsored)
- Sponsorship tiers with gas deposits and consumption tracking
- Transaction processing with automatic session lifecycle management
- Gas estimation across supported chains

ERC-8033 fits the ERC-80xx agent economy series alongside:
- ERC-8001 (coordination)
- ERC-8122 (registry)
- ERC-8126 (verification)

Reference: https://eips.ethereum.org/EIPS/eip-8033
Depends on: EIP-712, ERC-4337 (Account Abstraction)
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum


# ============ Constants ============

ERC8033_VERSION = "0.1.0"
DEFAULT_SESSION_HOURS = 24
DEFAULT_GAS_LIMIT = 1_000_000
DEFAULT_MAX_TX_COUNT = 100

# Gas price estimates per chain (in gwei)
GAS_PRICE_MAP: dict[str, float] = {
    "base": 0.001,
    "ethereum": 30.0,
    "polygon": 30.0,
    "arbitrum": 0.1,
    "optimism": 0.001,
}

# ETH/USD estimate for gas cost calculations
ETH_USD_ESTIMATE = 3000.0

# Sponsorship tier gas limits
SPONSORSHIP_TIERS: dict[str, int] = {
    "free": 100_000,
    "basic": 1_000_000,
    "premium": 10_000_000,
    "enterprise": 100_000_000,
}


# ============ Enums ============


class PaymasterType(str, Enum):
    """Types of paymaster contracts."""
    VERIFYING = "verifying"
    DEPOSITOR = "depositor"
    TOKEN = "token"
    SPONSORED = "sponsored"


class SessionStatus(str, Enum):
    """Gas session lifecycle status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    EXHAUSTED = "exhausted"


class SponsorshipTier(str, Enum):
    """Sponsorship tier levels."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class GasPolicy(str, Enum):
    """Gas payment policies."""
    SPONSOR_ALL = "sponsor_all"
    USER_PAYS = "user_pays"
    SPLIT = "split"
    PREPAID = "prepaid"


# ============ Data Classes ============


@dataclass
class PaymasterConfig:
    """Configuration for a paymaster instance."""
    paymaster_address: str = ""
    paymaster_type: PaymasterType = PaymasterType.VERIFYING
    chain: str = "base"
    max_gas_per_tx: int = 500_000
    daily_gas_budget: int = 10_000_000
    gas_policy: GasPolicy = GasPolicy.SPONSOR_ALL


@dataclass
class GasSession:
    """A gas session authorizing an agent to submit transactions.

    Sessions track gas usage and transaction counts, automatically
    transitioning to EXHAUSTED when limits are reached.
    """
    session_id: str
    agent_id: str
    paymaster: str
    gas_limit: int
    gas_used: int = 0
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tx_count: int = 0
    max_tx_count: int = 100

    @property
    def remaining_gas(self) -> int:
        """Gas remaining in this session."""
        return max(0, self.gas_limit - self.gas_used)

    @property
    def is_active(self) -> bool:
        """Session is active, not expired, and not exhausted."""
        return (
            self.status == SessionStatus.ACTIVE
            and not self.is_expired
            and not self.is_exhausted
        )

    @property
    def is_expired(self) -> bool:
        """Session has passed its expiry time."""
        return datetime.now(UTC) >= self.expires_at

    @property
    def is_exhausted(self) -> bool:
        """Session has used all gas or reached max transaction count."""
        return self.gas_used >= self.gas_limit or self.tx_count >= self.max_tx_count

    @property
    def utilization_pct(self) -> float:
        """Percentage of gas limit consumed."""
        if self.gas_limit == 0:
            return 0.0
        return self.gas_used / self.gas_limit * 100


@dataclass
class SponsorshipRecord:
    """A gas sponsorship deposit from a sponsor to a beneficiary."""
    record_id: str
    sponsor: str
    beneficiary: str
    tier: SponsorshipTier
    gas_deposited: int
    gas_consumed: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None

    @property
    def remaining_deposit(self) -> int:
        """Gas remaining in the sponsorship deposit."""
        return max(0, self.gas_deposited - self.gas_consumed)

    @property
    def is_active(self) -> bool:
        """Sponsorship is active if it has remaining deposit and is not expired."""
        if self.remaining_deposit <= 0:
            return False
        if self.expires_at is not None and datetime.now(UTC) >= self.expires_at:
            return False
        return True


@dataclass
class GasEstimate:
    """Estimated gas cost for a transaction on a specific chain."""
    chain: str
    estimated_gas: int
    gas_price_gwei: float
    cost_usd: float
    paymaster_covers: bool
    user_pays_usd: float = 0.0


@dataclass
class PaymasterTransaction:
    """A transaction processed through the paymaster."""
    tx_id: str
    session_id: str
    agent_id: str
    gas_used: int
    gas_price_gwei: float
    target: str
    value: int = 0
    sponsored: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class PaymasterStats:
    """Aggregate statistics for a paymaster instance."""
    total_sessions: int
    active_sessions: int
    total_gas_sponsored: int
    total_transactions: int
    unique_agents: int
    gas_savings_usd: float


# ============ Paymaster Manager ============


class PaymasterManager:
    """Manages ERC-8033 paymaster sessions and sponsorships.

    Handles the off-chain lifecycle of gas sessions, transaction
    processing, sponsorship management, and gas estimation.
    """

    def __init__(self, config: PaymasterConfig | None = None):
        self._config = config or PaymasterConfig()
        self._sessions: dict[str, GasSession] = {}
        self._sponsorships: dict[str, SponsorshipRecord] = {}
        self._transactions: dict[str, PaymasterTransaction] = {}

    # ---------- Session Management ----------

    def create_session(
        self,
        agent_id: str,
        gas_limit: int = DEFAULT_GAS_LIMIT,
        expires_in_hours: int = DEFAULT_SESSION_HOURS,
        max_tx_count: int = DEFAULT_MAX_TX_COUNT,
    ) -> GasSession:
        """Create a new gas session for an agent.

        Args:
            agent_id: The agent to authorize
            gas_limit: Maximum gas for this session
            expires_in_hours: Hours until session expires
            max_tx_count: Maximum number of transactions allowed

        Returns:
            The created GasSession
        """
        now = datetime.now(UTC)
        session = GasSession(
            session_id=uuid.uuid4().hex[:16],
            agent_id=agent_id,
            paymaster=self._config.paymaster_address,
            gas_limit=gas_limit,
            status=SessionStatus.ACTIVE,
            created_at=now,
            expires_at=now + timedelta(hours=expires_in_hours),
            max_tx_count=max_tx_count,
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> GasSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_sessions_for_agent(self, agent_id: str) -> list[GasSession]:
        """Get all sessions for a specific agent."""
        return [
            s for s in self._sessions.values()
            if s.agent_id == agent_id
        ]

    def revoke_session(self, session_id: str) -> None:
        """Revoke a gas session.

        Args:
            session_id: Session to revoke

        Raises:
            ValueError: If session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        session.status = SessionStatus.REVOKED

    def refresh_session(
        self,
        session_id: str,
        additional_gas: int = 0,
        extend_hours: int = 0,
    ) -> GasSession:
        """Refresh a session by adding gas and/or extending expiry.

        Args:
            session_id: Session to refresh
            additional_gas: Gas to add to the limit
            extend_hours: Hours to extend the expiry

        Returns:
            The updated GasSession

        Raises:
            ValueError: If session not found or not active
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        if session.status != SessionStatus.ACTIVE:
            raise ValueError(f"Session not active: {session.status.value}")

        if additional_gas > 0:
            session.gas_limit += additional_gas
        if extend_hours > 0:
            session.expires_at += timedelta(hours=extend_hours)

        return session

    # ---------- Transaction Processing ----------

    def process_transaction(
        self,
        session_id: str,
        gas_used: int,
        gas_price_gwei: float,
        target: str,
        value: int = 0,
    ) -> PaymasterTransaction:
        """Process a transaction against a gas session.

        Deducts gas from the session, increments the transaction count,
        and marks the session as EXHAUSTED if limits are reached.

        Args:
            session_id: Session to charge
            gas_used: Gas consumed by the transaction
            gas_price_gwei: Gas price in gwei
            target: Target contract address
            value: Transaction value in wei

        Returns:
            The recorded PaymasterTransaction

        Raises:
            ValueError: If session not active or insufficient gas
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        if not session.is_active:
            raise ValueError(f"Session not active: {session.status.value}")
        if gas_used > session.remaining_gas:
            raise ValueError(
                f"Insufficient gas: need {gas_used}, have {session.remaining_gas}"
            )

        # Deduct gas and increment tx count
        session.gas_used += gas_used
        session.tx_count += 1

        # Check if session is now exhausted
        if session.is_exhausted:
            session.status = SessionStatus.EXHAUSTED

        # Record transaction
        tx = PaymasterTransaction(
            tx_id=uuid.uuid4().hex[:16],
            session_id=session_id,
            agent_id=session.agent_id,
            gas_used=gas_used,
            gas_price_gwei=gas_price_gwei,
            target=target,
            value=value,
            sponsored=self._config.gas_policy == GasPolicy.SPONSOR_ALL,
        )
        self._transactions[tx.tx_id] = tx
        return tx

    def estimate_gas(
        self,
        chain: str,
        estimated_gas: int,
    ) -> GasEstimate:
        """Estimate gas cost for a transaction on a given chain.

        Args:
            chain: Target chain name
            estimated_gas: Estimated gas units

        Returns:
            GasEstimate with USD cost calculation
        """
        gas_price = GAS_PRICE_MAP.get(chain, 1.0)
        # cost = gas * price_gwei * 1e-9 * ETH_USD
        cost_usd = estimated_gas * gas_price * 1e-9 * ETH_USD_ESTIMATE
        paymaster_covers = self._config.gas_policy == GasPolicy.SPONSOR_ALL

        return GasEstimate(
            chain=chain,
            estimated_gas=estimated_gas,
            gas_price_gwei=gas_price,
            cost_usd=cost_usd,
            paymaster_covers=paymaster_covers,
            user_pays_usd=0.0 if paymaster_covers else cost_usd,
        )

    # ---------- Sponsorship ----------

    def create_sponsorship(
        self,
        sponsor: str,
        beneficiary: str,
        tier: SponsorshipTier,
        gas_amount: int,
        expires_in_hours: int | None = None,
    ) -> SponsorshipRecord:
        """Create a gas sponsorship deposit.

        Args:
            sponsor: Sponsor address
            beneficiary: Beneficiary agent address
            tier: Sponsorship tier
            gas_amount: Gas units to deposit
            expires_in_hours: Optional expiry in hours

        Returns:
            The created SponsorshipRecord
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=expires_in_hours) if expires_in_hours else None

        record = SponsorshipRecord(
            record_id=uuid.uuid4().hex[:16],
            sponsor=sponsor,
            beneficiary=beneficiary,
            tier=tier,
            gas_deposited=gas_amount,
            created_at=now,
            expires_at=expires_at,
        )
        self._sponsorships[record.record_id] = record
        return record

    def get_sponsorship(self, record_id: str) -> SponsorshipRecord | None:
        """Get a sponsorship record by ID."""
        return self._sponsorships.get(record_id)

    def consume_sponsorship(
        self,
        record_id: str,
        gas_amount: int,
    ) -> SponsorshipRecord:
        """Consume gas from a sponsorship deposit.

        Args:
            record_id: Sponsorship to consume from
            gas_amount: Gas units to consume

        Returns:
            The updated SponsorshipRecord

        Raises:
            ValueError: If sponsorship not found, not active, or insufficient gas
        """
        record = self._sponsorships.get(record_id)
        if not record:
            raise ValueError(f"Sponsorship not found: {record_id}")
        if not record.is_active:
            raise ValueError(f"Sponsorship not active: {record_id}")
        if gas_amount > record.remaining_deposit:
            raise ValueError(
                f"Insufficient sponsorship: need {gas_amount}, "
                f"have {record.remaining_deposit}"
            )

        record.gas_consumed += gas_amount
        return record

    # ---------- Statistics ----------

    def get_stats(self) -> PaymasterStats:
        """Compute aggregate paymaster statistics."""
        active = [s for s in self._sessions.values() if s.is_active]
        agents = {s.agent_id for s in self._sessions.values()}
        total_gas = sum(s.gas_used for s in self._sessions.values())

        # Estimate savings: gas sponsored * average gas price * ETH_USD
        avg_price = GAS_PRICE_MAP.get(self._config.chain, 1.0)
        savings_usd = total_gas * avg_price * 1e-9 * ETH_USD_ESTIMATE

        return PaymasterStats(
            total_sessions=len(self._sessions),
            active_sessions=len(active),
            total_gas_sponsored=total_gas,
            total_transactions=len(self._transactions),
            unique_agents=len(agents),
            gas_savings_usd=savings_usd,
        )

    # ---------- Properties ----------

    @property
    def total_sessions(self) -> int:
        """Total number of sessions created."""
        return len(self._sessions)

    @property
    def active_sessions(self) -> int:
        """Number of currently active sessions."""
        return len([s for s in self._sessions.values() if s.is_active])

    @property
    def total_gas_sponsored(self) -> int:
        """Total gas units consumed across all sessions."""
        return sum(s.gas_used for s in self._sessions.values())


# ============ Calldata Builders ============


def build_create_session_calldata(
    agent_id: str,
    gas_limit: int,
    expiry: int,
) -> bytes:
    """Build calldata for createSession(address, uint256, uint256).

    Args:
        agent_id: Agent address
        gas_limit: Maximum gas for the session
        expiry: Unix timestamp for session expiry

    Returns:
        ABI-encoded calldata
    """
    selector = bytes.fromhex("a1b2c3d4")  # createSession selector
    agent_bytes = agent_id.encode("utf-8").ljust(32, b"\x00")[:32]
    data = (
        agent_bytes
        + gas_limit.to_bytes(32, "big")
        + expiry.to_bytes(32, "big")
    )
    return selector + data


def build_sponsor_calldata(
    beneficiary: str,
    gas_amount: int,
) -> bytes:
    """Build calldata for sponsor(address, uint256).

    Args:
        beneficiary: Beneficiary address
        gas_amount: Gas units to sponsor

    Returns:
        ABI-encoded calldata
    """
    selector = bytes.fromhex("b2c3d4e5")  # sponsor selector
    beneficiary_bytes = beneficiary.encode("utf-8").ljust(32, b"\x00")[:32]
    data = (
        beneficiary_bytes
        + gas_amount.to_bytes(32, "big")
    )
    return selector + data


def build_revoke_session_calldata(session_id_hash: bytes) -> bytes:
    """Build calldata for revokeSession(bytes32).

    Args:
        session_id_hash: Hash of the session ID to revoke

    Returns:
        ABI-encoded calldata
    """
    selector = bytes.fromhex("c3d4e5f6")  # revokeSession selector
    return selector + session_id_hash.ljust(32, b"\x00")[:32]


# ============ Helper Functions ============


def create_paymaster_manager(
    paymaster_address: str = "",
    chain: str = "base",
    gas_policy: GasPolicy = GasPolicy.SPONSOR_ALL,
) -> PaymasterManager:
    """Factory function to create a PaymasterManager.

    Args:
        paymaster_address: Paymaster contract address
        chain: Target chain
        gas_policy: Gas payment policy

    Returns:
        Configured PaymasterManager instance
    """
    config = PaymasterConfig(
        paymaster_address=paymaster_address,
        chain=chain,
        gas_policy=gas_policy,
    )
    return PaymasterManager(config=config)


def estimate_tx_cost(chain: str, gas: int) -> float:
    """Estimate transaction cost in USD.

    Args:
        chain: Target chain name
        gas: Estimated gas units

    Returns:
        Estimated cost in USD
    """
    gas_price = GAS_PRICE_MAP.get(chain, 1.0)
    return gas * gas_price * 1e-9 * ETH_USD_ESTIMATE
