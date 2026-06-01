"""MPP Demo — Real intelligence endpoint for Stripe MPP team demo.

THIS endpoint sits behind the MPP-*conformant* gate (``mpp_gate``): the
"Payment" HTTP auth scheme (402 → pay on Tempo → retry with credential → 200 +
Payment-Receipt). It is the wire-protocol surface; the Sardis-native session/
budget authority lives in ``routes/protocol/mpp.py``.

Demonstrates the dual-access MPP gate middleware:
1. Authenticated users (API key / JWT) → free access
2. Unauthenticated users → 402 challenge, pay via Tempo, resend with credential
3. Payment validated → data returned with Payment-Receipt header

Returns real network data (agent counts, transaction volume) and runs the real
SpendingPolicy engine — the same one ``/api/v2/mpp/evaluate`` uses — when an
agent_id is supplied (fail-closed: no policy_store / no agent_id / engine error
=> DENIED).

Designed for Ben Berke (Stripe) to test with `npx mppx`.

Env vars:
    MPP_SECRET_KEY — HMAC secret for stateless challenge verification (required)
    MPP_RECIPIENT — Sardis wallet address to receive payments
    MPP_DEMO_PRICE — Price per request in USD (default: "0.001")
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from server.middleware.mpp_gate import add_mpp_receipt_header, mpp_gate
from server.services.mpp_policy import evaluate_mpp_policy

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Database helper — lazy-loaded pool (same pattern as mpp.py)
# ---------------------------------------------------------------------------

_db_pool = None


async def _get_db():
    """Get asyncpg connection pool, or None if no DATABASE_URL."""
    global _db_pool
    if _db_pool is not None:
        return _db_pool

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None

    try:
        import asyncpg
        _db_pool = await asyncpg.create_pool(db_url, min_size=1, max_size=3)
        logger.info("MPP demo: PostgreSQL pool initialized")
        return _db_pool
    except Exception as e:
        logger.warning("MPP demo: Failed to connect to PostgreSQL: %s", e)
        return None


# ---------------------------------------------------------------------------
# Real data queries
# ---------------------------------------------------------------------------


async def _fetch_network_status() -> dict[str, Any]:
    """Query real agent count, transaction count, and volume from the DB."""
    defaults: dict[str, Any] = {
        "agents_online": 0,
        "transactions_24h": 0,
        "volume_24h": 0.0,
        "kill_switch_active": False,
    }

    pool = await _get_db()
    if pool is None:
        return defaults

    try:
        async with pool.acquire() as conn:
            # Active agent count
            agent_row = await conn.fetchval(
                "SELECT COUNT(*) FROM agents WHERE is_active = true"
            )
            defaults["agents_online"] = agent_row or 0

            # Transaction stats (last 24h)
            tx_row = await conn.fetchrow(
                """SELECT
                    COUNT(*) as cnt,
                    COALESCE(SUM(amount), 0) as vol
                FROM ledger_entries
                WHERE created_at > NOW() - INTERVAL '24 hours'"""
            )
            if tx_row:
                defaults["transactions_24h"] = tx_row["cnt"] or 0
                defaults["volume_24h"] = float(tx_row["vol"] or 0)

            # Kill switch — check if any org-wide kill switch is active
            try:
                ks_row = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM kill_switches WHERE is_active = true)"
                )
                defaults["kill_switch_active"] = bool(ks_row)
            except Exception:
                # Table may not exist in all environments
                pass

    except Exception as e:
        logger.warning("MPP demo: network status query failed: %s", e)

    return defaults


# ---------------------------------------------------------------------------
# Policy check — delegates to the real SpendingPolicy engine
# ---------------------------------------------------------------------------


async def _policy_check(
    request: Request,
    *,
    agent_id: str,
    amount: float,
    merchant: str,
    currency: str,
    network: str = "tempo",
) -> dict[str, Any]:
    """Run the real Sardis SpendingPolicy and return demo-shaped results.

    Single source of policy truth: the same ``evaluate_mpp_policy`` engine that
    ``/api/v2/mpp/evaluate`` uses. Fail-closed — no policy_store / no agent /
    engine error => DENIED. No hardcoded thresholds, no module-global counter.
    """
    try:
        amount_dec = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        return {
            "result": "DENIED",
            "reason": "invalid_amount",
            "checks_passed": 0,
            "checks_total": 12,
        }

    policy_store = getattr(getattr(request.app, "state", None), "policy_store", None)
    decision = await evaluate_mpp_policy(
        policy_store=policy_store,
        agent_id=agent_id,
        amount=amount_dec,
        merchant=merchant,
        currency=currency,
        network=network,
    )
    return {
        "result": "ALLOWED" if decision.allowed else "DENIED",
        "reason": decision.reason,
        "checks_passed": decision.checks_passed,
        "checks_total": decision.checks_total,
    }


# ---------------------------------------------------------------------------
# Demo endpoint — now gated via mpp_gate middleware
# ---------------------------------------------------------------------------

DEMO_PRICE = os.getenv("MPP_DEMO_PRICE", "0.001")


@router.get(
    "/paid-data",
    dependencies=[Depends(mpp_gate(price=DEMO_PRICE, description="Sardis market intelligence - real-time agent economy data"))],
)
async def paid_data(
    request: Request,
    agent_id: str | None = Query(None, description="Agent ID for policy evaluation"),
    amount: float = Query(10.0, description="Amount to evaluate (USD)"),
    merchant: str = Query("demo-merchant", description="Merchant identifier"),
    currency: str = Query("USDC", description="Currency code"),
):
    """Sardis Intelligence API — returns real network data and policy evaluation.

    Authenticated users (API key / JWT) get free access.
    Unauthenticated users pay via MPP (402 challenge → payment → data).

    Query params:
    - agent_id: If provided, runs a real policy check for the agent
    - amount: Amount in USD to evaluate (default 10.0)
    - merchant: Merchant identifier (default "demo-merchant")
    - currency: Currency code (default "USDC")
    """
    # MPP receipt tracking (only relevant for paid requests). Replay/double-spend
    # protection lives in the gate's pympp store (tx-hash put_if_absent), not in
    # a process-local counter.
    receipt = getattr(getattr(request, "state", None), "mpp_receipt", None)
    if receipt is not None:
        logger.info(
            "MPP demo: payment verified (receipt=%s, amount=%s)",
            receipt.reference,
            DEMO_PRICE,
        )

    # Fetch real network status from DB
    network_status = await _fetch_network_status()

    # Build response
    now = datetime.now(UTC)
    data: dict[str, Any] = {
        "service": "sardis-intelligence",
        "timestamp": now.isoformat(),
        "network_status": network_status,
        "powered_by": "Sardis Intelligence Plane",
    }

    # Run real policy check if agent_id is provided
    if agent_id is not None:
        policy_result = await _policy_check(
            request,
            agent_id=agent_id,
            amount=amount,
            merchant=merchant,
            currency=currency,
        )
        data["policy_check"] = {
            "agent_id": agent_id,
            "amount": amount,
            "merchant": merchant,
            "currency": currency,
            **policy_result,
        }

        if policy_result["result"] == "DENIED":
            logger.warning(
                "MPP demo: policy denied for agent=%s amount=%s merchant=%s",
                agent_id, amount, merchant,
            )

    response = JSONResponse(status_code=200, content=data)
    add_mpp_receipt_header(request, response)
    return response


@router.get("/info")
async def demo_info():
    """Public info about the Sardis Intelligence API — no auth required."""
    network = os.getenv("SARDIS_MPP_NETWORK", "testnet").strip().lower()
    is_mainnet = network == "mainnet"
    return {
        "endpoint": "/api/v2/demo/paid-data",
        "price": DEMO_PRICE,
        "currency": "USDC" if is_mainnet else "PATH_USD",
        "network": "tempo-mainnet" if is_mainnet else "tempo-testnet",
        "chain_id": 4217 if is_mainnet else 42431,
        "method": "tempo",
        "description": "Sardis Intelligence API — real-time agent network data and policy evaluation, pay-per-request via MPP",
        "query_params": {
            "agent_id": "Optional — triggers policy evaluation for the given agent",
            "amount": "Amount in USD to evaluate (default: 10.0)",
            "merchant": "Merchant identifier (default: demo-merchant)",
            "currency": "Currency code (default: USDC)",
        },
        "test_command": "npx mppx GET https://api.sardis.sh/api/v2/demo/paid-data",
        "total_gated_endpoints": 24,
        "access_model": {
            "authenticated": "Free (API key or JWT)",
            "unauthenticated": f"Pay ${DEMO_PRICE} per request via MPP on Tempo",
        },
    }
