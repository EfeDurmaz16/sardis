"""Mandate ingestion + execution endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

import json

from sardis_protocol.schemas import IngestMandateRequest, MandateExecutionResponse
from sardis_v2_core.mandates import PaymentMandate
from sardis_v2_core.database import Database

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


async def _save_mandate(stored: StoredMandate) -> None:
    """Save or update a mandate in PostgreSQL."""
    await Database.execute(
        """
        INSERT INTO mandates (
            mandate_id, mandate_type, issuer, subject, domain, payload, status,
            attestation_bundle, validation_result, execution_result,
            amount_minor, currency, recipient, chain, memo, updated_at, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
        ON CONFLICT (mandate_id) DO UPDATE SET
            status = EXCLUDED.status,
            validation_result = EXCLUDED.validation_result,
            execution_result = EXCLUDED.execution_result,
            updated_at = EXCLUDED.updated_at
        """,
        stored.mandate_id,
        "payment",
        stored.mandate.subject,
        stored.mandate.subject,
        stored.mandate.domain,
        json.dumps(stored.mandate.model_dump(), default=str),
        stored.status,
        json.dumps(stored.attestation_bundle),
        json.dumps(stored.validation_result) if stored.validation_result else None,
        json.dumps(stored.execution_result) if stored.execution_result else None,
        stored.mandate.amount_minor,
        stored.mandate.currency,
        stored.mandate.recipient,
        stored.mandate.chain,
        getattr(stored.mandate, "memo", ""),
        stored.updated_at,
        stored.created_at,
    )


async def _get_mandate(mandate_id: str) -> Optional[StoredMandate]:
    """Get a mandate from PostgreSQL."""
    row = await Database.fetchrow(
        "SELECT * FROM mandates WHERE mandate_id = $1", mandate_id
    )
    if not row:
        return None
    return _row_to_stored(row)


async def _list_mandates(
    subject: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    """List mandates from PostgreSQL."""
    conditions = []
    args: list = []
    idx = 1

    if subject:
        conditions.append(f"subject = ${idx}")
        args.append(subject)
        idx += 1
    if status_filter:
        conditions.append(f"status = ${idx}")
        args.append(status_filter)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    args.extend([limit, offset])

    rows = await Database.fetch(
        f"SELECT * FROM mandates {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
        *args,
    )
    return [_row_to_stored(r) for r in rows]


def _row_to_stored(row) -> StoredMandate:
    """Convert a database row to StoredMandate."""
    payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])
    mandate = PaymentMandate(**payload)
    return StoredMandate(
        mandate_id=row["mandate_id"],
        mandate=mandate,
        status=row["status"] or "pending",
        attestation_bundle=json.loads(row["attestation_bundle"]) if isinstance(row["attestation_bundle"], str) else (row["attestation_bundle"] or {}),
        validation_result=json.loads(row["validation_result"]) if isinstance(row["validation_result"], str) else row["validation_result"],
        execution_result=json.loads(row["execution_result"]) if isinstance(row["execution_result"], str) else row["execution_result"],
        created_at=row["created_at"],
        updated_at=row.get("updated_at") or row["created_at"],
    )


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
    await _save_mandate(stored)
    
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
    results = await _list_mandates(
        subject=subject,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return [MandateResponse.from_stored(m) for m in results]


@router.get("/{mandate_id}", response_model=MandateResponse)
async def get_mandate(
    mandate_id: str,
    deps: Dependencies = Depends(get_deps),
):
    """Get mandate details."""
    stored = await _get_mandate(mandate_id)
    if not stored:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")
    return MandateResponse.from_stored(stored)


@router.post("/{mandate_id}/validate", response_model=ValidateMandateResponse)
async def validate_mandate(
    mandate_id: str,
    deps: Dependencies = Depends(get_deps),
):
    """Validate a mandate without executing it."""
    stored = await _get_mandate(mandate_id)
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
    await _save_mandate(stored)

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
    stored = await _get_mandate(mandate_id)
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
            await _save_mandate(stored)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=verification.reason)

        policy_result = deps.wallet_manager.validate_policies(stored.mandate)
        if not policy_result.allowed:
            stored.status = "failed"
            stored.updated_at = datetime.now(timezone.utc)
            await _save_mandate(stored)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=policy_result.reason)

        compliance_status = deps.compliance.preflight(stored.mandate)
        if not compliance_status.allowed:
            stored.status = "failed"
            stored.updated_at = datetime.now(timezone.utc)
            await _save_mandate(stored)
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
    await _save_mandate(stored)

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
    stored = await _get_mandate(mandate_id)
    if not stored:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")
    
    if stored.status == "executed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel executed mandate")
    
    stored.status = "cancelled"
    stored.updated_at = datetime.now(timezone.utc)
    await _save_mandate(stored)

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
