"""
Analytics API Router for Sardis

Endpoints for spending analytics, budget tracking, and anomaly detection.
Designed for consumption by the dashboard frontend (Recharts compatible).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Literal
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_v2_core.database import get_db_pool
from sardis_v2_core.anomaly_detection import AnomalyDetector, AnomalyResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/analytics", tags=["analytics"])


# ============================================================================
# Request/Response Models
# ============================================================================

class TimeSeriesDataPoint(BaseModel):
    """Single data point in time series."""
    date: str
    amount: float
    count: int


class SpendingOverTimeResponse(BaseModel):
    """Response for spending-over-time endpoint."""
    period: str
    data: List[TimeSeriesDataPoint]
    total: float
    average: float


class AgentSpendingItem(BaseModel):
    """Spending data for a single agent."""
    agent_id: str
    agent_name: Optional[str] = None
    total: float
    transaction_count: int
    average: float


class AgentSpendingResponse(BaseModel):
    """Response for spending-by-agent endpoint."""
    agents: List[AgentSpendingItem]
    total: float


class CategorySpendingItem(BaseModel):
    """Spending data for a single category/merchant."""
    name: str
    amount: float
    count: int
    percentage: float


class CategorySpendingResponse(BaseModel):
    """Response for category/merchant breakdown."""
    categories: List[CategorySpendingItem]
    total: float


class BudgetUtilizationItem(BaseModel):
    """Budget utilization for a single agent."""
    agent_id: str
    agent_name: Optional[str] = None
    spent: float
    budget: float
    utilization: float  # 0-100
    remaining: float


class BudgetUtilizationResponse(BaseModel):
    """Response for budget utilization endpoint."""
    items: List[BudgetUtilizationItem]


class PolicyBlockItem(BaseModel):
    """Policy block event."""
    timestamp: str
    agent_id: str
    agent_name: Optional[str] = None
    amount: float
    merchant: str
    reason: str


class PolicyBlocksResponse(BaseModel):
    """Response for policy blocks endpoint."""
    blocks: List[PolicyBlockItem]
    total_blocks: int
    block_rate: float  # Percentage of transactions blocked
    total_transactions: int


class TopMerchantItem(BaseModel):
    """Top merchant data."""
    merchant: str
    amount: float
    count: int
    percentage: float


class TopMerchantsResponse(BaseModel):
    """Response for top merchants endpoint."""
    merchants: List[TopMerchantItem]
    total: float


class AnalyticsSummaryResponse(BaseModel):
    """High-level analytics summary."""
    total_spend: float
    avg_daily_spend: float
    active_agents: int
    total_transactions: int
    successful_transactions: int
    blocked_transactions: int
    block_rate: float
    top_merchant: Optional[str] = None
    largest_transaction: float


class AnomalyAlert(BaseModel):
    """Anomaly detection alert."""
    timestamp: str
    agent_id: str
    agent_name: Optional[str] = None
    amount: float
    merchant: str
    reason: str
    confidence: float
    z_score: Optional[float] = None


class AnomaliesResponse(BaseModel):
    """Response for anomalies endpoint."""
    anomalies: List[AnomalyAlert]
    total: int


# ============================================================================
# Helper Functions
# ============================================================================

async def _get_date_range(
    period: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> tuple[datetime, datetime]:
    """Parse and validate date range parameters."""
    now = datetime.now(timezone.utc)

    if date_from and date_to:
        try:
            start = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            end = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601.")
    elif period:
        if period == "7d":
            start = now - timedelta(days=7)
            end = now
        elif period == "30d":
            start = now - timedelta(days=30)
            end = now
        elif period == "90d":
            start = now - timedelta(days=90)
            end = now
        else:
            raise HTTPException(status_code=400, detail="Invalid period. Use 7d, 30d, or 90d.")
    else:
        # Default to last 30 days
        start = now - timedelta(days=30)
        end = now

    return start, end


async def _query_transactions(
    start_date: datetime,
    end_date: datetime,
    agent_id: Optional[str] = None,
):
    """Query transactions from database."""
    pool = await get_db_pool()

    # Build query
    query = """
        SELECT
            t.id,
            t.agent_id,
            t.amount_usd,
            t.merchant,
            t.category,
            t.status,
            t.created_at,
            t.policy_block_reason,
            a.name as agent_name
        FROM transactions t
        LEFT JOIN agents a ON t.agent_id = a.id
        WHERE t.created_at >= $1 AND t.created_at <= $2
    """

    params = [start_date, end_date]

    if agent_id:
        query += " AND t.agent_id = $3"
        params.append(agent_id)

    query += " ORDER BY t.created_at DESC"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return rows


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/spending-over-time", response_model=SpendingOverTimeResponse)
async def get_spending_over_time(
    period: Optional[str] = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    date_to: Optional[str] = Query(None, description="End date (ISO 8601)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    group_by: Literal["day", "week", "month"] = Query("day", description="Group by interval"),
    principal: Principal = Depends(require_principal),
):
    """Get spending over time as time series data."""
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    pool = await get_db_pool()

    # Determine date truncation based on group_by
    if group_by == "day":
        trunc = "day"
    elif group_by == "week":
        trunc = "week"
    else:
        trunc = "month"

    query = f"""
        SELECT
            DATE_TRUNC('{trunc}', created_at) as date,
            SUM(amount_usd) as amount,
            COUNT(*) as count
        FROM transactions
        WHERE created_at >= $1 AND created_at <= $2
        AND status = 'completed'
    """

    params = [start_date, end_date]

    if agent_id:
        query += " AND agent_id = $3"
        params.append(agent_id)

    query += f" GROUP BY DATE_TRUNC('{trunc}', created_at) ORDER BY date"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    data = [
        TimeSeriesDataPoint(
            date=row["date"].isoformat(),
            amount=float(row["amount"] or 0),
            count=row["count"],
        )
        for row in rows
    ]

    total = sum(d.amount for d in data)
    average = total / len(data) if data else 0

    return SpendingOverTimeResponse(
        period=period or f"{date_from} to {date_to}",
        data=data,
        total=round(total, 2),
        average=round(average, 2),
    )


@router.get("/spending-by-agent", response_model=AgentSpendingResponse)
async def get_spending_by_agent(
    period: Optional[str] = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    date_to: Optional[str] = Query(None, description="End date (ISO 8601)"),
    principal: Principal = Depends(require_principal),
):
    """Get spending breakdown by agent."""
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    pool = await get_db_pool()

    query = """
        SELECT
            t.agent_id,
            a.name as agent_name,
            SUM(t.amount_usd) as total,
            COUNT(*) as transaction_count
        FROM transactions t
        LEFT JOIN agents a ON t.agent_id = a.id
        WHERE t.created_at >= $1 AND t.created_at <= $2
        AND t.status = 'completed'
        GROUP BY t.agent_id, a.name
        ORDER BY total DESC
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, start_date, end_date)

    agents = [
        AgentSpendingItem(
            agent_id=row["agent_id"],
            agent_name=row["agent_name"],
            total=float(row["total"] or 0),
            transaction_count=row["transaction_count"],
            average=float(row["total"] or 0) / row["transaction_count"] if row["transaction_count"] else 0,
        )
        for row in rows
    ]

    total = sum(a.total for a in agents)

    return AgentSpendingResponse(agents=agents, total=round(total, 2))


@router.get("/spending-by-category", response_model=CategorySpendingResponse)
async def get_spending_by_category(
    period: Optional[str] = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    date_to: Optional[str] = Query(None, description="End date (ISO 8601)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    principal: Principal = Depends(require_principal),
):
    """Get spending breakdown by category."""
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    pool = await get_db_pool()

    query = """
        SELECT
            COALESCE(category, 'uncategorized') as category,
            SUM(amount_usd) as amount,
            COUNT(*) as count
        FROM transactions
        WHERE created_at >= $1 AND created_at <= $2
        AND status = 'completed'
    """

    params = [start_date, end_date]

    if agent_id:
        query += " AND agent_id = $3"
        params.append(agent_id)

    query += " GROUP BY category ORDER BY amount DESC"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    total = sum(float(row["amount"] or 0) for row in rows)

    categories = [
        CategorySpendingItem(
            name=row["category"],
            amount=float(row["amount"] or 0),
            count=row["count"],
            percentage=round((float(row["amount"] or 0) / total * 100) if total > 0 else 0, 1),
        )
        for row in rows
    ]

    return CategorySpendingResponse(categories=categories, total=round(total, 2))


@router.get("/budget-utilization", response_model=BudgetUtilizationResponse)
async def get_budget_utilization(
    period: Optional[str] = Query("30d", description="Period: 7d, 30d, 90d"),
    principal: Principal = Depends(require_principal),
):
    """Get budget utilization per agent."""
    start_date, end_date = await _get_date_range(period)

    pool = await get_db_pool()

    # Get spending per agent
    query = """
        SELECT
            t.agent_id,
            a.name as agent_name,
            SUM(t.amount_usd) as spent,
            a.monthly_budget
        FROM transactions t
        LEFT JOIN agents a ON t.agent_id = a.id
        WHERE t.created_at >= $1 AND t.created_at <= $2
        AND t.status = 'completed'
        GROUP BY t.agent_id, a.name, a.monthly_budget
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, start_date, end_date)

    items = []
    for row in rows:
        spent = float(row["spent"] or 0)
        budget = float(row["monthly_budget"] or 0)
        utilization = (spent / budget * 100) if budget > 0 else 0

        items.append(
            BudgetUtilizationItem(
                agent_id=row["agent_id"],
                agent_name=row["agent_name"],
                spent=round(spent, 2),
                budget=round(budget, 2),
                utilization=round(utilization, 1),
                remaining=round(max(budget - spent, 0), 2),
            )
        )

    return BudgetUtilizationResponse(items=items)


@router.get("/policy-blocks", response_model=PolicyBlocksResponse)
async def get_policy_blocks(
    period: Optional[str] = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    date_to: Optional[str] = Query(None, description="End date (ISO 8601)"),
    principal: Principal = Depends(require_principal),
):
    """Get policy block statistics."""
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    pool = await get_db_pool()

    # Get blocked transactions
    blocked_query = """
        SELECT
            t.created_at,
            t.agent_id,
            a.name as agent_name,
            t.amount_usd,
            t.merchant,
            t.policy_block_reason
        FROM transactions t
        LEFT JOIN agents a ON t.agent_id = a.id
        WHERE t.created_at >= $1 AND t.created_at <= $2
        AND t.status = 'policy_blocked'
        ORDER BY t.created_at DESC
    """

    # Get total transaction count
    total_query = """
        SELECT COUNT(*) as total
        FROM transactions
        WHERE created_at >= $1 AND created_at <= $2
    """

    async with pool.acquire() as conn:
        blocked_rows = await conn.fetch(blocked_query, start_date, end_date)
        total_row = await conn.fetchrow(total_query, start_date, end_date)

    blocks = [
        PolicyBlockItem(
            timestamp=row["created_at"].isoformat(),
            agent_id=row["agent_id"],
            agent_name=row["agent_name"],
            amount=float(row["amount_usd"] or 0),
            merchant=row["merchant"] or "unknown",
            reason=row["policy_block_reason"] or "Policy violation",
        )
        for row in blocked_rows
    ]

    total_transactions = total_row["total"] if total_row else 0
    total_blocks = len(blocks)
    block_rate = (total_blocks / total_transactions * 100) if total_transactions > 0 else 0

    return PolicyBlocksResponse(
        blocks=blocks,
        total_blocks=total_blocks,
        block_rate=round(block_rate, 1),
        total_transactions=total_transactions,
    )


@router.get("/top-merchants", response_model=TopMerchantsResponse)
async def get_top_merchants(
    period: Optional[str] = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    date_to: Optional[str] = Query(None, description="End date (ISO 8601)"),
    limit: int = Query(10, description="Number of merchants to return"),
    principal: Principal = Depends(require_principal),
):
    """Get top merchants by spending volume."""
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    pool = await get_db_pool()

    query = """
        SELECT
            merchant,
            SUM(amount_usd) as amount,
            COUNT(*) as count
        FROM transactions
        WHERE created_at >= $1 AND created_at <= $2
        AND status = 'completed'
        AND merchant IS NOT NULL
        GROUP BY merchant
        ORDER BY amount DESC
        LIMIT $3
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, start_date, end_date, limit)

    total = sum(float(row["amount"] or 0) for row in rows)

    merchants = [
        TopMerchantItem(
            merchant=row["merchant"],
            amount=float(row["amount"] or 0),
            count=row["count"],
            percentage=round((float(row["amount"] or 0) / total * 100) if total > 0 else 0, 1),
        )
        for row in rows
    ]

    return TopMerchantsResponse(merchants=merchants, total=round(total, 2))


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    period: Optional[str] = Query("30d", description="Period: 7d, 30d, 90d"),
    principal: Principal = Depends(require_principal),
):
    """Get high-level analytics summary."""
    start_date, end_date = await _get_date_range(period)

    pool = await get_db_pool()

    summary_query = """
        SELECT
            SUM(CASE WHEN status = 'completed' THEN amount_usd ELSE 0 END) as total_spend,
            COUNT(*) as total_transactions,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_transactions,
            COUNT(CASE WHEN status = 'policy_blocked' THEN 1 END) as blocked_transactions,
            COUNT(DISTINCT agent_id) as active_agents,
            MAX(CASE WHEN status = 'completed' THEN amount_usd ELSE 0 END) as largest_transaction
        FROM transactions
        WHERE created_at >= $1 AND created_at <= $2
    """

    top_merchant_query = """
        SELECT merchant
        FROM transactions
        WHERE created_at >= $1 AND created_at <= $2
        AND status = 'completed'
        GROUP BY merchant
        ORDER BY SUM(amount_usd) DESC
        LIMIT 1
    """

    async with pool.acquire() as conn:
        summary_row = await conn.fetchrow(summary_query, start_date, end_date)
        top_merchant_row = await conn.fetchrow(top_merchant_query, start_date, end_date)

    total_spend = float(summary_row["total_spend"] or 0)
    days = (end_date - start_date).days or 1
    avg_daily_spend = total_spend / days

    total_transactions = summary_row["total_transactions"] or 0
    blocked_transactions = summary_row["blocked_transactions"] or 0
    block_rate = (blocked_transactions / total_transactions * 100) if total_transactions > 0 else 0

    return AnalyticsSummaryResponse(
        total_spend=round(total_spend, 2),
        avg_daily_spend=round(avg_daily_spend, 2),
        active_agents=summary_row["active_agents"] or 0,
        total_transactions=total_transactions,
        successful_transactions=summary_row["successful_transactions"] or 0,
        blocked_transactions=blocked_transactions,
        block_rate=round(block_rate, 1),
        top_merchant=top_merchant_row["merchant"] if top_merchant_row else None,
        largest_transaction=float(summary_row["largest_transaction"] or 0),
    )


@router.get("/export")
async def export_spending_data(
    period: Optional[str] = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    date_to: Optional[str] = Query(None, description="End date (ISO 8601)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    principal: Principal = Depends(require_principal),
):
    """Export spending data as CSV."""
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    rows = await _query_transactions(start_date, end_date, agent_id)

    # Generate CSV
    csv_lines = ["timestamp,agent_id,agent_name,amount,merchant,category,status,block_reason"]

    for row in rows:
        line = f"{row['created_at'].isoformat()},{row['agent_id']},{row['agent_name'] or ''},{row['amount_usd']},{row['merchant'] or ''},{row['category'] or ''},{row['status']},{row['policy_block_reason'] or ''}"
        csv_lines.append(line)

    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sardis-spending-{start_date.date()}-to-{end_date.date()}.csv"},
    )
