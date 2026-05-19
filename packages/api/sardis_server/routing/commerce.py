"""Commerce route registration helpers."""
from __future__ import annotations

from fastapi import FastAPI

from sardis_server.routes.commerce import (
    checkout_controls,
    counterparties,
    escrow_disputes,
    invoices,
    marketplace,
    service_directory,
)


def register_marketplace_routes(
    app: FastAPI,
    *,
    database_url: str,
    use_postgres: bool,
) -> None:
    """Register marketplace routes and their repository dependency."""
    from sardis_v2_core.marketplace import MarketplaceRepository

    marketplace_repo = MarketplaceRepository(dsn=database_url if use_postgres else "memory://")
    app.dependency_overrides[marketplace.get_deps] = lambda: marketplace.MarketplaceDependencies(  # type: ignore[arg-type]
        repository=marketplace_repo,
    )
    app.include_router(marketplace.router, prefix="/api/v2/marketplace")


def register_invoice_routes(app: FastAPI) -> None:
    """Register invoice routes."""
    app.include_router(invoices.router, prefix="/api/v2/invoices", tags=["invoices"])


def register_service_directory_routes(app: FastAPI) -> None:
    """Register public service-directory routes."""
    app.include_router(service_directory.router)


def register_commerce_support_routes(app: FastAPI) -> None:
    """Register commerce support routes used by checkout and merchants."""
    app.include_router(checkout_controls.router, prefix="/api/v2/checkout-controls", tags=["checkout-controls"])
    app.include_router(counterparties.router, prefix="/api/v2/counterparties", tags=["counterparties"])


def register_escrow_dispute_routes(app: FastAPI) -> None:
    """Register escrow and dispute routes."""
    app.include_router(escrow_disputes.router, prefix="/api/v2", tags=["escrow", "disputes"])
