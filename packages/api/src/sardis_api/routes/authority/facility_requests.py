"""Facility Gate API for partner-backed, non-custodial agent facility access."""
from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sardis_v2_core.facility_gate import (
    Facility,
    FacilityDecision,
    FacilityEventType,
    FacilityEvidenceRef,
    FacilityExecutionAdapter,
    FacilityLimit,
    FacilityProviderWebhookEvent,
    FacilityRail,
    FacilityRepaymentMirror,
    FacilityRepaymentStatus,
    FacilityRequest,
    FacilityRevocationScope,
    FacilityStatus,
    FacilityType,
    LiabilityAssignment,
    build_decision_packet,
    build_facility_decision,
    stable_payload_hash,
    to_jsonable,
)

from sardis_api.authz import Principal, require_principal
from sardis_api.repositories.facility_gate_repository import FacilityGateRepository
from sardis_api.routes.operations.metrics import (
    record_facility_adapter_event,
    record_facility_decision,
    record_facility_exception,
    record_facility_revocation,
    set_facility_manual_review_queue_depth,
)
from sardis_api.services.facility_gate_authority import (
    DefaultFacilityPolicyResolver,
    FacilityMandateResolver,
    FacilityPolicyResolver,
    FacilityRecordResolver,
    SnapshotBackedFacilityMandateResolver,
    SnapshotBackedFacilityRecordResolver,
    mandate_from_snapshot,
)
from sardis_api.services.facility_gate_limits import FacilityGateLimiter

router = APIRouter(dependencies=[Depends(require_principal)])
provider_webhooks_router = APIRouter()


def _facility_gate_enabled() -> bool:
    return os.getenv("SARDIS_FACILITY_GATE_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _require_facility_gate_globally_enabled() -> None:
    if not _facility_gate_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facility Gate is disabled. Set SARDIS_FACILITY_GATE_ENABLED=true to enable.",
        )


def _facility_gate_org_allowlist() -> set[str]:
    raw = os.getenv("SARDIS_FACILITY_GATE_ORG_ALLOWLIST", "").strip()
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def require_facility_gate_enabled(principal: Principal = Depends(require_principal)) -> None:
    _require_facility_gate_globally_enabled()
    allowlist = _facility_gate_org_allowlist()
    if allowlist and "*" not in allowlist and principal.organization_id not in allowlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facility Gate is not enabled for this organization.",
        )


def _provider_webhooks_enabled() -> bool:
    return os.getenv("SARDIS_FACILITY_PROVIDER_WEBHOOKS_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def require_provider_webhooks_enabled() -> None:
    _require_facility_gate_globally_enabled()
    if not _provider_webhooks_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facility provider webhooks are disabled.",
        )


class FacilityEvidenceInput(BaseModel):
    evidence_type: str = Field(..., min_length=1)
    content_hash: str = Field(..., min_length=8)
    uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MandateSnapshotInput(BaseModel):
    principal_id: str = "principal_demo"
    issuer_id: str = "principal_demo"
    org_id: str = ""
    agent_id: str | None = None
    id: str | None = None
    merchant_scope: dict[str, Any] = Field(default_factory=dict)
    purpose_scope: str | None = None
    amount_per_tx: Decimal | None = None
    amount_total: Decimal | None = None
    currency: str = "USD"
    allowed_rails: list[str] = Field(default_factory=lambda: ["simulated_card", "virtual_card"])
    approval_threshold: Decimal | None = None
    approval_mode: str = "auto"
    version: int = 1
    facility_authority_allowed: bool = False
    allowed_facility_ids: list[str] = Field(default_factory=list)
    facility_max_draw: Decimal | None = None
    facility_scope: dict[str, Any] = Field(default_factory=dict)


class FacilityRequestCreate(BaseModel):
    agent_id: str
    sponsor_id: str
    facility_id: str = "fac_sim_default"
    mandate_id: str
    merchant: str
    amount_minor: int = Field(..., gt=0)
    currency: str = "USD"
    category: str = "cloud"
    rail: FacilityRail = FacilityRail.SIMULATED_CARD
    purpose: str = ""
    task_graph_hash: str | None = None
    evidence: list[FacilityEvidenceInput] = Field(default_factory=list)
    mandate_snapshot: MandateSnapshotInput | None = None
    facility_snapshot: dict[str, Any] | None = None
    idempotency_key: str | None = None


class FacilityRecordUpsertRequest(BaseModel):
    facility_id: str
    sponsor_id: str
    provider: str = "simulated"
    facility_type: str = "sponsor_backed"
    status: str = "active"
    version: int = 1
    limit: dict[str, Any] = Field(default_factory=lambda: {"per_transaction_minor": 500_000, "currency": "USD"})
    allowed_categories: list[str] = Field(default_factory=lambda: ["cloud", "api", "saas", "developer_tools"])
    allowed_merchants: list[str] = Field(default_factory=list)
    blocked_merchants: list[str] = Field(default_factory=list)
    approval_threshold_minor: int = 100_000
    metadata: dict[str, Any] = Field(default_factory=dict)


class FacilityPolicyRecordUpsertRequest(BaseModel):
    facility_id: str
    policy_version: str
    snapshot: dict[str, Any]


class FacilityMandateRecordUpsertRequest(BaseModel):
    mandate: MandateSnapshotInput


class FacilityRequestResponse(BaseModel):
    request_id: str
    duplicate: bool = False
    event_id: str
    status: str = "created"


class FacilityDecisionResponse(BaseModel):
    decision_id: str
    request_id: str
    verdict: str
    reason_codes: list[str]
    policy: dict[str, Any]
    risk: dict[str, Any]
    liability: dict[str, Any]
    event_id: str


class FacilityEvidenceAttachRequest(BaseModel):
    evidence: list[FacilityEvidenceInput] = Field(..., min_length=1)
    idempotency_key: str | None = None


class FacilityExecutionResponse(BaseModel):
    credential: dict[str, Any]
    event_id: str


class FacilityRevocationRequest(BaseModel):
    scope: FacilityRevocationScope
    target_id: str
    reason: str = Field(..., min_length=3)
    idempotency_key: str | None = None


class FacilityApprovalRequest(BaseModel):
    approved: bool
    reviewed_by: str = Field(..., min_length=1)
    reason: str | None = None
    idempotency_key: str | None = None


class FacilityExceptionResolveRequest(BaseModel):
    event_id: str = Field(..., min_length=1)
    resolved_by: str = Field(..., min_length=1)
    resolution: str = Field(..., min_length=3)
    idempotency_key: str | None = None


class FacilityProviderWebhookRequest(BaseModel):
    organization_id: str
    provider_event_id: str = Field(..., min_length=3)
    event_type: str = Field(..., min_length=1)
    request_id: str | None = None
    authorization_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


@dataclass
class FacilityDependencies:
    repository: FacilityGateRepository
    adapter: FacilityExecutionAdapter
    mandate_resolver: FacilityMandateResolver | None = None
    facility_resolver: FacilityRecordResolver | None = None
    policy_resolver: FacilityPolicyResolver | None = None
    approval_service: Any | None = None


_deps: FacilityDependencies | None = None


def get_deps() -> FacilityDependencies:
    if _deps is None:
        raise RuntimeError("Facility dependencies not injected")
    return _deps


def _evidence_refs(evidence: list[FacilityEvidenceInput]) -> list[FacilityEvidenceRef]:
    return [
        FacilityEvidenceRef(
            evidence_id=f"fac_evd_{uuid4().hex[:12]}",
            evidence_type=item.evidence_type,
            content_hash=item.content_hash,
            uri=item.uri,
            metadata=item.metadata,
        )
        for item in evidence
    ]


def _request_from_payload(payload: dict[str, Any]) -> FacilityRequest:
    raw = payload.get("request", payload)
    return FacilityRequest(
        request_id=raw["request_id"],
        organization_id=raw["organization_id"],
        agent_id=raw["agent_id"],
        sponsor_id=raw["sponsor_id"],
        facility_id=raw["facility_id"],
        mandate_id=raw["mandate_id"],
        merchant=raw["merchant"],
        amount_minor=int(raw["amount_minor"]),
        currency=raw.get("currency", "USD"),
        category=raw.get("category", "cloud"),
        rail=FacilityRail(raw.get("rail", "simulated_card")),
        purpose=raw.get("purpose", ""),
        task_graph_hash=raw.get("task_graph_hash"),
        evidence=[
            FacilityEvidenceRef(
                evidence_id=e["evidence_id"],
                evidence_type=e["evidence_type"],
                content_hash=e["content_hash"],
                uri=e.get("uri"),
                metadata=e.get("metadata", {}),
            )
            for e in raw.get("evidence", [])
        ],
        request_payload_hash=raw.get("request_payload_hash"),
    )


def _facility_from_snapshot(org_id: str, sponsor_id: str, facility_id: str, snapshot: dict[str, Any] | None) -> Facility:
    if not snapshot:
        return Facility(facility_id=facility_id, organization_id=org_id, sponsor_id=sponsor_id)
    limit = snapshot.get("limit", {})
    return Facility(
        facility_id=facility_id,
        organization_id=org_id,
        sponsor_id=sponsor_id,
        provider=snapshot.get("provider", "simulated"),
        status=FacilityStatus(snapshot.get("status", "active")),
        limit=FacilityLimit(
            per_transaction_minor=int(limit.get("per_transaction_minor", 500_000)),
            daily_minor=limit.get("daily_minor"),
            monthly_minor=limit.get("monthly_minor"),
            currency=limit.get("currency", snapshot.get("currency", "USD")),
        ),
        allowed_categories=list(snapshot.get("allowed_categories", ["cloud", "api", "saas", "developer_tools"])),
        allowed_merchants=list(snapshot.get("allowed_merchants", [])),
        blocked_merchants=list(snapshot.get("blocked_merchants", [])),
        approval_threshold_minor=int(snapshot.get("approval_threshold_minor", 100_000)),
        version=int(snapshot.get("version", 1)),
        metadata=dict(snapshot.get("metadata", {})),
    )


def _require_persisted_authority() -> bool:
    return os.getenv("SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _mandate_resolver(deps: FacilityDependencies) -> FacilityMandateResolver:
    return deps.mandate_resolver or SnapshotBackedFacilityMandateResolver()


def _facility_resolver(deps: FacilityDependencies) -> FacilityRecordResolver:
    return deps.facility_resolver or SnapshotBackedFacilityRecordResolver(_facility_from_snapshot)


def _policy_resolver(deps: FacilityDependencies) -> FacilityPolicyResolver:
    return deps.policy_resolver or DefaultFacilityPolicyResolver()


async def _load_request_events_or_404(
    deps: FacilityDependencies,
    principal: Principal,
    request_id: str,
) -> list[dict[str, Any]]:
    events = await deps.repository.list_events(organization_id=principal.organization_id, aggregate_id=request_id)
    if not events:
        raise HTTPException(status_code=404, detail="Facility request not found")
    return events


def _latest_request_payload(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in events:
        if event["event_type"] == FacilityEventType.REQUEST_CREATED.value:
            return event["payload"]
    raise HTTPException(status_code=409, detail="Facility request is missing creation event")


async def _has_revocation(
    deps: FacilityDependencies,
    principal: Principal,
    request: FacilityRequest,
) -> str | None:
    aggregates = ["global", principal.organization_id, request.facility_id, request.mandate_id, request.agent_id, request.merchant, request.request_id]
    for aggregate in aggregates:
        events = await deps.repository.list_events(organization_id=principal.organization_id, aggregate_id=aggregate)
        for event in events:
            if event["event_type"] == FacilityEventType.REVOCATION_CREATED.value:
                return event["payload"].get("reason") or "facility_authority_revoked"
    return None


async def _append_exception(
    deps: FacilityDependencies,
    *,
    principal: Principal,
    aggregate_id: str,
    reason: str,
    payload: dict[str, Any],
) -> None:
    await deps.repository.append_event(
        organization_id=principal.organization_id,
        aggregate_id=aggregate_id,
        event_type=FacilityEventType.EXCEPTION_CREATED,
        payload={"reason": reason, **payload},
        actor_id=principal.user_id,
    )
    record_facility_exception(reason=reason)


def _latest_approval(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in reversed(events):
        if event["event_type"] == FacilityEventType.APPROVAL_RECORDED.value:
            return event["payload"]
    return None


def _latest_approval_request(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in reversed(events):
        if event["event_type"] == FacilityEventType.APPROVAL_REQUESTED.value:
            return event["payload"]
    return None


def _latest_authorization_event(events: list[dict[str, Any]]) -> tuple[int, dict[str, Any]] | None:
    for idx in range(len(events) - 1, -1, -1):
        if events[idx]["event_type"] in {
            FacilityEventType.AUTH_APPROVED.value,
            FacilityEventType.AUTH_DENIED.value,
            FacilityEventType.AUTH_STEP_UP_REQUIRED.value,
        }:
            return idx, events[idx]
    return None


def _decision_response_from_event(request_id: str, event: dict[str, Any]) -> FacilityDecisionResponse:
    decision_payload = event["payload"]["decision"]
    return FacilityDecisionResponse(
        decision_id=decision_payload["decision_id"],
        request_id=request_id,
        verdict=decision_payload["verdict"],
        reason_codes=decision_payload["reason_codes"],
        policy=decision_payload["policy"],
        risk=decision_payload["risk"],
        liability=decision_payload["liability"],
        event_id=event["event_id"],
    )


def _request_with_attached_evidence(events: list[dict[str, Any]]) -> FacilityRequest:
    facility_request = _request_from_payload(_latest_request_payload(events))
    for event in events:
        if event["event_type"] == FacilityEventType.EVIDENCE_ATTACHED.value:
            facility_request.evidence.extend(
                [
                    FacilityEvidenceRef(
                        evidence_id=e["evidence_id"],
                        evidence_type=e["evidence_type"],
                        content_hash=e["content_hash"],
                        uri=e.get("uri"),
                        metadata=e.get("metadata", {}),
                    )
                    for e in event["payload"].get("evidence", [])
                ]
            )
    return facility_request


def _snapshot_hash(snapshot: Any) -> str | None:
    if snapshot is None:
        return None
    return stable_payload_hash({"snapshot": to_jsonable(snapshot)})


def _repayment_mirror_from_snapshot(
    *,
    facility_id: str,
    sponsor_id: str,
    snapshot: dict[str, Any] | None,
) -> FacilityRepaymentMirror | None:
    if not snapshot:
        return None
    mirror = snapshot.get("repayment_mirror") or snapshot.get("repayment")
    if not isinstance(mirror, dict):
        return None
    raw_status = str(mirror.get("status") or "unknown").strip().lower()
    try:
        status_value = FacilityRepaymentStatus(raw_status)
    except ValueError:
        status_value = FacilityRepaymentStatus.UNKNOWN
    return FacilityRepaymentMirror(
        facility_id=str(mirror.get("facility_id") or facility_id),
        sponsor_id=str(mirror.get("sponsor_id") or sponsor_id),
        status=status_value,
        source=str(mirror.get("source") or "request_snapshot"),
        statement_ref=mirror.get("statement_ref"),
        days_past_due=mirror.get("days_past_due"),
        metadata=dict(mirror.get("metadata") or {}),
    )


def _provider_webhook_secret(provider: str) -> str | None:
    provider_key = provider.upper().replace("-", "_")
    return os.getenv(f"SARDIS_FACILITY_PROVIDER_WEBHOOK_SECRET_{provider_key}") or os.getenv(
        "SARDIS_FACILITY_PROVIDER_WEBHOOK_SECRET"
    )


def _verify_provider_webhook_signature(*, provider: str, raw_body: bytes, signature: str | None) -> None:
    secret = _provider_webhook_secret(provider)
    if not secret:
        raise HTTPException(status_code=503, detail="Facility provider webhook secret is not configured")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing Facility provider webhook signature")
    expected = hmac.new(secret.encode(), raw_body, sha256).hexdigest()
    received = signature.removeprefix("sha256=").strip()
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=401, detail="Invalid Facility provider webhook signature")


_SUPPORTED_PROVIDER_WEBHOOK_TYPES = {
    "authorization.approved",
    "authorization.declined",
    "authorization.captured",
    "authorization.voided",
    "authorization.reversed",
    "credential.revoked",
    "settlement.posted",
    "settlement.failed",
    "dispute.opened",
    "dispute.closed",
    "repayment.current",
    "repayment.late",
    "repayment.delinquent",
}


def _settlement_update_from_provider_webhook(
    *,
    provider: str,
    webhook: FacilityProviderWebhookEvent,
) -> dict[str, Any] | None:
    status_by_type = {
        "authorization.captured": "captured",
        "authorization.voided": "voided",
        "authorization.reversed": "reversed",
        "settlement.posted": "posted",
        "settlement.failed": "failed",
    }
    status_value = status_by_type.get(webhook.event_type)
    if status_value is None:
        return None
    amount_minor = webhook.payload.get("amount_minor")
    currency = webhook.payload.get("currency")
    return {
        "schema_version": "facility_settlement_update_v1",
        "provider": provider,
        "provider_event_id": webhook.provider_event_id,
        "provider_event_type": webhook.event_type,
        "request_id": webhook.request_id,
        "authorization_id": webhook.authorization_id,
        "status": status_value,
        "amount_minor": amount_minor,
        "currency": currency,
        "raw_payload_hash": webhook.raw_payload_hash,
        "source": "provider_webhook",
        "metadata": {
            key: value
            for key, value in webhook.payload.items()
            if key not in {"amount_minor", "currency"}
        },
    }


def _validate_request_snapshot_ownership(
    *,
    body: FacilityRequestCreate,
    principal: Principal,
) -> None:
    mandate_snapshot = body.mandate_snapshot
    if mandate_snapshot is not None:
        if mandate_snapshot.org_id and mandate_snapshot.org_id != principal.organization_id:
            raise HTTPException(status_code=403, detail="Mandate snapshot organization does not match caller")
        if mandate_snapshot.agent_id and mandate_snapshot.agent_id != body.agent_id:
            raise HTTPException(status_code=403, detail="Mandate snapshot agent does not match request")
        if mandate_snapshot.id and mandate_snapshot.id != body.mandate_id:
            raise HTTPException(status_code=403, detail="Mandate snapshot id does not match request")
    facility_snapshot = body.facility_snapshot or {}
    snapshot_org_id = facility_snapshot.get("organization_id") or facility_snapshot.get("org_id")
    if snapshot_org_id and snapshot_org_id != principal.organization_id:
        raise HTTPException(status_code=403, detail="Facility snapshot organization does not match caller")
    snapshot_facility_id = facility_snapshot.get("facility_id") or facility_snapshot.get("id")
    if snapshot_facility_id and snapshot_facility_id != body.facility_id:
        raise HTTPException(status_code=403, detail="Facility snapshot id does not match request")
    snapshot_sponsor_id = facility_snapshot.get("sponsor_id")
    if snapshot_sponsor_id and snapshot_sponsor_id != body.sponsor_id:
        raise HTTPException(status_code=403, detail="Facility snapshot sponsor does not match request")


def _require_facility_scope(principal: Principal, *required_scopes: str) -> None:
    if principal.is_admin or "*" in principal.scopes:
        return
    if any(scope in principal.scopes for scope in required_scopes):
        return
    raise HTTPException(status_code=403, detail="Facility Gate scope required")


async def _enforce_probe_limit(
    deps: FacilityDependencies,
    *,
    principal: Principal,
    agent_id: str,
    merchant: str,
) -> None:
    limiter = FacilityGateLimiter(deps.repository)
    decision = await limiter.check_request_allowed(
        organization_id=principal.organization_id,
        agent_id=agent_id,
        merchant=merchant,
    )
    if not decision.allowed:
        record_facility_exception(reason=decision.reason or "facility_probe_limit_exceeded")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many recent Facility Gate requests for this agent and merchant",
        )


async def _ensure_step_up_approval_request(
    deps: FacilityDependencies,
    *,
    principal: Principal,
    request_id: str,
    facility_request: FacilityRequest,
    decision_payload: dict[str, Any],
    existing_events: list[dict[str, Any]],
) -> str | None:
    if deps.approval_service is None or _latest_approval_request(existing_events) is not None:
        return None
    try:
        approval = await deps.approval_service.create_approval(
            action="facility_gate.step_up",
            requested_by=facility_request.agent_id,
            agent_id=facility_request.agent_id,
            vendor=facility_request.merchant,
            amount=Decimal(facility_request.amount_minor) / Decimal("100"),
            purpose=facility_request.purpose or "Facility Gate spend request",
            reason=", ".join(decision_payload.get("reason_codes") or ["facility_step_up_required"]),
            urgency="high" if decision_payload.get("risk", {}).get("tier") == "high" else "medium",
            organization_id=principal.organization_id,
            metadata={
                "facility_request_id": request_id,
                "facility_id": facility_request.facility_id,
                "mandate_id": facility_request.mandate_id,
                "decision_id": decision_payload["decision_id"],
                "decision_packet_hash": decision_payload.get("decision_packet_hash"),
            },
        )
    except Exception as exc:
        await _append_exception(
            deps,
            principal=principal,
            aggregate_id=request_id,
            reason="facility_approval_service_unavailable",
            payload={"error": str(exc)},
        )
        return None
    append = await deps.repository.append_event(
        organization_id=principal.organization_id,
        aggregate_id=request_id,
        event_type=FacilityEventType.APPROVAL_REQUESTED,
        payload={
            "approval_id": approval.id,
            "status": getattr(approval, "status", "pending"),
            "source": "approval_service",
            "decision_id": decision_payload["decision_id"],
        },
        idempotency_key=f"approval-request:{request_id}:{decision_payload['decision_id']}",
        actor_id=principal.user_id,
    )
    return append.event["payload"]["approval_id"]


@router.get("", dependencies=[Depends(require_facility_gate_enabled)])
async def list_facility_requests(
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "read", "facility:read")
    states = await deps.repository.list_request_states(organization_id=principal.organization_id, limit=100)
    return {"requests": states, "total": len(states)}


@router.get("/manual-review", dependencies=[Depends(require_facility_gate_enabled)])
async def list_facility_manual_review_queue(
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "read", "facility:read", "facility:review")
    states = await deps.repository.list_request_states(organization_id=principal.organization_id, limit=200)
    pending = [state for state in states if state.get("latest_verdict") == FacilityDecision.STEP_UP_REQUIRED.value]
    set_facility_manual_review_queue_depth(len(pending))
    return {"requests": pending, "total": len(pending)}


@router.get("/exceptions", dependencies=[Depends(require_facility_gate_enabled)])
async def list_facility_exceptions(
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "read", "facility:read", "facility:review")
    events = await deps.repository.list_events_by_type(
        organization_id=principal.organization_id,
        event_type=FacilityEventType.EXCEPTION_CREATED,
        limit=100,
    )
    return {"exceptions": events, "total": len(events)}


@router.post("/exceptions/resolve", dependencies=[Depends(require_facility_gate_enabled)])
async def resolve_facility_exception(
    body: FacilityExceptionResolveRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "admin", "facility:admin", "facility:review")
    exceptions = await deps.repository.list_events_by_type(
        organization_id=principal.organization_id,
        event_type=FacilityEventType.EXCEPTION_CREATED,
        limit=500,
    )
    exception = next((event for event in exceptions if event["event_id"] == body.event_id), None)
    if exception is None:
        raise HTTPException(status_code=404, detail="Facility exception not found")
    append = await deps.repository.append_event(
        organization_id=principal.organization_id,
        aggregate_id=exception["aggregate_id"],
        event_type=FacilityEventType.EXCEPTION_RESOLVED,
        payload={
            "exception_event_id": body.event_id,
            "resolved_by": body.resolved_by,
            "resolution": body.resolution,
            "exception_reason": exception["payload"].get("reason"),
        },
        idempotency_key=body.idempotency_key or request.headers.get("Idempotency-Key"),
        actor_id=principal.user_id,
    )
    return {"event_id": append.event["event_id"], "duplicate": append.duplicate}


@router.get("/limits", dependencies=[Depends(require_facility_gate_enabled)])
async def get_facility_limits_summary(
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "read", "facility:read")
    return await FacilityGateLimiter(deps.repository).summary(organization_id=principal.organization_id)


@router.put("/authority/facilities/{facility_id}", dependencies=[Depends(require_facility_gate_enabled)])
async def upsert_facility_authority_record(
    facility_id: str,
    body: FacilityRecordUpsertRequest,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "admin", "facility:admin", "facility:write")
    if body.facility_id != facility_id:
        raise HTTPException(status_code=400, detail="Facility id path/body mismatch")
    limit_payload = body.limit
    facility = Facility(
        facility_id=facility_id,
        organization_id=principal.organization_id,
        sponsor_id=body.sponsor_id,
        provider=body.provider,
        facility_type=FacilityType(body.facility_type),
        status=FacilityStatus(body.status),
        limit=FacilityLimit(
            per_transaction_minor=int(limit_payload.get("per_transaction_minor", 500_000)),
            daily_minor=limit_payload.get("daily_minor"),
            monthly_minor=limit_payload.get("monthly_minor"),
            currency=str(limit_payload.get("currency") or "USD"),
        ),
        allowed_categories=body.allowed_categories,
        allowed_merchants=body.allowed_merchants,
        blocked_merchants=body.blocked_merchants,
        approval_threshold_minor=body.approval_threshold_minor,
        version=body.version,
        metadata=body.metadata,
    )
    record = await deps.repository.upsert_facility_record(facility)
    return {"schema_version": "facility_authority_record_v1", "record": record}


@router.put("/authority/facilities/{facility_id}/policy", dependencies=[Depends(require_facility_gate_enabled)])
async def upsert_facility_policy_record(
    facility_id: str,
    body: FacilityPolicyRecordUpsertRequest,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "admin", "facility:admin", "facility:write")
    if body.facility_id != facility_id:
        raise HTTPException(status_code=400, detail="Facility id path/body mismatch")
    record = await deps.repository.upsert_facility_policy_record(
        organization_id=principal.organization_id,
        facility_id=facility_id,
        policy_version=body.policy_version,
        snapshot=body.snapshot,
        created_by=principal.user_id,
    )
    return {"schema_version": "facility_policy_record_v1", "record": record}


@router.put("/authority/mandates/{mandate_id}", dependencies=[Depends(require_facility_gate_enabled)])
async def upsert_facility_mandate_record(
    mandate_id: str,
    body: FacilityMandateRecordUpsertRequest,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "admin", "facility:admin", "facility:write")
    mandate_snapshot = body.mandate.model_dump(mode="json")
    mandate = mandate_from_snapshot(
        mandate_snapshot,
        fallback_id=mandate_id,
        org_id=principal.organization_id,
        agent_id=body.mandate.agent_id or "",
    )
    if mandate is None:
        raise HTTPException(status_code=400, detail="Invalid mandate snapshot")
    if mandate.id != mandate_id:
        raise HTTPException(status_code=400, detail="Mandate id path/body mismatch")
    mandate.org_id = principal.organization_id
    record = await deps.repository.upsert_facility_mandate_record(mandate, created_by=principal.user_id)
    return {"schema_version": "facility_mandate_record_v1", "record": record}


@router.get("/audit/exports", dependencies=[Depends(require_facility_gate_enabled)])
async def export_facility_audit_events(
    occurred_from: datetime | None = Query(default=None),
    occurred_to: datetime | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "read", "facility:read", "facility:audit")
    events = await deps.repository.list_events_for_organization(
        organization_id=principal.organization_id,
        event_type=event_type,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
    )
    decision_packets = [
        event["payload"]["decision_packet"]
        for event in events
        if event["event_type"] in {
            FacilityEventType.AUTH_APPROVED.value,
            FacilityEventType.AUTH_DENIED.value,
            FacilityEventType.AUTH_STEP_UP_REQUIRED.value,
        }
        and event["payload"].get("decision_packet")
    ]
    provider_webhooks = [
        event["payload"]["webhook"]
        for event in events
        if event["event_type"] == FacilityEventType.PROVIDER_WEBHOOK_RECEIVED.value
    ]
    settlements = [
        event["payload"]
        for event in events
        if event["event_type"] == FacilityEventType.SETTLEMENT_UPDATED.value
    ]
    exceptions = [
        event["payload"]
        for event in events
        if event["event_type"] == FacilityEventType.EXCEPTION_CREATED.value
    ]
    exception_resolutions = [
        event["payload"]
        for event in events
        if event["event_type"] == FacilityEventType.EXCEPTION_RESOLVED.value
    ]
    request_ids = sorted({
        event["aggregate_id"]
        for event in events
        if event["event_type"] != FacilityEventType.PROVIDER_WEBHOOK_RECEIVED.value
        or event["payload"].get("webhook", {}).get("request_id")
    })
    return {
        "schema_version": "facility_audit_event_export_v1",
        "organization_id": principal.organization_id,
        "filters": {
            "occurred_from": occurred_from.isoformat() if occurred_from else None,
            "occurred_to": occurred_to.isoformat() if occurred_to else None,
            "event_type": event_type,
            "limit": limit,
        },
        "event_count": len(events),
        "request_count": len(request_ids),
        "request_ids": request_ids,
        "decision_packets": decision_packets,
        "provider_webhooks": provider_webhooks,
        "settlements": settlements,
        "exceptions": exceptions,
        "exception_resolutions": exception_resolutions,
        "events": events,
    }


@router.post("", response_model=FacilityRequestResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_facility_gate_enabled)])
async def create_facility_request(
    body: FacilityRequestCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "write", "facility:write")
    _validate_request_snapshot_ownership(body=body, principal=principal)
    await _enforce_probe_limit(deps, principal=principal, agent_id=body.agent_id, merchant=body.merchant)
    request_id = f"fac_req_{uuid4().hex[:16]}"
    evidence = _evidence_refs(body.evidence)
    facility_request = FacilityRequest(
        request_id=request_id,
        organization_id=principal.organization_id,
        agent_id=body.agent_id,
        sponsor_id=body.sponsor_id,
        facility_id=body.facility_id,
        mandate_id=body.mandate_id,
        merchant=body.merchant,
        amount_minor=body.amount_minor,
        currency=body.currency,
        category=body.category,
        rail=body.rail,
        purpose=body.purpose,
        task_graph_hash=body.task_graph_hash,
        evidence=evidence,
    )
    payload = {
        "request": to_jsonable(facility_request),
        "mandate_snapshot": body.mandate_snapshot.model_dump(mode="json") if body.mandate_snapshot else None,
        "facility_snapshot": body.facility_snapshot,
    }
    facility_request.request_payload_hash = stable_payload_hash(payload)
    payload["request"] = to_jsonable(facility_request)
    append = await deps.repository.append_event(
        organization_id=principal.organization_id,
        aggregate_id=request_id,
        event_type=FacilityEventType.REQUEST_CREATED,
        payload=payload,
        idempotency_key=body.idempotency_key or request.headers.get("Idempotency-Key"),
        actor_id=principal.user_id,
    )
    stored_request_id = append.event["aggregate_id"]
    return FacilityRequestResponse(
        request_id=stored_request_id,
        duplicate=append.duplicate,
        event_id=append.event["event_id"],
    )


@router.post("/{request_id}/evidence", dependencies=[Depends(require_facility_gate_enabled)])
async def attach_facility_evidence(
    request_id: str,
    body: FacilityEvidenceAttachRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "write", "facility:write")
    await _load_request_events_or_404(deps, principal, request_id)
    append = await deps.repository.append_event(
        organization_id=principal.organization_id,
        aggregate_id=request_id,
        event_type=FacilityEventType.EVIDENCE_ATTACHED,
        payload={"evidence": to_jsonable(_evidence_refs(body.evidence))},
        idempotency_key=body.idempotency_key or request.headers.get("Idempotency-Key"),
        actor_id=principal.user_id,
    )
    return {"event_id": append.event["event_id"], "duplicate": append.duplicate}


@router.post("/{request_id}/approval", dependencies=[Depends(require_facility_gate_enabled)])
async def record_facility_approval(
    request_id: str,
    body: FacilityApprovalRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "write", "facility:review", "facility:approve")
    await _load_request_events_or_404(deps, principal, request_id)
    append = await deps.repository.append_event(
        organization_id=principal.organization_id,
        aggregate_id=request_id,
        event_type=FacilityEventType.APPROVAL_RECORDED,
        payload={
            "approved": body.approved,
            "reviewed_by": body.reviewed_by,
            "reason": body.reason,
        },
        idempotency_key=body.idempotency_key or request.headers.get("Idempotency-Key"),
        actor_id=principal.user_id,
    )
    return {"event_id": append.event["event_id"], "duplicate": append.duplicate}


@router.post("/{request_id}/authorize", response_model=FacilityDecisionResponse, dependencies=[Depends(require_facility_gate_enabled)])
async def authorize_facility_request(
    request_id: str,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "write", "facility:write", "facility:authorize")
    events = await _load_request_events_or_404(deps, principal, request_id)
    latest_authorization = _latest_authorization_event(events)
    if latest_authorization is not None:
        authorization_idx, authorization_event = latest_authorization
        has_later_approval = any(
            event["event_type"] == FacilityEventType.APPROVAL_RECORDED.value
            for event in events[authorization_idx + 1:]
        )
        if (
            authorization_event["event_type"] != FacilityEventType.AUTH_STEP_UP_REQUIRED.value
            or not has_later_approval
        ):
            return _decision_response_from_event(request_id, authorization_event)
    creation_payload = _latest_request_payload(events)
    facility_request = _request_with_attached_evidence(events)
    revoked_reason = await _has_revocation(deps, principal, facility_request)
    resolved_mandate = await _mandate_resolver(deps).resolve_mandate(
        organization_id=principal.organization_id,
        mandate_id=facility_request.mandate_id,
        agent_id=facility_request.agent_id,
        fallback_snapshot=creation_payload.get("mandate_snapshot"),
    )
    if _require_persisted_authority() and (
        resolved_mandate is None or resolved_mandate.source == "request_snapshot"
    ):
        await _append_exception(
            deps,
            principal=principal,
            aggregate_id=request_id,
            reason="facility_persisted_mandate_required",
            payload={"mandate_id": facility_request.mandate_id},
        )
        raise HTTPException(status_code=409, detail="Persisted mandate lookup is required")
    mandate_check = None
    if resolved_mandate is not None:
        mandate_check = resolved_mandate.mandate.check_facility_draw(
            amount=Decimal(facility_request.amount_minor) / Decimal("100"),
            facility_id=facility_request.facility_id,
            merchant=facility_request.merchant,
            category=facility_request.category,
            rail=facility_request.rail.value,
        )
    resolved_facility = await _facility_resolver(deps).resolve_facility(
        organization_id=principal.organization_id,
        sponsor_id=facility_request.sponsor_id,
        facility_id=facility_request.facility_id,
        fallback_snapshot=creation_payload.get("facility_snapshot"),
    )
    if resolved_facility is None:
        raise HTTPException(status_code=409, detail="Facility record not found")
    if _require_persisted_authority() and resolved_facility.source in {
        "request_snapshot",
        "default_simulated",
    }:
        await _append_exception(
            deps,
            principal=principal,
            aggregate_id=request_id,
            reason="facility_persisted_facility_required",
            payload={"facility_id": facility_request.facility_id},
        )
        raise HTTPException(status_code=409, detail="Persisted facility lookup is required")
    facility = resolved_facility.facility
    repayment_mirror = _repayment_mirror_from_snapshot(
        facility_id=facility.facility_id,
        sponsor_id=facility.sponsor_id,
        snapshot=creation_payload.get("facility_snapshot"),
    )
    resolved_policy = await _policy_resolver(deps).resolve_policy(
        organization_id=principal.organization_id,
        facility=facility,
    )
    liability = LiabilityAssignment(
        repayment_obligor=facility_request.sponsor_id,
        settlement_responsible_party=facility.provider,
        loss_owner=facility.provider,
        terms_ref=facility.metadata.get("terms_ref"),
    )
    decision = build_facility_decision(
        request=facility_request,
        facility=facility,
        mandate_check=mandate_check,
        liability=liability,
        repayment_mirror=repayment_mirror,
    )
    approval = _latest_approval(events)
    if revoked_reason:
        decision.verdict = FacilityDecision.DENIED
        decision.reason_codes = [revoked_reason]
    elif approval and approval.get("approved") is False:
        decision.verdict = FacilityDecision.DENIED
        decision.reason_codes = ["human_approval_denied"]
    elif approval and approval.get("approved") is True and decision.verdict == FacilityDecision.STEP_UP_REQUIRED:
        decision.verdict = FacilityDecision.APPROVED
        decision.reason_codes = ["human_step_up_approved", *decision.reason_codes]
    elif decision.verdict == FacilityDecision.STEP_UP_REQUIRED:
        fatigue = await FacilityGateLimiter(deps.repository).check_approval_fatigue(
            organization_id=principal.organization_id,
        )
        if not fatigue.allowed:
            fatigue_reason = fatigue.reason or "facility_approval_fatigue_limit_exceeded"
            await _append_exception(
                deps,
                principal=principal,
                aggregate_id=request_id,
                reason=fatigue_reason,
                payload={"count": fatigue.count, "threshold": fatigue.threshold},
            )
            decision.verdict = FacilityDecision.DENIED
            decision.reason_codes = [
                fatigue_reason,
                *decision.reason_codes,
            ]

    decision_packet = build_decision_packet(
        request=facility_request,
        decision=decision,
        evidence=facility_request.evidence,
        request_payload_hash=facility_request.request_payload_hash,
        mandate_snapshot_hash=_snapshot_hash(creation_payload.get("mandate_snapshot")),
        facility_snapshot_hash=_snapshot_hash(creation_payload.get("facility_snapshot")),
        policy_snapshot_hash=resolved_policy.snapshot_hash,
        repayment_mirror=repayment_mirror,
        adapter_contract_version=getattr(deps.adapter, "capabilities", None).contract_version
        if getattr(deps.adapter, "capabilities", None)
        else "facility_adapter_v1",
    )
    decision_packet["mandate"]["source"] = resolved_mandate.source if resolved_mandate else None
    decision_packet["mandate"]["version_id"] = resolved_mandate.version_id if resolved_mandate else None
    decision_packet["mandate"]["mandate_snapshot_hash"] = (
        resolved_mandate.snapshot_hash if resolved_mandate else None
    )
    decision_packet["facility"]["source"] = resolved_facility.source
    decision_packet["facility"]["version_id"] = resolved_facility.version_id
    decision_packet["facility"]["facility_snapshot_hash"] = resolved_facility.snapshot_hash
    decision_packet["policy"]["source"] = resolved_policy.source
    decision_packet["policy"]["policy_version"] = resolved_policy.policy_version
    decision_packet["policy"]["snapshot"] = resolved_policy.snapshot
    decision_packet["decision_packet_hash"] = stable_payload_hash(
        {key: value for key, value in decision_packet.items() if key != "decision_packet_hash"}
    )

    event_type = {
        FacilityDecision.APPROVED: FacilityEventType.AUTH_APPROVED,
        FacilityDecision.DENIED: FacilityEventType.AUTH_DENIED,
        FacilityDecision.STEP_UP_REQUIRED: FacilityEventType.AUTH_STEP_UP_REQUIRED,
    }[decision.verdict]
    append = await deps.repository.append_event(
        organization_id=principal.organization_id,
        aggregate_id=request_id,
        event_type=event_type,
        payload={"decision": to_jsonable(decision), "decision_packet": decision_packet},
        idempotency_key=f"authorize:{request_id}:{events[-1]['event_hash']}",
        actor_id=principal.user_id,
    )
    decision_payload = append.event["payload"]["decision"]
    if decision_payload["verdict"] == FacilityDecision.STEP_UP_REQUIRED.value and not append.duplicate:
        approval_id = await _ensure_step_up_approval_request(
            deps,
            principal=principal,
            request_id=request_id,
            facility_request=facility_request,
            decision_payload={**decision_payload, "decision_packet_hash": decision_packet["decision_packet_hash"]},
            existing_events=events,
        )
        if approval_id:
            append.event["payload"]["approval_id"] = approval_id
    if not append.duplicate:
        record_facility_decision(
            verdict=decision_payload["verdict"],
            reason=(decision_payload["reason_codes"] or ["none"])[0],
            risk_tier=decision_payload["risk"]["tier"],
        )
    return FacilityDecisionResponse(
        decision_id=decision_payload["decision_id"],
        request_id=request_id,
        verdict=decision_payload["verdict"],
        reason_codes=decision_payload["reason_codes"],
        policy=decision_payload["policy"],
        risk=decision_payload["risk"],
        liability=decision_payload["liability"],
        event_id=append.event["event_id"],
    )


@router.post("/{request_id}/execute", response_model=FacilityExecutionResponse, dependencies=[Depends(require_facility_gate_enabled)])
async def execute_facility_authorization(
    request_id: str,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "write", "facility:write", "facility:execute")
    events = await _load_request_events_or_404(deps, principal, request_id)
    facility_request = _request_with_attached_evidence(events)
    approved_decision = None
    for event in reversed(events):
        if event["event_type"] == FacilityEventType.AUTH_APPROVED.value:
            approved_decision = event["payload"]["decision"]
            break
    if approved_decision is None:
        raise HTTPException(status_code=409, detail="Facility request has no approved authorization")
    from sardis_v2_core.facility_gate import (
        FacilityAuthorizationDecision,
        FacilityPolicyEvaluation,
        FacilityRiskAssessment,
        FacilityRiskTier,
    )

    decision = FacilityAuthorizationDecision(
        decision_id=approved_decision["decision_id"],
        request_id=request_id,
        verdict=FacilityDecision.APPROVED,
        reason_codes=approved_decision["reason_codes"],
        policy=FacilityPolicyEvaluation(
            verdict=FacilityDecision(approved_decision["policy"]["verdict"]),
            reason_codes=approved_decision["policy"]["reason_codes"],
            checks=approved_decision["policy"]["checks"],
            policy_version=approved_decision["policy"]["policy_version"],
        ),
        risk=FacilityRiskAssessment(
            score=approved_decision["risk"]["score"],
            tier=FacilityRiskTier(approved_decision["risk"]["tier"]),
            reason_codes=approved_decision["risk"]["reason_codes"],
            features=approved_decision["risk"]["features"],
            model_version=approved_decision["risk"]["model_version"],
        ),
        liability=LiabilityAssignment(**approved_decision["liability"]),
        mandate_id=approved_decision["mandate_id"],
        mandate_version=approved_decision["mandate_version"],
        facility_id=approved_decision["facility_id"],
        facility_version=approved_decision["facility_version"],
    )
    capabilities = getattr(deps.adapter, "capabilities", None)
    if capabilities is not None:
        required = {
            "execute": capabilities.supports_execute,
            "merchant_lock": capabilities.supports_merchant_lock,
            "amount_limit": capabilities.supports_amount_limit,
        }
        unsupported = [name for name, supported in required.items() if not supported]
        if unsupported:
            await _append_exception(
                deps,
                principal=principal,
                aggregate_id=request_id,
                reason="facility_adapter_capability_unsupported",
                payload={"unsupported_capabilities": unsupported},
            )
            raise HTTPException(status_code=409, detail="Facility adapter lacks required capabilities")
    idempotency_key = f"execute:{request_id}"
    existing_execution = await deps.repository.find_event_by_idempotency_key(
        organization_id=principal.organization_id,
        idempotency_key=idempotency_key,
    )
    if existing_execution:
        return FacilityExecutionResponse(
            credential=existing_execution["payload"]["credential"],
            event_id=existing_execution["event_id"],
        )
    revoked_reason = await _has_revocation(deps, principal, facility_request)
    if revoked_reason:
        raise HTTPException(status_code=409, detail=f"Facility authorization revoked: {revoked_reason}")
    try:
        credential = await deps.adapter.execute_authorization(request=facility_request, decision=decision)
        record_facility_adapter_event(provider="simulated", operation="execute", status="success")
    except Exception as exc:
        record_facility_adapter_event(provider="simulated", operation="execute", status="failed")
        await _append_exception(
            deps,
            principal=principal,
            aggregate_id=request_id,
            reason="facility_adapter_execute_failed",
            payload={"error": str(exc)},
        )
        raise HTTPException(status_code=502, detail="Facility adapter execution failed") from exc
    append = await deps.repository.append_event(
        organization_id=principal.organization_id,
        aggregate_id=request_id,
        event_type=FacilityEventType.EXECUTION_SIMULATED,
        payload={"credential": to_jsonable(credential)},
        idempotency_key=idempotency_key,
        actor_id=principal.user_id,
    )
    return FacilityExecutionResponse(credential=append.event["payload"]["credential"], event_id=append.event["event_id"])


@router.get("/{request_id}/audit", dependencies=[Depends(require_facility_gate_enabled)])
async def get_facility_request_audit(
    request_id: str,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "read", "facility:read", "facility:audit")
    events = await _load_request_events_or_404(deps, principal, request_id)
    request_payload = _latest_request_payload(events)
    latest_decision = None
    evidence = list(request_payload["request"].get("evidence", []))
    execution = None
    for event in events:
        if event["event_type"] == FacilityEventType.EVIDENCE_ATTACHED.value:
            evidence.extend(event["payload"].get("evidence", []))
        if event["event_type"] in {
            FacilityEventType.AUTH_APPROVED.value,
            FacilityEventType.AUTH_DENIED.value,
            FacilityEventType.AUTH_STEP_UP_REQUIRED.value,
        }:
            latest_decision = event["payload"]["decision"]
        if event["event_type"] == FacilityEventType.EXECUTION_SIMULATED.value:
            execution = event["payload"]["credential"]
    return {
        "request_id": request_id,
        "request": request_payload["request"],
        "mandate_snapshot": request_payload.get("mandate_snapshot"),
        "facility_snapshot": request_payload.get("facility_snapshot"),
        "latest_decision": latest_decision,
        "liability": latest_decision.get("liability") if latest_decision else None,
        "evidence": evidence,
        "execution": execution,
        "events": events,
    }


@router.get("/{request_id}/audit/export", dependencies=[Depends(require_facility_gate_enabled)])
async def export_facility_request_audit(
    request_id: str,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "read", "facility:read", "facility:audit")
    events = await _load_request_events_or_404(deps, principal, request_id)
    request_payload = _latest_request_payload(events)
    latest_decision = None
    latest_decision_packet = None
    evidence = list(request_payload["request"].get("evidence", []))
    execution = None
    exceptions: list[dict[str, Any]] = []
    exception_resolutions: list[dict[str, Any]] = []
    provider_webhooks: list[dict[str, Any]] = []
    settlements: list[dict[str, Any]] = []
    for event in events:
        if event["event_type"] == FacilityEventType.EVIDENCE_ATTACHED.value:
            evidence.extend(event["payload"].get("evidence", []))
        if event["event_type"] in {
            FacilityEventType.AUTH_APPROVED.value,
            FacilityEventType.AUTH_DENIED.value,
            FacilityEventType.AUTH_STEP_UP_REQUIRED.value,
        }:
            latest_decision = event["payload"]["decision"]
            latest_decision_packet = event["payload"].get("decision_packet")
        if event["event_type"] == FacilityEventType.EXECUTION_SIMULATED.value:
            execution = event["payload"]["credential"]
        if event["event_type"] == FacilityEventType.EXCEPTION_CREATED.value:
            exceptions.append(event["payload"])
        if event["event_type"] == FacilityEventType.EXCEPTION_RESOLVED.value:
            exception_resolutions.append(event["payload"])
        if event["event_type"] == FacilityEventType.PROVIDER_WEBHOOK_RECEIVED.value:
            provider_webhooks.append(event["payload"]["webhook"])
        if event["event_type"] == FacilityEventType.SETTLEMENT_UPDATED.value:
            settlements.append(event["payload"])
    hash_chain = await deps.repository.verify_event_hash_chain(
        organization_id=principal.organization_id,
        aggregate_id=request_id,
    )
    return {
        "schema_version": "facility_audit_export_v1",
        "organization_id": principal.organization_id,
        "request_id": request_id,
        "request": request_payload["request"],
        "decision_packet": latest_decision_packet,
        "latest_decision": latest_decision,
        "liability": latest_decision.get("liability") if latest_decision else None,
        "evidence": evidence,
        "execution": execution,
        "provider_webhooks": provider_webhooks,
        "settlements": settlements,
        "exceptions": exceptions,
        "exception_resolutions": exception_resolutions,
        "event_hash_chain": hash_chain,
        "events": events,
    }


@router.post("/revocations", dependencies=[Depends(require_facility_gate_enabled)])
async def revoke_facility_authority(
    body: FacilityRevocationRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    deps: FacilityDependencies = Depends(get_deps),
):
    _require_facility_scope(principal, "admin", "facility:admin", "facility:revoke")
    aggregate_id = "global" if body.scope == FacilityRevocationScope.GLOBAL else body.target_id
    append = await deps.repository.append_event(
        organization_id=principal.organization_id,
        aggregate_id=aggregate_id,
        event_type=FacilityEventType.REVOCATION_CREATED,
        payload={
            "scope": body.scope.value,
            "target_id": body.target_id,
            "reason": body.reason,
        },
        idempotency_key=body.idempotency_key or request.headers.get("Idempotency-Key"),
        actor_id=principal.user_id,
    )
    record_facility_revocation(scope=body.scope.value)
    try:
        revoked = await deps.adapter.revoke_authorization(body.target_id, body.reason)
        record_facility_adapter_event(
            provider="simulated",
            operation="revoke",
            status="success" if revoked else "not_found",
        )
    except Exception as exc:
        record_facility_adapter_event(provider="simulated", operation="revoke", status="failed")
        await _append_exception(
            deps,
            principal=principal,
            aggregate_id=aggregate_id,
            reason="facility_adapter_revoke_failed",
            payload={"target_id": body.target_id, "error": str(exc)},
        )
        raise HTTPException(status_code=502, detail="Facility adapter revocation failed") from exc
    return {"event_id": append.event["event_id"], "duplicate": append.duplicate}


@provider_webhooks_router.post(
    "/{provider}/facility-gate",
    dependencies=[Depends(require_provider_webhooks_enabled)],
)
async def ingest_facility_provider_webhook(
    provider: str,
    body: FacilityProviderWebhookRequest,
    request: Request,
    deps: FacilityDependencies = Depends(get_deps),
):
    raw_body = await request.body()
    _verify_provider_webhook_signature(
        provider=provider,
        raw_body=raw_body,
        signature=request.headers.get("X-Sardis-Facility-Signature"),
    )
    aggregate_id = body.request_id or body.authorization_id or f"provider:{provider}:{body.provider_event_id}"
    if body.event_type not in _SUPPORTED_PROVIDER_WEBHOOK_TYPES:
        append = await deps.repository.append_event(
            organization_id=body.organization_id,
            aggregate_id=aggregate_id,
            event_type=FacilityEventType.EXCEPTION_CREATED,
            payload={
                "reason": "facility_provider_webhook_unsupported_type",
                "provider": provider,
                "provider_event_id": body.provider_event_id,
                "provider_event_type": body.event_type,
                "raw_payload_hash": sha256(raw_body).hexdigest(),
            },
            idempotency_key=f"provider-webhook-unsupported:{provider}:{body.provider_event_id}",
            actor_id=f"provider:{provider}",
        )
        record_facility_exception(reason="facility_provider_webhook_unsupported_type")
        return {
            "event_id": append.event["event_id"],
            "duplicate": append.duplicate,
            "aggregate_id": aggregate_id,
            "accepted": False,
            "reason": "facility_provider_webhook_unsupported_type",
        }
    webhook = FacilityProviderWebhookEvent(
        provider=provider,
        provider_event_id=body.provider_event_id,
        event_type=body.event_type,
        organization_id=body.organization_id,
        request_id=body.request_id,
        authorization_id=body.authorization_id,
        raw_payload_hash=sha256(raw_body).hexdigest(),
        payload=body.payload,
    )
    append = await deps.repository.append_event(
        organization_id=body.organization_id,
        aggregate_id=aggregate_id,
        event_type=FacilityEventType.PROVIDER_WEBHOOK_RECEIVED,
        payload={"webhook": to_jsonable(webhook)},
        idempotency_key=f"provider-webhook:{provider}:{body.provider_event_id}",
        actor_id=f"provider:{provider}",
    )
    settlement_append = None
    settlement_update = _settlement_update_from_provider_webhook(provider=provider, webhook=webhook)
    if settlement_update is not None:
        settlement_append = await deps.repository.append_event(
            organization_id=body.organization_id,
            aggregate_id=aggregate_id,
            event_type=FacilityEventType.SETTLEMENT_UPDATED,
            payload=settlement_update,
            idempotency_key=f"provider-settlement:{provider}:{body.provider_event_id}",
            actor_id=f"provider:{provider}",
        )
    return {
        "event_id": append.event["event_id"],
        "duplicate": append.duplicate,
        "aggregate_id": aggregate_id,
        "raw_payload_hash": webhook.raw_payload_hash,
        "settlement_event_id": settlement_append.event["event_id"] if settlement_append else None,
        "settlement_duplicate": settlement_append.duplicate if settlement_append else None,
    }
