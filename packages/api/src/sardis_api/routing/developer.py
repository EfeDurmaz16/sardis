"""Developer-facing route registration helpers."""
from __future__ import annotations

from fastapi import FastAPI
from sardis_v2_core.webhooks import WebhookRepository, WebhookService

from sardis_api.routes.developer import webhook_subscriptions


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
