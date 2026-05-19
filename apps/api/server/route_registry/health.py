"""Health route registration helpers."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from server.health import create_health_router


def register_health_routes(
    app: FastAPI,
    *,
    shutdown_state: Any,
    use_postgres: bool,
    database_url: str,
    redis_url: str,
    settings: Any,
) -> None:
    """Register liveness, readiness, and service discovery health routes."""
    app.include_router(
        create_health_router(
            shutdown_state=shutdown_state,
            use_postgres=use_postgres,
            database_url=database_url,
            redis_url=redis_url,
            settings=settings,
        )
    )
