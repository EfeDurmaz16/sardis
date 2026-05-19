"""Operations route registration helpers."""
from __future__ import annotations

from fastapi import FastAPI

from sardis_server.routes.operations import (
    alerts,
    analytics,
    dashboard_metrics,
    event_stream,
    exceptions,
    execution_modes,
    metrics,
    outcomes,
    reliability,
    ws_alerts,
)


def register_alert_routes(app: FastAPI) -> None:
    """Register alert REST routes."""
    app.include_router(alerts.router, prefix="/api/v2/alerts", tags=["alerts"])


def register_realtime_operations_routes(app: FastAPI) -> None:
    """Register realtime dashboard and observability routes."""
    app.include_router(ws_alerts.router, prefix="/api/v2")
    app.include_router(event_stream.router, prefix="/api/v2/events", tags=["events"])
    app.include_router(analytics.router)
    app.include_router(metrics.router)


def register_execution_mode_routes(app: FastAPI) -> None:
    """Register execution-mode inspection and control routes."""
    app.include_router(execution_modes.router)


def register_outcome_reliability_routes(app: FastAPI) -> None:
    """Register outcome and reliability reporting routes."""
    app.include_router(outcomes.router, prefix="/api/v2", tags=["outcomes"])
    app.include_router(reliability.router, prefix="/api/v2/reliability", tags=["reliability"])


def register_exception_routes(app: FastAPI) -> None:
    """Register exception workflow routes."""
    app.include_router(exceptions.router, prefix="/api/v2", tags=["exceptions"])


def register_dashboard_metrics_routes(app: FastAPI) -> None:
    """Register dashboard metrics routes."""
    app.include_router(dashboard_metrics.router, prefix="/api/v2/dashboard", tags=["dashboard"])
