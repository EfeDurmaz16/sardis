"""Identity and enterprise authentication route registration helpers."""
from __future__ import annotations

import logging

from fastapi import FastAPI

logger = logging.getLogger("server.api.routing.identity")


def register_agent_auth_routes(app: FastAPI) -> None:
    """Register Agent Auth Protocol discovery and management routes."""
    try:
        from server.routes.identity import agent_auth
    except ImportError:
        logger.warning("Agent Auth Protocol router not available")
        return

    app.include_router(agent_auth.discovery_router, tags=["agent-auth"])
    app.include_router(agent_auth.router, prefix="/api/v2", tags=["agent-auth"])
    logger.info("Agent Auth Protocol enabled (discovery + capability execution)")


def register_sso_routes(app: FastAPI) -> None:
    """Register SAML/OIDC SSO routes when the middleware module is installed."""
    try:
        from server.middleware.sso import router as sso_router
    except ImportError:
        logger.warning("SSO router not available")
        return

    app.include_router(sso_router, prefix="/api/v2", tags=["sso"])
