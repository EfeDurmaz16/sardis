"""Ledger API routes for transaction history."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from sardis_ledger.records import LedgerStore


router = APIRouter(tags=["ledger"])


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


class LedgerDependencies:
    """Dependencies for ledger routes."""
    def __init__(self, ledger: LedgerStore):
        self.ledger = ledger


def get_deps() -> LedgerDependencies:
    """Dependency injection placeholder."""
    raise NotImplementedError("Must be overridden")


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
