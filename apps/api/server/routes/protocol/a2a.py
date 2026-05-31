"""Agent-to-Agent (A2A) payment endpoints.

Enables first-class agent-to-agent transfers:
- POST /pay          — Direct agent-to-agent payment by agent IDs
- POST /messages     — Inbound A2A message handler (payment requests, etc.)
- GET  /agent-card   — Sardis agent card for discovery
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import time
import uuid
from decimal import Decimal
from inspect import isawaitable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sardis.chain.executor import ChainExecutor
from sardis.compliance.checks import ComplianceAuditEntry
from sardis.core import AgentRepository, WalletRepository
from sardis.core.identity import AgentIdentity, IdentityRegistry
from sardis.core.mandates import PaymentMandate, VCProof
from sardis.core.tokens import TokenType, to_raw_token_amount
from sardis.ledger.records import LedgerStore

from server.authz import Principal, require_principal
from server.idempotency import get_idempotency_key, run_idempotent
from server.kill_switch_dep import require_kill_switch_clear
from server.middleware.agent_payment_rate_limit import enforce_agent_payment_rate_limit
from server.operational_alerts import alert_payment_failure
from server.payment_logger import log_payment_event
from server.transaction_cap_dep import enforce_transaction_caps
from server.webhook_replay import run_with_replay_protection

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])

# Public router for unauthenticated endpoints (agent card)
public_router = APIRouter()


async def _emit_a2a_webhook(request: Request, event_type: str, data: dict) -> None:
    """Fire-and-forget webhook emission for A2A events."""
    try:
        from sardis.core.webhooks import EventType, WebhookEvent

        svc = getattr(request.app.state, "webhook_service", None)
        if not svc:
            return
        event = WebhookEvent(event_type=EventType(event_type), data=data)
        await svc.emit(event)
    except Exception as exc:
        logger.warning("A2A webhook emission failed: %s", exc)


# Cross-org A2A should stay disabled unless explicitly opted in.
def _allow_cross_org_a2a() -> bool:
    raw = os.getenv("SARDIS_A2A_ALLOW_CROSS_ORG", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_production_env() -> bool:
    env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
    return env in {"prod", "production"}


def _a2a_signature_required() -> bool:
    configured = os.getenv("SARDIS_A2A_REQUIRE_SIGNATURE", "").strip()
    if configured:
        return _is_truthy(configured)
    return _is_production_env()


def _allow_unsigned_a2a_dev() -> bool:
    configured = os.getenv("SARDIS_A2A_ALLOW_UNSIGNED_DEV", "1").strip()
    return _is_truthy(configured)


def _enforce_a2a_trust_table() -> bool:
    configured = os.getenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "").strip()
    if configured:
        return _is_truthy(configured)
    return _is_production_env()


def _require_approval_for_trust_mutations() -> bool:
    configured = os.getenv("SARDIS_A2A_TRUST_RELATION_MUTATION_REQUIRE_APPROVAL", "").strip()
    if configured:
        return _is_truthy(configured)
    return _is_production_env()


def _allowed_trust_mutation_approval_actions() -> set[str]:
    raw = os.getenv(
        "SARDIS_A2A_TRUST_RELATION_MUTATION_ALLOWED_ACTIONS",
        "a2a_trust_mutation,a2a_trust_relation_change",
    )
    out = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return out or {"a2a_trust_mutation"}


def _required_trust_mutation_approvals() -> int:
    raw = (os.getenv("SARDIS_A2A_TRUST_RELATION_MUTATION_MIN_APPROVALS", "") or "").strip()
    if raw:
        try:
            value = int(raw)
            return max(1, min(value, 5))
        except ValueError:
            pass
    if _require_approval_for_trust_mutations():
        return 2 if _is_production_env() else 1
    return 0


def _parse_a2a_trust_table() -> dict[str, set[str]]:
    """
    Parse trust relations from env.

    Format:
      SARDIS_A2A_TRUST_RELATIONS="agent_a>agent_b|agent_c,agent_b>agent_a,*>agent_ops"
    """
    raw = os.getenv("SARDIS_A2A_TRUST_RELATIONS", "")
    table: dict[str, set[str]] = {}
    for item in raw.split(","):
        relation = item.strip()
        if not relation or ">" not in relation:
            continue
        sender, recipients = relation.split(">", 1)
        sender_key = sender.strip()
        if not sender_key:
            continue
        targets = {part.strip() for part in recipients.split("|") if part.strip()}
        if not targets:
            continue
        table.setdefault(sender_key, set()).update(targets)
    return table


def _trust_table_hash(table: dict[str, set[str]]) -> str:
    canonical = {
        str(sender): sorted(str(recipient) for recipient in recipients)
        for sender, recipients in sorted(table.items())
    }
    return hashlib.sha256(
        json.dumps(canonical, separators=(",", ":"), sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()


def _evaluate_trust_table(
    *,
    sender_agent_id: str,
    recipient_agent_id: str,
    table: dict[str, set[str]],
) -> tuple[bool, str]:
    if sender_agent_id == recipient_agent_id:
        return True, "self_trusted"
    if not table:
        return False, "a2a_trust_table_not_configured"
    sender_targets = table.get(sender_agent_id, set())
    wildcard_targets = table.get("*", set())
    if "*" in sender_targets or recipient_agent_id in sender_targets:
        return True, "trusted_sender_relation"
    if "*" in wildcard_targets or recipient_agent_id in wildcard_targets:
        return True, "trusted_wildcard_relation"
    return False, "a2a_agent_not_trusted"


def _check_a2a_trust_relation(sender_agent_id: str, recipient_agent_id: str) -> tuple[bool, str]:
    if not _enforce_a2a_trust_table():
        return True, "trust_table_not_enforced"
    return _evaluate_trust_table(
        sender_agent_id=sender_agent_id,
        recipient_agent_id=recipient_agent_id,
        table=_parse_a2a_trust_table(),
    )


async def _resolve_a2a_trust_table(
    *,
    deps: A2ADependencies,
    organization_id: str,
) -> tuple[dict[str, set[str]], str]:
    repo = getattr(deps, "trust_repo", None)
    if repo is not None and hasattr(repo, "get_trust_table"):
        try:
            table = await repo.get_trust_table(organization_id)
            if table:
                normalized = {
                    str(sender): {str(recipient) for recipient in recipients}
                    for sender, recipients in table.items()
                }
                return normalized, "repository"
        except Exception:
            logger.exception("A2A trust repository unavailable for org=%s", organization_id)
            if _is_production_env():
                return {}, "repository_error"
    env_table = _parse_a2a_trust_table()
    if env_table:
        return env_table, "env"
    return {}, "none"


async def _check_a2a_trust_relation_with_deps(
    *,
    deps: A2ADependencies,
    organization_id: str,
    sender_agent_id: str,
    recipient_agent_id: str,
) -> tuple[bool, str, str]:
    if not _enforce_a2a_trust_table():
        return True, "trust_table_not_enforced", "disabled"
    table, source = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=organization_id,
    )
    if source == "repository_error":
        return False, "a2a_trust_repository_unavailable", "repository"
    allowed, reason = _evaluate_trust_table(
        sender_agent_id=sender_agent_id,
        recipient_agent_id=recipient_agent_id,
        table=table,
    )
    if not table:
        return False, reason, source
    return allowed, reason, source


async def _append_a2a_trust_audit_entry(
    *,
    deps: A2ADependencies,
    organization_id: str,
    actor_org_id: str,
    action: str,
    sender_agent_id: str,
    recipient_agent_id: str,
    before_table_hash: str,
    after_table_hash: str,
    source_before: str,
    source_after: str,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    if deps.audit_store is None:
        return None
    mandate_seed = (
        f"{organization_id}:{action}:{sender_agent_id}:{recipient_agent_id}:{after_table_hash}"
    )
    mandate_id = f"a2a_trust_{hashlib.sha256(mandate_seed.encode()).hexdigest()[:24]}"
    entry = ComplianceAuditEntry(
        mandate_id=mandate_id,
        subject=f"org:{organization_id}",
        allowed=True,
        reason=f"{action}_applied",
        rule_id=action,
        provider="a2a_trust",
        metadata={
            "event_type": "a2a_trust.relation_change",
            "organization_id": organization_id,
            "actor_organization_id": actor_org_id,
            "sender_agent_id": sender_agent_id,
            "recipient_agent_id": recipient_agent_id,
            "before_table_hash": before_table_hash,
            "after_table_hash": after_table_hash,
            "source_before": source_before,
            "source_after": source_after,
            **(metadata or {}),
        },
    )
    result = deps.audit_store.append(entry)
    if isawaitable(result):
        result = await result
    return str(result or entry.audit_id)


async def _validate_single_trust_mutation_approval(
    *,
    deps: A2ADependencies,
    principal: Principal,
    operation: str,
    sender_agent_id: str,
    recipient_agent_id: str,
    approval_id: str,
) -> tuple[bool, str, str | None]:
    if not approval_id:
        return False, "approval_required", None
    if deps.approval_service is None:
        return False, "approval_service_not_configured", None
    approval = await deps.approval_service.get_approval(approval_id)
    if not approval:
        return False, "approval_not_found", None
    if str(getattr(approval, "status", "")).strip().lower() != "approved":
        return False, "approval_not_approved", None
    reviewed_by = str(getattr(approval, "reviewed_by", "") or "").strip()
    if not reviewed_by:
        return False, "approval_missing_reviewer", None
    approval_org_id = str(getattr(approval, "organization_id", "") or "").strip()
    if approval_org_id and approval_org_id != str(principal.organization_id) and not principal.is_admin:
        return False, "approval_org_mismatch", None
    action = str(getattr(approval, "action", "") or "").strip().lower()
    if action not in _allowed_trust_mutation_approval_actions():
        return False, "approval_action_mismatch", None
    metadata = getattr(approval, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    meta_sender = str(metadata.get("sender_agent_id", "") or "").strip()
    meta_recipient = str(metadata.get("recipient_agent_id", "") or "").strip()
    meta_operation = str(metadata.get("operation", "") or "").strip().lower()
    meta_org = str(metadata.get("organization_id", "") or "").strip()
    if meta_sender and meta_sender != sender_agent_id:
        return False, "approval_sender_mismatch", None
    if meta_recipient and meta_recipient != recipient_agent_id:
        return False, "approval_recipient_mismatch", None
    if meta_operation and meta_operation != operation.lower():
        return False, "approval_operation_mismatch", None
    if meta_org and meta_org != str(principal.organization_id):
        return False, "approval_org_mismatch", None
    return True, "approval_valid", reviewed_by


async def _validate_trust_mutation_approvals(
    *,
    deps: A2ADependencies,
    principal: Principal,
    operation: str,
    sender_agent_id: str,
    recipient_agent_id: str,
    approval_id: str | None,
    approval_ids: list[str] | None = None,
) -> tuple[bool, str, list[str]]:
    if not _require_approval_for_trust_mutations():
        return True, "approval_not_required", []
    required = _required_trust_mutation_approvals()
    supplied: list[str] = []
    if approval_id:
        supplied.append(str(approval_id).strip())
    supplied.extend(str(item).strip() for item in (approval_ids or []) if str(item).strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in supplied:
        if candidate and candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)

    if not deduped:
        return False, "approval_required", deduped
    if len(deduped) < required:
        return False, f"approval_quorum_not_met:{len(deduped)}/{required}", deduped

    valid_ids: list[str] = []
    reviewers: set[str] = set()
    for candidate in deduped:
        ok, reason, reviewer = await _validate_single_trust_mutation_approval(
            deps=deps,
            principal=principal,
            operation=operation,
            sender_agent_id=sender_agent_id,
            recipient_agent_id=recipient_agent_id,
            approval_id=candidate,
        )
        if not ok:
            return False, reason, valid_ids
        valid_ids.append(candidate)
        if reviewer:
            reviewers.add(str(reviewer).strip().lower())

    if len(reviewers) < required:
        return False, f"approval_distinct_reviewer_quorum_not_met:{len(reviewers)}/{required}", valid_ids
    return True, "approval_valid", valid_ids


def _normalize_signature_algorithm(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in {"ed25519", "ecdsa-p256", "ecdsa_p256", "p256"}:
        return "ecdsa-p256" if value in {"ecdsa-p256", "ecdsa_p256", "p256"} else "ed25519"
    return ""


def _decode_signature(signature_value: str) -> bytes:
    value = (signature_value or "").strip()
    if not value:
        raise ValueError("missing_signature")

    if value.startswith("0x"):
        value = value[2:]
    if value and all(c in "0123456789abcdefABCDEF" for c in value) and len(value) % 2 == 0:
        try:
            return bytes.fromhex(value)
        except ValueError:
            pass

    padded = value + ("=" * ((4 - len(value) % 4) % 4))
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            return decoder(padded.encode())
        except Exception:  # noqa: BLE001
            continue
    raise ValueError("invalid_signature_encoding")


def _canonical_message_bytes(msg: A2AMessageRequest) -> bytes:
    payload_json = json.dumps(msg.payload or {}, separators=(",", ":"), sort_keys=True, ensure_ascii=True)
    canonical = "|".join(
        [
            msg.message_id,
            msg.message_type,
            msg.sender_id,
            msg.recipient_id,
            msg.correlation_id or "",
            msg.in_reply_to or "",
            payload_json,
        ]
    )
    return canonical.encode()


async def _verify_a2a_message_signature(
    msg: A2AMessageRequest,
    deps: A2ADependencies,
) -> tuple[bool, str | None]:
    signature_present = bool((msg.signature or "").strip())
    if not signature_present:
        if _a2a_signature_required() or not _allow_unsigned_a2a_dev():
            return False, "signature_required"
        return True, None

    if not deps.identity_registry:
        return False, "identity_registry_not_configured"

    identity_record = await deps.identity_registry.get_async(msg.sender_id)
    if not identity_record:
        return False, "sender_identity_not_found"

    expected_domain = os.getenv("SARDIS_A2A_SIGNATURE_DOMAIN", "sardis.sh").strip() or "sardis.sh"
    if not identity_record.is_active(expected_domain):
        return False, "sender_identity_domain_mismatch"

    requested_algorithm = _normalize_signature_algorithm(msg.signature_algorithm)
    if requested_algorithm and requested_algorithm != identity_record.algorithm:
        return False, "signature_algorithm_mismatch"

    try:
        signature_bytes = _decode_signature(msg.signature or "")
    except ValueError as exc:
        return False, str(exc)

    verifier = AgentIdentity(
        agent_id=identity_record.agent_id,
        public_key=identity_record.public_key,
        algorithm=identity_record.algorithm,
        domain=identity_record.domain,
    )
    valid = verifier.verify(
        message=_canonical_message_bytes(msg),
        signature=signature_bytes,
        domain=expected_domain,
        nonce=msg.message_id,
        purpose=f"a2a:{msg.message_type}",
    )
    if not valid:
        return False, "invalid_signature"
    return True, None


# ============================================================================
# Dependencies
# ============================================================================

class A2ADependencies:
    def __init__(
        self,
        wallet_repo: WalletRepository,
        agent_repo: AgentRepository,
        chain_executor: ChainExecutor | None = None,
        wallet_manager: Any | None = None,
        ledger: LedgerStore | None = None,
        compliance: Any | None = None,
        identity_registry: IdentityRegistry | None = None,
        trust_repo: Any | None = None,
        audit_store: Any | None = None,
        approval_service: Any | None = None,
        orchestrator: Any | None = None,
    ):
        self.wallet_repo = wallet_repo
        self.agent_repo = agent_repo
        self.chain_executor = chain_executor
        self.wallet_manager = wallet_manager
        self.ledger = ledger
        self.compliance = compliance
        self.identity_registry = identity_registry
        self.trust_repo = trust_repo
        self.audit_store = audit_store
        self.approval_service = approval_service
        # PaymentOrchestrator — the single authorized execution path
        # (KYA → spending-mandate → policy → compliance → chain → ledger → receipt).
        self.orchestrator = orchestrator


def get_deps() -> A2ADependencies:
    raise NotImplementedError("Dependency override required")


async def _run_a2a_guardrails(
    *,
    agent_id: str,
    org_id: str,
    chain: str,
    amount: Decimal,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Run the defense-in-depth guardrails that the orchestrator does NOT.

    ``PaymentOrchestrator.execute_chain`` runs KYA → spending-mandate → policy →
    compliance → chain → ledger → receipt, but does not run the kill switch,
    transaction caps, or anomaly engine.  The deprecated ``ControlPlane.submit``
    path used to run those (steps 0a/0b/1.5).  To avoid silently dropping a check
    on a money path, we run them explicitly here before ``execute_chain``.

    Raises:
        KillSwitchError-derived ``HTTPException`` (503) when a kill switch is active.
        ``HTTPException`` (403) when a transaction cap is exceeded or the anomaly
        engine blocks the transaction.

    Returns:
        An optional ``anomaly_flag`` dict when the anomaly engine FLAGs (but does
        not block) the transaction; ``None`` otherwise.
    """
    metadata = metadata or {}

    # Step 0a: Kill switch (global / org / agent / chain scopes).
    from sardis.guardrails.kill_switch import KillSwitchError, get_kill_switch

    kill_switch = get_kill_switch()
    try:
        await kill_switch.check(agent_id=agent_id, org_id=org_id)
        if chain:
            await kill_switch.check_chain(chain)
    except KillSwitchError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"kill_switch_active: {e}",
        ) from e

    # Step 0b: Transaction caps.
    if amount > 0:
        from sardis.guardrails.transaction_caps import get_transaction_cap_engine

        cap_engine = get_transaction_cap_engine()
        cap_result = await cap_engine.check_and_record(
            amount=amount,
            org_id=org_id,
            agent_id=agent_id or None,
        )
        if not cap_result.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"transaction_cap_exceeded: {cap_result.message}",
            )

    # Step 1.5: Anomaly risk assessment.
    from sardis.guardrails.anomaly_engine import RiskAction, get_anomaly_engine

    anomaly_engine = get_anomaly_engine()
    assessment = anomaly_engine.assess_risk(
        agent_id=agent_id,
        amount=amount,
        merchant_id=metadata.get("merchant_id"),
        merchant_category=metadata.get("merchant_category"),
        behavioral_alerts=metadata.get("behavioral_alerts"),
        baseline_mean=metadata.get("baseline_mean"),
        baseline_std=metadata.get("baseline_std"),
        recent_tx_count_1h=metadata.get("recent_tx_count_1h", 0),
        is_new_merchant=metadata.get("is_new_merchant", False),
        hour_of_day=metadata.get("hour_of_day"),
        typical_hours=metadata.get("typical_hours"),
    )
    logger.info(
        "a2a: anomaly assessment agent=%s score=%.3f action=%s",
        agent_id, assessment.overall_score, assessment.action.value,
    )
    blocking_actions = {
        RiskAction.KILL_SWITCH: "kill_switch_activated_by_anomaly",
        RiskAction.FREEZE_AGENT: "agent_frozen_by_anomaly",
        RiskAction.REQUIRE_APPROVAL: "anomaly_requires_approval",
    }
    if assessment.action in blocking_actions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=blocking_actions[assessment.action],
        )

    if assessment.action == RiskAction.FLAG:
        logger.warning(
            "a2a: agent=%s flagged by anomaly engine (score=%.3f)",
            agent_id, assessment.overall_score,
        )
        return {
            "anomaly_flagged": True,
            "anomaly_score": assessment.overall_score,
            "anomaly_action": assessment.action.value,
        }

    # RiskAction.ALLOW → no flag.
    return None


# ============================================================================
# Request/Response Models
# ============================================================================

class A2APayRequest(BaseModel):
    """Request for agent-to-agent payment."""
    sender_agent_id: str = Field(..., description="Source agent ID (payer)")
    recipient_agent_id: str = Field(..., description="Destination agent ID (payee)")
    amount: Decimal = Field(..., gt=0, description="Amount in token units (e.g. 10.50)")
    token: str = Field(default="USDC")
    chain: str = Field(default="base_sepolia")
    memo: str | None = Field(default=None, description="Optional memo for audit trail")
    reference: str | None = Field(default=None, description="External reference (order, invoice)")


class A2APayResponse(BaseModel):
    """Response from agent-to-agent payment."""
    success: bool
    tx_hash: str
    status: str
    sender_agent_id: str
    recipient_agent_id: str
    sender_wallet_id: str
    recipient_wallet_id: str
    from_address: str
    to_address: str
    amount: str
    token: str
    chain: str
    memo: str | None = None
    reference: str | None = None
    ledger_tx_id: str | None = None
    audit_anchor: str | None = None
    receipt_id: str | None = None


class A2AMessageRequest(BaseModel):
    """Inbound A2A message."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: str
    sender_id: str
    recipient_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    in_reply_to: str | None = None
    signature: str | None = None
    signature_algorithm: str = "Ed25519"


class A2AMessageResponse(BaseModel):
    """Outbound A2A message response."""
    message_id: str
    message_type: str
    sender_id: str
    recipient_id: str
    status: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    in_reply_to: str | None = None
    error: str | None = None
    error_code: str | None = None


class A2ATrustCheckRequest(BaseModel):
    sender_agent_id: str
    recipient_agent_id: str


class A2ATrustCheckResponse(BaseModel):
    sender_agent_id: str
    recipient_agent_id: str
    enforced: bool
    allowed: bool
    reason: str
    source: str
    table_hash: str


class A2ATrustTableResponse(BaseModel):
    enforced: bool
    source: str
    table_hash: str
    audit_id: str | None = None
    approval_id: str | None = None
    approval_ids: list[str] = Field(default_factory=list)
    relations: dict[str, list[str]] = Field(default_factory=dict)


class A2ATrustRelationUpsertRequest(BaseModel):
    sender_agent_id: str
    recipient_agent_id: str
    approval_id: str | None = None
    approval_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2ATrustRelationDeleteRequest(BaseModel):
    sender_agent_id: str
    recipient_agent_id: str
    approval_id: str | None = None
    approval_ids: list[str] = Field(default_factory=list)


class A2APeerTrustEntry(BaseModel):
    agent_id: str
    owner_id: str
    is_active: bool
    wallet_id: str | None = None
    wallet_addresses: dict[str, str] = Field(default_factory=dict)
    kya_level: str | None = None
    kya_status: str | None = None
    trusted: bool
    is_broadcast_target: bool = False
    trust_reason: str


class A2ATrustPeersResponse(BaseModel):
    sender_agent_id: str
    sender_wallet_id: str | None = None
    sender_wallet_addresses: dict[str, str] = Field(default_factory=dict)
    enforced: bool
    source: str
    table_hash: str
    total_candidates: int
    trusted_count: int
    broadcast_targets: list[str] = Field(default_factory=list)
    peers: list[A2APeerTrustEntry] = Field(default_factory=list)


class A2ATrustAuditEntryResponse(BaseModel):
    audit_id: str
    mandate_id: str
    subject: str
    allowed: bool
    reason: str | None = None
    rule_id: str | None = None
    provider: str | None = None
    evaluated_at: str | None = None
    proof_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2ATrustAuditListResponse(BaseModel):
    organization_id: str
    count: int
    entries: list[A2ATrustAuditEntryResponse] = Field(default_factory=list)


class A2ASecurityPolicyResponse(BaseModel):
    signature_required: bool
    allow_unsigned_dev: bool
    trust_table_enforced: bool
    trust_mutation_approval_required: bool
    trust_mutation_approval_actions: list[str] = Field(default_factory=list)


# ============================================================================
# POST /pay — Agent-to-Agent Direct Payment
# ============================================================================

@router.post("/pay", response_model=A2APayResponse)
async def a2a_pay(
    req: A2APayRequest,
    request: Request,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
    _ks: None = Depends(require_kill_switch_clear),
    _cap: None = Depends(enforce_transaction_caps),
):
    """
    Execute a direct agent-to-agent payment.

    Transfers tokens from sender agent's wallet to recipient agent's wallet.
    Both agents must exist, have active wallets, and have addresses on the
    specified chain. Policy checks are enforced on the sender's wallet.
    """
    # Idempotency key
    derived = f"a2a:{req.sender_agent_id}:{req.recipient_agent_id}:{req.amount}:{req.token}:{req.chain}:{req.reference or ''}"
    idem_key = get_idempotency_key(request) or derived

    async def _execute() -> tuple[int, object]:
        # Look up sender agent
        sender_agent = await deps.agent_repo.get(req.sender_agent_id)
        if not sender_agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender agent not found")
        if not sender_agent.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender agent is inactive")
        if not principal.is_admin and sender_agent.owner_id != principal.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Look up recipient agent
        recipient_agent = await deps.agent_repo.get(req.recipient_agent_id)
        if not recipient_agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient agent not found")
        if not recipient_agent.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient agent is inactive")
        if (
            not principal.is_admin
            and not _allow_cross_org_a2a()
            and recipient_agent.owner_id != principal.organization_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="cross_org_a2a_disabled",
            )

        trust_ok, trust_reason, _ = await _check_a2a_trust_relation_with_deps(
            deps=deps,
            organization_id=str(principal.organization_id),
            sender_agent_id=req.sender_agent_id,
            recipient_agent_id=req.recipient_agent_id,
        )
        if not trust_ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=trust_reason,
            )

        # Rate limit check
        await enforce_agent_payment_rate_limit(
            agent_id=req.sender_agent_id,
            operation="a2a.pay",
        )

        # Look up sender wallet
        sender_wallet = await deps.wallet_repo.get_by_agent(req.sender_agent_id)
        if not sender_wallet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender agent has no wallet")
        if not sender_wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender wallet is inactive")
        if sender_wallet.is_frozen:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sender wallet is frozen")

        # Look up recipient wallet
        recipient_wallet = await deps.wallet_repo.get_by_agent(req.recipient_agent_id)
        if not recipient_wallet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient agent has no wallet")

        # Get addresses
        sender_address = sender_wallet.get_address(req.chain)
        if not sender_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sender wallet has no address on {req.chain}",
            )

        recipient_address = recipient_wallet.get_address(req.chain)
        if not recipient_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipient wallet has no address on {req.chain}",
            )

        if not deps.chain_executor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chain executor not available",
            )

        # Convert amount to minor units
        try:
            amount_minor = to_raw_token_amount(TokenType(req.token.upper()), req.amount)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported token: {req.token}",
            ) from exc

        # Build payment mandate
        digest = hashlib.sha256(str(idem_key).encode()).hexdigest()
        mandate = PaymentMandate(
            mandate_id=f"a2a_{digest[:16]}",
            mandate_type="payment",
            issuer=f"agent:{req.sender_agent_id}",
            subject=sender_wallet.agent_id,
            expires_at=int(time.time()) + 300,
            nonce=digest,
            proof=VCProof(
                verification_method=f"wallet:{sender_wallet.wallet_id}#key-1",
                created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                proof_value="a2a-transfer",
            ),
            domain="sardis.sh",
            purpose="a2a_transfer",
            chain=req.chain,
            token=req.token,
            amount_minor=amount_minor,
            destination=recipient_address,
            audit_hash=hashlib.sha256(
                f"a2a:{sender_wallet.wallet_id}:{recipient_wallet.wallet_id}:{amount_minor}:{req.memo or ''}".encode()
            ).hexdigest(),
            wallet_id=sender_wallet.wallet_id,
            merchant_domain="sardis.sh",
        )

        # Execute through the single authorized path: PaymentOrchestrator.execute_chain
        # (KYA → spending-mandate → policy → compliance → chain → ledger → receipt).
        # The mandate chain is built first-party here; upstream agent/trust/wallet
        # verification (above) has already authorized the transfer, so the typed
        # factory's internal system proof is the correct contract (same as ap2/mvp).
        from sardis.core.mandate_chain_factory import build_mandate_chain
        from sardis.core.orchestrator import (
            ChainExecutionError,
            ComplianceViolationError,
            KYAViolationError,
            MandateViolationError,
            PaymentExecutionError,
            PolicyViolationError,
        )

        if deps.orchestrator is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="orchestrator_not_configured",
            )

        # Preserve the defense-in-depth guardrails the orchestrator does not run
        # (kill switch / transaction caps / anomaly) that ControlPlane.submit used to.
        await _run_a2a_guardrails(
            agent_id=req.sender_agent_id,
            org_id=str(principal.organization_id),
            chain=req.chain,
            amount=Decimal(str(req.amount)),
        )

        chain = build_mandate_chain(
            agent_id=req.sender_agent_id,
            amount=Decimal(str(req.amount)),
            currency=req.token,
            counterparty=recipient_address,
            wallet_id=sender_wallet.wallet_id,
            mandate_id=mandate.mandate_id,
            chain=req.chain,
            purpose=req.memo or "a2a_transfer",
            merchant_domain="sardis.sh",
            issuer=f"agent:{req.sender_agent_id}",
        )

        async def _a2a_payment_failed(err: str, *, alert: bool) -> None:
            log_payment_event("a2a.payment.failed",
                org_id=str(principal.organization_id),
                agent_id=req.sender_agent_id,
                amount=str(req.amount), currency=req.token, chain=req.chain,
                status="failed", error=err)
            if alert:
                asyncio.create_task(alert_payment_failure(
                    error=err,
                    org_id=str(principal.organization_id),
                    agent_id=req.sender_agent_id,
                    tx_id=str(idem_key),
                ))
            await _emit_a2a_webhook(request, "a2a.payment.failed", {
                "sender_agent_id": req.sender_agent_id,
                "recipient_agent_id": req.recipient_agent_id,
                "amount": str(req.amount),
                "token": req.token,
                "chain": req.chain,
                "error": err,
            })

        try:
            result = await deps.orchestrator.execute_chain(chain)
        except (
            PolicyViolationError,
            MandateViolationError,
            KYAViolationError,
            ComplianceViolationError,
        ) as e:
            # All deny outcomes (policy / spending-mandate / KYA / compliance) → 403.
            await _a2a_payment_failed(str(e), alert=False)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        except ChainExecutionError as e:
            await _a2a_payment_failed(str(e), alert=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e
        except PaymentExecutionError as e:
            # Catch-all for LedgerAppendError and any future PaymentExecutionError
            # subclass so an execution failure never leaks as a raw 500/stacktrace.
            await _a2a_payment_failed(str(e), alert=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e

        # Post-execution: record spend (best-effort)
        if deps.wallet_manager:
            try:
                await deps.wallet_manager.async_record_spend(mandate)
            except Exception as e:
                logger.warning("Failed to record spend for A2A mandate %s: %s", mandate.mandate_id, e)

        log_payment_event("a2a.payment.completed",
            org_id=str(principal.organization_id),
            agent_id=req.sender_agent_id,
            amount=str(req.amount), currency=req.token, chain=req.chain,
            status="completed",
            tx_hash=result.chain_tx_hash)

        await _emit_a2a_webhook(request, "a2a.payment.completed", {
            "sender_agent_id": req.sender_agent_id,
            "recipient_agent_id": req.recipient_agent_id,
            "amount": str(req.amount),
            "token": req.token,
            "chain": req.chain,
            "tx_hash": result.chain_tx_hash,
            "reference": req.reference,
        })

        return 200, A2APayResponse(
            success=True,
            tx_hash=result.chain_tx_hash,
            status="submitted",
            sender_agent_id=req.sender_agent_id,
            recipient_agent_id=req.recipient_agent_id,
            sender_wallet_id=sender_wallet.wallet_id,
            recipient_wallet_id=recipient_wallet.wallet_id,
            from_address=sender_address,
            to_address=recipient_address,
            amount=str(req.amount),
            token=req.token,
            chain=req.chain,
            memo=req.memo,
            reference=req.reference,
            ledger_tx_id=result.ledger_tx_id or None,
            audit_anchor=result.audit_anchor or None,
            receipt_id=result.mandate_id or None,
        )

    return await run_idempotent(
        request=request,
        principal=principal,
        operation="a2a.pay",
        key=str(idem_key),
        payload=req.model_dump(),
        fn=_execute,
    )


# ============================================================================
# POST /messages — Inbound A2A Message Handler
# ============================================================================

@router.post("/messages", response_model=A2AMessageResponse)
async def handle_a2a_message(
    msg: A2AMessageRequest,
    request: Request,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """
    Handle inbound A2A messages (payment requests, credential verifications, etc.).

    Processes structured A2A messages according to the A2A protocol.
    Currently supports: payment_request, credential_request, ack.
    """
    logger.info(f"A2A message received: type={msg.message_type}, from={msg.sender_id}, to={msg.recipient_id}")

    signature_ok, signature_reason = await _verify_a2a_message_signature(msg, deps)
    if not signature_ok:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="error",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error=f"A2A signature validation failed: {signature_reason}",
            error_code=signature_reason or "invalid_signature",
        )

    async def _dispatch_message() -> A2AMessageResponse:
        if msg.message_type == "payment_request":
            return await _handle_payment_request(msg, request, deps, principal)
        if msg.message_type == "credential_request":
            return _handle_credential_request(msg)
        if msg.message_type == "ack":
            return A2AMessageResponse(
                message_id=str(uuid.uuid4()),
                message_type="ack",
                sender_id=msg.recipient_id,
                recipient_id=msg.sender_id,
                status="received",
                in_reply_to=msg.message_id,
            )
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="error",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            error=f"Unsupported message type: {msg.message_type}",
            error_code="unsupported_message_type",
        )

    body = await request.body()
    duplicate_response = A2AMessageResponse(
        message_id=msg.message_id,
        message_type="ack",
        sender_id=msg.recipient_id,
        recipient_id=msg.sender_id,
        status="duplicate",
        in_reply_to=msg.message_id,
        correlation_id=msg.correlation_id,
        payload={"deduplicated": True},
    )
    return await run_with_replay_protection(
        request=request,
        provider="a2a",
        event_id=msg.message_id,
        body=body,
        response_on_duplicate=duplicate_response,
        fn=_dispatch_message,
    )


@router.get("/trust/table", response_model=A2ATrustTableResponse)
async def get_a2a_trust_table(
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    table, source = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=str(principal.organization_id),
    )
    if source == "repository_error":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="a2a_trust_repository_unavailable")
    normalized = {sender: sorted(recipients) for sender, recipients in table.items()}
    return A2ATrustTableResponse(
        enforced=_enforce_a2a_trust_table(),
        source=source,
        table_hash=_trust_table_hash(table),
        relations=normalized,
    )


@router.post("/trust/check", response_model=A2ATrustCheckResponse)
async def check_a2a_trust(
    payload: A2ATrustCheckRequest,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        sender_agent = await deps.agent_repo.get(payload.sender_agent_id)
        recipient_agent = await deps.agent_repo.get(payload.recipient_agent_id)
        if (
            sender_agent is None
            or recipient_agent is None
            or sender_agent.owner_id != principal.organization_id
            or recipient_agent.owner_id != principal.organization_id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="access_denied")

    allowed, reason, source = await _check_a2a_trust_relation_with_deps(
        deps=deps,
        organization_id=str(principal.organization_id),
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
    )
    table_hash = _trust_table_hash({})
    if _enforce_a2a_trust_table():
        table, table_source = await _resolve_a2a_trust_table(
            deps=deps,
            organization_id=str(principal.organization_id),
        )
        if table_source != "repository_error":
            table_hash = _trust_table_hash(table)
    return A2ATrustCheckResponse(
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
        enforced=_enforce_a2a_trust_table(),
        allowed=allowed,
        reason=reason,
        source=source,
        table_hash=table_hash,
    )


@router.get("/trust/peers", response_model=A2ATrustPeersResponse)
async def list_a2a_trust_peers(
    sender_agent_id: str = Query(..., description="Sender agent to evaluate trust from"),
    include_untrusted: bool = Query(default=False),
    include_inactive: bool = Query(default=False),
    include_wallet_addresses: bool = Query(default=False),
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    sender = await deps.agent_repo.get(sender_agent_id)
    if sender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sender_not_found")
    if not principal.is_admin and sender.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="access_denied")

    lister = getattr(deps.agent_repo, "list", None)
    if not callable(lister):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="agent_repository_list_not_configured")

    org_id = str(sender.owner_id)
    agents = await lister(owner_id=org_id, limit=1000, offset=0)
    if not include_inactive:
        agents = [item for item in agents if bool(getattr(item, "is_active", False))]

    enforced = _enforce_a2a_trust_table()
    if not enforced:
        source = "disabled"
        table: dict[str, set[str]] = {}
    else:
        table, source = await _resolve_a2a_trust_table(deps=deps, organization_id=org_id)
        if source == "repository_error":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="a2a_trust_repository_unavailable")

    rows: list[A2APeerTrustEntry] = []
    broadcast_targets: list[str] = []
    trusted_count = 0

    async def _resolve_wallet_snapshot(
        *,
        agent_id: str,
        fallback_wallet_id: str | None,
    ) -> tuple[str | None, dict[str, str]]:
        wallet_id = str(fallback_wallet_id or "") or None
        addresses: dict[str, str] = {}
        if not include_wallet_addresses:
            return wallet_id, addresses
        repo = getattr(deps, "wallet_repo", None)
        getter = getattr(repo, "get_by_agent", None)
        if callable(getter):
            try:
                wallet = await getter(agent_id)
            except Exception:
                wallet = None
            if wallet is not None:
                wallet_id = str(getattr(wallet, "wallet_id", "") or wallet_id or "") or None
                raw_addresses = getattr(wallet, "addresses", {}) or {}
                if isinstance(raw_addresses, dict):
                    for chain, addr in raw_addresses.items():
                        if addr:
                            addresses[str(chain)] = str(addr)
        return wallet_id, addresses

    sender_wallet_id, sender_wallet_addresses = await _resolve_wallet_snapshot(
        agent_id=sender_agent_id,
        fallback_wallet_id=getattr(sender, "wallet_id", None),
    )

    for candidate in agents:
        candidate_id = str(getattr(candidate, "agent_id", ""))
        if not candidate_id or candidate_id == sender_agent_id:
            continue
        if not enforced:
            trusted = True
            reason = "trust_table_not_enforced"
        else:
            trusted, reason = _evaluate_trust_table(
                sender_agent_id=sender_agent_id,
                recipient_agent_id=candidate_id,
                table=table,
            )
        if trusted:
            trusted_count += 1
            if bool(getattr(candidate, "is_active", False)):
                broadcast_targets.append(candidate_id)
        if not trusted and not include_untrusted:
            continue
        wallet_id, wallet_addresses = await _resolve_wallet_snapshot(
            agent_id=candidate_id,
            fallback_wallet_id=getattr(candidate, "wallet_id", None),
        )
        rows.append(
            A2APeerTrustEntry(
                agent_id=candidate_id,
                owner_id=str(getattr(candidate, "owner_id", "")),
                is_active=bool(getattr(candidate, "is_active", False)),
                wallet_id=wallet_id,
                wallet_addresses=wallet_addresses,
                kya_level=getattr(candidate, "kya_level", None),
                kya_status=getattr(candidate, "kya_status", None),
                trusted=trusted,
                is_broadcast_target=trusted and bool(getattr(candidate, "is_active", False)),
                trust_reason=reason,
            )
        )

    rows.sort(key=lambda item: (not item.trusted, item.agent_id))
    broadcast_targets = sorted(set(broadcast_targets))
    return A2ATrustPeersResponse(
        sender_agent_id=sender_agent_id,
        sender_wallet_id=sender_wallet_id,
        sender_wallet_addresses=sender_wallet_addresses,
        enforced=enforced,
        source=source,
        table_hash=_trust_table_hash(table),
        total_candidates=max(len(agents) - 1, 0),
        trusted_count=trusted_count,
        broadcast_targets=broadcast_targets,
        peers=rows,
    )


@router.get("/trust/security-policy", response_model=A2ASecurityPolicyResponse)
async def get_a2a_security_policy(
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    return A2ASecurityPolicyResponse(
        signature_required=_a2a_signature_required(),
        allow_unsigned_dev=_allow_unsigned_a2a_dev(),
        trust_table_enforced=_enforce_a2a_trust_table(),
        trust_mutation_approval_required=_require_approval_for_trust_mutations(),
        trust_mutation_approval_actions=sorted(_allowed_trust_mutation_approval_actions()),
    )


@router.get("/trust/audit/recent", response_model=A2ATrustAuditListResponse)
async def list_a2a_trust_audit_recent(
    limit: int = Query(default=20, ge=1, le=200),
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    if deps.audit_store is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="audit_store_not_configured")
    getter = getattr(deps.audit_store, "get_recent", None)
    if not callable(getter):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="audit_store_recent_not_supported")
    recent = getter(max(limit * 5, 50))
    if isawaitable(recent):
        recent = await recent
    org_id = str(principal.organization_id)
    out: list[A2ATrustAuditEntryResponse] = []
    for item in recent or []:
        raw = item.to_dict() if hasattr(item, "to_dict") else item
        if not isinstance(raw, dict):
            raw = {
                "audit_id": str(getattr(item, "audit_id", "")),
                "mandate_id": str(getattr(item, "mandate_id", "")),
                "subject": str(getattr(item, "subject", "")),
                "allowed": bool(getattr(item, "allowed", False)),
                "reason": getattr(item, "reason", None),
                "rule_id": getattr(item, "rule_id", None),
                "provider": getattr(item, "provider", None),
                "evaluated_at": str(getattr(item, "evaluated_at", "")),
                "metadata": getattr(item, "metadata", {}) or {},
            }
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        if str(raw.get("provider", "")) != "a2a_trust":
            continue
        if str(metadata.get("organization_id", "")) != org_id:
            continue
        out.append(
            A2ATrustAuditEntryResponse(
                audit_id=str(raw.get("audit_id", "")),
                mandate_id=str(raw.get("mandate_id", "")),
                subject=str(raw.get("subject", "")),
                allowed=bool(raw.get("allowed", False)),
                reason=raw.get("reason"),
                rule_id=raw.get("rule_id"),
                provider=raw.get("provider"),
                evaluated_at=str(raw.get("evaluated_at", "")),
                proof_path=(
                    f"/api/v2/compliance/audit/mandate/{raw.get('mandate_id')}/proof/{raw.get('audit_id')}"
                    if raw.get("mandate_id") and raw.get("audit_id")
                    else None
                ),
                metadata=metadata,
            )
        )
        if len(out) >= limit:
            break
    return A2ATrustAuditListResponse(
        organization_id=org_id,
        count=len(out),
        entries=out,
    )


@router.post("/trust/relations", response_model=A2ATrustTableResponse)
async def upsert_a2a_trust_relation(
    payload: A2ATrustRelationUpsertRequest,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    repo = getattr(deps, "trust_repo", None)
    upserter = getattr(repo, "upsert_relation", None)
    if not callable(upserter):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="a2a_trust_repository_not_configured")
    approval_ok, approval_reason, valid_approval_ids = await _validate_trust_mutation_approvals(
        deps=deps,
        principal=principal,
        operation="upsert_relation",
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
        approval_id=payload.approval_id,
        approval_ids=payload.approval_ids,
    )
    if not approval_ok:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=approval_reason)
    table_before, source_before = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=str(principal.organization_id),
    )
    before_hash = _trust_table_hash(table_before)
    await upserter(
        organization_id=str(principal.organization_id),
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
        metadata=payload.metadata,
    )
    table, source = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=str(principal.organization_id),
    )
    normalized = {sender: sorted(recipients) for sender, recipients in table.items()}
    after_hash = _trust_table_hash(table)
    audit_id = await _append_a2a_trust_audit_entry(
        deps=deps,
        organization_id=str(principal.organization_id),
        actor_org_id=str(principal.organization_id),
        action="upsert_relation",
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
        before_table_hash=before_hash,
        after_table_hash=after_hash,
        source_before=source_before,
        source_after=source,
        metadata={
            "request_metadata": payload.metadata,
            "approval_id": payload.approval_id,
            "approval_ids": valid_approval_ids,
            "approval_validation": approval_reason,
        },
    )
    return A2ATrustTableResponse(
        enforced=_enforce_a2a_trust_table(),
        source=source,
        table_hash=after_hash,
        audit_id=audit_id,
        approval_id=valid_approval_ids[0] if valid_approval_ids else (payload.approval_id if approval_ok else None),
        approval_ids=valid_approval_ids,
        relations=normalized,
    )


@router.delete("/trust/relations", response_model=A2ATrustTableResponse)
async def delete_a2a_trust_relation(
    payload: A2ATrustRelationDeleteRequest,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    repo = getattr(deps, "trust_repo", None)
    deleter = getattr(repo, "delete_relation", None)
    if not callable(deleter):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="a2a_trust_repository_not_configured")
    approval_ok, approval_reason, valid_approval_ids = await _validate_trust_mutation_approvals(
        deps=deps,
        principal=principal,
        operation="delete_relation",
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
        approval_id=payload.approval_id,
        approval_ids=payload.approval_ids,
    )
    if not approval_ok:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=approval_reason)
    table_before, source_before = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=str(principal.organization_id),
    )
    before_hash = _trust_table_hash(table_before)
    deleted = await deleter(
        organization_id=str(principal.organization_id),
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
    )
    table, source = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=str(principal.organization_id),
    )
    normalized = {sender: sorted(recipients) for sender, recipients in table.items()}
    after_hash = _trust_table_hash(table)
    audit_id = await _append_a2a_trust_audit_entry(
        deps=deps,
        organization_id=str(principal.organization_id),
        actor_org_id=str(principal.organization_id),
        action="delete_relation",
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
        before_table_hash=before_hash,
        after_table_hash=after_hash,
        source_before=source_before,
        source_after=source,
        metadata={
            "deleted": bool(deleted),
            "approval_id": payload.approval_id,
            "approval_ids": valid_approval_ids,
            "approval_validation": approval_reason,
        },
    )
    return A2ATrustTableResponse(
        enforced=_enforce_a2a_trust_table(),
        source=source,
        table_hash=after_hash,
        audit_id=audit_id,
        approval_id=valid_approval_ids[0] if valid_approval_ids else (payload.approval_id if approval_ok else None),
        approval_ids=valid_approval_ids,
        relations=normalized,
    )


async def _handle_payment_request(
    msg: A2AMessageRequest,
    request: Request,
    deps: A2ADependencies,
    principal: Principal,
) -> A2AMessageResponse:
    """Handle an inbound A2A payment request."""
    payload = msg.payload
    sender_agent_id = payload.get("sender_agent_id") or msg.sender_id
    recipient_agent_id = payload.get("recipient_agent_id") or msg.recipient_id
    amount_minor = payload.get("amount_minor", 0)
    token = payload.get("token", "USDC")
    chain = payload.get("chain", "base_sepolia")
    destination = payload.get("destination", "")

    if not destination or not amount_minor:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Missing required fields: destination, amount_minor",
            error_code="invalid_request",
        )

    # Validate sender/recipient agents and enforce org boundaries.
    sender_agent = await deps.agent_repo.get(sender_agent_id)
    if not sender_agent:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Sender agent not found",
            error_code="sender_not_found",
        )
    if not sender_agent.is_active:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Sender agent is inactive",
            error_code="sender_inactive",
        )

    recipient_agent = await deps.agent_repo.get(recipient_agent_id)
    if not recipient_agent:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Recipient agent not found",
            error_code="recipient_not_found",
        )
    if not recipient_agent.is_active:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Recipient agent is inactive",
            error_code="recipient_inactive",
        )

    if not principal.is_admin and recipient_agent.owner_id != principal.organization_id:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Access denied",
            error_code="forbidden",
        )
    if (
        not principal.is_admin
        and not _allow_cross_org_a2a()
        and sender_agent.owner_id != principal.organization_id
    ):
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="cross_org_a2a_disabled",
            error_code="forbidden",
        )

    trust_ok, trust_reason, _ = await _check_a2a_trust_relation_with_deps(
        deps=deps,
        organization_id=str(principal.organization_id),
        sender_agent_id=sender_agent_id,
        recipient_agent_id=recipient_agent_id,
    )
    if not trust_ok:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error=trust_reason,
            error_code=trust_reason,
        )

    # Look up recipient wallet to execute from
    recipient_wallet = await deps.wallet_repo.get_by_agent(recipient_agent_id)
    if not recipient_wallet:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Recipient agent has no wallet",
            error_code="no_wallet",
        )

    if not deps.chain_executor:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            error="Chain executor not available",
            error_code="service_unavailable",
        )

    # Build mandate
    digest = hashlib.sha256(f"{msg.message_id}:{amount_minor}:{destination}".encode()).hexdigest()
    mandate = PaymentMandate(
        mandate_id=f"a2a_msg_{digest[:16]}",
        mandate_type="payment",
        issuer=f"agent:{sender_agent_id}",
        subject=recipient_wallet.agent_id,
        expires_at=int(time.time()) + 300,
        nonce=digest,
        proof=VCProof(
            verification_method=f"wallet:{recipient_wallet.wallet_id}#key-1",
            created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            proof_value="a2a-message",
        ),
        domain="sardis.sh",
        purpose="a2a_transfer",
        chain=chain,
        token=token,
        amount_minor=amount_minor,
        destination=destination,
        audit_hash=hashlib.sha256(
            f"a2a_msg:{msg.message_id}:{amount_minor}:{destination}".encode()
        ).hexdigest(),
        wallet_id=recipient_wallet.wallet_id,
        merchant_domain="sardis.sh",
    )

    # Execute through the single authorized path: PaymentOrchestrator.execute_chain
    # (KYA → spending-mandate → policy → compliance → chain → ledger → receipt).
    # Inbound A2A payment requests pay FROM the recipient's wallet to `destination`;
    # the message signature was verified upstream in handle_a2a_message, so the
    # chain is built first-party with the factory's internal system proof.
    if deps.orchestrator is None:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="orchestrator_not_configured",
            error_code="configuration_error",
        )

    from sardis.core.mandate_chain_factory import build_mandate_chain
    from sardis.core.orchestrator import (
        ChainExecutionError,
        ComplianceViolationError,
        KYAViolationError,
        MandateViolationError,
        PaymentExecutionError,
        PolicyViolationError,
    )
    from sardis.core.tokens import normalize_token_amount

    # The recipient's wallet is the payer for inbound payment requests; policy /
    # KYA / caps must therefore evaluate the recipient agent's wallet.
    payer_agent_id = recipient_wallet.agent_id

    # amount_minor is in minor units; convert to major (token) units using the
    # token's real decimals so a non-6-decimal token can't mis-scale the
    # cap/anomaly reading. Fall back to the factory default precision if the
    # token symbol isn't recognised.
    try:
        guardrail_amount = normalize_token_amount(TokenType(token.upper()), int(amount_minor))
    except (KeyError, ValueError):
        guardrail_amount = Decimal(amount_minor) / (Decimal(10) ** 6)

    # Preserve the defense-in-depth guardrails the orchestrator does not run
    # (kill switch / transaction caps / anomaly). This route has no route-level
    # kill_switch/cap dependency, so running them here is load-bearing.
    try:
        await _run_a2a_guardrails(
            agent_id=payer_agent_id,
            org_id=str(principal.organization_id),
            chain=chain,
            amount=guardrail_amount,
        )
    except HTTPException as e:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error=str(e.detail),
            error_code="policy_denied",
        )

    # amount_minor is already minor units → decimals=0 stores it exactly.
    payment_chain = build_mandate_chain(
        agent_id=payer_agent_id,
        amount=amount_minor,
        currency=token,
        counterparty=destination,
        wallet_id=recipient_wallet.wallet_id,
        mandate_id=mandate.mandate_id,
        chain=chain,
        decimals=0,
        purpose=f"a2a_msg:{msg.message_id}",
        merchant_domain="sardis.sh",
        issuer=f"agent:{sender_agent_id}",
    )

    try:
        result = await deps.orchestrator.execute_chain(payment_chain)
    except (
        PolicyViolationError,
        MandateViolationError,
        KYAViolationError,
        ComplianceViolationError,
    ) as e:
        # All deny outcomes (policy / spending-mandate / KYA / compliance).
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error=str(e),
            error_code="policy_denied",
        )
    except ChainExecutionError as e:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error=str(e),
            error_code="execution_failed",
        )
    except PaymentExecutionError as e:
        # Catch-all for LedgerAppendError and any future PaymentExecutionError
        # subclass so an execution failure returns a structured response, not a
        # raw unhandled handler error.
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error=str(e),
            error_code="execution_failed",
        )

    # Record spend state for policy enforcement
    if deps.wallet_manager:
        try:
            await deps.wallet_manager.async_record_spend(mandate)
        except Exception:
            logger.warning("Failed to record spend for A2A message mandate %s", mandate.mandate_id)

    return A2AMessageResponse(
        message_id=str(uuid.uuid4()),
        message_type="payment_response",
        sender_id=msg.recipient_id,
        recipient_id=msg.sender_id,
        status="completed",
        in_reply_to=msg.message_id,
        correlation_id=msg.correlation_id,
        payload={
            "success": True,
            "tx_hash": result.chain_tx_hash,
            "chain": chain,
            "amount_minor": amount_minor,
            "token": token,
            "receipt_id": result.mandate_id,
        },
    )


def _handle_credential_request(msg: A2AMessageRequest) -> A2AMessageResponse:
    """Handle an inbound credential verification request."""
    from sardis.core.agent_card import verify_agent_card

    payload = msg.payload or {}
    agent_card = payload.get("agent_card")
    verified_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if not agent_card or not isinstance(agent_card, dict):
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="credential_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="completed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            payload={
                "valid": False,
                "reason": "No agent_card provided in credential request payload",
                "verified_at": verified_at,
            },
        )

    is_valid = verify_agent_card(agent_card)

    return A2AMessageResponse(
        message_id=str(uuid.uuid4()),
        message_type="credential_response",
        sender_id=msg.recipient_id,
        recipient_id=msg.sender_id,
        status="completed",
        in_reply_to=msg.message_id,
        correlation_id=msg.correlation_id,
        payload={
            "valid": is_valid,
            "reason": "Agent card verified" if is_valid else "Agent card verification failed",
            "verified_at": verified_at,
        },
    )


# ============================================================================
# GET /agent-card — Sardis Agent Card for A2A Discovery
# ============================================================================

@public_router.get("/agent-card")
async def get_agent_card():
    """
    Return the Sardis agent card for A2A discovery.

    Other agents can use this to discover Sardis capabilities,
    supported tokens/chains, and API endpoints.
    """
    import os

    api_base = os.getenv("SARDIS_API_BASE_URL", "https://sardis-api-staging-ogq6bgc5rq-ue.a.run.app")

    return {
        "agent_id": "sardis-platform",
        "name": "Sardis Payment Agent",
        "version": "2.0.0",
        "description": "Sardis Payment OS - Secure AI payment infrastructure with policy guardrails",
        "operator": {
            "name": "Sardis",
            "url": "https://sardis.sh",
            "contact": "support@sardis.sh",
        },
        "capabilities": [
            "payment.execute",
            "payment.verify",
            "payment.refund",
            "mandate.ingest",
            "mandate.sign",
            "wallet.balance",
            "wallet.hold",
            "checkout.create",
            "checkout.complete",
            "x402.micropay",
        ],
        "payment": {
            "supported_tokens": ["USDC", "USDT", "EURC"],
            "supported_chains": ["base", "polygon", "ethereum", "arbitrum", "optimism", "tempo"],
            "min_amount_minor": 100,
            "max_amount_minor": 10_000_000,
            "ap2_compliant": True,
            "x402_compliant": True,
            "ucp_compliant": True,
        },
        "endpoints": {
            "api": {
                "url": f"{api_base}/api/v2",
                "protocol": "https",
                "auth_required": True,
                "auth_type": "bearer",
            },
            "a2a": {
                "url": f"{api_base}/api/v2/a2a",
                "protocol": "https",
                "auth_required": True,
                "auth_type": "signature",
            },
            "mcp": "npx @sardis/mcp-server start",
        },
        "a2a_protocol": {
            "version": "1.0",
            "supported_messages": [
                "payment_request",
                "payment_response",
                "credential_request",
                "credential_response",
                "ack",
            ],
            "pay_endpoint": f"{api_base}/api/v2/a2a/pay",
            "messages_endpoint": f"{api_base}/api/v2/a2a/messages",
        },
    }
