"""Wallet, ramp, and card route registration helpers."""
from __future__ import annotations

from fastapi import FastAPI

from sardis_server.routes.wallets import offramp, onramp, virtual_cards


def register_ramp_edge_routes(app: FastAPI) -> None:
    """Register simple fiat ramp and virtual-card edge routes."""
    app.include_router(offramp.router, prefix="/api/v2", tags=["offramp"])
    app.include_router(onramp.router, prefix="/api/v2", tags=["onramp"])
    app.include_router(
        onramp.webhook_router,
        prefix="/api/v2",
        tags=["stripe-onramp-webhooks"],
    )
    app.include_router(virtual_cards.router, prefix="/api/v2", tags=["virtual-cards"])
