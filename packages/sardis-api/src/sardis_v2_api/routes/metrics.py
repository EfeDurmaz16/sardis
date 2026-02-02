"""
Metrics API Routes

Investor dashboard and real-time metrics endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from sardis_v2_core.analytics import (
    get_analytics,
    MetricsSummary,
    AnalyticsService,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


class DashboardResponse(BaseModel):
    """Dashboard metrics response."""
    timestamp: str
    period: str

    # Wallet metrics
    total_wallets: int
    new_wallets_period: int
    active_wallets: int

    # Transaction metrics
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    blocked_transactions: int
    success_rate: float
    total_volume_usd: float
    average_transaction_usd: float

    # API metrics
    api_requests: int
    api_error_rate: float

    # MCP metrics
    mcp_tool_calls: int
    mcp_sessions: int

    # Compliance metrics
    kyc_completions: int
    aml_checks: int

    # Product metrics
    cards_issued: int
    fiat_volume: float


class RealtimeResponse(BaseModel):
    """Real-time stats response."""
    timestamp: str
    wallets_created_today: int
    transactions_today: int
    volume_today_usd: float
    api_requests_today: int
    mcp_calls_today: int
    current_success_rate: float


class HealthResponse(BaseModel):
    """System health response."""
    status: str
    timestamp: str
    components: dict


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_metrics(
    period: str = Query("30d", regex="^(7d|30d|90d|all)$"),
) -> DashboardResponse:
    """
    Get aggregated metrics for investor dashboard.

    Periods:
    - 7d: Last 7 days
    - 30d: Last 30 days (default)
    - 90d: Last 90 days
    - all: All time
    """
    analytics = get_analytics()

    now = datetime.utcnow()
    if period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "30d":
        start_date = now - timedelta(days=30)
    elif period == "90d":
        start_date = now - timedelta(days=90)
    else:  # all
        start_date = datetime(2024, 1, 1)  # Platform launch date

    summary = await analytics.get_metrics_summary(start_date, now)

    # Calculate success rate
    total_tx = max(summary.total_transactions, 1)
    success_rate = (summary.successful_transactions / total_tx) * 100

    return DashboardResponse(
        timestamp=now.isoformat(),
        period=period,
        total_wallets=summary.total_wallets,
        new_wallets_period=summary.new_wallets,
        active_wallets=summary.active_wallets,
        total_transactions=summary.total_transactions,
        successful_transactions=summary.successful_transactions,
        failed_transactions=summary.failed_transactions,
        blocked_transactions=summary.blocked_transactions,
        success_rate=round(success_rate, 2),
        total_volume_usd=round(summary.total_volume_usd, 2),
        average_transaction_usd=round(summary.average_transaction_usd, 2),
        api_requests=summary.api_requests,
        api_error_rate=round(summary.api_error_rate * 100, 2),
        mcp_tool_calls=summary.mcp_tool_calls,
        mcp_sessions=summary.mcp_sessions,
        kyc_completions=summary.kyc_completions,
        aml_checks=summary.aml_checks,
        cards_issued=summary.cards_issued,
        fiat_volume=round(summary.fiat_onramp_volume + summary.fiat_offramp_volume, 2),
    )


@router.get("/realtime", response_model=RealtimeResponse)
async def get_realtime_stats() -> RealtimeResponse:
    """
    Get real-time stats for live dashboard.

    Updates every minute. Shows today's metrics.
    """
    analytics = get_analytics()
    stats = await analytics.get_realtime_stats()

    return RealtimeResponse(
        timestamp=stats["timestamp"],
        wallets_created_today=stats["today"]["wallets_created"],
        transactions_today=stats["today"]["transactions"],
        volume_today_usd=stats["today"]["volume_usd"],
        api_requests_today=stats["today"]["api_requests"],
        mcp_calls_today=stats["today"]["mcp_calls"],
        current_success_rate=round(stats["success_rate"], 2),
    )


@router.get("/health", response_model=HealthResponse)
async def get_system_health() -> HealthResponse:
    """
    Get system health status.

    Checks all critical components.
    """
    components = {}

    # Check analytics
    try:
        analytics = get_analytics()
        await analytics.get_realtime_stats()
        components["analytics"] = "healthy"
    except Exception as e:
        components["analytics"] = f"degraded: {str(e)}"

    # Check database
    import os
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            import asyncpg
            conn = await asyncpg.connect(db_url, timeout=5)
            await conn.execute("SELECT 1")
            await conn.close()
            components["database"] = "healthy"
        except Exception as e:
            components["database"] = f"degraded: {str(e)}"
    else:
        components["database"] = "in_memory"

    # Check Redis
    redis_url = os.getenv("UPSTASH_REDIS_URL") or os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(redis_url, socket_connect_timeout=3)
            await r.ping()
            await r.aclose()
            components["redis"] = "healthy"
        except Exception as e:
            components["redis"] = f"degraded: {str(e)}"

    # Overall status
    all_healthy = all(v == "healthy" or v == "in_memory" for v in components.values())
    status = "healthy" if all_healthy else "degraded"

    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow().isoformat(),
        components=components,
    )


@router.get("/export")
async def export_metrics(
    format: str = Query("json", regex="^(json|csv)$"),
    period: str = Query("30d", regex="^(7d|30d|90d|all)$"),
):
    """
    Export metrics data for external analysis.

    Formats:
    - json: JSON format
    - csv: CSV format
    """
    analytics = get_analytics()

    now = datetime.utcnow()
    if period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "30d":
        start_date = now - timedelta(days=30)
    elif period == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = datetime(2024, 1, 1)

    summary = await analytics.get_metrics_summary(start_date, now)

    data = {
        "export_timestamp": now.isoformat(),
        "period_start": start_date.isoformat(),
        "period_end": now.isoformat(),
        "metrics": {
            "wallets": {
                "total": summary.total_wallets,
                "new": summary.new_wallets,
                "active": summary.active_wallets,
            },
            "transactions": {
                "total": summary.total_transactions,
                "successful": summary.successful_transactions,
                "failed": summary.failed_transactions,
                "blocked": summary.blocked_transactions,
                "volume_usd": summary.total_volume_usd,
                "avg_usd": summary.average_transaction_usd,
            },
            "api": {
                "requests": summary.api_requests,
                "errors": summary.api_errors,
                "error_rate": summary.api_error_rate,
            },
            "mcp": {
                "tool_calls": summary.mcp_tool_calls,
                "sessions": summary.mcp_sessions,
            },
            "compliance": {
                "kyc_completions": summary.kyc_completions,
                "aml_checks": summary.aml_checks,
            },
            "products": {
                "cards_issued": summary.cards_issued,
                "card_volume_usd": summary.card_volume_usd,
                "fiat_onramp": summary.fiat_onramp_volume,
                "fiat_offramp": summary.fiat_offramp_volume,
            },
        },
    }

    if format == "csv":
        # Convert to CSV format
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Metric", "Value"])

        # Flatten metrics
        for category, values in data["metrics"].items():
            for key, value in values.items():
                writer.writerow([f"{category}_{key}", value])

        return {"content_type": "text/csv", "data": output.getvalue()}

    return data
