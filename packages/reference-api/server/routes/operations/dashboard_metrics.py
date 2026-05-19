"""Dashboard metrics — aggregated data for overview page."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from server.authz import Principal, require_principal

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
    online_agents: int = 0
    api_calls_24h: int = 0
    agent_events_24h: int = 0
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
    online_agents = 0
    api_calls_24h = 0
    agent_events_24h = 0
    mandate_count = 0
    active_sessions = 0
    wallet_count = 0
    blocked_24h = 0

    try:
        from server.dependencies import get_container
        container = get_container()

        if hasattr(container, 'db_pool') and container.db_pool:
            pool = container.db_pool

            # Helper coroutines — each acquires its own connection so they
            # can run concurrently via asyncio.gather.

            async def _tx_stats():
                async with pool.acquire() as conn:
                    return await conn.fetchrow(
                        """SELECT
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as last_24h,
                            COALESCE(SUM(CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN amount ELSE 0 END), 0) as volume_24h
                        FROM ledger_entries WHERE org_id = $1""",
                        principal.org_id,
                    )

            async def _agent_stats():
                async with pool.acquire() as conn:
                    return await conn.fetchrow(
                        """SELECT
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE is_active = true) as active
                        FROM agents WHERE owner_id = $1""",
                        principal.org_id,
                    )

            async def _mandate_count_q():
                async with pool.acquire() as conn:
                    return await conn.fetchval(
                        "SELECT COUNT(*) FROM spending_mandates WHERE org_id = $1",
                        principal.org_id,
                    ) or 0

            async def _active_sessions_q():
                async with pool.acquire() as conn:
                    return await conn.fetchval(
                        "SELECT COUNT(*) FROM mpp_sessions WHERE org_id = $1 AND status = 'active'",
                        principal.org_id,
                    ) or 0

            async def _wallet_count_q():
                async with pool.acquire() as conn:
                    return await conn.fetchval(
                        "SELECT COUNT(*) FROM wallets WHERE org_id = $1",
                        principal.org_id,
                    ) or 0

            async def _blocked_24h_q():
                async with pool.acquire() as conn:
                    return await conn.fetchval(
                        """SELECT COUNT(*) FROM ledger_entries
                        WHERE org_id = $1 AND status = 'blocked'
                        AND created_at > NOW() - INTERVAL '24 hours'""",
                        principal.org_id,
                    ) or 0

            async def _online_agents_q():
                try:
                    async with pool.acquire() as conn:
                        return await conn.fetchval(
                            """SELECT COUNT(*) FROM agents a
                            JOIN organizations o ON o.id = a.organization_id
                            WHERE o.external_id = $1
                              AND a.is_active = TRUE
                              AND a.last_seen_at > NOW() - INTERVAL '2 minutes'""",
                            principal.org_id,
                        ) or 0
                except Exception:
                    return 0  # Column may not exist yet

            async def _api_calls_q():
                try:
                    async with pool.acquire() as conn:
                        return await conn.fetchval(
                            """SELECT COUNT(*) FROM api_activity_log
                            WHERE org_id = $1
                              AND created_at > NOW() - INTERVAL '24 hours'""",
                            principal.org_id,
                        ) or 0
                except Exception:
                    return 0  # Table may not exist yet

            async def _agent_events_q():
                try:
                    async with pool.acquire() as conn:
                        return await conn.fetchval(
                            """SELECT COUNT(*) FROM agent_events
                            WHERE org_id = $1
                              AND created_at > NOW() - INTERVAL '24 hours'""",
                            principal.org_id,
                        ) or 0
                except Exception:
                    return 0  # Table may not exist yet

            # Run all queries concurrently
            (
                tx_row,
                agent_row,
                mandate_count,
                active_sessions,
                wallet_count,
                blocked_24h,
                online_agents,
                api_calls_24h,
                agent_events_24h,
            ) = await asyncio.gather(
                _tx_stats(),
                _agent_stats(),
                _mandate_count_q(),
                _active_sessions_q(),
                _wallet_count_q(),
                _blocked_24h_q(),
                _online_agents_q(),
                _api_calls_q(),
                _agent_events_q(),
            )

            if tx_row:
                tx_total = tx_row["total"] or 0
                tx_24h = tx_row["last_24h"] or 0
                volume_24h = f"{float(tx_row['volume_24h'] or 0):.2f}"

            if agent_row:
                agent_count = agent_row["total"] or 0
                active_agents = agent_row["active"] or 0

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
        online_agents=online_agents,
        api_calls_24h=api_calls_24h,
        agent_events_24h=agent_events_24h,
        mandate_count=mandate_count,
        active_sessions=active_sessions,
        policy_pass_rate=policy_pass_rate,
        policy_blocked_24h=blocked_24h,
        wallet_count=wallet_count,
        environment=env,
        chain=chain,
    )
