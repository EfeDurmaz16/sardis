"""Agent route registration helpers."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from sardis_server.routes.agents import (
    agent_activity,
    agent_events,
    agent_heartbeat,
    agent_registry,
    agents,
)
from sardis_server.routes.identity import fides_identity


def register_agent_lifecycle_routes(
    app: FastAPI,
    *,
    agent_repo: Any,
    wallet_repo: Any,
    kya_service: Any,
    wallet_manager: Any,
    database_url: str,
    settings: Any,
) -> None:
    """Register agent lifecycle, activity, heartbeat, events, and FIDES identity routes."""
    app.dependency_overrides[agents.get_deps] = lambda: agents.AgentDependencies(  # type: ignore[arg-type]
        agent_repo=agent_repo,
        wallet_repo=wallet_repo,
        kya_service=kya_service,
        wallet_manager=wallet_manager,
    )
    app.include_router(agents.router, prefix="/api/v2/agents", tags=["agents"])
    app.include_router(agent_activity.router, prefix="/api/v2/agents", tags=["agent-activity"])

    app.dependency_overrides[agent_heartbeat.get_deps] = lambda: agent_heartbeat.HeartbeatDependencies(
        database_url=database_url,
    )
    app.include_router(agent_heartbeat.router, prefix="/api/v2/agents", tags=["agent-heartbeat"])

    app.dependency_overrides[agent_events.get_deps] = lambda: agent_events.EventsDependencies(
        database_url=database_url,
    )
    app.include_router(agent_events.router, prefix="/api/v2/agents", tags=["agent-events"])

    if settings.fides.enabled:
        app.dependency_overrides[fides_identity.get_agent_repo] = lambda: agent_repo
        app.include_router(fides_identity.router, prefix="/api/v2", tags=["fides-identity"])


def register_agent_registry_routes(app: FastAPI) -> None:
    """Register agent discovery and registry routes."""
    app.include_router(agent_registry.router)
    app.include_router(agent_registry.public_router)
