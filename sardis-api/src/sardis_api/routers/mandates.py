"""Mandate ingestion + execution endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

from sardis_protocol.schemas import IngestMandateRequest, MandateExecutionResponse

if TYPE_CHECKING:
    from sardis_wallet.manager import WalletManager
    from sardis_chain.executor import ChainExecutor
    from sardis_protocol.verifier import MandateVerifier
    from sardis_ledger.records import LedgerStore
    from sardis_compliance.checks import ComplianceEngine

router = APIRouter()


@dataclass
class Dependencies:
    wallet_manager: "WalletManager"
    chain_executor: "ChainExecutor"
    verifier: "MandateVerifier"
    ledger: "LedgerStore"
    compliance: "ComplianceEngine"


def get_deps() -> Dependencies:
    raise NotImplementedError("Dependency override required")


@router.post("/execute", response_model=MandateExecutionResponse)
async def execute_payment_mandate(payload: IngestMandateRequest, deps: Dependencies = Depends(get_deps)):
    verifier = deps.verifier
    verification = verifier.verify(payload.mandate)
    if not verification.accepted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=verification.reason)

    policy_result = deps.wallet_manager.validate_policies(payload.mandate)
    if not policy_result.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=policy_result.reason)

    compliance_status = deps.compliance.preflight(payload.mandate)
    if not compliance_status.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=compliance_status.reason)

    tx = await deps.chain_executor.dispatch_payment(payload.mandate)
    deps.ledger.append(payment_mandate=payload.mandate, chain_receipt=tx)

    return MandateExecutionResponse(
        mandate_id=payload.mandate.mandate_id,
        status="submitted",
        tx_hash=tx.tx_hash,
        chain=tx.chain,
        audit_anchor=tx.audit_anchor,
    )
