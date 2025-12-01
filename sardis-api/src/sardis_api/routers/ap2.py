"""AP2 payment execution endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

from sardis_protocol.schemas import AP2PaymentExecuteRequest, AP2PaymentExecuteResponse
from sardis_v2_core.orchestrator import PaymentExecutionError

if TYPE_CHECKING:
    from sardis_protocol.verifier import MandateVerifier
    from sardis_v2_core.orchestrator import PaymentOrchestrator

router = APIRouter()


@dataclass
class Dependencies:
    verifier: "MandateVerifier"
    orchestrator: "PaymentOrchestrator"


def get_deps(dep: Dependencies = Depends()) -> Dependencies:
    return dep


@router.post("/payments/execute", response_model=AP2PaymentExecuteResponse)
async def execute_ap2_payment(payload: AP2PaymentExecuteRequest, deps: Dependencies = Depends(get_deps)):
    verification = deps.verifier.verify_chain(payload)
    if not verification.accepted or not verification.chain:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=verification.reason or "mandate_invalid")

    try:
        result = await deps.orchestrator.execute_chain(verification.chain)
    except PaymentExecutionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AP2PaymentExecuteResponse(
        mandate_id=result.mandate_id,
        ledger_tx_id=result.ledger_tx_id,
        chain_tx_hash=result.chain_tx_hash,
        chain=result.chain,
        audit_anchor=result.audit_anchor,
        status=result.status,
        compliance_provider=result.compliance_provider,
        compliance_rule=result.compliance_rule,
    )
