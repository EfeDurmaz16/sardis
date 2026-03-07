"""Admin reconciliation API — ledger vs on-chain comparison.

Exposes the existing ReconciliationEngine behind admin-only endpoints.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.middleware.mfa import require_mfa_if_enabled
from sardis_api.routers.admin import require_admin_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_mfa_if_enabled)])


class ReconciliationCheckRequest(BaseModel):
    """Request to reconcile a specific wallet or entry."""
    wallet_id: Optional[str] = Field(default=None, description="Wallet to reconcile")
    entry_id: Optional[str] = Field(default=None, description="Specific ledger entry ID")
    chain: Optional[str] = Field(default=None, description="Chain filter (e.g. 'base')")
    limit: int = Field(default=50, ge=1, le=500, description="Max entries to reconcile")


class ReconciliationResultResponse(BaseModel):
    """Result of a reconciliation check."""
    total_checked: int = 0
    matched: int = 0
    unmatched: int = 0
    discrepancies: list[dict[str, Any]] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


@router.post("/check", response_model=ReconciliationResultResponse)
async def reconciliation_check(
    request: Request,
    body: ReconciliationCheckRequest,
    _: None = Depends(require_admin_rate_limit(is_sensitive=True)),
):
    """Run reconciliation check for specified entries.

    Compares ledger entries against on-chain state and returns discrepancies.
    """
    try:
        from sardis_ledger.reconciliation import ReconciliationEngine

        # Get the reconciliation engine from app state or create one
        engine = getattr(request.app.state, "reconciliation_engine", None)
        if engine is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Reconciliation engine not configured",
            )

        # Fetch entries to reconcile
        ledger_repo = getattr(request.app.state, "ledger_repo", None)
        if ledger_repo is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ledger repository not configured",
            )

        if body.entry_id:
            entry = await ledger_repo.get_entry(body.entry_id)
            if not entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ledger entry {body.entry_id} not found",
                )
            entries = [entry]
        elif body.wallet_id:
            entries = await ledger_repo.list_entries(
                wallet_id=body.wallet_id,
                chain=body.chain,
                limit=body.limit,
            )
        else:
            entries = await ledger_repo.list_entries(
                chain=body.chain,
                limit=body.limit,
            )

        if not entries:
            return ReconciliationResultResponse(
                total_checked=0,
                stats={"message": "No entries found matching criteria"},
            )

        # Run reconciliation
        records = await engine.reconcile_batch(entries, actor_id="admin")

        matched = sum(1 for r in records if r.status.value == "matched")
        unmatched = sum(1 for r in records if r.status.value != "matched")

        discrepancies = []
        for r in records:
            if r.status.value != "matched":
                discrepancies.append({
                    "entry_id": r.ledger_entry_id,
                    "chain": r.chain,
                    "tx_hash": r.chain_tx_hash,
                    "ledger_amount": str(r.ledger_amount),
                    "chain_amount": str(r.chain_amount) if r.chain_amount is not None else None,
                    "discrepancy_amount": str(r.discrepancy_amount) if r.discrepancy_amount is not None else None,
                    "reason": r.discrepancy_reason,
                    "status": r.status.value,
                })

        return ReconciliationResultResponse(
            total_checked=len(records),
            matched=matched,
            unmatched=unmatched,
            discrepancies=discrepancies,
            stats=engine._stats,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Reconciliation check failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reconciliation failed: {e}",
        )


@router.get("/stats")
async def reconciliation_stats(
    request: Request,
    _: None = Depends(require_admin_rate_limit()),
):
    """Get current reconciliation statistics."""
    engine = getattr(request.app.state, "reconciliation_engine", None)
    if engine is None:
        return {
            "configured": False,
            "message": "Reconciliation engine not configured",
        }

    return {
        "configured": True,
        "stats": engine._stats,
        "discrepancy_count": len(engine._discrepancies),
    }
