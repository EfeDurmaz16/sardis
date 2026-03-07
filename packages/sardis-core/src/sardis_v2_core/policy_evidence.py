"""Policy decision evidence — complete audit trail for every evaluate() call.

Every policy evaluation produces a signed evidence bundle containing:
- Each check step with pass/fail, details, and timing
- Link to the policy version that was in effect
- SHA-256 evidence hash for tamper detection

Required for SOC 2 compliance and enterprise audit requirements.

Usage:
    result, evidence = await evaluate_with_evidence(policy, wallet, amount, ...)
    bundle = export_evidence_bundle(evidence)
    # Store or send to auditor
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional


def _nanoid() -> str:
    return f"dec_{uuid.uuid4().hex[:16]}"


@dataclass(slots=True)
class PolicyStepResult:
    """Result of a single policy check step."""
    step_number: int
    step_name: str
    passed: bool
    details: dict[str, Any]
    duration_ms: float


@dataclass(slots=True)
class PolicyDecisionLog:
    """Complete evidence bundle for a policy evaluation."""
    decision_id: str
    agent_id: str
    mandate_id: Optional[str]
    timestamp: datetime
    policy_version_id: Optional[str]
    steps: list[PolicyStepResult]
    final_verdict: str  # "approved" | "denied" | "escalated"
    evidence_hash: str
    group_hierarchy_applied: Optional[list[str]] = None


def compute_evidence_hash(steps: list[PolicyStepResult]) -> str:
    """SHA-256 of canonical JSON of all step results."""
    payload = [
        {
            "step_number": s.step_number,
            "step_name": s.step_name,
            "passed": s.passed,
            "details": s.details,
            "duration_ms": round(s.duration_ms, 3),
        }
        for s in steps
    ]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def evaluate_with_evidence(
    policy: Any,
    wallet: Any,
    amount: Decimal,
    fee: Decimal,
    *,
    chain: str,
    token: Any,
    merchant_id: Optional[str] = None,
    merchant_category: Optional[str] = None,
    mcc_code: Optional[str] = None,
    scope: Any = None,
    rpc_client: Any = None,
    drift_score: Optional[Decimal] = None,
    policy_store: Any = None,
    kya_client: Any = None,
    mandate_id: Optional[str] = None,
    policy_version_id: Optional[str] = None,
    group_hierarchy: Optional[list[str]] = None,
) -> tuple[tuple[bool, str], PolicyDecisionLog]:
    """Evaluate policy and capture step-by-step evidence.

    Wraps SpendingPolicy.evaluate() with timing and evidence collection
    for each of the 11 check steps.

    Returns:
        ((approved, reason), PolicyDecisionLog)
    """
    from .spending_policy import SpendingScope

    if scope is None:
        scope = SpendingScope.ALL

    steps: list[PolicyStepResult] = []
    total_cost = amount + fee

    # Step 1: Amount validation
    t0 = time.perf_counter()
    if amount <= 0:
        steps.append(PolicyStepResult(1, "amount_validation", False, {"reason": "amount_must_be_positive"}, _ms(t0)))
        return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, "amount_must_be_positive")
    if fee < 0:
        steps.append(PolicyStepResult(1, "amount_validation", False, {"reason": "fee_must_be_non_negative"}, _ms(t0)))
        return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, "fee_must_be_non_negative")
    steps.append(PolicyStepResult(1, "amount_validation", True, {"amount": str(amount), "fee": str(fee)}, _ms(t0)))

    # Step 2: Scope check
    t0 = time.perf_counter()
    if SpendingScope.ALL not in policy.allowed_scopes and scope not in policy.allowed_scopes:
        steps.append(PolicyStepResult(2, "scope_check", False, {"scope": str(scope)}, _ms(t0)))
        return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, "scope_not_allowed")
    steps.append(PolicyStepResult(2, "scope_check", True, {"scope": str(scope)}, _ms(t0)))

    # Step 3: MCC check
    t0 = time.perf_counter()
    if mcc_code:
        mcc_ok, mcc_reason = policy._check_mcc_policy(mcc_code)
        if not mcc_ok:
            steps.append(PolicyStepResult(3, "mcc_check", False, {"mcc_code": mcc_code, "reason": mcc_reason}, _ms(t0)))
            return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, mcc_reason)
    steps.append(PolicyStepResult(3, "mcc_check", True, {"mcc_code": mcc_code}, _ms(t0)))

    # Step 4: Per-transaction limit
    t0 = time.perf_counter()
    effective_per_tx = policy._get_effective_per_tx_limit(mcc_code, merchant_category)
    if total_cost > effective_per_tx:
        steps.append(PolicyStepResult(4, "per_tx_limit", False, {"total_cost": str(total_cost), "limit": str(effective_per_tx)}, _ms(t0)))
        return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, "per_transaction_limit")
    steps.append(PolicyStepResult(4, "per_tx_limit", True, {"total_cost": str(total_cost), "limit": str(effective_per_tx)}, _ms(t0)))

    # Step 5: Total limit
    t0 = time.perf_counter()
    if policy.spent_total + total_cost > policy.limit_total:
        steps.append(PolicyStepResult(5, "total_limit", False, {"spent": str(policy.spent_total), "limit": str(policy.limit_total)}, _ms(t0)))
        return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, "total_limit_exceeded")
    steps.append(PolicyStepResult(5, "total_limit", True, {"spent": str(policy.spent_total), "limit": str(policy.limit_total)}, _ms(t0)))

    # Step 6: Time-window limits
    t0 = time.perf_counter()
    window_details = {}
    for window_limit in filter(None, [policy.daily_limit, policy.weekly_limit, policy.monthly_limit]):
        ok, reason = window_limit.can_spend(total_cost)
        window_details[window_limit.window_type] = {"ok": ok, "remaining": str(window_limit.remaining())}
        if not ok:
            steps.append(PolicyStepResult(6, "time_window_limits", False, window_details, _ms(t0)))
            return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, reason)
    steps.append(PolicyStepResult(6, "time_window_limits", True, window_details, _ms(t0)))

    # Step 7: On-chain balance (skip in evidence mode without rpc_client)
    t0 = time.perf_counter()
    if rpc_client:
        try:
            balance = await wallet.get_balance(chain, token, rpc_client)
            if balance < total_cost:
                steps.append(PolicyStepResult(7, "onchain_balance", False, {"balance": str(balance)}, _ms(t0)))
                return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, "insufficient_balance")
            steps.append(PolicyStepResult(7, "onchain_balance", True, {"balance": str(balance)}, _ms(t0)))
        except Exception as e:
            steps.append(PolicyStepResult(7, "onchain_balance", True, {"skipped": str(e)}, _ms(t0)))
    else:
        steps.append(PolicyStepResult(7, "onchain_balance", True, {"skipped": "no_rpc_client"}, _ms(t0)))

    # Step 8: Merchant rules
    t0 = time.perf_counter()
    if merchant_id:
        merchant_ok, merchant_reason = policy._check_merchant_rules(merchant_id, merchant_category, amount)
        if not merchant_ok:
            steps.append(PolicyStepResult(8, "merchant_rules", False, {"merchant_id": merchant_id, "reason": merchant_reason}, _ms(t0)))
            return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, merchant_reason)
    steps.append(PolicyStepResult(8, "merchant_rules", True, {"merchant_id": merchant_id}, _ms(t0)))

    # Step 9: Goal drift
    t0 = time.perf_counter()
    if drift_score is not None and policy.max_drift_score is not None:
        if drift_score > policy.max_drift_score:
            steps.append(PolicyStepResult(9, "goal_drift", False, {"score": str(drift_score), "max": str(policy.max_drift_score)}, _ms(t0)))
            return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, "goal_drift_exceeded")
    steps.append(PolicyStepResult(9, "goal_drift", True, {"score": str(drift_score)}, _ms(t0)))

    # Step 10: Approval threshold
    t0 = time.perf_counter()
    if policy.approval_threshold is not None and amount > policy.approval_threshold:
        steps.append(PolicyStepResult(10, "approval_threshold", True, {"amount": str(amount), "threshold": str(policy.approval_threshold), "requires_approval": True}, _ms(t0)))
        return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, True, "requires_approval")
    steps.append(PolicyStepResult(10, "approval_threshold", True, {"requires_approval": False}, _ms(t0)))

    # Step 11: KYA attestation
    t0 = time.perf_counter()
    from .spending_policy import TrustLevel
    if kya_client and policy.trust_level in (TrustLevel.MEDIUM, TrustLevel.HIGH):
        try:
            kya_ok, kya_reason = await policy._check_kya_attestation(wallet, kya_client)
            if not kya_ok:
                steps.append(PolicyStepResult(11, "kya_attestation", False, {"reason": kya_reason}, _ms(t0)))
                return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, kya_reason)
        except Exception as e:
            steps.append(PolicyStepResult(11, "kya_attestation", False, {"error": str(e)}, _ms(t0)))
            return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, False, "kya_verification_failed")
    steps.append(PolicyStepResult(11, "kya_attestation", True, {"skipped": kya_client is None}, _ms(t0)))

    return _finalize(steps, policy, mandate_id, policy_version_id, group_hierarchy, True, "OK")


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


def _finalize(
    steps: list[PolicyStepResult],
    policy: Any,
    mandate_id: Optional[str],
    policy_version_id: Optional[str],
    group_hierarchy: Optional[list[str]],
    approved: bool,
    reason: str,
) -> tuple[tuple[bool, str], PolicyDecisionLog]:
    if reason == "requires_approval":
        verdict = "escalated"
    elif approved:
        verdict = "approved"
    else:
        verdict = "denied"

    evidence_hash = compute_evidence_hash(steps)

    log = PolicyDecisionLog(
        decision_id=_nanoid(),
        agent_id=policy.agent_id,
        mandate_id=mandate_id,
        timestamp=datetime.now(timezone.utc),
        policy_version_id=policy_version_id,
        steps=steps,
        final_verdict=verdict,
        evidence_hash=evidence_hash,
        group_hierarchy_applied=group_hierarchy,
    )

    return (approved, reason), log


def export_evidence_bundle(decision_log: PolicyDecisionLog) -> dict[str, Any]:
    """Serialize a PolicyDecisionLog to a portable JSON dict."""
    return {
        "decision_id": decision_log.decision_id,
        "agent_id": decision_log.agent_id,
        "mandate_id": decision_log.mandate_id,
        "timestamp": decision_log.timestamp.isoformat(),
        "policy_version_id": decision_log.policy_version_id,
        "final_verdict": decision_log.final_verdict,
        "evidence_hash": decision_log.evidence_hash,
        "group_hierarchy_applied": decision_log.group_hierarchy_applied,
        "steps": [
            {
                "step_number": s.step_number,
                "step_name": s.step_name,
                "passed": s.passed,
                "details": s.details,
                "duration_ms": round(s.duration_ms, 3),
            }
            for s in decision_log.steps
        ],
    }
