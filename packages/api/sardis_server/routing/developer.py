"""Developer-facing route registration helpers."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from sardis_v2_core.webhooks import WebhookRepository, WebhookService

from sardis_server.routes.developer import (
    dev,
    enterprise_support,
    environment_templates,
    faucet,
    notifications,
    sandbox,
    sdk_metrics,
    simulation,
    webhook_subscriptions,
    workflow_templates,
)

logger = logging.getLogger("sardis_server.api.routing.developer")


def register_webhook_subscriptions(app: FastAPI, *, dsn: str) -> WebhookService:
    """Register outbound webhook subscription routes.

    These are the customer-facing `/api/v2/webhooks` endpoints. Inbound provider
    callbacks remain in provider-specific routers.
    """
    webhook_repo = WebhookRepository(dsn=dsn)
    webhook_service = WebhookService(repository=webhook_repo)
    app.dependency_overrides[webhook_subscriptions.get_deps] = (
        lambda: webhook_subscriptions.WebhookDependencies(
            repository=webhook_repo,
            service=webhook_service,
        )
    )
    app.include_router(webhook_subscriptions.router, prefix="/api/v2/webhooks")
    app.state.webhook_service = webhook_service
    return webhook_service


def register_developer_utility_routes(app: FastAPI, *, is_production: bool) -> None:
    """Register public developer utilities and non-production dev routes."""
    app.include_router(sdk_metrics.router)
    app.include_router(simulation.router, prefix="/api/v2/simulate", tags=["simulation"])

    if not is_production:
        app.include_router(dev.router, prefix="/api/v2/dev", tags=["dev"])
        logger.info("Dev routes enabled (faucet, etc.)")

    sandbox_env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
    sandbox_flag = os.getenv("SARDIS_ENABLE_SANDBOX", "").strip().lower()
    sandbox_enabled_explicit = sandbox_flag in ("1", "true", "yes", "on")
    sandbox_disabled_explicit = sandbox_flag in ("0", "false", "no", "off")
    if sandbox_env in ("prod", "production"):
        sandbox_enabled = sandbox_enabled_explicit
    else:
        sandbox_enabled = not sandbox_disabled_explicit

    if sandbox_enabled:
        app.include_router(sandbox.router, prefix="/api/v2/sandbox", tags=["sandbox"])
        logger.info("Sandbox/Playground routes enabled")
    else:
        logger.info("Sandbox/Playground routes disabled")


def register_enterprise_support_routes(
    app: FastAPI,
    *,
    database_url: str,
    use_postgres: bool,
) -> None:
    """Register enterprise support ticket/profile routes."""
    from sardis_server.repositories.enterprise_support_repository import EnterpriseSupportRepository

    support_repo = EnterpriseSupportRepository(dsn=database_url if use_postgres else None)
    app.dependency_overrides[enterprise_support.get_deps] = (
        lambda: enterprise_support.EnterpriseSupportDependencies(
            support_repo=support_repo,
        )
    )
    app.include_router(enterprise_support.router)


def register_faucet_routes(app: FastAPI) -> None:
    """Register testnet faucet routes."""
    app.include_router(faucet.router, prefix="/api/v2/faucet", tags=["faucet"])


def register_notification_routes(app: FastAPI) -> None:
    """Register notification webhook configuration routes."""
    app.include_router(
        notifications.router,
        prefix="/api/v2/notifications",
        tags=["notifications"],
    )


def register_template_routes(app: FastAPI) -> None:
    """Register workflow and environment template routes."""
    app.include_router(
        workflow_templates.router,
        prefix="/api/v2/templates",
        tags=["workflow-templates"],
    )
    app.include_router(
        environment_templates.router,
        prefix="/api/v2/environments",
        tags=["Environment Templates"],
    )
