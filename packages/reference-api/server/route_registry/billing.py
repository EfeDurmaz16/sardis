"""Billing route registration helpers."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from server.routes.billing import billing, subscriptions, usage


def register_subscription_routes(
    app: FastAPI,
    *,
    database_url: str,
    use_postgres: bool,
    wallet_repo: Any,
    agent_repo: Any,
    chain_executor: Any,
    wallet_manager: Any,
    compliance: Any,
    allow_simulated_autofund: bool,
    live_mode: bool,
) -> Any:
    """Register recurring subscription routes and return the billing service."""
    from server.repositories.subscriptions_repository import SubscriptionRepository
    from server.services.recurring_billing import RecurringBillingService

    subscription_repo = SubscriptionRepository(dsn=database_url if use_postgres else None)
    recurring_billing_service = RecurringBillingService(
        subscription_repo=subscription_repo,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=chain_executor,
        wallet_manager=wallet_manager,
        compliance=compliance,
        allow_simulated_autofund=allow_simulated_autofund,
    )
    if live_mode:
        recurring_billing_service.configure_autofund_handler(
            None,
            allow_simulated_fallback=False,
        )
    app.state.recurring_billing_runner = recurring_billing_service.process_due_subscriptions
    app.dependency_overrides[subscriptions.get_deps] = lambda: subscriptions.SubscriptionDependencies(
        subscription_repo=subscription_repo,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        recurring_service=recurring_billing_service,
    )
    app.include_router(subscriptions.router, prefix="/api/v2/subscriptions", tags=["subscriptions"])
    return recurring_billing_service


def register_billing_routes(app: FastAPI) -> None:
    """Register billing account and billing webhook routes."""
    app.include_router(billing.router)
    app.include_router(billing.webhook_router)


def register_usage_routes(app: FastAPI) -> None:
    """Register metered usage reporting routes."""
    app.include_router(usage.router, prefix="/api/v2", tags=["usage"])
