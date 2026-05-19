"""Developer-facing route registration helpers."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from sardis_v2_core.webhooks import WebhookRepository, WebhookService

from sardis_server.routes.developer import dev, sandbox, sdk_metrics, simulation, webhook_subscriptions

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
