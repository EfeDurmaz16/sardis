"""SDK install metrics API endpoints.

Provides aggregate and per-package SDK download metrics
from PyPI and npm for investor-grade reporting.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.services.sdk_metrics import SDKMetricsService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/metrics",
    tags=["metrics", "sdk"],
)

# Singleton metrics service (caches internally)
_metrics_service = SDKMetricsService()


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class PackageStatsResponse(BaseModel):
    package: str
    registry: str
    last_day: int = 0
    last_week: int = 0
    last_month: int = 0


class AggregateMetricsResponse(BaseModel):
    total_installs: int
    pypi_total: int
    npm_total: int
    packages: list[PackageStatsResponse]
    growth_rate_weekly: float
    fetched_at: str


class GrowthResponse(BaseModel):
    weekly_installs: int
    growth_rate_weekly: float
    packages: list[PackageStatsResponse]
    fetched_at: str


# ---------------------------------------------------------------------------
# Endpoints (public — no auth required for transparency)
# ---------------------------------------------------------------------------

@router.get("/sdk-installs", response_model=AggregateMetricsResponse)
async def get_sdk_installs():
    """Get aggregate SDK install metrics across all packages."""
    metrics = await _metrics_service.get_aggregate_metrics()
    return AggregateMetricsResponse(
        total_installs=metrics.total_installs,
        pypi_total=metrics.pypi_total,
        npm_total=metrics.npm_total,
        packages=[
            PackageStatsResponse(
                package=p.package,
                registry=p.registry,
                last_day=p.last_day,
                last_week=p.last_week,
                last_month=p.last_month,
            )
            for p in metrics.packages
        ],
        growth_rate_weekly=metrics.growth_rate_weekly,
        fetched_at=metrics.fetched_at,
    )


@router.get("/sdk-installs/{package:path}", response_model=PackageStatsResponse)
async def get_package_installs(package: str):
    """Get download stats for a specific package."""
    stats = await _metrics_service.get_package_stats(package)
    return PackageStatsResponse(
        package=stats.package,
        registry=stats.registry,
        last_day=stats.last_day,
        last_week=stats.last_week,
        last_month=stats.last_month,
    )


@router.get("/growth", response_model=GrowthResponse)
async def get_growth_metrics():
    """Get week-over-week growth rates across all SDK packages."""
    metrics = await _metrics_service.get_aggregate_metrics()
    return GrowthResponse(
        weekly_installs=sum(p.last_week for p in metrics.packages),
        growth_rate_weekly=metrics.growth_rate_weekly,
        packages=[
            PackageStatsResponse(
                package=p.package,
                registry=p.registry,
                last_day=p.last_day,
                last_week=p.last_week,
                last_month=p.last_month,
            )
            for p in metrics.packages
        ],
        fetched_at=metrics.fetched_at,
    )
