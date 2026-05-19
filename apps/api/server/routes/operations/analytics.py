"""
Analytics API Router for Sardis

Endpoints for spending analytics, budget tracking, and anomaly detection.
Designed for consumption by the dashboard frontend (Recharts compatible).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sardis_v2_core.database import get_db_pool

from server.authz import Principal, optional_principal, require_principal
from server.middleware.mpp_gate import mpp_gate

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
    data: list[TimeSeriesDataPoint]
    total: float
    average: float


class AgentSpendingItem(BaseModel):
    """Spending data for a single agent."""
    agent_id: str
    agent_name: str | None = None
    total: float
    transaction_count: int
    average: float


class AgentSpendingResponse(BaseModel):
    """Response for spending-by-agent endpoint."""
    agents: list[AgentSpendingItem]
    total: float


class CategorySpendingItem(BaseModel):
    """Spending data for a single category/merchant."""
    name: str
    amount: float
    count: int
    percentage: float


class CategorySpendingResponse(BaseModel):
    """Response for category/merchant breakdown."""
    categories: list[CategorySpendingItem]
    total: float


class BudgetUtilizationItem(BaseModel):
    """Budget utilization for a single agent."""
    agent_id: str
    agent_name: str | None = None
    spent: float
    budget: float
    utilization: float  # 0-100
    remaining: float


class BudgetUtilizationResponse(BaseModel):
    """Response for budget utilization endpoint."""
    items: list[BudgetUtilizationItem]


class PolicyBlockItem(BaseModel):
    """Policy block event."""
    timestamp: str
    agent_id: str
    agent_name: str | None = None
    amount: float
    merchant: str
    reason: str


class PolicyBlocksResponse(BaseModel):
    """Response for policy blocks endpoint."""
    blocks: list[PolicyBlockItem]
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
    merchants: list[TopMerchantItem]
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
    top_merchant: str | None = None
    largest_transaction: float


class AnomalyAlert(BaseModel):
    """Anomaly detection alert."""
    timestamp: str
    agent_id: str
    agent_name: str | None = None
    amount: float
    merchant: str
    reason: str
    confidence: float
    z_score: float | None = None


class AnomaliesResponse(BaseModel):
    """Response for anomalies endpoint."""
    anomalies: list[AnomalyAlert]
    total: int


# ============================================================================
# Helper Functions
# ============================================================================

async def _get_date_range(
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[datetime, datetime]:
    """Parse and validate date range parameters."""
    now = datetime.now(UTC)

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
    agent_id: str | None = None,
):
    """Query transactions from database.

    Joins transactions → wallets → agents to resolve agent info.
    Column mapping:
      - amount (not amount_usd)
      - purpose (not merchant)
      - error_message (not policy_block_reason)
      - No category column — returns NULL
    """
    pool = await get_db_pool()

    # Build query — join through wallets to reach agents
    query = """
        SELECT
            t.id,
            w.agent_id,
            t.amount,
            t.purpose,
            t.status,
            t.created_at,
            t.error_message,
            a.name as agent_name
        FROM transactions t
        LEFT JOIN wallets w ON t.from_wallet_id = w.id
        LEFT JOIN agents a ON w.agent_id = a.id
        WHERE t.created_at >= $1 AND t.created_at <= $2
    """

    params: list = [start_date, end_date]

    if agent_id:
        query += " AND w.agent_id = $3::uuid"
        params.append(agent_id)

    query += " ORDER BY t.created_at DESC"

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
    except Exception:
        logger.exception("_query_transactions failed")
        return []

    return rows


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/spending-over-time", response_model=SpendingOverTimeResponse)
async def get_spending_over_time(
    period: str | None = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: str | None = Query(None, description="Start date (ISO 8601)"),
    date_to: str | None = Query(None, description="End date (ISO 8601)"),
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    group_by: Literal["day", "week", "month"] = Query("day", description="Group by interval"),
    principal: Principal = Depends(require_principal),
):
    """Get spending over time as time series data."""
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    pool = await get_db_pool()

    # Whitelist-validated date truncation to prevent SQL injection
    _TRUNC_MAP = {"day": "day", "week": "week", "month": "month"}
    trunc_sql = _TRUNC_MAP.get(group_by)
    if not trunc_sql:
        raise HTTPException(status_code=400, detail=f"Invalid group_by: {group_by}")

    query = f"""
        SELECT
            DATE_TRUNC('{trunc_sql}', t.created_at) as date,
            SUM(t.amount) as amount,
            COUNT(*) as count
        FROM transactions t
        LEFT JOIN wallets w ON t.from_wallet_id = w.id
        WHERE t.created_at >= $1 AND t.created_at <= $2
        AND t.status = 'completed'
    """

    params: list = [start_date, end_date]

    if agent_id:
        query += " AND w.agent_id = $3::uuid"
        params.append(agent_id)

    query += f" GROUP BY DATE_TRUNC('{trunc_sql}', t.created_at) ORDER BY date"

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
    except Exception:
        logger.exception("get_spending_over_time query failed")
        rows = []

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


@router.get("/spending-by-agent", response_model=AgentSpendingResponse, dependencies=[Depends(mpp_gate(price="0.01", description="Per-agent spending analytics"))])
async def get_spending_by_agent(
    period: str | None = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: str | None = Query(None, description="Start date (ISO 8601)"),
    date_to: str | None = Query(None, description="End date (ISO 8601)"),
    principal: Principal | None = Depends(optional_principal),
):
    """Get spending breakdown by agent."""
    org_id = principal.organization_id if principal else None
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    pool = await get_db_pool()

    org_filter = ""
    params: list = [start_date, end_date]
    if org_id:
        org_filter = " AND a.organization_id = $3::uuid"
        params.append(org_id)

    query = f"""
        SELECT
            w.agent_id,
            a.name as agent_name,
            SUM(t.amount) as total,
            COUNT(*) as transaction_count
        FROM transactions t
        LEFT JOIN wallets w ON t.from_wallet_id = w.id
        LEFT JOIN agents a ON w.agent_id = a.id
        WHERE t.created_at >= $1 AND t.created_at <= $2
        AND t.status = 'completed'
        {org_filter}
        GROUP BY w.agent_id, a.name
        ORDER BY total DESC
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
    except Exception:
        logger.exception("get_spending_by_agent query failed")
        rows = []

    agents = [
        AgentSpendingItem(
            agent_id=str(row["agent_id"] or "unknown"),
            agent_name=row["agent_name"],
            total=float(row["total"] or 0),
            transaction_count=row["transaction_count"],
            average=float(row["total"] or 0) / row["transaction_count"] if row["transaction_count"] else 0,
        )
        for row in rows
    ]

    total = sum(a.total for a in agents)

    return AgentSpendingResponse(agents=agents, total=round(total, 2))


@router.get("/spending-by-category", response_model=CategorySpendingResponse, dependencies=[Depends(mpp_gate(price="0.01", description="Category spending analytics"))])
async def get_spending_by_category(
    period: str | None = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: str | None = Query(None, description="Start date (ISO 8601)"),
    date_to: str | None = Query(None, description="End date (ISO 8601)"),
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    principal: Principal | None = Depends(optional_principal),
):
    """Get spending breakdown by category."""
    org_id = principal.organization_id if principal else None
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    pool = await get_db_pool()

    query = """
        SELECT
            COALESCE(t.purpose, 'uncategorized') as category,
            SUM(t.amount) as amount,
            COUNT(*) as count
        FROM transactions t
        LEFT JOIN wallets w ON t.from_wallet_id = w.id
        LEFT JOIN agents a ON w.agent_id = a.id
        WHERE t.created_at >= $1 AND t.created_at <= $2
        AND t.status = 'completed'
    """

    params: list = [start_date, end_date]
    param_idx = 3

    if org_id:
        query += f" AND a.organization_id = ${param_idx}::uuid"
        params.append(org_id)
        param_idx += 1

    if agent_id:
        query += f" AND w.agent_id = ${param_idx}::uuid"
        params.append(agent_id)
        param_idx += 1

    query += " GROUP BY t.purpose ORDER BY amount DESC"

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
    except Exception:
        logger.exception("get_spending_by_category query failed")
        rows = []

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
    period: str | None = Query("30d", description="Period: 7d, 30d, 90d"),
    principal: Principal = Depends(require_principal),
):
    """Get budget utilization per agent."""
    start_date, end_date = await _get_date_range(period)

    pool = await get_db_pool()

    # Get spending per agent.
    # Note: agents table has no monthly_budget column; use spending_policies.limit_total
    # as a budget proxy (or 0 if no policy exists).
    query = """
        SELECT
            w.agent_id,
            a.name as agent_name,
            SUM(t.amount) as spent,
            COALESCE(sp.limit_total, 0) as budget
        FROM transactions t
        LEFT JOIN wallets w ON t.from_wallet_id = w.id
        LEFT JOIN agents a ON w.agent_id = a.id
        LEFT JOIN spending_policies sp ON sp.agent_id = a.id
        WHERE t.created_at >= $1 AND t.created_at <= $2
        AND t.status = 'completed'
        GROUP BY w.agent_id, a.name, sp.limit_total
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, start_date, end_date)
    except Exception:
        logger.exception("get_budget_utilization query failed")
        return BudgetUtilizationResponse(items=[])

    items = []
    for row in rows:
        spent = float(row["spent"] or 0)
        budget = float(row["budget"] or 0)
        utilization = (spent / budget * 100) if budget > 0 else 0

        items.append(
            BudgetUtilizationItem(
                agent_id=str(row["agent_id"] or "unknown"),
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
    period: str | None = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: str | None = Query(None, description="Start date (ISO 8601)"),
    date_to: str | None = Query(None, description="End date (ISO 8601)"),
    principal: Principal = Depends(require_principal),
):
    """Get policy block statistics."""
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    pool = await get_db_pool()

    # Get blocked transactions (status = 'policy_blocked')
    # Column mapping: amount (not amount_usd), purpose (not merchant),
    # error_message (not policy_block_reason)
    blocked_query = """
        SELECT
            t.created_at,
            w.agent_id,
            a.name as agent_name,
            t.amount,
            t.purpose,
            t.error_message
        FROM transactions t
        LEFT JOIN wallets w ON t.from_wallet_id = w.id
        LEFT JOIN agents a ON w.agent_id = a.id
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

    try:
        async with pool.acquire() as conn:
            blocked_rows = await conn.fetch(blocked_query, start_date, end_date)
            total_row = await conn.fetchrow(total_query, start_date, end_date)
    except Exception:
        logger.exception("get_policy_blocks query failed")
        return PolicyBlocksResponse(blocks=[], total_blocks=0, block_rate=0.0, total_transactions=0)

    blocks = [
        PolicyBlockItem(
            timestamp=row["created_at"].isoformat(),
            agent_id=str(row["agent_id"] or "unknown"),
            agent_name=row["agent_name"],
            amount=float(row["amount"] or 0),
            merchant=row["purpose"] or "unknown",
            reason=row["error_message"] or "Policy violation",
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
    period: str | None = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: str | None = Query(None, description="Start date (ISO 8601)"),
    date_to: str | None = Query(None, description="End date (ISO 8601)"),
    limit: int = Query(10, description="Number of merchants to return"),
    principal: Principal = Depends(require_principal),
):
    """Get top merchants by spending volume."""
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    pool = await get_db_pool()

    query = """
        SELECT
            purpose as merchant,
            SUM(amount) as amount,
            COUNT(*) as count
        FROM transactions
        WHERE created_at >= $1 AND created_at <= $2
        AND status = 'completed'
        AND purpose IS NOT NULL
        GROUP BY purpose
        ORDER BY amount DESC
        LIMIT $3
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, start_date, end_date, limit)
    except Exception:
        logger.exception("get_top_merchants query failed")
        return TopMerchantsResponse(merchants=[], total=0.0)

    total = sum(float(row["amount"] or 0) for row in rows)

    merchants = [
        TopMerchantItem(
            merchant=row["merchant"] or "unknown",
            amount=float(row["amount"] or 0),
            count=row["count"],
            percentage=round((float(row["amount"] or 0) / total * 100) if total > 0 else 0, 1),
        )
        for row in rows
    ]

    return TopMerchantsResponse(merchants=merchants, total=round(total, 2))


@router.get("/summary", response_model=AnalyticsSummaryResponse, dependencies=[Depends(mpp_gate(price="0.01", description="Spending analytics summary"))])
async def get_analytics_summary(
    period: str | None = Query("30d", description="Period: 7d, 30d, 90d"),
    principal: Principal | None = Depends(optional_principal),
):
    """Get high-level analytics summary."""
    org_id = principal.organization_id if principal else None
    start_date, end_date = await _get_date_range(period)

    pool = await get_db_pool()

    # Build org-scoped or unscoped queries
    # Join transactions → wallets → agents for org scoping and agent counting
    org_filter = ""
    params: list = [start_date, end_date]
    if org_id:
        org_filter = " AND a.organization_id = $3::uuid"
        params.append(org_id)

    summary_query = f"""
        SELECT
            SUM(CASE WHEN t.status = 'completed' THEN t.amount ELSE 0 END) as total_spend,
            COUNT(*) as total_transactions,
            COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as successful_transactions,
            COUNT(CASE WHEN t.status = 'policy_blocked' THEN 1 END) as blocked_transactions,
            COUNT(DISTINCT w.agent_id) as active_agents,
            MAX(CASE WHEN t.status = 'completed' THEN t.amount ELSE 0 END) as largest_transaction
        FROM transactions t
        LEFT JOIN wallets w ON t.from_wallet_id = w.id
        LEFT JOIN agents a ON w.agent_id = a.id
        WHERE t.created_at >= $1 AND t.created_at <= $2
        {org_filter}
    """

    top_merchant_query = f"""
        SELECT t.purpose as merchant
        FROM transactions t
        LEFT JOIN wallets w ON t.from_wallet_id = w.id
        LEFT JOIN agents a ON w.agent_id = a.id
        WHERE t.created_at >= $1 AND t.created_at <= $2
        AND t.status = 'completed'
        AND t.purpose IS NOT NULL
        {org_filter}
        GROUP BY t.purpose
        ORDER BY SUM(t.amount) DESC
        LIMIT 1
    """

    try:
        async with pool.acquire() as conn:
            summary_row = await conn.fetchrow(summary_query, *params)
            top_merchant_row = await conn.fetchrow(top_merchant_query, *params)
    except Exception:
        logger.exception("get_analytics_summary query failed")
        return AnalyticsSummaryResponse(
            total_spend=0, avg_daily_spend=0, active_agents=0,
            total_transactions=0, successful_transactions=0,
            blocked_transactions=0, block_rate=0, largest_transaction=0,
        )

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
    period: str | None = Query(None, description="Period: 7d, 30d, 90d"),
    date_from: str | None = Query(None, description="Start date (ISO 8601)"),
    date_to: str | None = Query(None, description="End date (ISO 8601)"),
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    principal: Principal = Depends(require_principal),
):
    """Export spending data as CSV."""
    start_date, end_date = await _get_date_range(period, date_from, date_to)

    rows = await _query_transactions(start_date, end_date, agent_id)

    # Generate CSV
    csv_lines = ["timestamp,agent_id,agent_name,amount,purpose,status,error_message"]

    for row in rows:
        line = (
            f"{row['created_at'].isoformat()},"
            f"{row['agent_id'] or ''},"
            f"{row['agent_name'] or ''},"
            f"{row['amount']},"
            f"{row['purpose'] or ''},"
            f"{row['status']},"
            f"{row['error_message'] or ''}"
        )
        csv_lines.append(line)

    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sardis-spending-{start_date.date()}-to-{end_date.date()}.csv"},
    )
