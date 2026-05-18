"""Execution mode discovery and simulation endpoints."""
from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from sardis_api.authz import require_principal

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/execution-modes",
    tags=["execution-modes"],
    dependencies=[Depends(require_principal)],
)


class SimulateRequest(BaseModel):
    agent_id: str
    amount: str
    currency: str = "USDC"
    merchant_id: str | None = None
    execution_mode: str | None = None


def _get_mode_router(request: Request):
    router_instance = getattr(request.app.state, "execution_mode_router", None)
    if router_instance is None:
        raise HTTPException(503, "Execution mode router not initialized")
    return router_instance


@router.get("/available")
async def available_modes(
    request: Request,
    agent_id: str = Query(...),
    amount: str = Query(...),
    currency: str = Query("USDC"),
    merchant_id: str | None = Query(None),
    mode_router=Depends(_get_mode_router),
):
    """Available execution modes for agent + amount + currency + merchant."""
    modes = await mode_router.get_available_modes(
        agent_id=agent_id,
        amount=Decimal(amount),
        currency=currency,
        merchant_id=merchant_id,
    )
    return {
        "modes": [m.to_dict() for m in modes],
        "count": len(modes),
    }


@router.post("/simulate")
async def simulate_mode(
    body: SimulateRequest,
    mode_router=Depends(_get_mode_router),
):
    """Dry-run execution via specific mode."""
    from sardis_v2_core.execution_intent import ExecutionIntent

    intent = ExecutionIntent(
        agent_id=body.agent_id,
        amount=Decimal(body.amount),
        currency=body.currency,
        metadata={
            "merchant_id": body.merchant_id or "",
            "execution_mode": body.execution_mode or "",
        },
    )

    try:
        selection = await mode_router.resolve(intent)
        return {
            "viable": True,
            "selection": selection.to_dict(),
        }
    except ValueError as e:
        return {
            "viable": False,
            "error": str(e),
        }
