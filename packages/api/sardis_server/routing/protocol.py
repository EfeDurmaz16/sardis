"""Protocol route registration helpers."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI

from sardis_server.routes.protocol import a2a, a2a_payments, acp, mpp, mpp_demo, spt, x402

logger = logging.getLogger("sardis_server.api.routing.protocol")


def register_x402_routes(app: FastAPI, *, facilitator_enabled: bool) -> None:
    """Register x402 facilitator routes when enabled."""
    if facilitator_enabled:
        app.include_router(x402.router, prefix="/api/v2/x402", tags=["x402"])
        logger.info("x402 facilitator router registered at /api/v2/x402")
    else:
        logger.info("x402 facilitator router disabled (set SARDIS_X402_FACILITATOR_ENABLED=true to enable)")


def register_erc8183_routes(app: FastAPI, *, enabled: bool) -> None:
    """Register ERC-8183 agentic commerce routes when enabled."""
    if enabled:
        from sardis_server.routes.protocol import erc8183

        app.include_router(erc8183.router, prefix="/api/v2", tags=["erc8183"])
        logger.info("ERC-8183 agentic commerce router registered at /api/v2/erc8183")
    else:
        logger.info("ERC-8183 router disabled (set SARDIS_ERC8183_ENABLED=true to enable)")


def register_a2a_routes(
    app: FastAPI,
    *,
    database_url: str,
    use_postgres: bool,
    wallet_repo: Any,
    agent_repo: Any,
    chain_executor: Any,
    wallet_manager: Any,
    ledger_store: Any,
    compliance: Any,
    identity_registry: Any,
    audit_store: Any,
    approval_service: Any,
) -> None:
    """Register A2A protocol routes and trust-repository dependencies."""
    from sardis_server.repositories.a2a_trust_repository import A2ATrustRepository

    a2a_trust_repo = A2ATrustRepository(dsn=database_url if use_postgres else None)
    app.state.a2a_trust_repo = a2a_trust_repo

    app.dependency_overrides[a2a.get_deps] = lambda: a2a.A2ADependencies(
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=chain_executor,
        wallet_manager=wallet_manager,
        ledger=ledger_store,
        compliance=compliance,
        identity_registry=identity_registry,
        trust_repo=a2a_trust_repo,
        audit_store=audit_store,
        approval_service=approval_service,
    )
    app.include_router(a2a.router, prefix="/api/v2/a2a", tags=["a2a"])
    app.include_router(a2a.public_router, prefix="/api/v2/a2a", tags=["a2a"])
    app.include_router(a2a_payments.router, prefix="/api/v2", tags=["a2a-payments"])


def register_a2a_discovery_routes(app: FastAPI) -> None:
    """Register A2A discovery routes that live outside the versioned API prefix."""

    @app.get("/.well-known/agent-card.json", tags=["a2a"])
    async def well_known_agent_card():
        """A2A agent card for discovery at the standard .well-known path."""
        return await a2a.get_agent_card()


def register_mpp_routes(app: FastAPI) -> None:
    """Register MPP and MPP demo routes."""
    app.include_router(mpp.router, prefix="/api/v2/mpp", tags=["mpp"])
    logger.info("MPP routes enabled")
    app.include_router(mpp_demo.router, prefix="/api/v2/demo", tags=["mpp-demo"])
    logger.info("MPP demo routes enabled")


def register_protocol_v1_routes(app: FastAPI) -> None:
    """Register protocol v1 adapter routes."""
    app.include_router(spt.router, prefix="/api/v2", tags=["spt"])
    app.include_router(acp.router, prefix="/api/v2", tags=["acp"])
