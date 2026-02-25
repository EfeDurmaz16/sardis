"""On-chain payment endpoints."""

from __future__ import annotations

import hashlib
from inspect import isawaitable
import json
import os
import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_api.middleware.agent_payment_rate_limit import enforce_agent_payment_rate_limit
from sardis_api.routers.metrics import record_policy_check, record_policy_denial_spike
from sardis_compliance.checks import ComplianceAuditEntry
from sardis_v2_core.mandates import PaymentMandate, VCProof
from sardis_v2_core.policy_attestation import build_policy_decision_receipt
from sardis_v2_core.tokens import TokenType, to_raw_token_amount

router = APIRouter()


class OnChainPaymentRequest(BaseModel):
    to: str
    amount: Decimal = Field(gt=0)
    token: str = "USDC"
    chain: str = "base"
    memo: Optional[str] = None
    rail: Optional[Literal["turnkey", "cdp"]] = Field(
        default=None,
        description="Execution rail override. If omitted, uses server default.",
    )
    cdp_wallet_id: Optional[str] = Field(
        default=None,
        description="Optional CDP wallet id override. Falls back to wallet.cdp_wallet_id.",
    )
    policy_hash: Optional[str] = Field(
        default=None,
        description="Optional expected policy hash pin. Execution fails on mismatch.",
    )
    policy_id: Optional[str] = Field(
        default=None,
        description="Optional expected policy id/version pin. Execution fails on mismatch.",
    )
    goal_drift_score: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Optional deterministic goal-drift score in [0,1] from caller-side verifier.",
    )
    goal_drift_reasons: list[str] = Field(
        default_factory=list,
        description="Optional structured drift reasons from external verifier.",
    )


class OnChainPaymentResponse(BaseModel):
    tx_hash: Optional[str] = None
    explorer_url: Optional[str] = None
    status: str = "submitted"
    approval_id: Optional[str] = None
    policy_hash: Optional[str] = None
    policy_audit_anchor: Optional[str] = None
    policy_audit_id: Optional[str] = None
    compliance_audit_id: Optional[str] = None


@dataclass
class OnChainPaymentDependencies:
    wallet_repo: Any
    agent_repo: Any
    chain_executor: Any
    policy_store: Any = None
    approval_service: Any = None
    sanctions_service: Any = None
    kya_service: Any = None
    coinbase_cdp_provider: Any = None
    default_on_chain_provider: Optional[str] = None
    audit_store: Any = None
    settings: Any = None


def get_deps() -> OnChainPaymentDependencies:
    raise NotImplementedError("must be overridden")


PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\s+(all\s+)?(previous|prior)\s+instructions\b", re.IGNORECASE),
    re.compile(r"\boverride\s+safety\b", re.IGNORECASE),
    re.compile(r"\bbypass\s+policy\b", re.IGNORECASE),
    re.compile(r"\bdisable\s+compliance\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"\b(do\s+not|don't)\s+enforce\s+(policy|compliance)\b", re.IGNORECASE),
)
KYT_REVIEW_DEFAULT = {"high", "severe"}


def _explorer_url(chain: str, tx_hash: str) -> Optional[str]:
    c = (chain or "").strip().lower()
    if c in {"base", "base-mainnet"}:
        return f"https://basescan.org/tx/{tx_hash}"
    if c in {"base_sepolia", "base-sepolia"}:
        return f"https://sepolia.basescan.org/tx/{tx_hash}"
    return None


async def _require_wallet_access(wallet: Any, principal: Principal, deps: OnChainPaymentDependencies) -> None:
    if principal.is_admin:
        return
    if deps.agent_repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="agent_repository_not_configured",
        )
    agent = await deps.agent_repo.get(wallet.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _contains_prompt_injection_signal(text: Optional[str]) -> Optional[str]:
    value = (text or "").strip()
    if not value:
        return None
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(value):
            return pattern.pattern
    return None


def _is_truthy_env(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _decimal_env(name: str, default: str) -> Decimal:
    raw = (os.getenv(name, default) or default).strip()
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _goal_drift_review_threshold() -> Decimal:
    value = _decimal_env("SARDIS_GOAL_DRIFT_REVIEW_THRESHOLD", "0.70")
    return min(max(value, Decimal("0")), Decimal("1"))


def _goal_drift_block_threshold() -> Decimal:
    value = _decimal_env("SARDIS_GOAL_DRIFT_BLOCK_THRESHOLD", "0.90")
    review = _goal_drift_review_threshold()
    value = min(max(value, Decimal("0")), Decimal("1"))
    return max(value, review)


def _kya_enforcement_enabled() -> bool:
    return _is_truthy_env(os.getenv("SARDIS_KYA_ENFORCEMENT_ENABLED", "false"))


def _kyt_review_levels() -> set[str]:
    raw = os.getenv("SARDIS_KYT_REVIEW_LEVELS", "high,severe")
    parsed = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return parsed or set(KYT_REVIEW_DEFAULT)


def _kyt_review_levels_for_org(organization_id: Optional[str]) -> set[str]:
    default_levels = _kyt_review_levels()
    org_id = (organization_id or "").strip()
    if not org_id:
        return default_levels

    raw = os.getenv("SARDIS_KYT_REVIEW_LEVELS_BY_ORG_JSON", "").strip()
    if not raw:
        return default_levels
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return default_levels
    if not isinstance(parsed, dict):
        return default_levels

    value = parsed.get(org_id)
    if value is None:
        return default_levels
    if isinstance(value, str):
        levels = {part.strip().lower() for part in value.split(",") if part.strip()}
    elif isinstance(value, list):
        levels = {str(part).strip().lower() for part in value if str(part).strip()}
    else:
        return default_levels
    return levels or default_levels


def _sanctions_risk_level(screening_result: Any) -> str:
    level = getattr(screening_result, "risk_level", None)
    level_value = getattr(level, "value", level)
    if level_value is None:
        return "unknown"
    return str(level_value).strip().lower()


def _risk_rank(level: str) -> int:
    order = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "severe": 4,
        "blocked": 5,
        "unknown": 0,
    }
    return order.get(level, 0)


def _try_build_policy_receipt(
    *,
    policy: Any,
    decision: str,
    reason: str,
    context: dict[str, Any],
) -> Optional[dict[str, Any]]:
    try:
        return build_policy_decision_receipt(
            policy=policy,
            decision=decision,
            reason=reason,
            context=context,
        ).to_dict()
    except Exception:
        return None


async def _append_policy_audit_entry(
    *,
    deps: OnChainPaymentDependencies,
    mandate_id: str,
    subject: str,
    allowed: bool,
    reason: str,
    receipt_payload: dict[str, Any],
) -> Optional[str]:
    if deps.audit_store is None:
        return None
    entry = ComplianceAuditEntry(
        mandate_id=mandate_id,
        subject=subject,
        allowed=allowed,
        reason=reason,
        rule_id=receipt_payload.get("policy_id"),
        provider="policy_engine",
        metadata=receipt_payload,
    )
    result = deps.audit_store.append(entry)
    if isawaitable(result):
        result = await result
    return str(result or entry.audit_id)


async def _append_compliance_audit_entry(
    *,
    deps: OnChainPaymentDependencies,
    mandate_id: str,
    subject: str,
    allowed: bool,
    reason: str,
    provider: str,
    rule_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    if deps.audit_store is None:
        return None
    entry = ComplianceAuditEntry(
        mandate_id=mandate_id,
        subject=subject,
        allowed=allowed,
        reason=reason,
        rule_id=rule_id,
        provider=provider,
        metadata=metadata or {},
    )
    result = deps.audit_store.append(entry)
    if isawaitable(result):
        result = await result
    return str(result or entry.audit_id)


@router.post("/{wallet_id}/pay/onchain", response_model=OnChainPaymentResponse, status_code=status.HTTP_200_OK)
async def pay_onchain(
    wallet_id: str,
    request: OnChainPaymentRequest,
    deps: OnChainPaymentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    await _require_wallet_access(wallet, principal, deps)
    await enforce_agent_payment_rate_limit(
        agent_id=wallet.agent_id,
        operation="wallets.pay_onchain",
        settings=deps.settings,
    )
    env_name = (os.getenv("SARDIS_ENVIRONMENT", "dev") or "dev").strip().lower()
    nonce = hashlib.sha256(
        f"{wallet_id}:{request.chain}:{request.token}:{request.to}:{request.amount}:{request.memo or ''}".encode()
    ).hexdigest()
    preflight_audit_id = f"onchain_preflight_{nonce[:16]}"
    source_address = wallet.get_address(request.chain) if hasattr(wallet, "get_address") else None

    # Policy enforcement gate (fail-closed in production when policy store missing).
    policy_receipt: Optional[dict[str, Any]] = None
    policy_audit_id: Optional[str] = None
    compliance_audit_id: Optional[str] = None
    requested_policy_hash = (request.policy_hash or "").strip() or None
    requested_policy_id = (request.policy_id or "").strip() or None
    policy_pin_requested = requested_policy_hash is not None or requested_policy_id is not None
    if deps.policy_store is None:
        if env_name in {"prod", "production"}:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="policy_store_not_configured",
            )
        if policy_pin_requested:
            deny_reason = "policy_pin_requires_active_policy"
            record_policy_check(False, deny_reason)
            record_policy_denial_spike(deny_reason)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=deny_reason,
            )
    else:
        policy = await deps.policy_store.fetch_policy(wallet.agent_id)
        if policy is not None:
            policy_receipt = _try_build_policy_receipt(
                policy=policy,
                decision="evaluate",
                reason="policy_evaluation_started",
                context={
                    "wallet_id": wallet_id,
                    "agent_id": wallet.agent_id,
                    "destination": request.to,
                    "amount": str(request.amount),
                    "token": request.token,
                    "chain": request.chain,
                },
            )
            if policy_pin_requested and policy_receipt is None:
                deny_reason = "policy_pin_attestation_unavailable"
                record_policy_check(False, deny_reason)
                record_policy_denial_spike(deny_reason)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=deny_reason,
                )
            if requested_policy_hash and policy_receipt is not None:
                actual_hash = str(policy_receipt.get("policy_hash", ""))
                if actual_hash != requested_policy_hash:
                    deny_reason = "policy_hash_mismatch"
                    record_policy_check(False, deny_reason)
                    record_policy_denial_spike(deny_reason)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=deny_reason,
                    )
            if requested_policy_id and policy_receipt is not None:
                actual_policy_id = str(policy_receipt.get("policy_id", ""))
                if actual_policy_id != requested_policy_id:
                    deny_reason = "policy_id_mismatch"
                    record_policy_check(False, deny_reason)
                    record_policy_denial_spike(deny_reason)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=deny_reason,
                    )
            allowed, reason = policy.validate_payment(
                amount=request.amount,
                fee=Decimal("0"),
                merchant_id=request.to,
                mcc_code=None,
                merchant_category="onchain_transfer",
                drift_score=request.goal_drift_score,
            )
            if not allowed:
                deny_reason = reason or "spending_policy_denied"
                if deny_reason == "goal_drift_exceeded" and deps.approval_service is not None:
                    if policy_receipt is not None:
                        policy_receipt["decision"] = "pending_approval"
                        policy_receipt["reason"] = "goal_drift_exceeded"
                        policy_receipt.setdefault("context", {})["goal_drift_score"] = (
                            str(request.goal_drift_score) if request.goal_drift_score is not None else None
                        )
                        policy_receipt["context"]["goal_drift_reasons"] = request.goal_drift_reasons
                        policy_audit_id = await _append_policy_audit_entry(
                            deps=deps,
                            mandate_id=policy_receipt["decision_id"],
                            subject=wallet.agent_id,
                            allowed=False,
                            reason=policy_receipt["reason"],
                            receipt_payload=policy_receipt,
                        )
                    approval = await deps.approval_service.create_approval(
                        action="onchain_payment",
                        requested_by=wallet.agent_id,
                        agent_id=wallet.agent_id,
                        wallet_id=wallet.wallet_id,
                        vendor=request.to,
                        amount=request.amount,
                        purpose="On-chain payment",
                        reason="goal_drift_exceeded",
                        urgency="high",
                        organization_id=principal.organization_id,
                        metadata={
                            "wallet_id": wallet_id,
                            "token": request.token,
                            "chain": request.chain,
                            "rail": request.rail,
                            "memo": request.memo,
                            "goal_drift_score": str(request.goal_drift_score) if request.goal_drift_score is not None else None,
                            "goal_drift_reasons": request.goal_drift_reasons,
                        },
                    )
                    return OnChainPaymentResponse(
                        tx_hash=None,
                        explorer_url=None,
                        status="pending_approval",
                        approval_id=approval.id,
                        policy_hash=policy_receipt["policy_hash"] if policy_receipt else None,
                        policy_audit_anchor=policy_receipt["audit_anchor"] if policy_receipt else None,
                        policy_audit_id=policy_audit_id,
                        compliance_audit_id=compliance_audit_id,
                    )
                record_policy_check(False, deny_reason)
                record_policy_denial_spike(deny_reason)
                if policy_receipt is not None:
                    policy_receipt["decision"] = "deny"
                    policy_receipt["reason"] = deny_reason
                    policy_audit_id = await _append_policy_audit_entry(
                        deps=deps,
                        mandate_id=policy_receipt["decision_id"],
                        subject=wallet.agent_id,
                        allowed=False,
                        reason=policy_receipt["reason"],
                        receipt_payload=policy_receipt,
                    )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=deny_reason,
                )
            if hasattr(policy, "validate_execution_context"):
                rails_ok, rails_reason = policy.validate_execution_context(
                    destination=request.to,
                    chain=request.chain,
                    token=request.token,
                )
                if not rails_ok:
                    deny_reason = rails_reason or "execution_context_denied"
                    record_policy_check(False, deny_reason)
                    record_policy_denial_spike(deny_reason)
                    if policy_receipt is not None:
                        policy_receipt["decision"] = "deny"
                        policy_receipt["reason"] = deny_reason
                        policy_audit_id = await _append_policy_audit_entry(
                            deps=deps,
                            mandate_id=policy_receipt["decision_id"],
                            subject=wallet.agent_id,
                            allowed=False,
                            reason=policy_receipt["reason"],
                            receipt_payload=policy_receipt,
                        )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=deny_reason,
                    )
            if reason == "requires_approval":
                if deps.approval_service is not None:
                    if policy_receipt is not None:
                        policy_receipt["decision"] = "pending_approval"
                        policy_receipt["reason"] = "policy_requires_approval"
                        policy_audit_id = await _append_policy_audit_entry(
                            deps=deps,
                            mandate_id=policy_receipt["decision_id"],
                            subject=wallet.agent_id,
                            allowed=False,
                            reason=policy_receipt["reason"],
                            receipt_payload=policy_receipt,
                        )
                    approval = await deps.approval_service.create_approval(
                        action="onchain_payment",
                        requested_by=wallet.agent_id,
                        agent_id=wallet.agent_id,
                        wallet_id=wallet.wallet_id,
                        vendor=request.to,
                        amount=request.amount,
                        purpose="On-chain payment",
                        reason="policy_requires_approval",
                        urgency="medium",
                        organization_id=principal.organization_id,
                        metadata={
                            "wallet_id": wallet_id,
                            "token": request.token,
                            "chain": request.chain,
                            "rail": request.rail,
                            "memo": request.memo,
                        },
                    )
                    return OnChainPaymentResponse(
                        tx_hash=None,
                        explorer_url=None,
                        status="pending_approval",
                        approval_id=approval.id,
                        policy_hash=policy_receipt["policy_hash"] if policy_receipt else None,
                        policy_audit_anchor=policy_receipt["audit_anchor"] if policy_receipt else None,
                        policy_audit_id=policy_audit_id,
                        compliance_audit_id=compliance_audit_id,
                    )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="requires_approval",
                )
            record_policy_check(True)
        elif policy_pin_requested:
            deny_reason = "policy_pin_requires_active_policy"
            record_policy_check(False, deny_reason)
            record_policy_denial_spike(deny_reason)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=deny_reason,
            )

    # Prompt-injection guard for agent-provided memo/input strings.
    if os.getenv("SARDIS_PROMPT_INJECTION_GUARD_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}:
        match = _contains_prompt_injection_signal(request.memo)
        if match:
            if deps.approval_service is not None:
                approval = await deps.approval_service.create_approval(
                    action="onchain_payment",
                    requested_by=wallet.agent_id,
                    agent_id=wallet.agent_id,
                    wallet_id=wallet.wallet_id,
                    vendor=request.to,
                    amount=request.amount,
                    purpose="On-chain payment",
                    reason=f"prompt_injection_signal_detected:{match}",
                    urgency="high",
                    organization_id=principal.organization_id,
                    metadata={
                        "wallet_id": wallet_id,
                        "token": request.token,
                        "chain": request.chain,
                        "rail": request.rail,
                        "memo": request.memo,
                    },
                )
                return OnChainPaymentResponse(
                    tx_hash=None,
                    explorer_url=None,
                    status="pending_approval",
                    approval_id=approval.id,
                    policy_hash=policy_receipt["policy_hash"] if policy_receipt else None,
                    policy_audit_anchor=policy_receipt["audit_anchor"] if policy_receipt else None,
                    policy_audit_id=policy_audit_id,
                    compliance_audit_id=compliance_audit_id,
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="prompt_injection_signal_detected",
            )

    # Runtime goal-drift guard: advisory model output cannot bypass deterministic controls.
    drift_score = request.goal_drift_score
    if drift_score is not None:
        review_threshold = _goal_drift_review_threshold()
        block_threshold = _goal_drift_block_threshold()
        if drift_score >= block_threshold:
            deny_reason = "goal_drift_blocked"
            record_policy_check(False, deny_reason)
            record_policy_denial_spike(deny_reason)
            if policy_receipt is not None:
                policy_receipt["decision"] = "deny"
                policy_receipt["reason"] = deny_reason
                policy_receipt.setdefault("context", {})["goal_drift_score"] = str(drift_score)
                policy_receipt["context"]["goal_drift_reasons"] = request.goal_drift_reasons
                policy_audit_id = await _append_policy_audit_entry(
                    deps=deps,
                    mandate_id=policy_receipt["decision_id"],
                    subject=wallet.agent_id,
                    allowed=False,
                    reason=policy_receipt["reason"],
                    receipt_payload=policy_receipt,
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=deny_reason,
            )
        if drift_score >= review_threshold:
            if deps.approval_service is not None:
                if policy_receipt is not None:
                    policy_receipt["decision"] = "pending_approval"
                    policy_receipt["reason"] = "goal_drift_review_required"
                    policy_receipt.setdefault("context", {})["goal_drift_score"] = str(drift_score)
                    policy_receipt["context"]["goal_drift_reasons"] = request.goal_drift_reasons
                    policy_audit_id = await _append_policy_audit_entry(
                        deps=deps,
                        mandate_id=policy_receipt["decision_id"],
                        subject=wallet.agent_id,
                        allowed=False,
                        reason=policy_receipt["reason"],
                        receipt_payload=policy_receipt,
                    )
                approval = await deps.approval_service.create_approval(
                    action="onchain_payment",
                    requested_by=wallet.agent_id,
                    agent_id=wallet.agent_id,
                    wallet_id=wallet.wallet_id,
                    vendor=request.to,
                    amount=request.amount,
                    purpose="On-chain payment",
                    reason=f"goal_drift_review_required:{drift_score}",
                    urgency="high",
                    organization_id=principal.organization_id,
                    metadata={
                        "wallet_id": wallet_id,
                        "token": request.token,
                        "chain": request.chain,
                        "rail": request.rail,
                        "memo": request.memo,
                        "goal_drift_score": str(drift_score),
                        "goal_drift_reasons": request.goal_drift_reasons,
                        "goal_drift_review_threshold": str(review_threshold),
                        "goal_drift_block_threshold": str(block_threshold),
                    },
                )
                return OnChainPaymentResponse(
                    tx_hash=None,
                    explorer_url=None,
                    status="pending_approval",
                    approval_id=approval.id,
                    policy_hash=policy_receipt["policy_hash"] if policy_receipt else None,
                    policy_audit_anchor=policy_receipt["audit_anchor"] if policy_receipt else None,
                    policy_audit_id=policy_audit_id,
                    compliance_audit_id=compliance_audit_id,
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="goal_drift_review_required",
            )

    if _kya_enforcement_enabled():
        if deps.kya_service is None:
            if env_name in {"prod", "production"}:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="kya_service_not_configured",
                )
        else:
            try:
                from sardis_compliance.kya import KYACheckRequest

                kya_result = await deps.kya_service.check_agent(
                    KYACheckRequest(
                        agent_id=wallet.agent_id,
                        amount=request.amount,
                        merchant_id=request.to,
                    )
                )
                if not getattr(kya_result, "allowed", False):
                    compliance_audit_id = await _append_compliance_audit_entry(
                        deps=deps,
                        mandate_id=preflight_audit_id,
                        subject=wallet.agent_id,
                        allowed=False,
                        reason="kya_denied",
                        provider="sardis_kya",
                        rule_id=getattr(kya_result, "reason", None) or "kya_verification",
                        metadata={
                            "wallet_id": wallet_id,
                            "destination": request.to,
                            "amount": str(request.amount),
                            "token": request.token,
                            "chain": request.chain,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="kya_denied",
                    )
            except HTTPException:
                raise
            except Exception as exc:
                compliance_audit_id = await _append_compliance_audit_entry(
                    deps=deps,
                    mandate_id=preflight_audit_id,
                    subject=wallet.agent_id,
                    allowed=False,
                    reason="kya_service_error",
                    provider="sardis_kya",
                    rule_id="kya_verification",
                    metadata={
                        "error": str(exc),
                        "wallet_id": wallet_id,
                        "destination": request.to,
                        "amount": str(request.amount),
                        "token": request.token,
                        "chain": request.chain,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="kya_service_error",
                ) from exc

    if deps.sanctions_service is None:
        if env_name in {"prod", "production"}:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="sanctions_service_not_configured",
            )
    else:
        try:
            screenings: list[tuple[str, Any]] = []
            destination_screening = await deps.sanctions_service.screen_address(request.to, chain=request.chain)
            screenings.append((request.to, destination_screening))
            if source_address and source_address.lower() != request.to.lower():
                source_screening = await deps.sanctions_service.screen_address(source_address, chain=request.chain)
                screenings.append((source_address, source_screening))

            highest_risk_level = "unknown"
            highest_risk_result: Any = None
            for screened_address, screen in screenings:
                if getattr(screen, "should_block", False):
                    compliance_audit_id = await _append_compliance_audit_entry(
                        deps=deps,
                        mandate_id=preflight_audit_id,
                        subject=wallet.agent_id,
                        allowed=False,
                        reason="sanctions_hit",
                        provider=getattr(screen, "provider", None) or "sanctions",
                        rule_id=getattr(screen, "reason", None) or "sanctions_screening",
                        metadata={
                            "wallet_id": wallet_id,
                            "screened_address": screened_address,
                            "source_address": source_address,
                            "destination": request.to,
                            "amount": str(request.amount),
                            "token": request.token,
                            "chain": request.chain,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="sanctions_hit",
                    )
                risk_level = _sanctions_risk_level(screen)
                if _risk_rank(risk_level) > _risk_rank(highest_risk_level):
                    highest_risk_level = risk_level
                    highest_risk_result = screen

            if highest_risk_level in _kyt_review_levels_for_org(principal.organization_id):
                compliance_audit_id = await _append_compliance_audit_entry(
                    deps=deps,
                    mandate_id=preflight_audit_id,
                    subject=wallet.agent_id,
                    allowed=False,
                    reason="kyt_review_required",
                    provider=getattr(highest_risk_result, "provider", None) or "sanctions",
                    rule_id=f"kyt_risk:{highest_risk_level}",
                    metadata={
                        "wallet_id": wallet_id,
                        "source_address": source_address,
                        "destination": request.to,
                        "risk_level": highest_risk_level,
                        "risk_reason": getattr(highest_risk_result, "reason", None),
                        "amount": str(request.amount),
                        "token": request.token,
                        "chain": request.chain,
                    },
                )
                if deps.approval_service is not None:
                    approval = await deps.approval_service.create_approval(
                        action="onchain_payment",
                        requested_by=wallet.agent_id,
                        agent_id=wallet.agent_id,
                        wallet_id=wallet.wallet_id,
                        vendor=request.to,
                        amount=request.amount,
                        purpose="On-chain payment",
                        reason=f"kyt_review_required:risk={highest_risk_level}",
                        urgency="high",
                        organization_id=principal.organization_id,
                        metadata={
                            "wallet_id": wallet_id,
                            "token": request.token,
                            "chain": request.chain,
                            "rail": request.rail,
                            "memo": request.memo,
                            "source_address": source_address,
                            "risk_level": highest_risk_level,
                            "risk_reason": getattr(highest_risk_result, "reason", None),
                        },
                    )
                    return OnChainPaymentResponse(
                        tx_hash=None,
                        explorer_url=None,
                        status="pending_approval",
                        approval_id=approval.id,
                        policy_hash=policy_receipt["policy_hash"] if policy_receipt else None,
                        policy_audit_anchor=policy_receipt["audit_anchor"] if policy_receipt else None,
                        policy_audit_id=policy_audit_id,
                        compliance_audit_id=compliance_audit_id,
                    )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="kyt_review_required",
                )

            compliance_audit_id = await _append_compliance_audit_entry(
                deps=deps,
                mandate_id=preflight_audit_id,
                subject=wallet.agent_id,
                allowed=True,
                reason="kyt_passed",
                provider=getattr(highest_risk_result, "provider", None) or "sanctions",
                rule_id=f"kyt_risk:{highest_risk_level}",
                metadata={
                    "wallet_id": wallet_id,
                    "source_address": source_address,
                    "destination": request.to,
                    "risk_level": highest_risk_level,
                    "amount": str(request.amount),
                    "token": request.token,
                    "chain": request.chain,
                },
            )
        except HTTPException:
            raise
        except Exception as exc:
            compliance_audit_id = await _append_compliance_audit_entry(
                deps=deps,
                mandate_id=preflight_audit_id,
                subject=wallet.agent_id,
                allowed=False,
                reason="sanctions_service_error",
                provider="sanctions",
                rule_id="sanctions_service_error",
                metadata={
                    "wallet_id": wallet_id,
                    "source_address": source_address,
                    "destination": request.to,
                    "amount": str(request.amount),
                    "token": request.token,
                    "chain": request.chain,
                    "error": str(exc),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="sanctions_service_error",
            ) from exc

    use_cdp_rail = False
    if request.rail:
        use_cdp_rail = request.rail == "cdp"
    elif deps.default_on_chain_provider == "coinbase_cdp":
        use_cdp_rail = True

    if use_cdp_rail:
        if request.token.upper() != "USDC":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cdp_rail_only_supports_usdc",
            )
        if not deps.coinbase_cdp_provider:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="coinbase_cdp_not_configured",
            )
        cdp_wallet_id = request.cdp_wallet_id or getattr(wallet, "cdp_wallet_id", None)
        if not cdp_wallet_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cdp_wallet_id_required",
            )
        try:
            tx_hash = await deps.coinbase_cdp_provider.send_usdc(
                cdp_wallet_id=cdp_wallet_id,
                to_address=request.to,
                amount_usdc=request.amount,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"cdp_payment_failed: {exc}",
            ) from exc
        return OnChainPaymentResponse(
            tx_hash=tx_hash,
            explorer_url=_explorer_url(request.chain, tx_hash),
            status="submitted",
            policy_hash=policy_receipt["policy_hash"] if policy_receipt else None,
            policy_audit_anchor=policy_receipt["audit_anchor"] if policy_receipt else None,
            policy_audit_id=policy_audit_id,
            compliance_audit_id=compliance_audit_id,
        )

    source_address = source_address or (
        wallet.get_address(request.chain) if hasattr(wallet, "get_address") else None
    )
    if not source_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No address for chain {request.chain}",
        )

    try:
        amount_minor = to_raw_token_amount(TokenType(request.token.upper()), request.amount)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported_token: {request.token}",
        ) from exc

    mandate = PaymentMandate(
        mandate_id=f"onchain_{nonce[:16]}",
        mandate_type="payment",
        issuer=f"wallet:{wallet_id}",
        subject=wallet.agent_id,
        expires_at=int(time.time()) + 300,
        nonce=nonce,
        proof=VCProof(
            verification_method=f"wallet:{wallet_id}#key-1",
            created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            proof_value="onchain-payment",
        ),
        domain="sardis.sh",
        purpose="checkout",
        chain=request.chain,
        token=request.token.upper(),
        amount_minor=amount_minor,
        destination=request.to,
        audit_hash=hashlib.sha256(
            f"{wallet_id}:{request.to}:{amount_minor}:{request.chain}:{request.memo or ''}".encode()
        ).hexdigest(),
        wallet_id=wallet_id,
        account_type=wallet.account_type,
        smart_account_address=wallet.smart_account_address,
        merchant_domain=request.memo or "onchain",
    )

    if not deps.chain_executor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="chain_executor_not_configured",
        )
    try:
        receipt = await deps.chain_executor.dispatch_payment(mandate)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"onchain_payment_failed: {exc}",
        ) from exc

    if policy_receipt is not None:
        policy_receipt["decision"] = "allow"
        policy_receipt["reason"] = "executed"
        policy_receipt["context"]["mandate_id"] = mandate.mandate_id
        policy_receipt["context"]["destination"] = request.to
        policy_audit_id = await _append_policy_audit_entry(
            deps=deps,
            mandate_id=mandate.mandate_id,
            subject=wallet.agent_id,
            allowed=True,
            reason="executed",
            receipt_payload=policy_receipt,
        )

    tx_hash = receipt.tx_hash if hasattr(receipt, "tx_hash") else str(receipt)
    return OnChainPaymentResponse(
        tx_hash=tx_hash,
        explorer_url=_explorer_url(request.chain, tx_hash),
        status="submitted",
        policy_hash=policy_receipt["policy_hash"] if policy_receipt else None,
        policy_audit_anchor=policy_receipt["audit_anchor"] if policy_receipt else None,
        policy_audit_id=policy_audit_id,
        compliance_audit_id=compliance_audit_id,
    )
