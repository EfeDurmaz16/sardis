"""Commerce route registration helpers."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from sardis_server.repositories.secure_checkout_job_repository import SecureCheckoutJobRepository
from sardis_server.routes.commerce import (
    checkout,
    checkout_controls,
    counterparties,
    escrow_disputes,
    invoices,
    marketplace,
    merchants,
    secure_checkout,
    service_directory,
)


def register_checkout_routes(
    app: FastAPI,
    *,
    database_url: str,
    use_postgres: bool,
    orchestrator: Any,
) -> None:
    """Register agentic checkout routes and their wallet repository dependency."""
    from sardis_v2_core.wallet_repository import WalletRepository

    wallet_repo = WalletRepository(dsn=database_url if use_postgres else "memory://")
    app.dependency_overrides[checkout.get_deps] = lambda: checkout.CheckoutDependencies(  # type: ignore[arg-type]
        wallet_repo=wallet_repo,
        orchestrator=orchestrator,
    )
    app.include_router(checkout.router, prefix="/api/v2/checkout", tags=["checkout"])
    if hasattr(checkout, "public_router"):
        app.include_router(checkout.public_router, prefix="/api/v2/checkout", tags=["checkout"])


def register_secure_checkout_routes(
    app: FastAPI,
    *,
    database_url: str,
    use_postgres: bool,
    is_production: bool,
    wallet_repo: Any,
    agent_repo: Any,
    card_repo: Any,
    card_provider: Any,
    policy_store: Any,
    approval_service: Any,
    audit_store: Any,
    cache_service: Any,
) -> None:
    """Register secure checkout executor routes and fail closed without persistent storage in production."""
    import os

    secure_checkout_store: Any = secure_checkout.InMemorySecureCheckoutStore()
    if use_postgres:
        secure_checkout_job_repo = SecureCheckoutJobRepository(dsn=database_url)
        secure_checkout_store = secure_checkout.RepositoryBackedSecureCheckoutStore(
            secure_checkout_job_repo,
            cache_service=cache_service,
        )
    secure_checkout_enabled = os.getenv("SARDIS_ENABLE_SECURE_CHECKOUT_EXECUTOR", "1").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if is_production and secure_checkout_enabled and not use_postgres:
        raise RuntimeError("secure_checkout_executor requires PostgreSQL in production")

    app.dependency_overrides[secure_checkout.get_deps] = lambda: secure_checkout.SecureCheckoutDependencies(
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        card_repo=card_repo,
        card_provider=card_provider,
        policy_store=policy_store,
        approval_service=approval_service,
        audit_sink=audit_store,
        cache_service=cache_service,
        store=secure_checkout_store,
    )
    if secure_checkout_enabled:
        app.include_router(
            secure_checkout.router,
            prefix="/api/v2/checkout",
            tags=["checkout-secure"],
        )


def register_merchant_routes(
    app: FastAPI,
    *,
    merchant_repo: Any,
    wallet_manager: Any,
    settlement_service: Any,
    checkout_base_url: str,
) -> None:
    """Register merchant management and checkout-link routes."""
    app.dependency_overrides[merchants.get_deps] = lambda: merchants.MerchantDependencies(
        merchant_repo=merchant_repo,
        wallet_manager=wallet_manager,
        settlement_service=settlement_service,
        checkout_base_url=checkout_base_url,
    )
    app.include_router(merchants.router, prefix="/api/v2/merchants", tags=["merchants"])


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
