"""Money movement route registration helpers."""
from __future__ import annotations

from fastapi import FastAPI
from sardis_v2_core.orchestrator import PaymentOrchestrator

from sardis_api.routes.money_movement import pay


def register_pay_endpoint(
    app: FastAPI,
    *,
    orchestrator: PaymentOrchestrator,
    chain_mode: str,
) -> None:
    """Register the unified payment execution endpoint."""
    app.dependency_overrides[pay.get_deps] = lambda: pay.PayDependencies(  # type: ignore[arg-type]
        orchestrator=orchestrator,
        chain_mode=chain_mode,
    )
    app.include_router(pay.router, prefix="/api/v2/pay", tags=["pay"])
