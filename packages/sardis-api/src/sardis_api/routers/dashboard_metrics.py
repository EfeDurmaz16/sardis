"""Dashboard metrics — aggregated data for overview page."""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)
router = APIRouter()


class DashboardMetrics(BaseModel):
    balance_usd: str
    balance_chain: str
    volume_24h_usd: str
    tx_count_24h: int
    tx_count_total: int
    agent_count: int
    active_agents: int
    mandate_count: int
    active_sessions: int
    policy_pass_rate: float
    policy_blocked_24h: int
    wallet_count: int
    environment: str
    chain: str


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    principal: Principal = Depends(require_principal),
):
    """Get aggregated dashboard metrics for the current org.

    Returns balance, volume, transaction counts, agent counts,
    policy stats, and environment info in a single call.
    """
    env = getattr(principal, "environment", "test")
    chain = "tempo" if env == "live" else "base_sepolia"

    # Default values
    balance = "0.00"
    volume_24h = "0.00"
    tx_total = 0
    tx_24h = 0
    agent_count = 0
    active_agents = 0
    mandate_count = 0
    active_sessions = 0
    wallet_count = 0
    blocked_24h = 0

    try:
        from sardis_api.dependencies import get_container
        container = get_container()

        if hasattr(container, 'db_pool') and container.db_pool:
            pool = container.db_pool
            async with pool.acquire() as conn:
                # Transaction stats
                tx_row = await conn.fetchrow(
                    """SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as last_24h,
                        COALESCE(SUM(CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN amount ELSE 0 END), 0) as volume_24h
                    FROM ledger_entries WHERE org_id = $1""",
                    principal.org_id,
                )
                if tx_row:
                    tx_total = tx_row["total"] or 0
                    tx_24h = tx_row["last_24h"] or 0
                    volume_24h = f"{float(tx_row['volume_24h'] or 0):.2f}"

                # Agent count
                agent_row = await conn.fetchrow(
                    """SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE is_active = true) as active
                    FROM agents WHERE owner_id = $1""",
                    principal.org_id,
                )
                if agent_row:
                    agent_count = agent_row["total"] or 0
                    active_agents = agent_row["active"] or 0

                # Mandate count
                mandate_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM spending_mandates WHERE org_id = $1",
                    principal.org_id,
                ) or 0

                # Active MPP sessions
                active_sessions = await conn.fetchval(
                    "SELECT COUNT(*) FROM mpp_sessions WHERE org_id = $1 AND status = 'active'",
                    principal.org_id,
                ) or 0

                # Wallet count
                wallet_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM wallets WHERE org_id = $1",
                    principal.org_id,
                ) or 0

                # Blocked transactions (policy violations)
                blocked_24h = await conn.fetchval(
                    """SELECT COUNT(*) FROM ledger_entries
                    WHERE org_id = $1 AND status = 'blocked'
                    AND created_at > NOW() - INTERVAL '24 hours'""",
                    principal.org_id,
                ) or 0

    except Exception as e:
        logger.warning("Dashboard metrics query failed: %s", e)

    # Calculate policy pass rate
    policy_pass_rate = 100.0
    if tx_total > 0 and blocked_24h > 0:
        total_attempts = tx_24h + blocked_24h
        if total_attempts > 0:
            policy_pass_rate = round((tx_24h / total_attempts) * 100, 1)

    return DashboardMetrics(
        balance_usd=balance,
        balance_chain=chain,
        volume_24h_usd=volume_24h,
        tx_count_24h=tx_24h,
        tx_count_total=tx_total,
        agent_count=agent_count,
        active_agents=active_agents,
        mandate_count=mandate_count,
        active_sessions=active_sessions,
        policy_pass_rate=policy_pass_rate,
        policy_blocked_24h=blocked_24h,
        wallet_count=wallet_count,
        environment=env,
        chain=chain,
    )
