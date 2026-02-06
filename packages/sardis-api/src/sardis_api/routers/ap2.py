"""AP2 payment execution endpoints with compliance enforcement."""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request

from sardis_protocol.schemas import AP2PaymentExecuteRequest, AP2PaymentExecuteResponse
from sardis_v2_core.orchestrator import PaymentExecutionError
from sardis_v2_core.mandates import MandateChain
from sardis_v2_core.transactions import validate_wallet_not_frozen

from sardis_api.authz import Principal, require_principal
from sardis_v2_core import AgentRepository
from sardis_api.idempotency import run_idempotent

if TYPE_CHECKING:
    from sardis_protocol.verifier import MandateVerifier
    from sardis_v2_core.orchestrator import PaymentOrchestrator
    from sardis_compliance.kyc import KYCService
    from sardis_compliance.sanctions import SanctionsService
    from sardis_v2_core.wallet_repository import WalletRepository

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
