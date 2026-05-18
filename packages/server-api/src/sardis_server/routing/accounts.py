"""Account and authentication route registration helpers."""
from __future__ import annotations

from fastapi import FastAPI
from sardis_v2_core.agent_groups import AgentGroupRepository

from sardis_server.routes.accounts import api_keys, auth, data_export, email_verification, groups, me


def register_auth_routes(app: FastAPI) -> None:
    """Register user authentication and verification routes."""
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(auth.router, prefix="/api/v2/auth")
    app.include_router(email_verification.router, prefix="/api/v2/auth", tags=["auth"])


def register_account_group_routes(app: FastAPI) -> None:
    """Register account group and API key routes."""
    group_repo = AgentGroupRepository(dsn="memory://")
    app.dependency_overrides[groups.get_deps] = lambda: groups.GroupDependencies(  # type: ignore[arg-type]
        group_repo=group_repo,
    )
    app.include_router(groups.router, prefix="/api/v2/groups", tags=["groups"])
    app.include_router(api_keys.router, prefix="/api/v2/api-keys", tags=["api-keys"])


def register_account_self_service_routes(app: FastAPI) -> None:
    """Register per-user account and data export routes."""
    app.include_router(me.router)
    app.include_router(data_export.router, tags=["account"])
