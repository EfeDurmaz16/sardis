"""Policy route registration helpers."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI

from sardis_server.routes.policy import (
    fallback_policies,
    policies,
    policy_analytics,
    policy_simulation,
)

logger = logging.getLogger("sardis_server.api.routing.policy")


def register_policy_routes(
    app: FastAPI,
    *,
    policy_store: Any,
    agent_repo: Any,
) -> None:
    """Register core policy routes and dependency wiring."""
    app.dependency_overrides[policies.get_deps] = lambda: policies.PolicyDependencies(  # type: ignore[attr-defined]
        policy_store=policy_store,
        agent_repo=agent_repo,
    )
    app.include_router(policies.router, prefix="/api/v2/policies", tags=["policies"])


def register_policy_simulation_routes(app: FastAPI) -> None:
    """Register policy simulation routes."""
    app.include_router(policy_simulation.router, prefix="/api/v2/policies", tags=["policy-dsl"])


def register_policy_analytics_routes(app: FastAPI) -> None:
    """Register policy analytics routes."""
    app.include_router(
        policy_analytics.router,
        prefix="/api/v2/policies/analytics",
        tags=["policy-analytics"],
    )


def register_fallback_policy_routes(app: FastAPI) -> None:
    """Register fallback policy routes."""
    app.include_router(fallback_policies.router, prefix="/api/v2/fallback", tags=["Fallback Policies"])
    logger.info("Fallback policies router registered at /api/v2/fallback")
