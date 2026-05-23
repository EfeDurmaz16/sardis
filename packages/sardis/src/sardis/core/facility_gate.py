"""Facility Gate primitives for partner-backed agent credit/facility access.

The module deliberately models authority and evidence, not lending.  Agents
request delegated access to an external/sponsor-backed facility; Sardis makes
an explainable authorization decision and records the basis for replay.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Protocol
from uuid import uuid4

FACILITY_RISK_MODEL_VERSION = "facility_gate_rules_v0"
FACILITY_POLICY_VERSION = "facility_policy_v0"
FACILITY_DECISION_PACKET_SCHEMA_VERSION = "facility_decision_packet_v1"


class FacilityStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PARTNER_DISABLED = "partner_disabled"


class FacilityRail(str, Enum):
    VIRTUAL_CARD = "virtual_card"
    INVOICE = "invoice"
    ACH = "ach"
    STABLECOIN = "stablecoin"
    SIMULATED_CARD = "simulated_card"


class FacilityType(str, Enum):
    REVOLVING = "revolving"
    TRANSACTIONAL_LIMIT = "transactional_limit"
    JIT_FUNDING = "jit_funding"
    SPONSOR_BACKED = "sponsor_backed"


class FacilityDecision(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    STEP_UP_REQUIRED = "step_up_required"


class FacilityEventType(str, Enum):
    REQUEST_CREATED = "facility.request.created"
    EVIDENCE_ATTACHED = "facility.evidence.attached"
    AUTH_APPROVED = "facility.authorization.approved"
    AUTH_DENIED = "facility.authorization.denied"
    AUTH_STEP_UP_REQUIRED = "facility.authorization.step_up_required"
    APPROVAL_REQUESTED = "facility.approval.requested"
    APPROVAL_RECORDED = "facility.approval.recorded"
    EXECUTION_SIMULATED = "facility.execution.simulated"
    PROVIDER_WEBHOOK_RECEIVED = "facility.provider_webhook.received"
    SETTLEMENT_UPDATED = "facility.settlement.updated"
    REVOCATION_CREATED = "facility.revocation.created"
    EXCEPTION_CREATED = "facility.exception.created"
    EXCEPTION_RESOLVED = "facility.exception.resolved"


class FacilityRevocationScope(str, Enum):
    GLOBAL = "global"
    ORGANIZATION = "organization"
    FACILITY = "facility"
    MANDATE = "mandate"
    AGENT = "agent"
    MERCHANT = "merchant"
    AUTHORIZATION = "authorization"


class FacilityRiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FacilityRepaymentStatus(str, Enum):
    CURRENT = "current"
    GRACE = "grace"
    LATE = "late"
    DELINQUENT = "delinquent"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class FacilityLimit:
    per_transaction_minor: int
    daily_minor: int | None = None
    monthly_minor: int | None = None
    currency: str = "USD"


@dataclass(slots=True)
class Facility:
    facility_id: str
    organization_id: str
    sponsor_id: str
    provider: str = "simulated"
    facility_type: FacilityType = FacilityType.SPONSOR_BACKED
    status: FacilityStatus = FacilityStatus.ACTIVE
    limit: FacilityLimit = field(default_factory=lambda: FacilityLimit(per_transaction_minor=500_000))
    allowed_categories: list[str] = field(default_factory=lambda: ["cloud", "api", "saas", "developer_tools"])
    allowed_merchants: list[str] = field(default_factory=list)
    blocked_merchants: list[str] = field(default_factory=list)
    approval_threshold_minor: int = 100_000
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FacilityEvidenceRef:
    evidence_id: str
    evidence_type: str
    content_hash: str
    uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FacilityRequest:
    request_id: str
    organization_id: str
    agent_id: str
    sponsor_id: str
    facility_id: str
    mandate_id: str
    merchant: str
    amount_minor: int
    currency: str = "USD"
    category: str = "cloud"
    rail: FacilityRail = FacilityRail.SIMULATED_CARD
    purpose: str = ""
    task_graph_hash: str | None = None
    evidence: list[FacilityEvidenceRef] = field(default_factory=list)
    request_payload_hash: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class LiabilityAssignment:
    repayment_obligor: str
    settlement_responsible_party: str
    loss_owner: str
    sardis_role: str = "policy_authorization_evidence_layer"
    terms_ref: str | None = None


@dataclass(slots=True)
class FacilityPolicyEvaluation:
    verdict: FacilityDecision
    reason_codes: list[str]
    checks: list[dict[str, Any]]
    policy_version: str = FACILITY_POLICY_VERSION


@dataclass(slots=True)
class FacilityRiskAssessment:
    score: int
    tier: FacilityRiskTier
    reason_codes: list[str]
    features: dict[str, Any]
    model_version: str = FACILITY_RISK_MODEL_VERSION


@dataclass(slots=True)
class FacilityRepaymentMirror:
    facility_id: str
    sponsor_id: str
    status: FacilityRepaymentStatus = FacilityRepaymentStatus.UNKNOWN
    source: str = "unknown"
    statement_ref: str | None = None
    days_past_due: int | None = None
    as_of: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FacilityAuthorizationDecision:
    decision_id: str
    request_id: str
    verdict: FacilityDecision
    reason_codes: list[str]
    policy: FacilityPolicyEvaluation
    risk: FacilityRiskAssessment
    liability: LiabilityAssignment
    mandate_id: str
    mandate_version: int | None
    facility_id: str
    facility_version: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class FacilityRevocation:
    revocation_id: str
    organization_id: str
    scope: FacilityRevocationScope
    target_id: str
    reason: str
    created_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class SimulatedFacilityCredential:
    credential_id: str
    authorization_id: str
    merchant: str
    amount_minor: int
    currency: str
    status: str = "active"
    last4: str = "4242"
    provider: str = "simulated"


@dataclass(slots=True, frozen=True)
class FacilityAdapterCapabilities:
    provider: str
    contract_version: str = "facility_adapter_v1"
    supports_execute: bool = True
    supports_revoke: bool = True
    supports_void: bool = False
    supports_webhooks: bool = False
    supports_merchant_lock: bool = True
    supports_amount_limit: bool = True
    supports_single_use: bool = True
    supports_expiry: bool = True


@dataclass(slots=True)
class FacilityProviderWebhookEvent:
    provider: str
    provider_event_id: str
    event_type: str
    organization_id: str
    request_id: str | None
    authorization_id: str | None
    raw_payload_hash: str
    payload: dict[str, Any]
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FacilityExecutionAdapter(Protocol):
    capabilities: FacilityAdapterCapabilities

    async def execute_authorization(
        self,
        *,
        request: FacilityRequest,
        decision: FacilityAuthorizationDecision,
    ) -> SimulatedFacilityCredential:
        ...

    async def revoke_authorization(self, authorization_id: str, reason: str) -> bool:
        ...


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    return value


def stable_payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(to_jsonable(payload), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_decision_packet(
    *,
    request: FacilityRequest,
    decision: FacilityAuthorizationDecision,
    evidence: list[FacilityEvidenceRef] | None = None,
    request_payload_hash: str | None = None,
    mandate_snapshot_hash: str | None = None,
    facility_snapshot_hash: str | None = None,
    policy_snapshot_hash: str | None = None,
    repayment_mirror: FacilityRepaymentMirror | None = None,
    adapter_contract_version: str = "facility_adapter_v1",
) -> dict[str, Any]:
    """Build the immutable, exportable decision basis for audit review."""
    packet = {
        "schema_version": FACILITY_DECISION_PACKET_SCHEMA_VERSION,
        "request_id": request.request_id,
        "decision_id": decision.decision_id,
        "verdict": decision.verdict.value,
        "reason_codes": list(decision.reason_codes),
        "mandate": {
            "mandate_id": decision.mandate_id,
            "mandate_version": decision.mandate_version,
            "mandate_snapshot_hash": mandate_snapshot_hash,
        },
        "facility": {
            "facility_id": decision.facility_id,
            "facility_version": decision.facility_version,
            "facility_snapshot_hash": facility_snapshot_hash,
        },
        "policy": {
            "policy_version": decision.policy.policy_version,
            "policy_snapshot_hash": policy_snapshot_hash,
            "checks": to_jsonable(decision.policy.checks),
        },
        "risk": to_jsonable(decision.risk),
        "repayment_mirror": to_jsonable(repayment_mirror) if repayment_mirror else None,
        "liability": to_jsonable(decision.liability),
        "request_payload_hash": request_payload_hash or request.request_payload_hash,
        "considered_evidence_ids": [item.evidence_id for item in evidence or request.evidence],
        "considered_evidence_hashes": [item.content_hash for item in evidence or request.evidence],
        "adapter_contract_version": adapter_contract_version,
        "created_at": decision.created_at.isoformat(),
    }
    packet["decision_packet_hash"] = stable_payload_hash(packet)
    return packet


def evaluate_facility_policy(
    *,
    request: FacilityRequest,
    facility: Facility,
    mandate_check: Any | None,
) -> FacilityPolicyEvaluation:
    checks: list[dict[str, Any]] = []
    reasons: list[str] = []

    def record(name: str, passed: bool, reason: str | None = None) -> None:
        checks.append({"name": name, "passed": passed, "reason": reason})
        if not passed and reason:
            reasons.append(reason)

    if mandate_check is None:
        record("mandate_present", False, "mandate_required")
    elif not getattr(mandate_check, "approved", False):
        record("mandate_facility_authority", False, getattr(mandate_check, "error_code", None) or "mandate_denied")
    else:
        record("mandate_facility_authority", True)

    record("facility_active", facility.status == FacilityStatus.ACTIVE, f"facility_{facility.status.value}")
    record(
        "amount_per_transaction",
        request.amount_minor <= facility.limit.per_transaction_minor,
        "facility_amount_exceeds_per_transaction_limit",
    )
    record("currency", request.currency == facility.limit.currency, "facility_currency_not_allowed")
    record("category", request.category in facility.allowed_categories, "facility_category_not_allowed")
    record("merchant_not_blocked", request.merchant not in facility.blocked_merchants, "facility_merchant_blocked")
    if facility.allowed_merchants:
        record("merchant_allowed", request.merchant in facility.allowed_merchants, "facility_merchant_not_allowed")
    else:
        record("merchant_allowed", True)

    if any(not c["passed"] for c in checks):
        return FacilityPolicyEvaluation(verdict=FacilityDecision.DENIED, reason_codes=reasons, checks=checks)

    step_up_reasons: list[str] = []
    if request.amount_minor > facility.approval_threshold_minor:
        step_up_reasons.append("facility_amount_requires_approval")
    if not request.evidence:
        step_up_reasons.append("facility_evidence_required")
    if request.task_graph_hash is None:
        step_up_reasons.append("facility_task_graph_required")

    if step_up_reasons:
        return FacilityPolicyEvaluation(
            verdict=FacilityDecision.STEP_UP_REQUIRED,
            reason_codes=step_up_reasons,
            checks=checks,
        )

    return FacilityPolicyEvaluation(verdict=FacilityDecision.APPROVED, reason_codes=["facility_policy_passed"], checks=checks)


def score_facility_request(
    *,
    request: FacilityRequest,
    facility: Facility,
    merchant_is_novel: bool = True,
    sponsor_repayment_status: str = "unknown",
    agent_trust_tier: str = "new",
) -> FacilityRiskAssessment:
    score = 20
    reasons: list[str] = []
    features = {
        "amount_minor": request.amount_minor,
        "facility_limit_minor": facility.limit.per_transaction_minor,
        "merchant_is_novel": merchant_is_novel,
        "sponsor_repayment_status": sponsor_repayment_status,
        "agent_trust_tier": agent_trust_tier,
        "evidence_count": len(request.evidence),
    }
    if request.amount_minor > facility.approval_threshold_minor:
        score += 20
        reasons.append("amount_above_approval_threshold")
    if merchant_is_novel:
        score += 15
        reasons.append("novel_merchant")
    if not request.evidence:
        score += 20
        reasons.append("missing_evidence")
    if sponsor_repayment_status in {"late", "delinquent", "unknown"}:
        score += 15
        reasons.append(f"sponsor_repayment_{sponsor_repayment_status}")
    if agent_trust_tier in {"new", "restricted"}:
        score += 10
        reasons.append(f"agent_trust_{agent_trust_tier}")

    score = min(score, 100)
    tier = FacilityRiskTier.LOW if score < 40 else FacilityRiskTier.MEDIUM if score < 75 else FacilityRiskTier.HIGH
    return FacilityRiskAssessment(score=score, tier=tier, reason_codes=reasons or ["baseline"], features=features)


def build_facility_decision(
    *,
    request: FacilityRequest,
    facility: Facility,
    mandate_check: Any | None,
    liability: LiabilityAssignment,
    merchant_is_novel: bool = True,
    sponsor_repayment_status: str = "unknown",
    agent_trust_tier: str = "new",
    repayment_mirror: FacilityRepaymentMirror | None = None,
) -> FacilityAuthorizationDecision:
    effective_repayment_status = (
        repayment_mirror.status.value
        if repayment_mirror is not None
        else sponsor_repayment_status
    )
    policy = evaluate_facility_policy(request=request, facility=facility, mandate_check=mandate_check)
    risk = score_facility_request(
        request=request,
        facility=facility,
        merchant_is_novel=merchant_is_novel,
        sponsor_repayment_status=effective_repayment_status,
        agent_trust_tier=agent_trust_tier,
    )

    verdict = policy.verdict
    reasons = list(policy.reason_codes)
    if verdict == FacilityDecision.APPROVED and risk.tier == FacilityRiskTier.HIGH:
        verdict = FacilityDecision.STEP_UP_REQUIRED
        reasons.append("risk_tier_requires_approval")
    elif verdict == FacilityDecision.APPROVED:
        reasons.append("facility_authorization_approved")

    return FacilityAuthorizationDecision(
        decision_id=f"fac_dec_{uuid4().hex[:16]}",
        request_id=request.request_id,
        verdict=verdict,
        reason_codes=reasons,
        policy=policy,
        risk=risk,
        liability=liability,
        mandate_id=request.mandate_id,
        mandate_version=getattr(mandate_check, "mandate_version", None),
        facility_id=facility.facility_id,
        facility_version=facility.version,
    )


class SimulatedFacilityAdapter:
    """Non-money-moving adapter used to validate the authorization lifecycle."""

    capabilities = FacilityAdapterCapabilities(provider="simulated")

    def __init__(self) -> None:
        self._credentials: dict[str, SimulatedFacilityCredential] = {}

    async def execute_authorization(
        self,
        *,
        request: FacilityRequest,
        decision: FacilityAuthorizationDecision,
    ) -> SimulatedFacilityCredential:
        if decision.verdict != FacilityDecision.APPROVED:
            raise ValueError("facility_authorization_not_approved")
        credential = SimulatedFacilityCredential(
            credential_id=f"sim_fac_cred_{uuid4().hex[:16]}",
            authorization_id=decision.decision_id,
            merchant=request.merchant,
            amount_minor=request.amount_minor,
            currency=request.currency,
        )
        self._credentials[credential.credential_id] = credential
        return credential

    async def revoke_authorization(self, authorization_id: str, reason: str) -> bool:
        revoked = False
        for credential in self._credentials.values():
            if credential.authorization_id == authorization_id:
                credential.status = "revoked"
                revoked = True
        return revoked


class DisabledProviderFacilityAdapter:
    """Compile-time provider adapter skeleton that cannot execute live money movement."""

    def __init__(self, provider: str) -> None:
        self.capabilities = FacilityAdapterCapabilities(
            provider=provider,
            supports_webhooks=True,
        )

    async def execute_authorization(
        self,
        *,
        request: FacilityRequest,
        decision: FacilityAuthorizationDecision,
    ) -> SimulatedFacilityCredential:
        raise RuntimeError("facility_provider_adapter_disabled")

    async def revoke_authorization(self, authorization_id: str, reason: str) -> bool:
        raise RuntimeError("facility_provider_adapter_disabled")


class MockProviderFacilityAdapter:
    """Sandbox/mock provider adapter used for contract tests before real provider work."""

    capabilities = FacilityAdapterCapabilities(
        provider="mock_provider",
        supports_webhooks=True,
    )

    def __init__(self) -> None:
        self._credentials: dict[str, SimulatedFacilityCredential] = {}

    async def execute_authorization(
        self,
        *,
        request: FacilityRequest,
        decision: FacilityAuthorizationDecision,
    ) -> SimulatedFacilityCredential:
        if decision.verdict != FacilityDecision.APPROVED:
            raise ValueError("facility_authorization_not_approved")
        credential = SimulatedFacilityCredential(
            credential_id=f"mock_fac_cred_{uuid4().hex[:16]}",
            authorization_id=decision.decision_id,
            merchant=request.merchant,
            amount_minor=request.amount_minor,
            currency=request.currency,
            last4="1111",
            provider=self.capabilities.provider,
        )
        self._credentials[credential.credential_id] = credential
        return credential

    async def revoke_authorization(self, authorization_id: str, reason: str) -> bool:
        revoked = False
        for credential in self._credentials.values():
            if credential.authorization_id == authorization_id:
                credential.status = "revoked"
                revoked = True
        return revoked
