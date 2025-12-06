"""Mandate ingestion + execution endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from sardis_protocol.schemas import IngestMandateRequest, MandateExecutionResponse
from sardis_v2_core.mandates import PaymentMandate

if TYPE_CHECKING:
    from sardis_wallet.manager import WalletManager
    from sardis_chain.executor import ChainExecutor
    from sardis_protocol.verifier import MandateVerifier
    from sardis_ledger.records import LedgerStore
    from sardis_compliance.checks import ComplianceEngine

router = APIRouter()


# Stored mandate model
class StoredMandate(BaseModel):
    mandate_id: str
    mandate: PaymentMandate
    status: str = "pending"  # pending, validated, executed, failed, cancelled
    attestation_bundle: dict = Field(default_factory=dict)
    validation_result: Optional[dict] = None
    execution_result: Optional[dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# In-memory mandate store (swap for PostgreSQL in production)
_mandate_store: Dict[str, StoredMandate] = {}


# Request/Response models
class CreateMandateRequest(BaseModel):
    subject: str = Field(..., description="Agent ID initiating the payment")
    domain: str = Field(..., description="Merchant/recipient domain")
    amount_minor: int = Field(..., description="Amount in minor units (cents)")
    currency: str = Field(default="USDC")
    recipient: str = Field(..., description="Recipient wallet address")
    chain: str = Field(default="base")
    memo: Optional[str] = None
    attestation_bundle: dict = Field(default_factory=dict)


class MandateResponse(BaseModel):
    mandate_id: str
    subject: str
    domain: str
    amount_minor: int
    currency: str
    recipient: str
    chain: str
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_stored(cls, stored: StoredMandate) -> "MandateResponse":
        return cls(
            mandate_id=stored.mandate_id,
            subject=stored.mandate.subject,
            domain=stored.mandate.domain,
            amount_minor=stored.mandate.amount_minor,
            currency=stored.mandate.currency,
            recipient=stored.mandate.recipient,
            chain=stored.mandate.chain,
            status=stored.status,
            created_at=stored.created_at.isoformat(),
            updated_at=stored.updated_at.isoformat(),
        )


class ValidateMandateResponse(BaseModel):
    mandate_id: str
    valid: bool
    status: str
    reason: Optional[str] = None
    policy_check: Optional[dict] = None
    compliance_check: Optional[dict] = None


@dataclass
class Dependencies:
    wallet_manager: "WalletManager"
    chain_executor: "ChainExecutor"
    verifier: "MandateVerifier"
    ledger: "LedgerStore"
    compliance: "ComplianceEngine"


def get_deps() -> Dependencies:
    raise NotImplementedError("Dependency override required")


# Endpoints

@router.post("", response_model=MandateResponse, status_code=status.HTTP_201_CREATED)
async def create_mandate(
    request: CreateMandateRequest,
    deps: Dependencies = Depends(get_deps),
):
    """Create and store a new payment mandate (does not execute)."""
    mandate_id = f"mandate_{uuid4().hex[:16]}"
    
    mandate = PaymentMandate(
        mandate_id=mandate_id,
        subject=request.subject,
        domain=request.domain,
        amount_minor=request.amount_minor,
        currency=request.currency,
        recipient=request.recipient,
        chain=request.chain,
        memo=request.memo or "",
    )
    
    stored = StoredMandate(
        mandate_id=mandate_id,
        mandate=mandate,
        attestation_bundle=request.attestation_bundle,
    )
    _mandate_store[mandate_id] = stored
    
    return MandateResponse.from_stored(stored)


@router.get("", response_model=List[MandateResponse])
async def list_mandates(
    subject: Optional[str] = Query(None, description="Filter by agent ID"),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    deps: Dependencies = Depends(get_deps),
):
    """List all mandates."""
    mandates = list(_mandate_store.values())
    if subject:
        mandates = [m for m in mandates if m.mandate.subject == subject]
    if status_filter:
        mandates = [m for m in mandates if m.status == status_filter]
    mandates = mandates[offset : offset + limit]
    return [MandateResponse.from_stored(m) for m in mandates]


@router.get("/{mandate_id}", response_model=MandateResponse)
async def get_mandate(
    mandate_id: str,
    deps: Dependencies = Depends(get_deps),
):
    """Get mandate details."""
    stored = _mandate_store.get(mandate_id)
    if not stored:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")
    return MandateResponse.from_stored(stored)


@router.post("/{mandate_id}/validate", response_model=ValidateMandateResponse)
async def validate_mandate(
    mandate_id: str,
    deps: Dependencies = Depends(get_deps),
):
    """Validate a mandate without executing it."""
    stored = _mandate_store.get(mandate_id)
    if not stored:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")
    
    # Verify mandate structure
    verification = deps.verifier.verify(stored.mandate)
    if not verification.accepted:
        stored.status = "failed"
        stored.validation_result = {"valid": False, "reason": verification.reason}
        stored.updated_at = datetime.now(timezone.utc)
        return ValidateMandateResponse(
            mandate_id=mandate_id,
            valid=False,
            status="failed",
            reason=verification.reason,
        )
    
    # Check spending policies
    policy_result = deps.wallet_manager.validate_policies(stored.mandate)
    policy_check = {"allowed": policy_result.allowed, "reason": policy_result.reason}
    
    # Check compliance
    compliance_status = deps.compliance.preflight(stored.mandate)
    compliance_check = {"allowed": compliance_status.allowed, "reason": compliance_status.reason}
    
    valid = policy_result.allowed and compliance_status.allowed
    stored.status = "validated" if valid else "failed"
    stored.validation_result = {
        "valid": valid,
        "policy": policy_check,
        "compliance": compliance_check,
    }
    stored.updated_at = datetime.now(timezone.utc)
    
    return ValidateMandateResponse(
        mandate_id=mandate_id,
        valid=valid,
        status=stored.status,
        reason=None if valid else (policy_result.reason or compliance_status.reason),
        policy_check=policy_check,
        compliance_check=compliance_check,
    )


@router.post("/{mandate_id}/execute", response_model=MandateExecutionResponse)
async def execute_stored_mandate(
    mandate_id: str,
    deps: Dependencies = Depends(get_deps),
):
    """Execute a previously created mandate."""
    stored = _mandate_store.get(mandate_id)
    if not stored:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")
    
    if stored.status == "executed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mandate already executed")
    
    if stored.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mandate was cancelled")
    
    # Validate if not already validated
    if stored.status != "validated":
        verification = deps.verifier.verify(stored.mandate)
        if not verification.accepted:
            stored.status = "failed"
            stored.updated_at = datetime.now(timezone.utc)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=verification.reason)
        
        policy_result = deps.wallet_manager.validate_policies(stored.mandate)
        if not policy_result.allowed:
            stored.status = "failed"
            stored.updated_at = datetime.now(timezone.utc)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=policy_result.reason)
        
        compliance_status = deps.compliance.preflight(stored.mandate)
        if not compliance_status.allowed:
            stored.status = "failed"
            stored.updated_at = datetime.now(timezone.utc)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=compliance_status.reason)
    
    # Execute
    tx = await deps.chain_executor.dispatch_payment(stored.mandate)
    deps.ledger.append(payment_mandate=stored.mandate, chain_receipt=tx)
    
    stored.status = "executed"
    stored.execution_result = {
        "tx_hash": tx.tx_hash,
        "chain": tx.chain,
        "audit_anchor": tx.audit_anchor,
    }
    stored.updated_at = datetime.now(timezone.utc)
    
    return MandateExecutionResponse(
        mandate_id=stored.mandate.mandate_id,
        status="submitted",
        tx_hash=tx.tx_hash,
        chain=tx.chain,
        audit_anchor=tx.audit_anchor,
    )


@router.post("/{mandate_id}/cancel", response_model=MandateResponse)
async def cancel_mandate(
    mandate_id: str,
    deps: Dependencies = Depends(get_deps),
):
    """Cancel a pending mandate."""
    stored = _mandate_store.get(mandate_id)
    if not stored:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")
    
    if stored.status == "executed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel executed mandate")
    
    stored.status = "cancelled"
    stored.updated_at = datetime.now(timezone.utc)
    
    return MandateResponse.from_stored(stored)


# Legacy endpoint for backwards compatibility
@router.post("/execute", response_model=MandateExecutionResponse)
async def execute_payment_mandate(payload: IngestMandateRequest, deps: Dependencies = Depends(get_deps)):
    """Execute a payment mandate directly (legacy endpoint)."""
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
