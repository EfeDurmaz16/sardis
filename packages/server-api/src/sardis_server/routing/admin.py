"""Admin-only route registration helpers."""
from __future__ import annotations

from fastapi import FastAPI

from sardis_server.routes.admin import control, reconciliation
from sardis_server.routes.operations import emergency


def register_admin_routes(app: FastAPI) -> None:
    """Register privileged admin, reconciliation, and emergency routes."""
    app.include_router(control.router, prefix="/api/v2/admin", tags=["admin"])
    app.include_router(
        reconciliation.router,
        prefix="/api/v2/admin/reconciliation",
        tags=["admin", "reconciliation"],
    )
    app.include_router(emergency.router)
