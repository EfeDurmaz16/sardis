"""AP2 payment execution endpoints with compliance enforcement."""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, replace
from decimal import Decimal
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request

from sardis_compliance.checks import ComplianceAuditEntry
from sardis_protocol.schemas import AP2PaymentExecuteRequest, AP2PaymentExecuteResponse
from sardis_v2_core.orchestrator import PaymentExecutionError
from sardis_v2_core.mandates import MandateChain
from sardis_v2_core.policy_attestation import build_policy_decision_receipt
from sardis_v2_core.transactions import validate_wallet_not_frozen

from sardis_api.authz import Principal, require_principal
from sardis_api.execution_mode import enforce_staging_live_guard, get_pilot_execution_policy
from sardis_api.middleware.agent_payment_rate_limit import enforce_agent_payment_rate_limit
from sardis_v2_core import AgentRepository
from sardis_api.idempotency import run_idempotent

if TYPE_CHECKING:
    from sardis_protocol.verifier import MandateVerifier
    from sardis_v2_core.orchestrator import PaymentOrchestrator
    from sardis_compliance.kyc import KYCService
    from sardis_compliance.sanctions import SanctionsService
    from sardis_v2_core.wallet_repository import WalletRepository
    from sardis_v2_core.approval_service import ApprovalService
    from sardis_v2_core.spending_policy import SpendingPolicy

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])

# KYC thresholds (amounts in minor units - cents for USD)
KYC_THRESHOLD_MINOR = 100000  # $1000 requires KYC
HIGH_VALUE_THRESHOLD_MINOR = 1000000  # $10000 enhanced verification
KYT_REVIEW_DEFAULT = {"high", "severe"}
PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\s+previous\s+instructions\b", re.IGNORECASE),
    re.compile(r"\boverride\s+safety\b", re.IGNORECASE),
    re.compile(r"\bbypass\s+policy\b", re.IGNORECASE),
    re.compile(r"\bdisable\s+compliance\b", re.IGNORECASE),
    re.compile(r"\bsystem\s+prompt\b", re.IGNORECASE),
    re.compile(r"\bdeveloper\s+mode\b", re.IGNORECASE),
)


@dataclass
class Dependencies:
    verifier: "MandateVerifier"
    orchestrator: "PaymentOrchestrator"
    wallet_repo: "WalletRepository"
    agent_repo: AgentRepository
    kyc_service: Optional["KYCService"] = None
    kya_service: Optional[Any] = None
    sanctions_service: Optional["SanctionsService"] = None
    approval_service: Optional["ApprovalService"] = None
    settings: Optional[object] = None
    wallet_manager: Optional[Any] = None
    policy_store: Optional[Any] = None
    audit_store: Optional[Any] = None


def get_deps() -> Dependencies:
    raise NotImplementedError("Dependency override required")


@dataclass
class ComplianceCheckResult:
    """Result of compliance checks."""
    passed: bool
    kya_verified: bool = False
    kyc_verified: bool = False
    sanctions_clear: bool = True
    kyt_review_required: bool = False
    kyt_risk_level: Optional[str] = None
    kyt_reason: Optional[str] = None
    reason: Optional[str] = None
    provider: Optional[str] = None
    rule: Optional[str] = None


def _is_truthy_env(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
        logger.warning("Invalid SARDIS_KYT_REVIEW_LEVELS_BY_ORG_JSON; using global defaults")
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


async def _compliance_checks_impl(
    deps: Dependencies,
    agent_id: str,
    destination: str,
    chain: str,
    amount_minor: int,
    source_address: Optional[str] = None,
    token: str = "USDC",
    organization_id: Optional[str] = None,
) -> ComplianceCheckResult:
    """
    Perform all compliance checks for a payment.
    
    Checks:
    1. KYC status for high-value transactions
    2. Sanctions screening for sender and recipient addresses
    """
    result = ComplianceCheckResult(passed=True)
    env_name = (os.getenv("SARDIS_ENVIRONMENT", "dev") or "dev").strip().lower()

    # Check KYA for agent-level constraints if explicitly enabled.
    if _kya_enforcement_enabled():
        if deps.kya_service is None:
            if env_name in {"prod", "production"}:
                result.passed = False
                result.reason = "kya_service_not_configured"
                result.provider = "sardis_kya"
                result.rule = "kya_configuration"
                return result
        else:
            try:
                from sardis_compliance.kya import KYACheckRequest

                amount_decimal = Decimal(str(amount_minor)) / Decimal("100")
                kya_result = await deps.kya_service.check_agent(
                    KYACheckRequest(
                        agent_id=agent_id,
                        amount=amount_decimal,
                        merchant_id=destination,
                    )
                )
                if not getattr(kya_result, "allowed", False):
                    result.passed = False
                    result.reason = "kya_denied"
                    result.provider = "sardis_kya"
                    result.rule = getattr(kya_result, "reason", None) or "kya_verification"
                    return result
                result.kya_verified = True
            except Exception as e:
                logger.error("KYA check failed for agent %s: %s", agent_id, e)
                result.passed = False
                result.reason = "kya_service_error"
                result.provider = "sardis_kya"
                result.rule = "kya_verification"
                return result
    
    # Check KYC for high-value transactions
    if deps.kyc_service and amount_minor >= KYC_THRESHOLD_MINOR:
        try:
            kyc = await deps.kyc_service.check_verification(agent_id)
            kyc_status = getattr(getattr(kyc, "status", None), "value", getattr(kyc, "status", None))

            if kyc.is_verified:
                result.kyc_verified = True
            elif kyc_status == "declined":
                result.passed = False
                result.reason = "kyc_denied"
                result.provider = "persona"
                result.rule = "kyc_verification"
                return result
            else:
                # Pending/not started/expired/needs_review:
                # fail-closed for high value; allow lower-value but flag.
                if amount_minor >= HIGH_VALUE_THRESHOLD_MINOR:
                    result.passed = False
                    result.reason = "kyc_required_high_value"
                    result.provider = "persona"
                    result.rule = "high_value_payment"
                    return result
                logger.info("KYC not complete for agent %s (amount_minor=%s)", agent_id, amount_minor)
                result.kyc_verified = False
                
        except Exception as e:
            logger.error(f"KYC check failed for agent {agent_id}: {e}")
            # Fail closed for all KYC service errors
            result.passed = False
            result.reason = "kyc_service_error"
            result.provider = "persona"
            result.rule = "kyc_service_error"
            return result
    
    # Screen destination address for sanctions
    if deps.sanctions_service:
        try:
            # Screen recipient and source (if present) to strengthen KYT coverage.
            screenings: list[tuple[str, Any]] = []
            screening_result = await deps.sanctions_service.screen_address(destination, chain=chain)
            screenings.append((destination, screening_result))
            if source_address and source_address.lower() != destination.lower():
                source_result = await deps.sanctions_service.screen_address(source_address, chain=chain)
                screenings.append((source_address, source_result))

            highest_risk_level = "unknown"
            highest_risk_result: Any = None
            for screened_address, screen in screenings:
                if getattr(screen, "should_block", False):
                    result.passed = False
                    result.sanctions_clear = False
                    result.reason = "sanctions_hit"
                    result.provider = getattr(screen, "provider", None)
                    result.rule = getattr(screen, "reason", None) or "sanctions"

                    logger.warning(
                        "Sanctions hit for %s: %s",
                        screened_address,
                        getattr(screen, "reason", None),
                    )
                    return result
                risk_level = _sanctions_risk_level(screen)
                if _risk_rank(risk_level) > _risk_rank(highest_risk_level):
                    highest_risk_level = risk_level
                    highest_risk_result = screen

            result.sanctions_clear = True
            review_levels = _kyt_review_levels_for_org(organization_id)
            if highest_risk_level in review_levels:
                result.kyt_review_required = True
                result.kyt_risk_level = highest_risk_level
                result.kyt_reason = (
                    getattr(highest_risk_result, "reason", None)
                    or f"kyt_{highest_risk_level}_risk_review_required"
                )
                result.provider = getattr(highest_risk_result, "provider", None) or "sanctions"
                result.rule = f"kyt_risk:{highest_risk_level}"
            
        except Exception as e:
            logger.error(f"Sanctions screening failed for {destination}: {e}")
            # Fail closed for sanctions errors
            result.passed = False
            result.reason = "sanctions_service_error"
            result.provider = "sanctions"
            result.rule = "sanctions_service_error"
            return result
    
    return result


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _iter_strings(v)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _detect_prompt_injection_signal(payload: AP2PaymentExecuteRequest) -> Optional[str]:
    for text in _iter_strings(payload.intent):
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                return pattern.pattern
    for text in _iter_strings(payload.cart):
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                return pattern.pattern
    for text in _iter_strings(payload.payment):
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                return pattern.pattern
    return None


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


async def _append_policy_decision_audit(
    *,
    deps: Dependencies,
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


async def _append_compliance_decision_audit(
    *,
    deps: Dependencies,
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


@router.post("/payments/execute", response_model=AP2PaymentExecuteResponse)
async def execute_ap2_payment(
    payload: AP2PaymentExecuteRequest,
    request: Request,
    deps: Dependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """
    Execute an AP2 payment with full compliance checks.
    
    Flow:
    1. Verify mandate chain (signature, expiry, amount validation)
    2. Check rate limits
    3. Perform KYC verification for high-value transactions
    4. Screen addresses for sanctions
    5. Execute payment
    6. Log compliance decisions
    """
    async def _execute() -> tuple[int, object]:
        # Step 1: Verify mandate chain
        verification = deps.verifier.verify_chain(payload, canonicalization_mode=payload.canonicalization_mode)
        if not verification.accepted or not verification.chain:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=verification.reason or "mandate_invalid",
            )

        chain = verification.chain
        payment = chain.payment

        agent = await deps.agent_repo.get(payment.subject)
        if not agent:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="agent_not_found")
        if not principal.is_admin and agent.owner_id != principal.organization_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="access_denied")

        pilot_policy = get_pilot_execution_policy(deps.settings)
        enforce_staging_live_guard(
            policy=pilot_policy,
            principal=principal,
            merchant_domain=getattr(payment, "merchant_domain", None),
            amount=None,
            operation="ap2.payments.execute",
        )

        # Resolve wallet for the agent (needed for signing in live mode) + freeze gate
        wallet = await deps.wallet_repo.get_by_agent(payment.subject)
        if not wallet:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="wallet_not_found_for_agent")
        await enforce_agent_payment_rate_limit(
            agent_id=payment.subject,
            operation="ap2.payments.execute",
            settings=deps.settings,
        )
        freeze_ok, freeze_reason = validate_wallet_not_frozen(wallet)
        if not freeze_ok:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=freeze_reason)
        chain = MandateChain(
            intent=chain.intent,
            cart=chain.cart,
            payment=replace(payment, wallet_id=wallet.wallet_id),
        )
        payment = chain.payment

        # SpendingPolicy enforcement
        # TODO: Migrate to PaymentOrchestrator gateway
        if not deps.wallet_manager:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="wallet_manager_not_configured",
            )
        policy_result = await deps.wallet_manager.async_validate_policies(payment)
        if not getattr(policy_result, "allowed", False):
            policy = await deps.policy_store.fetch_policy(payment.subject) if deps.policy_store else None
            if policy is not None:
                receipt = _try_build_policy_receipt(
                    policy=policy,
                    decision="deny",
                    reason=getattr(policy_result, "reason", None) or "spending_policy_denied",
                    context={
                        "mandate_id": payment.mandate_id,
                        "subject": payment.subject,
                        "destination": payment.destination,
                        "amount_minor": payment.amount_minor,
                        "token": payment.token,
                        "chain": payment.chain,
                    },
                )
                if receipt is not None:
                    await _append_policy_decision_audit(
                        deps=deps,
                        mandate_id=payment.mandate_id,
                        subject=payment.subject,
                        allowed=False,
                        reason=receipt["reason"],
                        receipt_payload=receipt,
                    )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=getattr(policy_result, "reason", None) or "spending_policy_denied",
            )

        # Deterministic final gate (AI advisory-only mode):
        # enforce chain/token/destination rails from persisted policy.
        advisory_only = os.getenv("SARDIS_AI_ADVISORY_ONLY", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        env_name = (os.getenv("SARDIS_ENVIRONMENT", "dev") or "dev").strip().lower()
        if advisory_only:
            if deps.policy_store is None:
                if env_name in {"prod", "production"}:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="deterministic_policy_unavailable",
                    )
            else:
                policy = await deps.policy_store.fetch_policy(payment.subject)
                if policy is None:
                    if env_name in {"prod", "production"}:
                        raise HTTPException(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="deterministic_policy_not_found",
                        )
                elif hasattr(policy, "validate_execution_context"):
                    rails_ok, rails_reason = policy.validate_execution_context(
                        destination=payment.destination,
                        chain=payment.chain,
                        token=payment.token,
                    )
                    if not rails_ok:
                        receipt = _try_build_policy_receipt(
                            policy=policy,
                            decision="deny",
                            reason=rails_reason or "deterministic_guardrail_denied",
                            context={
                                "mandate_id": payment.mandate_id,
                                "subject": payment.subject,
                                "destination": payment.destination,
                                "amount_minor": payment.amount_minor,
                                "token": payment.token,
                                "chain": payment.chain,
                            },
                        )
                        if receipt is not None:
                            await _append_policy_decision_audit(
                                deps=deps,
                                mandate_id=payment.mandate_id,
                                subject=payment.subject,
                                allowed=False,
                                reason=receipt["reason"],
                                receipt_payload=receipt,
                            )
                        if deps.approval_service:
                            amount_decimal = Decimal(str(payment.amount_minor)) / Decimal("100")
                            approval = await deps.approval_service.create_approval(
                                action="payment",
                                requested_by=payment.subject,
                                agent_id=payment.subject,
                                wallet_id=getattr(payment, "wallet_id", None),
                                vendor=payment.destination,
                                amount=amount_decimal,
                                purpose=f"AP2 payment to {payment.destination}",
                                reason=f"deterministic_guardrail_violation:{rails_reason}",
                                urgency="high",
                                metadata={
                                    "mandate_id": payment.mandate_id,
                                    "risk_signal": "deterministic_guardrail",
                                    "guardrail_reason": rails_reason,
                                    "canonicalization_mode": payload.canonicalization_mode,
                                    "policy_receipt": receipt,
                                },
                            )
                            return 202, AP2PaymentExecuteResponse(
                                mandate_id=payment.mandate_id,
                                ledger_tx_id="",
                                chain_tx_hash="",
                                chain=payment.chain,
                                audit_anchor="",
                                status="pending_approval",
                                approval_id=approval.id,
                            )
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=rails_reason or "deterministic_guardrail_denied",
                        )
                receipt = _try_build_policy_receipt(
                    policy=policy,
                    decision="allow",
                    reason="deterministic_guardrail_passed",
                    context={
                        "mandate_id": payment.mandate_id,
                        "subject": payment.subject,
                        "destination": payment.destination,
                        "amount_minor": payment.amount_minor,
                        "token": payment.token,
                        "chain": payment.chain,
                    },
                )
                if receipt is not None:
                    await _append_policy_decision_audit(
                        deps=deps,
                        mandate_id=payment.mandate_id,
                        subject=payment.subject,
                        allowed=True,
                        reason=receipt["reason"],
                        receipt_payload=receipt,
                    )

        # Runtime safety guard: prompt-injection signal detection on AP2 envelope.
        prompt_guard_enabled = os.getenv("SARDIS_PROMPT_INJECTION_GUARD_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if prompt_guard_enabled:
            injection_match = _detect_prompt_injection_signal(payload)
            if injection_match:
                if deps.approval_service:
                    amount_decimal = Decimal(str(payment.amount_minor)) / Decimal("100")
                    approval = await deps.approval_service.create_approval(
                        action="payment",
                        requested_by=payment.subject,
                        agent_id=payment.subject,
                        wallet_id=getattr(payment, "wallet_id", None),
                        vendor=payment.merchant_domain,
                        amount=amount_decimal,
                        purpose=f"AP2 payment to {payment.merchant_domain}",
                        reason=f"prompt_injection_signal_detected:{injection_match}",
                        urgency="high",
                        metadata={
                            "mandate_id": payment.mandate_id,
                            "risk_signal": "prompt_injection",
                            "pattern": injection_match,
                            "canonicalization_mode": payload.canonicalization_mode,
                        },
                    )
                    return 202, AP2PaymentExecuteResponse(
                        mandate_id=payment.mandate_id,
                        ledger_tx_id="",
                        chain_tx_hash="",
                        chain=payment.chain,
                        audit_anchor="",
                        status="pending_approval",
                        approval_id=approval.id,
                    )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="prompt_injection_signal_detected",
                )

        # Runtime safety guard: goal drift threshold block/review.
        drift_score = float(getattr(verification, "drift_score", 0.0) or 0.0)
        drift_block_threshold = float(os.getenv("SARDIS_GOAL_DRIFT_BLOCK_THRESHOLD", "0.90"))
        if drift_score >= drift_block_threshold:
            if deps.approval_service:
                amount_decimal = Decimal(str(payment.amount_minor)) / Decimal("100")
                approval = await deps.approval_service.create_approval(
                    action="payment",
                    requested_by=payment.subject,
                    agent_id=payment.subject,
                    wallet_id=getattr(payment, "wallet_id", None),
                    vendor=payment.merchant_domain,
                    amount=amount_decimal,
                    purpose=f"AP2 payment to {payment.merchant_domain}",
                    reason=f"goal_drift_score={drift_score:.3f} threshold={drift_block_threshold:.3f}",
                    urgency="high",
                    metadata={
                        "mandate_id": payment.mandate_id,
                        "risk_signal": "goal_drift",
                        "drift_score": drift_score,
                        "drift_reasons": getattr(verification, "drift_reasons", []),
                        "canonicalization_mode": payload.canonicalization_mode,
                    },
                )
                return 202, AP2PaymentExecuteResponse(
                    mandate_id=payment.mandate_id,
                    ledger_tx_id="",
                    chain_tx_hash="",
                    chain=payment.chain,
                    audit_anchor="",
                    status="pending_approval",
                    approval_id=approval.id,
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="goal_drift_blocked",
            )

        # Step 2: Perform compliance checks
        compliance = await _compliance_checks_impl(
            deps=deps,
            agent_id=payment.subject,
            destination=payment.destination,
            chain=payment.chain,
            amount_minor=payment.amount_minor,
            source_address=wallet.get_address(payment.chain) if hasattr(wallet, "get_address") else None,
            token=payment.token,
            organization_id=principal.organization_id,
        )

        if not compliance.passed:
            logger.warning(
                f"Compliance check failed for mandate {payment.mandate_id}: "
                f"{compliance.reason}"
            )
            await _append_compliance_decision_audit(
                deps=deps,
                mandate_id=payment.mandate_id,
                subject=payment.subject,
                allowed=False,
                reason=compliance.reason or "compliance_denied",
                provider=compliance.provider or "compliance_engine",
                rule_id=compliance.rule,
                metadata={
                    "phase": "pre_execution",
                    "destination": payment.destination,
                    "amount_minor": payment.amount_minor,
                    "token": payment.token,
                    "chain": payment.chain,
                    "kyt_risk_level": compliance.kyt_risk_level,
                },
            )
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail={
                    "code": compliance.reason,
                    "provider": compliance.provider,
                    "rule": compliance.rule,
                    "kyt_risk_level": compliance.kyt_risk_level,
                },
            )

        if compliance.kyt_review_required:
            await _append_compliance_decision_audit(
                deps=deps,
                mandate_id=payment.mandate_id,
                subject=payment.subject,
                allowed=False,
                reason="kyt_review_required",
                provider=compliance.provider or "sanctions",
                rule_id=compliance.rule,
                metadata={
                    "phase": "pre_execution",
                    "kyt_risk_level": compliance.kyt_risk_level,
                    "kyt_reason": compliance.kyt_reason,
                    "destination": payment.destination,
                    "source": wallet.get_address(payment.chain) if hasattr(wallet, "get_address") else None,
                    "amount_minor": payment.amount_minor,
                    "token": payment.token,
                    "chain": payment.chain,
                },
            )
            if deps.approval_service:
                amount_decimal = Decimal(str(payment.amount_minor)) / Decimal("100")
                approval = await deps.approval_service.create_approval(
                    action="payment",
                    requested_by=payment.subject,
                    agent_id=payment.subject,
                    wallet_id=getattr(payment, "wallet_id", None),
                    vendor=payment.destination,
                    amount=amount_decimal,
                    purpose=f"AP2 payment to {payment.destination}",
                    reason=(
                        f"kyt_review_required:risk={compliance.kyt_risk_level}"
                        f":{compliance.kyt_reason or 'unspecified'}"
                    ),
                    urgency="high",
                    metadata={
                        "mandate_id": payment.mandate_id,
                        "risk_signal": "kyt_risk",
                        "kyt_risk_level": compliance.kyt_risk_level,
                        "kyt_reason": compliance.kyt_reason,
                        "canonicalization_mode": payload.canonicalization_mode,
                    },
                )
                return 202, AP2PaymentExecuteResponse(
                    mandate_id=payment.mandate_id,
                    ledger_tx_id="",
                    chain_tx_hash="",
                    chain=payment.chain,
                    audit_anchor="",
                    status="pending_approval",
                    compliance_provider=compliance.provider,
                    compliance_rule=compliance.rule,
                    approval_id=approval.id,
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "kyt_review_required",
                    "provider": compliance.provider,
                    "rule": compliance.rule,
                    "kyt_risk_level": compliance.kyt_risk_level,
                },
            )

        await _append_compliance_decision_audit(
            deps=deps,
            mandate_id=payment.mandate_id,
            subject=payment.subject,
            allowed=True,
            reason="compliance_passed",
            provider=compliance.provider or "compliance_engine",
            rule_id=compliance.rule or "compliance_preflight",
            metadata={
                "phase": "pre_execution",
                "destination": payment.destination,
                "amount_minor": payment.amount_minor,
                "token": payment.token,
                "chain": payment.chain,
                "kyt_risk_level": compliance.kyt_risk_level,
                "kya_verified": compliance.kya_verified,
                "kyc_verified": compliance.kyc_verified,
            },
        )

        # Step 2.5: Goal drift logging
        if verification.drift_score > 0:
            logger.warning(
                "Goal drift detected for mandate %s: score=%.2f reasons=%s",
                payment.mandate_id, verification.drift_score,
                verification.drift_reasons,
            )

        # Step 2.6: Approval check — if agent has approval threshold configured
        if deps.approval_service:
            # Load agent spending policy to check approval_threshold
            agent_record = await deps.agent_repo.get(payment.subject)
            approval_threshold = None
            if agent_record and hasattr(agent_record, 'spending_policy') and agent_record.spending_policy:
                policy = agent_record.spending_policy
                approval_threshold = getattr(policy, 'approval_threshold', None)

            if approval_threshold is not None:
                amount_decimal = Decimal(str(payment.amount_minor)) / Decimal("100")
                if amount_decimal > approval_threshold:
                    # Create approval request and return 202
                    approval = await deps.approval_service.create_approval(
                        action="payment",
                        requested_by=payment.subject,
                        agent_id=payment.subject,
                        wallet_id=getattr(payment, 'wallet_id', None),
                        vendor=payment.merchant_domain,
                        amount=amount_decimal,
                        purpose=f"AP2 payment to {payment.merchant_domain}",
                        reason=f"Amount ${amount_decimal} exceeds approval threshold ${approval_threshold}",
                        urgency='high' if amount_decimal > approval_threshold * 5 else 'medium',
                        metadata={
                            "mandate_id": payment.mandate_id,
                            "mandate_chain_snapshot": {
                                "intent": payload.intent,
                                "cart": payload.cart,
                                "payment": payload.payment,
                            },
                            "drift_score": verification.drift_score,
                            "drift_reasons": verification.drift_reasons,
                            "canonicalization_mode": payload.canonicalization_mode,
                        },
                    )
                    logger.info(
                        "Payment %s requires approval (amount=%s, threshold=%s, approval_id=%s)",
                        payment.mandate_id, amount_decimal, approval_threshold, approval.id,
                    )
                    return 202, AP2PaymentExecuteResponse(
                        mandate_id=payment.mandate_id,
                        ledger_tx_id="",
                        chain_tx_hash="",
                        chain=payment.chain,
                        audit_anchor="",
                        status="pending_approval",
                        compliance_provider=compliance.provider,
                        compliance_rule=compliance.rule,
                        approval_id=approval.id,
                    )

        # Step 3: Execute payment
        try:
            result = await deps.orchestrator.execute_chain(chain)
        except PaymentExecutionError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        logger.info(
            f"Payment executed: mandate={payment.mandate_id}, "
            f"amount={payment.amount_minor}, kyc={compliance.kyc_verified}, "
            f"sanctions_clear={compliance.sanctions_clear}"
        )

        return 200, AP2PaymentExecuteResponse(
            mandate_id=result.mandate_id,
            ledger_tx_id=result.ledger_tx_id,
            chain_tx_hash=result.chain_tx_hash,
            chain=result.chain,
            audit_anchor=result.audit_anchor,
            status=result.status,
            compliance_provider=compliance.provider or result.compliance_provider,
            compliance_rule=compliance.rule or result.compliance_rule,
        )

    # Use payment.mandate_id for dedupe; mandate chain verification ensures it's stable.
    # If multiple requests use the same idempotency key with different payloads, we reject.
    key = payload.payment.get("mandate_id") if isinstance(payload.payment, dict) else None
    if not key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="missing_payment_mandate_id")

    return await run_idempotent(
        request=request,
        principal=principal,
        operation="ap2.payments.execute",
        key=str(key),
        payload=payload.model_dump(),
        fn=_execute,
    )


async def perform_compliance_checks(
    deps: Dependencies,
    agent_id: str,
    destination: str,
    chain: str,
    amount_minor: int,
    organization_id: Optional[str] = None,
) -> ComplianceCheckResult:
    """
    Compatibility wrapper kept for tests/introspection:
    policy gate is enforced before this check inside execute_ap2_payment().
    """
    return await _compliance_checks_impl(
        deps=deps,
        agent_id=agent_id,
        destination=destination,
        chain=chain,
        amount_minor=amount_minor,
        organization_id=organization_id,
    )
