"""Ledger API routes for transaction history."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from sardis_ledger.records import LedgerStore

from sardis_api.authz import require_principal


router = APIRouter(dependencies=[Depends(require_principal)], tags=["ledger"])


class TransactionResponse(BaseModel):
    """Transaction response model."""
    tx_id: str
    from_wallet: str
    to_wallet: str
    amount: str
    currency: str
    chain: Optional[str] = None
    chain_tx_hash: Optional[str] = None
    audit_anchor: Optional[str] = None
    created_at: str
    status: str = "confirmed"

class LedgerEntryResponse(BaseModel):
    """Ledger entry response model (SDK-compatible)."""

    tx_id: str
    mandate_id: Optional[str] = None
    from_wallet: Optional[str] = None
    to_wallet: Optional[str] = None
    amount: str
    currency: str
    chain: Optional[str] = None
    chain_tx_hash: Optional[str] = None
    audit_anchor: Optional[str] = None
    created_at: str


class LedgerDependencies:
    """Dependencies for ledger routes."""
    def __init__(self, ledger: LedgerStore):
        self.ledger = ledger


def get_deps() -> LedgerDependencies:
    """Dependency injection placeholder."""
    raise NotImplementedError("Must be overridden")

@router.get("/entries", response_model=dict)
async def list_entries(
    wallet_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    deps: LedgerDependencies = Depends(get_deps),
):
    """
    List ledger entries.

    This is the canonical endpoint used by SDKs.
    """
    if hasattr(deps.ledger, "list_entry_records_async"):
        entries = await deps.ledger.list_entry_records_async(wallet_id=wallet_id, limit=limit, offset=offset)
    else:
        entries = deps.ledger.list_entry_records(wallet_id=wallet_id, limit=limit, offset=offset)
    return {"entries": [LedgerEntryResponse(**e).model_dump() for e in entries]}


@router.get("/entries/{tx_id}", response_model=LedgerEntryResponse)
async def get_entry(
    tx_id: str,
    deps: LedgerDependencies = Depends(get_deps),
):
    """Get a ledger entry by transaction ID."""
    if hasattr(deps.ledger, "get_entry_record_async"):
        entry = await deps.ledger.get_entry_record_async(tx_id)
    else:
        entry = deps.ledger.get_entry_record(tx_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger entry not found")
    return LedgerEntryResponse(**entry)


@router.get("/entries/{tx_id}/verify", response_model=dict)
async def verify_entry(
    tx_id: str,
    deps: LedgerDependencies = Depends(get_deps),
):
    """
    Verify a ledger entry's audit anchor.

    Verifies the cryptographic receipt chain step for the entry:
    - Fetches receipt by chain_tx_hash
    - Recomputes leaf hash from receipt payload
    - Recomputes Merkle root from previous_root + leaf
    """
    if hasattr(deps.ledger, "get_entry_record_async"):
        entry = await deps.ledger.get_entry_record_async(tx_id)
    else:
        entry = deps.ledger.get_entry_record(tx_id)

    if not entry:
        return {"valid": False, "reason": "entry_not_found"}

    anchor = entry.get("audit_anchor")
    if not anchor:
        return {"valid": False, "reason": "missing_audit_anchor", "anchor": None}

    tx_hash = entry.get("chain_tx_hash")
    if not tx_hash:
        return {"valid": False, "reason": "missing_chain_tx_hash", "anchor": anchor}

    if hasattr(deps.ledger, "get_receipt_by_tx_hash_async"):
        receipt = await deps.ledger.get_receipt_by_tx_hash_async(tx_hash)
    else:
        receipt = deps.ledger.get_receipt_by_tx_hash(tx_hash)

    if not receipt:
        return {"valid": False, "reason": "receipt_not_found", "anchor": anchor}

    if hasattr(deps.ledger, "get_current_merkle_root_async"):
        current_root = await deps.ledger.get_current_merkle_root_async()
    else:
        current_root = deps.ledger.get_current_merkle_root()

    verification = deps.ledger.verify_receipt_integrity(receipt, current_root=current_root)
    return {
        # Backward-compatible fields:
        "valid": verification["valid"],
        "anchor": anchor,
        # Extended verification details:
        "tx_id": tx_id,
        "tx_hash": tx_hash,
        "receipt_id": receipt.get("receipt_id"),
        "merkle_root": receipt.get("merkle_root"),
        "current_root": current_root,
        "is_current_root": verification.get("is_current_root"),
        "checks": verification.get("checks", {}),
    }


@router.get("/recent", response_model=List[TransactionResponse])
async def get_recent_transactions(
    limit: int = Query(default=50, ge=1, le=500),
    deps: LedgerDependencies = Depends(get_deps),
):
    """Get recent ledger transactions."""
    # Try async first, fall back to sync
    if hasattr(deps.ledger, 'list_recent_async'):
        transactions = await deps.ledger.list_recent_async(limit)
    else:
        transactions = deps.ledger.list_recent(limit)
    
    return [
        TransactionResponse(
            tx_id=tx.tx_id,
            from_wallet=tx.from_wallet,
            to_wallet=tx.to_wallet,
            amount=str(tx.amount),
            currency=tx.currency,
            chain=tx.on_chain_records[0].chain if tx.on_chain_records else None,
            chain_tx_hash=tx.on_chain_records[0].tx_hash if tx.on_chain_records else None,
            audit_anchor=tx.audit_anchor,
            created_at=tx.created_at.isoformat(),
            status=tx.on_chain_records[0].status if tx.on_chain_records else "pending",
        )
        for tx in transactions
    ]


@router.get("/stats")
async def get_ledger_stats(
    deps: LedgerDependencies = Depends(get_deps),
):
    """Get ledger statistics."""
    # Get recent transactions for stats
    if hasattr(deps.ledger, 'list_recent_async'):
        transactions = await deps.ledger.list_recent_async(1000)
    else:
        transactions = deps.ledger.list_recent(1000)
    
    total_volume = sum(float(tx.amount) for tx in transactions)
    
    return {
        "total_transactions": len(transactions),
        "total_volume": str(total_volume),
        "currency": "USDC",
    }
