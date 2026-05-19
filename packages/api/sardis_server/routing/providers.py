"""Provider integration and webhook route registration helpers."""
from __future__ import annotations

import logging

from fastapi import FastAPI

from sardis_server.routes.providers import mastercard_webhooks

logger = logging.getLogger("sardis_server.api.routing.providers")


def register_mastercard_webhook_routes(app: FastAPI) -> None:
    """Register Mastercard Agent Pay inbound webhook routes."""
    app.include_router(mastercard_webhooks.router)
    logger.info("Mastercard webhook router enabled at /mastercard/webhooks")
