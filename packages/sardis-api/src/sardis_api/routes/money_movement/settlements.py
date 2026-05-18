"""Settlement tracking API endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from sardis_api.authz import require_principal

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/settlements",
    tags=["settlements"],
    dependencies=[Depends(require_principal)],
)


def _get_settlement_store(request: Request):
    store = getattr(request.app.state, "settlement_store", None)
    if store is None:
        raise HTTPException(503, "Settlement store not initialized")
    return store


@router.get("")
async def list_settlements(
    request: Request,
    mode: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    store=Depends(_get_settlement_store),
):
    """List settlements for the org."""
    all_records = list(getattr(store, '_records', {}).values()) if hasattr(store, '_records') else await store.get_pending()
    results = []
    for r in all_records:
        if mode and r.mode.value != mode:
            continue
        if status and r.status.value != status:
            continue
        results.append(r.to_dict())
        if len(results) >= limit:
            break
    return {"settlements": results, "count": len(results)}


@router.get("/summary")
async def settlement_summary(
    request: Request,
    store=Depends(_get_settlement_store),
):
    """Aggregated settlement summary by mode."""
    summary = await store.get_summary()
    return {"summary": summary}


@router.get("/{settlement_id}")
async def get_settlement(
    settlement_id: str,
    store=Depends(_get_settlement_store),
):
    """Get settlement details."""
    record = await store.get(settlement_id)
    if record is None:
        raise HTTPException(404, "Settlement not found")
    return record.to_dict()


@router.post("/{settlement_id}/retry")
async def retry_settlement(
    settlement_id: str,
    store=Depends(_get_settlement_store),
):
    """Admin retry a failed settlement."""
    from sardis_v2_core.settlement import SettlementStatus

    record = await store.get(settlement_id)
    if record is None:
        raise HTTPException(404, "Settlement not found")
    if record.status != SettlementStatus.FAILED:
        raise HTTPException(400, f"Cannot retry settlement in status {record.status.value}")
    await store.update_status(
        settlement_id, SettlementStatus.INITIATED,
    )
    return {"status": "retrying", "settlement_id": settlement_id}
