"""Receipts API — retrieve and verify execution receipts.

Endpoints:
    GET /receipts/{receipt_id}        — Get a receipt by ID
    GET /receipts/verify/{receipt_id} — Verify receipt HMAC signature
    GET /receipts                     — List receipts (by agent_id or org_id)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Response Models ──────────────────────────────────────────────────


class ReceiptResponse(BaseModel):
    """Execution receipt."""
    receipt_id: str
    timestamp: float
    intent_hash: str
    policy_snapshot_hash: str
    compliance_result_hash: str
    tx_hash: str
    chain: str
    ledger_entry_id: str
    ledger_tx_id: str
    org_id: str
    agent_id: str
    amount: str
    currency: str
    signature: str


class VerifyResponse(BaseModel):
    """Receipt verification result."""
    valid: bool
    receipt: ReceiptResponse | None = None


class ReceiptListResponse(BaseModel):
    """List of receipts."""
    receipts: list[ReceiptResponse] = Field(default_factory=list)
    count: int = 0


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: str,
    principal: Principal = Depends(require_principal),
):
    """Get a receipt by ID."""

    store = _get_receipt_store()
    receipt = await store.get(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail=f"Receipt not found: {receipt_id}")

    # Org-scoped access control
    if receipt.org_id and receipt.org_id != principal.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _receipt_to_response(receipt)


@router.get("/verify/{receipt_id}", response_model=VerifyResponse)
async def verify_receipt(
    receipt_id: str,
    principal: Principal = Depends(require_principal),
):
    """Verify a receipt's HMAC signature."""
    store = _get_receipt_store()
    receipt = await store.get(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail=f"Receipt not found: {receipt_id}")

    if receipt.org_id and receipt.org_id != principal.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    valid = receipt.verify()
    return VerifyResponse(
        valid=valid,
        receipt=_receipt_to_response(receipt),
    )


@router.get("/", response_model=ReceiptListResponse)
async def list_receipts(
    agent_id: str | None = Query(None),
    org_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    principal: Principal = Depends(require_principal),
):
    """List receipts filtered by agent_id or org_id."""
    store = _get_receipt_store()
    effective_org = org_id or principal.organization_id

    if agent_id:
        receipts = await store.list_by_agent(agent_id, limit=limit)
    else:
        receipts = await store.list_by_org(effective_org, limit=limit)

    # Filter to caller's org
    filtered = [r for r in receipts if not r.org_id or r.org_id == principal.organization_id]

    return ReceiptListResponse(
        receipts=[_receipt_to_response(r) for r in filtered],
        count=len(filtered),
    )


# ── Helpers ──────────────────────────────────────────────────────────


# Singleton store — replaced with PostgresReceiptStore in production
_store_instance = None


def _get_receipt_store():
    """Get the receipt store singleton."""
    global _store_instance
    if _store_instance is None:
        from sardis_v2_core.receipt_store import InMemoryReceiptStore
        _store_instance = InMemoryReceiptStore()
    return _store_instance


def set_receipt_store(store) -> None:
    """Override the receipt store (for production wiring)."""
    global _store_instance
    _store_instance = store


def _receipt_to_response(receipt) -> ReceiptResponse:
    return ReceiptResponse(
        receipt_id=receipt.receipt_id,
        timestamp=receipt.timestamp,
        intent_hash=receipt.intent_hash,
        policy_snapshot_hash=receipt.policy_snapshot_hash,
        compliance_result_hash=receipt.compliance_result_hash,
        tx_hash=receipt.tx_hash,
        chain=receipt.chain,
        ledger_entry_id=receipt.ledger_entry_id,
        ledger_tx_id=receipt.ledger_tx_id,
        org_id=receipt.org_id,
        agent_id=receipt.agent_id,
        amount=receipt.amount,
        currency=receipt.currency,
        signature=receipt.signature,
    )
