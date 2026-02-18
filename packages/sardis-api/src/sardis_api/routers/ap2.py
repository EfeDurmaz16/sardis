"""AP2 payment execution endpoints with compliance enforcement."""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request

from sardis_protocol.schemas import AP2PaymentExecuteRequest, AP2PaymentExecuteResponse
from sardis_v2_core.orchestrator import PaymentExecutionError
from sardis_v2_core.mandates import MandateChain
from sardis_v2_core.transactions import validate_wallet_not_frozen

from sardis_api.authz import Principal, require_principal
from sardis_api.execution_mode import enforce_staging_live_guard, get_pilot_execution_policy
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


@dataclass
class Dependencies:
    verifier: "MandateVerifier"
    orchestrator: "PaymentOrchestrator"
    wallet_repo: "WalletRepository"
    agent_repo: AgentRepository
    kyc_service: Optional["KYCService"] = None
    sanctions_service: Optional["SanctionsService"] = None
    approval_service: Optional["ApprovalService"] = None
    settings: Optional[object] = None
    wallet_manager: Optional[Any] = None


def get_deps() -> Dependencies:
    raise NotImplementedError("Dependency override required")


@dataclass
class ComplianceCheckResult:
    """Result of compliance checks."""
    passed: bool
    kyc_verified: bool = False
    sanctions_clear: bool = True
    reason: Optional[str] = None
    provider: Optional[str] = None
    rule: Optional[str] = None


async def perform_compliance_checks(
    deps: Dependencies,
    agent_id: str,
    destination: str,
    chain: str,
    amount_minor: int,
) -> ComplianceCheckResult:
    """
    Perform all compliance checks for a payment.
    
    Checks:
    1. KYC status for high-value transactions
    2. Sanctions screening for sender and recipient addresses
    """
    result = ComplianceCheckResult(passed=True)
    
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
            # Screen the recipient address
            screening_result = await deps.sanctions_service.screen_address(destination, chain=chain)

            if screening_result.should_block:
                result.passed = False
                result.sanctions_clear = False
                result.reason = "sanctions_hit"
                result.provider = screening_result.provider
                result.rule = screening_result.reason or "sanctions"

                logger.warning(
                    "Sanctions hit for destination %s: %s",
                    destination,
                    screening_result.reason,
                )
                return result
                
            result.sanctions_clear = True
            
        except Exception as e:
            logger.error(f"Sanctions screening failed for {destination}: {e}")
            # Fail closed for sanctions errors
            result.passed = False
            result.reason = "sanctions_service_error"
            return result
    
    return result


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
        if deps.wallet_manager:
            policy_result = await deps.wallet_manager.async_validate_policies(payment)
            if not getattr(policy_result, "allowed", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=getattr(policy_result, "reason", None) or "spending_policy_denied",
                )

        # Step 2: Perform compliance checks
        compliance = await perform_compliance_checks(
            deps=deps,
            agent_id=payment.subject,
            destination=payment.destination,
            chain=payment.chain,
            amount_minor=payment.amount_minor,
        )

        if not compliance.passed:
            logger.warning(
                f"Compliance check failed for mandate {payment.mandate_id}: "
                f"{compliance.reason}"
            )
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail={
                    "code": compliance.reason,
                    "provider": compliance.provider,
                    "rule": compliance.rule,
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
                from decimal import Decimal
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
