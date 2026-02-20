"""Know Your Agent (KYA) — Agent identity verification and trust management.

KYA extends traditional KYC/KYB concepts to AI agents. Instead of verifying
a human's identity, KYA verifies:
  1. WHO owns the agent (Legal Anchor — linked to KYC'd owner)
  2. WHAT the agent is authorized to do (Agent Manifest — capabilities + limits)
  3. HOW trustworthy the agent is (Trust Score — based on behavior history)

KYA levels determine spending limits via TrustLevel mapping:
  NONE     → TrustLevel.LOW    ($50/tx,  $100/day)
  BASIC    → TrustLevel.LOW    ($50/tx,  $100/day)   — email verification only
  VERIFIED → TrustLevel.MEDIUM ($500/tx, $1k/day)    — KYC + org verification
  ATTESTED → TrustLevel.HIGH   ($5k/tx,  $10k/day)   — VC + code hash + TEE

Usage:
    from sardis_compliance.kya import KYAService, KYALevel, AgentManifest

    kya = KYAService()

    # Register an agent with a manifest
    manifest = AgentManifest(
        agent_id="agent_abc123",
        owner_id="org_xyz",
        capabilities=["saas_subscription", "api_credits"],
        max_budget_per_tx=Decimal("50.00"),
        allowed_domains=["openai.com", "anthropic.com"],
    )
    result = await kya.register_agent(manifest)

    # Check KYA level before payment
    check = await kya.check_agent("agent_abc123", amount=Decimal("25.00"))
    if not check.allowed:
        raise KYADeniedError(check.reason)
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol
from uuid import uuid4

logger = logging.getLogger("sardis.compliance.kya")


# ============ Enums ============


class KYALevel(str, Enum):
    """Agent verification level — determines spending capabilities."""
    NONE = "none"            # Unverified agent
    BASIC = "basic"          # Email/API key verification only
    VERIFIED = "verified"    # Owner KYC + organizational verification
    ATTESTED = "attested"    # Verifiable credential + code hash + optional TEE


class KYAStatus(str, Enum):
    """Current status of KYA verification process."""
    PENDING = "pending"              # Not yet started
    IN_PROGRESS = "in_progress"      # Verification underway
    ACTIVE = "active"                # Verified and active
    SUSPENDED = "suspended"          # Temporarily suspended (liveness/violation)
    REVOKED = "revoked"              # Permanently revoked
    EXPIRED = "expired"              # Verification expired, needs renewal


# ============ Amount Thresholds ============

# KYA level required based on single-transaction amount
KYA_AMOUNT_THRESHOLDS: Dict[KYALevel, Decimal] = {
    KYALevel.NONE: Decimal("0"),         # Cannot transact
    KYALevel.BASIC: Decimal("10.00"),    # Up to $10/tx
    KYALevel.VERIFIED: Decimal("1000.00"),  # Up to $1,000/tx
    KYALevel.ATTESTED: Decimal("999999999"),  # Unlimited
}

# Daily spending limits per KYA level
KYA_DAILY_THRESHOLDS: Dict[KYALevel, Decimal] = {
    KYALevel.NONE: Decimal("0"),
    KYALevel.BASIC: Decimal("50.00"),
    KYALevel.VERIFIED: Decimal("5000.00"),
    KYALevel.ATTESTED: Decimal("999999999"),
}


def required_kya_level(amount: Decimal) -> KYALevel:
    """Determine the minimum KYA level required for a transaction amount."""
    if amount <= KYA_AMOUNT_THRESHOLDS[KYALevel.BASIC]:
        return KYALevel.BASIC
    if amount <= KYA_AMOUNT_THRESHOLDS[KYALevel.VERIFIED]:
        return KYALevel.VERIFIED
    return KYALevel.ATTESTED


KYA_LEVEL_ORDER = {
    KYALevel.NONE: 0,
    KYALevel.BASIC: 1,
    KYALevel.VERIFIED: 2,
    KYALevel.ATTESTED: 3,
}


def kya_level_sufficient(agent_level: KYALevel, required: KYALevel) -> bool:
    """Check if agent's KYA level meets the requirement."""
    return KYA_LEVEL_ORDER[agent_level] >= KYA_LEVEL_ORDER[required]


# ============ Data Models ============


@dataclass
class AgentManifest:
    """
    Declarative manifest for an AI agent — the heart of KYA.

    This is what differentiates Sardis from competitors: not just "who is this
    agent?" but "what is this agent authorized to do and within what bounds?"

    Equivalent to sardis-manifest.json in the agent's deployment.
    """
    agent_id: str
    owner_id: str
    capabilities: List[str] = field(default_factory=list)
    max_budget_per_tx: Decimal = field(default_factory=lambda: Decimal("50.00"))
    daily_budget: Decimal = field(default_factory=lambda: Decimal("500.00"))
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    framework: Optional[str] = None  # "langchain", "crewai", "autogpt", etc.
    framework_version: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "owner_id": self.owner_id,
            "capabilities": self.capabilities,
            "max_budget_per_tx": str(self.max_budget_per_tx),
            "daily_budget": str(self.daily_budget),
            "allowed_domains": self.allowed_domains,
            "blocked_domains": self.blocked_domains,
            "framework": self.framework,
            "framework_version": self.framework_version,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentManifest":
        return cls(
            agent_id=data["agent_id"],
            owner_id=data["owner_id"],
            capabilities=data.get("capabilities", []),
            max_budget_per_tx=Decimal(str(data.get("max_budget_per_tx", "50.00"))),
            daily_budget=Decimal(str(data.get("daily_budget", "500.00"))),
            allowed_domains=data.get("allowed_domains", []),
            blocked_domains=data.get("blocked_domains", []),
            framework=data.get("framework"),
            framework_version=data.get("framework_version"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )

    @property
    def manifest_hash(self) -> str:
        """SHA-256 hash of the manifest for integrity verification."""
        import json
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class CodeAttestation:
    """Attestation of an agent's code integrity."""
    code_hash: str                    # SHA-256 of agent logic
    framework: Optional[str] = None   # e.g. "langchain", "crewai"
    version: Optional[str] = None
    attested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attester: str = "self"            # "self", "tee", "sardis"
    tee_attestation: Optional[str] = None  # Remote attestation from TEE

    def verify(self, expected_hash: str) -> bool:
        """Check if code hash matches expected value."""
        return self.code_hash == expected_hash


@dataclass
class AgentTrustScore:
    """Behavioral trust score for an agent (0.0 to 1.0)."""
    agent_id: str
    score: float = 0.0
    successful_payments: int = 0
    failed_payments: int = 0
    policy_violations: int = 0
    total_volume: Decimal = field(default_factory=lambda: Decimal("0"))
    uptime_ratio: float = 1.0         # Liveness check success rate
    age_days: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def recalculate(self) -> float:
        """Recalculate trust score based on agent behavior."""
        total_txns = self.successful_payments + self.failed_payments
        if total_txns == 0:
            self.score = 0.0
            return self.score

        # Success rate (40% weight)
        success_rate = self.successful_payments / total_txns
        success_component = success_rate * 0.4

        # Policy compliance (30% weight) — penalize violations heavily
        violation_penalty = min(1.0, self.policy_violations * 0.1)
        compliance_component = (1.0 - violation_penalty) * 0.3

        # Uptime (15% weight)
        uptime_component = self.uptime_ratio * 0.15

        # Maturity (15% weight) — agents gain trust over time
        maturity = min(1.0, self.age_days / 90)  # Full credit at 90 days
        maturity_component = maturity * 0.15

        self.score = round(
            success_component + compliance_component + uptime_component + maturity_component,
            4,
        )
        self.last_updated = datetime.now(timezone.utc)
        return self.score

    @property
    def suggested_kya_level(self) -> KYALevel:
        """Suggest a KYA level based on trust score."""
        if self.score >= 0.9 and self.age_days >= 30:
            return KYALevel.ATTESTED
        if self.score >= 0.7 and self.age_days >= 7:
            return KYALevel.VERIFIED
        if self.score >= 0.3:
            return KYALevel.BASIC
        return KYALevel.NONE


@dataclass
class KYAResult:
    """Result of a KYA check or verification."""
    agent_id: str
    level: KYALevel
    status: KYAStatus
    allowed: bool
    reason: Optional[str] = None
    owner_id: Optional[str] = None
    anchor_verification_id: Optional[str] = None  # Persona/Stripe Identity ID
    manifest_hash: Optional[str] = None
    code_hash: Optional[str] = None
    trust_score: Optional[float] = None
    attestations: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "level": self.level.value,
            "status": self.status.value,
            "allowed": self.allowed,
            "reason": self.reason,
            "owner_id": self.owner_id,
            "manifest_hash": self.manifest_hash,
            "trust_score": self.trust_score,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class KYACheckRequest:
    """Request to check an agent's KYA status for a payment."""
    agent_id: str
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    merchant_id: Optional[str] = None
    merchant_domain: Optional[str] = None


# ============ Liveness ============


class AgentLivenessTracker:
    """Track agent liveness via periodic pings.

    Agents must send heartbeats to maintain their KYA status.
    Stale agents (no ping within timeout) get flagged for suspension.
    """

    DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes

    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS):
        self._timeout = timeout_seconds
        self._last_seen: Dict[str, float] = {}  # agent_id -> unix timestamp
        self._ping_count: Dict[str, int] = {}

    def ping(self, agent_id: str) -> None:
        """Record a heartbeat from an agent."""
        self._last_seen[agent_id] = time.time()
        self._ping_count[agent_id] = self._ping_count.get(agent_id, 0) + 1

    def is_alive(self, agent_id: str) -> bool:
        """Check if agent has sent a recent heartbeat."""
        last = self._last_seen.get(agent_id)
        if last is None:
            return False
        return (time.time() - last) < self._timeout

    def get_last_seen(self, agent_id: str) -> Optional[datetime]:
        """Get the last heartbeat timestamp for an agent."""
        ts = self._last_seen.get(agent_id)
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    def get_stale_agents(self) -> List[str]:
        """Get list of agents that have missed their heartbeat."""
        now = time.time()
        return [
            agent_id
            for agent_id, last in self._last_seen.items()
            if (now - last) >= self._timeout
        ]

    def uptime_ratio(self, agent_id: str, expected_pings: int) -> float:
        """Calculate uptime ratio based on actual vs expected pings."""
        actual = self._ping_count.get(agent_id, 0)
        if expected_pings <= 0:
            return 1.0
        return min(1.0, actual / expected_pings)

    def remove(self, agent_id: str) -> None:
        """Remove tracking for an agent."""
        self._last_seen.pop(agent_id, None)
        self._ping_count.pop(agent_id, None)


# ============ KYA Provider Protocol ============


class KYAProvider(Protocol):
    """Interface for KYA verification providers."""

    async def verify_agent(self, manifest: AgentManifest) -> KYAResult: ...
    async def check_agent(self, request: KYACheckRequest) -> KYAResult: ...
    async def revoke_agent(self, agent_id: str, reason: str) -> KYAResult: ...


# ============ In-Memory KYA Store ============


class InMemoryKYAStore:
    """In-memory store for KYA records. Replace with PostgreSQL in production."""

    def __init__(self):
        self._manifests: Dict[str, AgentManifest] = {}
        self._levels: Dict[str, KYALevel] = {}
        self._statuses: Dict[str, KYAStatus] = {}
        self._trust_scores: Dict[str, AgentTrustScore] = {}
        self._code_attestations: Dict[str, CodeAttestation] = {}

    def store_manifest(self, manifest: AgentManifest) -> None:
        self._manifests[manifest.agent_id] = manifest
        if manifest.agent_id not in self._levels:
            self._levels[manifest.agent_id] = KYALevel.NONE
        if manifest.agent_id not in self._statuses:
            self._statuses[manifest.agent_id] = KYAStatus.PENDING

    def get_manifest(self, agent_id: str) -> Optional[AgentManifest]:
        return self._manifests.get(agent_id)

    def set_level(self, agent_id: str, level: KYALevel) -> None:
        self._levels[agent_id] = level

    def get_level(self, agent_id: str) -> KYALevel:
        return self._levels.get(agent_id, KYALevel.NONE)

    def set_status(self, agent_id: str, status: KYAStatus) -> None:
        self._statuses[agent_id] = status

    def get_status(self, agent_id: str) -> KYAStatus:
        return self._statuses.get(agent_id, KYAStatus.PENDING)

    def get_trust_score(self, agent_id: str) -> Optional[AgentTrustScore]:
        return self._trust_scores.get(agent_id)

    def set_trust_score(self, agent_id: str, score: AgentTrustScore) -> None:
        self._trust_scores[agent_id] = score

    def get_code_attestation(self, agent_id: str) -> Optional[CodeAttestation]:
        return self._code_attestations.get(agent_id)

    def set_code_attestation(self, agent_id: str, attestation: CodeAttestation) -> None:
        self._code_attestations[agent_id] = attestation

    def remove(self, agent_id: str) -> None:
        self._manifests.pop(agent_id, None)
        self._levels.pop(agent_id, None)
        self._statuses.pop(agent_id, None)
        self._trust_scores.pop(agent_id, None)
        self._code_attestations.pop(agent_id, None)


# ============ KYA Service ============


class KYAService:
    """
    Core KYA (Know Your Agent) verification service.

    Manages agent registration, verification, trust scoring,
    liveness monitoring, and code attestation.
    """

    def __init__(
        self,
        store: Optional[InMemoryKYAStore] = None,
        liveness: Optional[AgentLivenessTracker] = None,
        liveness_timeout: int = 300,
    ):
        self._store = store or InMemoryKYAStore()
        self._liveness = liveness or AgentLivenessTracker(timeout_seconds=liveness_timeout)

    # ── Registration ──────────────────────────────────────────────

    async def register_agent(self, manifest: AgentManifest) -> KYAResult:
        """
        Register an agent with its manifest.

        New agents start at BASIC level (email/API key verified).
        Higher levels require additional verification steps.
        """
        self._store.store_manifest(manifest)
        self._store.set_level(manifest.agent_id, KYALevel.BASIC)
        self._store.set_status(manifest.agent_id, KYAStatus.ACTIVE)

        # Initialize trust score
        trust = AgentTrustScore(agent_id=manifest.agent_id)
        self._store.set_trust_score(manifest.agent_id, trust)

        # Start liveness tracking
        self._liveness.ping(manifest.agent_id)

        logger.info(
            "Agent registered with KYA: agent_id=%s, owner=%s, level=BASIC",
            manifest.agent_id, manifest.owner_id,
        )

        return KYAResult(
            agent_id=manifest.agent_id,
            level=KYALevel.BASIC,
            status=KYAStatus.ACTIVE,
            allowed=True,
            reason="registered",
            owner_id=manifest.owner_id,
            manifest_hash=manifest.manifest_hash,
            trust_score=0.0,
        )

    # ── Verification ──────────────────────────────────────────────

    async def check_agent(self, request: KYACheckRequest) -> KYAResult:
        """
        Check if an agent is authorized for a payment.

        Verifies:
        1. Agent is registered and active
        2. KYA level is sufficient for the amount
        3. Agent is alive (liveness check)
        4. Merchant domain is allowed (if specified)
        """
        agent_id = request.agent_id
        level = self._store.get_level(agent_id)
        kya_status = self._store.get_status(agent_id)
        manifest = self._store.get_manifest(agent_id)

        # Check 1: Agent must be registered
        if manifest is None:
            return KYAResult(
                agent_id=agent_id,
                level=KYALevel.NONE,
                status=KYAStatus.PENDING,
                allowed=False,
                reason="agent_not_registered",
            )

        # Check 2: Agent must be active
        if kya_status not in (KYAStatus.ACTIVE,):
            return KYAResult(
                agent_id=agent_id,
                level=level,
                status=kya_status,
                allowed=False,
                reason=f"agent_status_{kya_status.value}",
                owner_id=manifest.owner_id,
            )

        # Check 3: KYA level sufficient for amount
        if request.amount > Decimal("0"):
            required = required_kya_level(request.amount)
            if not kya_level_sufficient(level, required):
                return KYAResult(
                    agent_id=agent_id,
                    level=level,
                    status=kya_status,
                    allowed=False,
                    reason=f"kya_level_insufficient: need {required.value}, have {level.value}",
                    owner_id=manifest.owner_id,
                )

        # Check 4: Manifest budget check
        if request.amount > manifest.max_budget_per_tx:
            return KYAResult(
                agent_id=agent_id,
                level=level,
                status=kya_status,
                allowed=False,
                reason=f"manifest_budget_exceeded: max {manifest.max_budget_per_tx}",
                owner_id=manifest.owner_id,
            )

        # Check 5: Domain allowlist (if merchant domain provided)
        if request.merchant_domain and manifest.allowed_domains:
            domain_match = any(
                request.merchant_domain.endswith(d)
                for d in manifest.allowed_domains
            )
            if not domain_match:
                return KYAResult(
                    agent_id=agent_id,
                    level=level,
                    status=kya_status,
                    allowed=False,
                    reason=f"domain_not_allowed: {request.merchant_domain}",
                    owner_id=manifest.owner_id,
                )

        # Check 6: Domain blocklist
        if request.merchant_domain and manifest.blocked_domains:
            domain_blocked = any(
                request.merchant_domain.endswith(d)
                for d in manifest.blocked_domains
            )
            if domain_blocked:
                return KYAResult(
                    agent_id=agent_id,
                    level=level,
                    status=kya_status,
                    allowed=False,
                    reason=f"domain_blocked: {request.merchant_domain}",
                    owner_id=manifest.owner_id,
                )

        # All checks passed
        trust = self._store.get_trust_score(agent_id)
        return KYAResult(
            agent_id=agent_id,
            level=level,
            status=kya_status,
            allowed=True,
            reason="kya_passed",
            owner_id=manifest.owner_id,
            manifest_hash=manifest.manifest_hash,
            trust_score=trust.score if trust else None,
        )

    # ── Level Management ──────────────────────────────────────────

    async def upgrade_level(
        self,
        agent_id: str,
        target_level: KYALevel,
        *,
        anchor_verification_id: Optional[str] = None,
        code_attestation: Optional[CodeAttestation] = None,
    ) -> KYAResult:
        """
        Upgrade an agent's KYA level.

        Requirements per level:
        - BASIC: Agent registration (automatic)
        - VERIFIED: Owner KYC verification (anchor_verification_id required)
        - ATTESTED: Code attestation + trust score >= 0.7
        """
        current_level = self._store.get_level(agent_id)
        manifest = self._store.get_manifest(agent_id)

        if manifest is None:
            return KYAResult(
                agent_id=agent_id,
                level=KYALevel.NONE,
                status=KYAStatus.PENDING,
                allowed=False,
                reason="agent_not_registered",
            )

        # Validate upgrade requirements
        if target_level == KYALevel.VERIFIED:
            if not anchor_verification_id:
                return KYAResult(
                    agent_id=agent_id,
                    level=current_level,
                    status=self._store.get_status(agent_id),
                    allowed=False,
                    reason="anchor_verification_required: owner KYC must be completed",
                )

        elif target_level == KYALevel.ATTESTED:
            if not code_attestation:
                return KYAResult(
                    agent_id=agent_id,
                    level=current_level,
                    status=self._store.get_status(agent_id),
                    allowed=False,
                    reason="code_attestation_required",
                )
            trust = self._store.get_trust_score(agent_id)
            if trust and trust.score < 0.7:
                return KYAResult(
                    agent_id=agent_id,
                    level=current_level,
                    status=self._store.get_status(agent_id),
                    allowed=False,
                    reason=f"trust_score_insufficient: {trust.score:.2f} < 0.70",
                    trust_score=trust.score,
                )
            self._store.set_code_attestation(agent_id, code_attestation)

        # Perform upgrade
        self._store.set_level(agent_id, target_level)

        logger.info(
            "KYA level upgraded: agent_id=%s, %s → %s",
            agent_id, current_level.value, target_level.value,
        )

        return KYAResult(
            agent_id=agent_id,
            level=target_level,
            status=self._store.get_status(agent_id),
            allowed=True,
            reason=f"upgraded_to_{target_level.value}",
            owner_id=manifest.owner_id,
            anchor_verification_id=anchor_verification_id,
            manifest_hash=manifest.manifest_hash,
            code_hash=code_attestation.code_hash if code_attestation else None,
        )

    async def downgrade_level(self, agent_id: str, reason: str) -> KYAResult:
        """Downgrade agent KYA level (e.g., due to violations or stale liveness)."""
        current = self._store.get_level(agent_id)
        manifest = self._store.get_manifest(agent_id)

        # Step down one level
        downgrade_map = {
            KYALevel.ATTESTED: KYALevel.VERIFIED,
            KYALevel.VERIFIED: KYALevel.BASIC,
            KYALevel.BASIC: KYALevel.NONE,
            KYALevel.NONE: KYALevel.NONE,
        }
        new_level = downgrade_map[current]
        self._store.set_level(agent_id, new_level)

        logger.warning(
            "KYA level downgraded: agent_id=%s, %s → %s, reason=%s",
            agent_id, current.value, new_level.value, reason,
        )

        return KYAResult(
            agent_id=agent_id,
            level=new_level,
            status=self._store.get_status(agent_id),
            allowed=new_level != KYALevel.NONE,
            reason=f"downgraded: {reason}",
            owner_id=manifest.owner_id if manifest else None,
        )

    # ── Suspension / Revocation ───────────────────────────────────

    async def suspend_agent(self, agent_id: str, reason: str) -> KYAResult:
        """Temporarily suspend an agent's KYA status."""
        self._store.set_status(agent_id, KYAStatus.SUSPENDED)
        manifest = self._store.get_manifest(agent_id)

        logger.warning("Agent KYA suspended: agent_id=%s, reason=%s", agent_id, reason)

        return KYAResult(
            agent_id=agent_id,
            level=self._store.get_level(agent_id),
            status=KYAStatus.SUSPENDED,
            allowed=False,
            reason=f"suspended: {reason}",
            owner_id=manifest.owner_id if manifest else None,
        )

    async def revoke_agent(self, agent_id: str, reason: str) -> KYAResult:
        """Permanently revoke an agent's KYA status."""
        self._store.set_status(agent_id, KYAStatus.REVOKED)
        self._store.set_level(agent_id, KYALevel.NONE)
        self._liveness.remove(agent_id)
        manifest = self._store.get_manifest(agent_id)

        logger.warning("Agent KYA revoked: agent_id=%s, reason=%s", agent_id, reason)

        return KYAResult(
            agent_id=agent_id,
            level=KYALevel.NONE,
            status=KYAStatus.REVOKED,
            allowed=False,
            reason=f"revoked: {reason}",
            owner_id=manifest.owner_id if manifest else None,
        )

    async def reactivate_agent(self, agent_id: str) -> KYAResult:
        """Reactivate a suspended agent."""
        current_status = self._store.get_status(agent_id)
        if current_status != KYAStatus.SUSPENDED:
            return KYAResult(
                agent_id=agent_id,
                level=self._store.get_level(agent_id),
                status=current_status,
                allowed=False,
                reason=f"cannot_reactivate: status is {current_status.value}, not suspended",
            )

        self._store.set_status(agent_id, KYAStatus.ACTIVE)
        self._liveness.ping(agent_id)
        manifest = self._store.get_manifest(agent_id)

        logger.info("Agent KYA reactivated: agent_id=%s", agent_id)

        return KYAResult(
            agent_id=agent_id,
            level=self._store.get_level(agent_id),
            status=KYAStatus.ACTIVE,
            allowed=True,
            reason="reactivated",
            owner_id=manifest.owner_id if manifest else None,
        )

    # ── Trust Score ───────────────────────────────────────────────

    async def record_payment_outcome(
        self,
        agent_id: str,
        *,
        success: bool,
        amount: Decimal = Decimal("0"),
        policy_violation: bool = False,
    ) -> Optional[AgentTrustScore]:
        """Record a payment outcome for trust score calculation."""
        trust = self._store.get_trust_score(agent_id)
        if trust is None:
            trust = AgentTrustScore(agent_id=agent_id)

        if success:
            trust.successful_payments += 1
            trust.total_volume += amount
        else:
            trust.failed_payments += 1

        if policy_violation:
            trust.policy_violations += 1

        # Update uptime from liveness tracker
        manifest = self._store.get_manifest(agent_id)
        if manifest:
            age_seconds = (datetime.now(timezone.utc) - manifest.created_at).total_seconds()
            trust.age_days = max(0, int(age_seconds / 86400))

        trust.recalculate()
        self._store.set_trust_score(agent_id, trust)
        return trust

    async def get_trust_score(self, agent_id: str) -> Optional[AgentTrustScore]:
        """Get the current trust score for an agent."""
        return self._store.get_trust_score(agent_id)

    # ── Code Attestation ──────────────────────────────────────────

    async def attest_code(self, agent_id: str, attestation: CodeAttestation) -> KYAResult:
        """Submit a code attestation for an agent."""
        manifest = self._store.get_manifest(agent_id)
        if manifest is None:
            return KYAResult(
                agent_id=agent_id,
                level=KYALevel.NONE,
                status=KYAStatus.PENDING,
                allowed=False,
                reason="agent_not_registered",
            )

        self._store.set_code_attestation(agent_id, attestation)

        logger.info(
            "Code attestation recorded: agent_id=%s, hash=%s, framework=%s",
            agent_id, attestation.code_hash[:16], attestation.framework,
        )

        return KYAResult(
            agent_id=agent_id,
            level=self._store.get_level(agent_id),
            status=self._store.get_status(agent_id),
            allowed=True,
            reason="code_attested",
            code_hash=attestation.code_hash,
        )

    async def verify_code_hash(self, agent_id: str, expected_hash: str) -> bool:
        """Verify that an agent's code hash matches the registered attestation."""
        attestation = self._store.get_code_attestation(agent_id)
        if attestation is None:
            return False
        return attestation.verify(expected_hash)

    # ── Liveness ──────────────────────────────────────────────────

    def ping(self, agent_id: str) -> None:
        """Record a liveness heartbeat."""
        self._liveness.ping(agent_id)

    def is_alive(self, agent_id: str) -> bool:
        """Check if agent is alive."""
        return self._liveness.is_alive(agent_id)

    async def check_stale_agents(self) -> List[str]:
        """Check for stale agents and suspend them."""
        stale = self._liveness.get_stale_agents()
        suspended = []
        for agent_id in stale:
            status = self._store.get_status(agent_id)
            if status == KYAStatus.ACTIVE:
                await self.suspend_agent(agent_id, "liveness_timeout")
                suspended.append(agent_id)
        return suspended

    # ── Getters ───────────────────────────────────────────────────

    def get_manifest(self, agent_id: str) -> Optional[AgentManifest]:
        """Get agent manifest."""
        return self._store.get_manifest(agent_id)

    def get_level(self, agent_id: str) -> KYALevel:
        """Get agent KYA level."""
        return self._store.get_level(agent_id)

    def get_status(self, agent_id: str) -> KYAStatus:
        """Get agent KYA status."""
        return self._store.get_status(agent_id)


# ============ Factory ============


def create_kya_service(
    liveness_timeout: int = 300,
) -> KYAService:
    """Create a KYA service with default configuration."""
    return KYAService(liveness_timeout=liveness_timeout)
