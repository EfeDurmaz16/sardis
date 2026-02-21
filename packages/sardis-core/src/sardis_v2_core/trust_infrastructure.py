"""Trust Infrastructure — Unified trust framework for the agent economy.

Connects identity, compliance, reputation, and behavioral analysis into
a coherent trust layer that all Sardis components can query.

Components:
  1. Agent Registry     — register and lookup agents with their trust profiles
  2. Trust Evaluator    — evaluate trust between two agents for a transaction
  3. Attestation Manager — manage verifiable credentials and attestations
  4. Trust Network      — graph of trust relationships between agents

Usage:
    from sardis_v2_core.trust_infrastructure import (
        TrustFramework,
        AgentProfile,
        TrustAttestation,
    )

    framework = TrustFramework()

    # Register agent with trust profile
    profile = await framework.register_agent(
        agent_id="agent_123",
        owner_id="org_456",
        kya_level=KYALevel.VERIFIED,
        capabilities=["payment", "escrow"],
    )

    # Evaluate trust for a specific transaction
    evaluation = await framework.evaluate_trust(
        requester="agent_123",
        counterparty="agent_789",
        amount=Decimal("500"),
        operation="escrow",
    )

    if evaluation.approved:
        print(f"Trust approved: {evaluation.trust_score}")
    else:
        print(f"Denied: {evaluation.denial_reason}")
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from .kya_trust_scoring import (
    TrustScorer,
    TrustScore,
    TrustTier,
    KYALevel,
    TransactionRecord,
    ComplianceRecord,
    ReputationRecord,
    BehavioralRecord,
)

logger = logging.getLogger("sardis.core.trust_infrastructure")


# ============ Enums ============


class AttestationType(str, Enum):
    """Types of verifiable attestations."""
    IDENTITY = "identity"           # KYC/KYB verification
    CAPABILITY = "capability"       # Authorized capabilities
    COMPLIANCE = "compliance"       # Regulatory compliance
    CODE_AUDIT = "code_audit"       # Code has been audited
    BEHAVIOR = "behavior"           # Behavioral attestation from monitor
    COUNTERPARTY = "counterparty"   # Rating from a counterparty


class TrustRelationType(str, Enum):
    """Types of trust relationships between agents."""
    DIRECT = "direct"               # Direct interaction history
    TRANSITIVE = "transitive"       # Trust through mutual connections
    ORGANIZATIONAL = "organizational"  # Same org/team
    ATTESTATION = "attestation"     # Vouched for by trusted entity


# ============ Data Models ============


@dataclass
class TrustAttestation:
    """A verifiable trust attestation for an agent."""
    id: str = field(default_factory=lambda: f"att_{uuid4().hex[:12]}")
    agent_id: str = ""
    attestation_type: AttestationType = AttestationType.IDENTITY
    issuer_id: str = ""  # Who issued this attestation
    claim: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[str] = None  # Ed25519/ECDSA signature
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    revoked: bool = False

    @property
    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "type": self.attestation_type.value,
            "issuer_id": self.issuer_id,
            "claim": self.claim,
            "is_valid": self.is_valid,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class TrustRelation:
    """A trust relationship between two agents."""
    source_id: str
    target_id: str
    relation_type: TrustRelationType
    strength: float = 0.5  # 0.0 to 1.0
    interactions: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_interaction: Optional[datetime] = None


@dataclass
class AgentProfile:
    """Complete trust profile for an agent."""
    agent_id: str
    owner_id: str
    kya_level: KYALevel = KYALevel.NONE
    capabilities: List[str] = field(default_factory=list)
    attestations: List[TrustAttestation] = field(default_factory=list)
    trust_score: Optional[TrustScore] = None
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def valid_attestations(self) -> List[TrustAttestation]:
        return [a for a in self.attestations if a.is_valid]

    @property
    def has_capability(self) -> bool:
        return len(self.capabilities) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "owner_id": self.owner_id,
            "kya_level": self.kya_level.value,
            "capabilities": self.capabilities,
            "attestation_count": len(self.valid_attestations),
            "trust_score": self.trust_score.to_dict() if self.trust_score else None,
            "registered_at": self.registered_at.isoformat(),
        }


@dataclass
class TrustEvaluation:
    """Result of a trust evaluation between two agents."""
    requester_id: str
    counterparty_id: str
    operation: str
    amount: Decimal
    approved: bool
    trust_score: float
    requester_tier: TrustTier
    counterparty_tier: TrustTier
    denial_reason: Optional[str] = None
    required_attestations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requester_id": self.requester_id,
            "counterparty_id": self.counterparty_id,
            "operation": self.operation,
            "amount": str(self.amount),
            "approved": self.approved,
            "trust_score": round(self.trust_score, 4),
            "requester_tier": self.requester_tier.value,
            "counterparty_tier": self.counterparty_tier.value,
            "denial_reason": self.denial_reason,
            "warnings": self.warnings,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


# ============ Trust Framework ============


class TrustFramework:
    """Unified trust framework for the Sardis agent economy.

    Provides agent registration, trust evaluation, attestation management,
    and trust network analysis.
    """

    def __init__(self, scorer: Optional[TrustScorer] = None) -> None:
        self._scorer = scorer or TrustScorer()
        self._profiles: Dict[str, AgentProfile] = {}
        self._attestations: Dict[str, TrustAttestation] = {}
        self._relations: List[TrustRelation] = []

    # ---- Agent Registry ----

    async def register_agent(
        self,
        agent_id: str,
        owner_id: str,
        kya_level: KYALevel = KYALevel.NONE,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentProfile:
        """Register an agent with a trust profile."""
        profile = AgentProfile(
            agent_id=agent_id,
            owner_id=owner_id,
            kya_level=kya_level,
            capabilities=capabilities or [],
            metadata=metadata or {},
        )

        # Calculate initial trust score
        profile.trust_score = await self._scorer.calculate_trust(
            agent_id=agent_id,
            kya_level=kya_level,
        )

        self._profiles[agent_id] = profile

        logger.info(
            "Agent registered",
            extra={
                "agent_id": agent_id,
                "kya_level": kya_level.value,
                "trust_tier": profile.trust_score.tier.value,
            },
        )
        return profile

    async def get_profile(self, agent_id: str) -> Optional[AgentProfile]:
        """Get an agent's trust profile."""
        return self._profiles.get(agent_id)

    async def update_kya_level(
        self, agent_id: str, new_level: KYALevel
    ) -> AgentProfile:
        """Update an agent's KYA level and recalculate trust."""
        profile = self._profiles.get(agent_id)
        if not profile:
            raise ValueError(f"Agent not found: {agent_id}")

        profile.kya_level = new_level

        # Recalculate trust score
        self._scorer.invalidate_cache(agent_id)
        profile.trust_score = await self._scorer.calculate_trust(
            agent_id=agent_id,
            kya_level=new_level,
        )

        logger.info("KYA level updated", extra={"agent_id": agent_id, "level": new_level.value})
        return profile

    # ---- Trust Evaluation ----

    async def evaluate_trust(
        self,
        requester: str,
        counterparty: str,
        amount: Decimal,
        operation: str = "payment",
        history: Optional[TransactionRecord] = None,
        compliance: Optional[ComplianceRecord] = None,
        reputation: Optional[ReputationRecord] = None,
        behavioral: Optional[BehavioralRecord] = None,
    ) -> TrustEvaluation:
        """Evaluate trust between two agents for a specific transaction.

        Checks both agents' trust scores, their relationship, and
        validates the operation against capabilities and limits.
        """
        # Get or create profiles
        req_profile = self._profiles.get(requester)
        cpty_profile = self._profiles.get(counterparty)

        if not req_profile:
            req_profile = await self.register_agent(requester, owner_id="unknown")
        if not cpty_profile:
            cpty_profile = await self.register_agent(counterparty, owner_id="unknown")

        # Calculate fresh trust scores
        req_score = await self._scorer.calculate_trust(
            agent_id=requester,
            kya_level=req_profile.kya_level,
            history=history,
            compliance=compliance,
            reputation=reputation,
            behavioral=behavioral,
        )
        req_profile.trust_score = req_score

        cpty_score = await self._scorer.calculate_trust(
            agent_id=counterparty,
            kya_level=cpty_profile.kya_level,
        )
        cpty_profile.trust_score = cpty_score

        # Combined trust score (geometric mean)
        combined_score = (req_score.overall * cpty_score.overall) ** 0.5

        # Check limits
        warnings: List[str] = []
        denial_reason: Optional[str] = None
        approved = True

        # Check requester's spending limit
        if amount > req_score.max_per_tx:
            approved = False
            denial_reason = (
                f"Amount ${amount} exceeds requester's tx limit "
                f"${req_score.max_per_tx} (tier: {req_score.tier.value})"
            )

        # Check counterparty trust
        if cpty_score.tier == TrustTier.UNTRUSTED and amount > Decimal("10"):
            if approved:
                approved = False
                denial_reason = "Counterparty is untrusted for this amount"

        # Check capability
        if operation not in req_profile.capabilities and req_profile.capabilities:
            warnings.append(f"Operation '{operation}' not in agent capabilities")

        # Check for trust relationship
        relation = self._find_relation(requester, counterparty)
        if relation and relation.strength > 0.7:
            # Boost for strong relationship
            combined_score = min(1.0, combined_score * 1.1)
        elif not relation and amount > Decimal("100"):
            warnings.append("No prior trust relationship with counterparty")

        # Record interaction
        self._record_interaction(requester, counterparty)

        evaluation = TrustEvaluation(
            requester_id=requester,
            counterparty_id=counterparty,
            operation=operation,
            amount=amount,
            approved=approved,
            trust_score=combined_score,
            requester_tier=req_score.tier,
            counterparty_tier=cpty_score.tier,
            denial_reason=denial_reason,
            warnings=warnings,
        )

        logger.info(
            "Trust evaluation",
            extra={
                "requester": requester,
                "counterparty": counterparty,
                "approved": approved,
                "score": round(combined_score, 4),
            },
        )

        return evaluation

    # ---- Attestation Management ----

    async def issue_attestation(
        self,
        agent_id: str,
        attestation_type: AttestationType,
        issuer_id: str,
        claim: Dict[str, Any],
        ttl_days: int = 365,
    ) -> TrustAttestation:
        """Issue a trust attestation for an agent."""
        profile = self._profiles.get(agent_id)
        if not profile:
            raise ValueError(f"Agent not found: {agent_id}")

        # Create attestation with signature hash
        claim_str = str(sorted(claim.items()))
        signature = hashlib.sha256(
            f"{agent_id}:{issuer_id}:{claim_str}".encode()
        ).hexdigest()

        attestation = TrustAttestation(
            agent_id=agent_id,
            attestation_type=attestation_type,
            issuer_id=issuer_id,
            claim=claim,
            signature=signature,
            expires_at=datetime.now(timezone.utc) + timedelta(days=ttl_days),
        )

        profile.attestations.append(attestation)
        self._attestations[attestation.id] = attestation

        # Recalculate trust after attestation
        self._scorer.invalidate_cache(agent_id)

        logger.info(
            "Attestation issued",
            extra={
                "agent_id": agent_id,
                "type": attestation_type.value,
                "issuer": issuer_id,
            },
        )
        return attestation

    async def revoke_attestation(self, attestation_id: str) -> bool:
        """Revoke an attestation."""
        attestation = self._attestations.get(attestation_id)
        if not attestation:
            return False

        attestation.revoked = True

        # Invalidate trust cache for affected agent
        self._scorer.invalidate_cache(attestation.agent_id)

        logger.info("Attestation revoked", extra={"attestation_id": attestation_id})
        return True

    async def verify_attestation(self, attestation_id: str) -> Dict[str, Any]:
        """Verify an attestation's validity."""
        attestation = self._attestations.get(attestation_id)
        if not attestation:
            return {"valid": False, "reason": "not_found"}

        if attestation.revoked:
            return {"valid": False, "reason": "revoked"}

        if attestation.expires_at and datetime.now(timezone.utc) > attestation.expires_at:
            return {"valid": False, "reason": "expired"}

        # Verify signature
        claim_str = str(sorted(attestation.claim.items()))
        expected_sig = hashlib.sha256(
            f"{attestation.agent_id}:{attestation.issuer_id}:{claim_str}".encode()
        ).hexdigest()

        if attestation.signature != expected_sig:
            return {"valid": False, "reason": "invalid_signature"}

        return {
            "valid": True,
            "attestation": attestation.to_dict(),
            "issuer": attestation.issuer_id,
        }

    async def get_attestations(
        self,
        agent_id: str,
        attestation_type: Optional[AttestationType] = None,
        valid_only: bool = True,
    ) -> List[TrustAttestation]:
        """Get attestations for an agent."""
        profile = self._profiles.get(agent_id)
        if not profile:
            return []

        attestations = profile.attestations

        if attestation_type:
            attestations = [a for a in attestations if a.attestation_type == attestation_type]

        if valid_only:
            attestations = [a for a in attestations if a.is_valid]

        return attestations

    # ---- Trust Network ----

    def _find_relation(self, source: str, target: str) -> Optional[TrustRelation]:
        """Find trust relationship between two agents."""
        for rel in self._relations:
            if (rel.source_id == source and rel.target_id == target) or \
               (rel.source_id == target and rel.target_id == source):
                return rel
        return None

    def _record_interaction(self, agent_a: str, agent_b: str) -> None:
        """Record an interaction between two agents, updating trust relation."""
        relation = self._find_relation(agent_a, agent_b)

        if relation:
            relation.interactions += 1
            relation.last_interaction = datetime.now(timezone.utc)
            # Strengthen trust with interactions (asymptotic to 1.0)
            relation.strength = min(1.0, relation.strength + 0.05 * (1.0 - relation.strength))
        else:
            self._relations.append(TrustRelation(
                source_id=agent_a,
                target_id=agent_b,
                relation_type=TrustRelationType.DIRECT,
                strength=0.1,
                interactions=1,
                last_interaction=datetime.now(timezone.utc),
            ))

    async def get_trust_network(
        self, agent_id: str, depth: int = 1
    ) -> Dict[str, Any]:
        """Get the trust network around an agent.

        Returns direct connections (depth=1) or extended network (depth>1).
        """
        visited: Set[str] = set()
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        await self._traverse_network(agent_id, depth, visited, nodes, edges)

        return {
            "center": agent_id,
            "depth": depth,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    async def _traverse_network(
        self,
        agent_id: str,
        depth: int,
        visited: Set[str],
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
    ) -> None:
        """Recursively traverse trust network."""
        if depth < 0 or agent_id in visited:
            return

        visited.add(agent_id)

        profile = self._profiles.get(agent_id)
        nodes.append({
            "id": agent_id,
            "kya_level": profile.kya_level.value if profile else "none",
            "trust_tier": profile.trust_score.tier.value if profile and profile.trust_score else "untrusted",
        })

        for rel in self._relations:
            if rel.source_id == agent_id or rel.target_id == agent_id:
                other = rel.target_id if rel.source_id == agent_id else rel.source_id

                edges.append({
                    "source": rel.source_id,
                    "target": rel.target_id,
                    "type": rel.relation_type.value,
                    "strength": round(rel.strength, 4),
                    "interactions": rel.interactions,
                })

                if other not in visited:
                    await self._traverse_network(other, depth - 1, visited, nodes, edges)

    # ---- Utility ----

    async def get_stats(self) -> Dict[str, Any]:
        """Get trust infrastructure statistics."""
        tier_counts: Dict[str, int] = {}
        for profile in self._profiles.values():
            if profile.trust_score:
                tier = profile.trust_score.tier.value
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

        return {
            "total_agents": len(self._profiles),
            "total_attestations": len(self._attestations),
            "total_relations": len(self._relations),
            "agents_by_tier": tier_counts,
            "valid_attestations": sum(
                1 for a in self._attestations.values() if a.is_valid
            ),
        }
