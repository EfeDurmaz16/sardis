"""AP2 payment execution endpoints with compliance enforcement."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from sardis_protocol.schemas import AP2PaymentExecuteRequest, AP2PaymentExecuteResponse
from sardis_v2_core.orchestrator import PaymentExecutionError

from sardis_api.authz import require_principal

if TYPE_CHECKING:
    from sardis_protocol.verifier import MandateVerifier
    from sardis_v2_core.orchestrator import PaymentOrchestrator
    from sardis_compliance.kyc import KYCService
    from sardis_compliance.sanctions import SanctionsService

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])

# KYC thresholds (amounts in minor units - cents for USD)
KYC_THRESHOLD_MINOR = 100000  # $1000 requires KYC
HIGH_VALUE_THRESHOLD_MINOR = 1000000  # $10000 enhanced verification


@dataclass
class Dependencies:
    verifier: "MandateVerifier"
    orchestrator: "PaymentOrchestrator"
    kyc_service: Optional["KYCService"] = None
    sanctions_service: Optional["SanctionsService"] = None


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
            kyc_status = await deps.kyc_service.get_agent_kyc_status(agent_id)
            
            if kyc_status == "approved":
                result.kyc_verified = True
            elif amount_minor >= HIGH_VALUE_THRESHOLD_MINOR:
                # Enhanced verification required for very high amounts
                result.passed = False
                result.reason = "kyc_required_high_value"
                result.provider = "persona"
                result.rule = "high_value_payment"
                return result
            elif kyc_status == "denied":
                result.passed = False
                result.reason = "kyc_denied"
                result.provider = "persona"
                result.rule = "kyc_verification"
                return result
            else:
                # Pending or not started - allow low-value but flag
                logger.info(f"KYC not complete for agent {agent_id}, amount {amount_minor}")
                result.kyc_verified = False
                
        except Exception as e:
            logger.error(f"KYC check failed for agent {agent_id}: {e}")
            # Fail open for service errors on lower amounts
            if amount_minor >= HIGH_VALUE_THRESHOLD_MINOR:
                result.passed = False
                result.reason = "kyc_service_error"
                return result
    
    # Screen destination address for sanctions
    if deps.sanctions_service:
        try:
            # Screen the recipient address
            screening_result = await deps.sanctions_service.screen_address(destination)
            
            if not screening_result.clear:
                result.passed = False
                result.sanctions_clear = False
                result.reason = "sanctions_hit"
                result.provider = "elliptic"
                result.rule = screening_result.matched_list or "ofac"
                
                logger.warning(
                    f"Sanctions hit for destination {destination}: "
                    f"{screening_result.matched_list}"
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
    deps: Dependencies = Depends(get_deps),
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
    # Step 1: Verify mandate chain
    verification = deps.verifier.verify_chain(payload)
    if not verification.accepted or not verification.chain:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=verification.reason or "mandate_invalid"
        )
    
    chain = verification.chain
    payment = chain.payment
    
    # Step 2: Perform compliance checks
    compliance = await perform_compliance_checks(
        deps=deps,
        agent_id=payment.subject,
        destination=payment.destination,
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
            }
        )
    
    # Step 3: Execute payment
    try:
        result = await deps.orchestrator.execute_chain(chain)
    except PaymentExecutionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    
    # Log successful transaction with compliance info
    logger.info(
        f"Payment executed: mandate={payment.mandate_id}, "
        f"amount={payment.amount_minor}, kyc={compliance.kyc_verified}, "
        f"sanctions_clear={compliance.sanctions_clear}"
    )
    
    return AP2PaymentExecuteResponse(
        mandate_id=result.mandate_id,
        ledger_tx_id=result.ledger_tx_id,
        chain_tx_hash=result.chain_tx_hash,
        chain=result.chain,
        audit_anchor=result.audit_anchor,
        status=result.status,
        compliance_provider=compliance.provider or result.compliance_provider,
        compliance_rule=compliance.rule or result.compliance_rule,
    )
