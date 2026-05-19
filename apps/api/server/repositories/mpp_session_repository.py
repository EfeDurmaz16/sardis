"""MPP session persistence helpers for the reference API."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

_db_pool = None
_sessions: dict[str, dict[str, Any]] = {}
_payments: dict[str, list[dict[str, Any]]] = {}


async def get_db_pool():
    """Get asyncpg connection pool, or None when DATABASE_URL is not configured."""
    global _db_pool
    if _db_pool is not None:
        return _db_pool

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None

    try:
        import asyncpg

        _db_pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5)
        logger.info("MPP: PostgreSQL pool initialized")
        return _db_pool
    except Exception as exc:
        logger.warning("MPP: Failed to connect to PostgreSQL, using in-memory: %s", exc)
        return None


async def create_session_record(
    *,
    session: dict[str, Any],
    metadata: dict[str, Any],
    expires_at_dt: datetime | None,
) -> None:
    pool = await get_db_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO mpp_sessions
                   (session_id, org_id, mandate_id, wallet_id, agent_id,
                    method, chain, currency, spending_limit, remaining,
                    total_spent, payment_count, status, created_at, expires_at, metadata)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)""",
                session["session_id"],
                session["org_id"],
                session.get("mandate_id"),
                session.get("wallet_id"),
                session.get("agent_id"),
                session["method"],
                session["chain"],
                session["currency"],
                session["spending_limit"],
                session["remaining"],
                session["total_spent"],
                session["payment_count"],
                session["status"],
                session["created_at"],
                expires_at_dt,
                json.dumps(metadata),
            )
        return

    _sessions[session["session_id"]] = dict(session)
    _payments[session["session_id"]] = []


async def load_session(session_id: str, org_id: str) -> dict[str, Any] | None:
    pool = await get_db_pool()
    if pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mpp_sessions WHERE session_id = $1", session_id
            )
            return dict(row) if row else None

    session = _sessions.get(session_id)
    return dict(session) if session else None


async def mark_session_expired(session_id: str) -> None:
    pool = await get_db_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE mpp_sessions SET status = 'expired' WHERE session_id = $1",
                session_id,
            )
        return

    if session_id in _sessions:
        _sessions[session_id]["status"] = "expired"


async def record_payment(
    *,
    session_id: str,
    amount: Decimal,
    merchant: str,
    merchant_url: str | None,
    metadata: dict[str, Any],
    payment_id: str,
    currency: str,
    chain: str,
    new_remaining: Decimal,
    new_total: Decimal,
    new_count: int,
    new_status: str,
    pay_status: str,
    tx_hash: str | None,
    created_at: datetime,
) -> None:
    pool = await get_db_pool()
    if pool:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """UPDATE mpp_sessions
                       SET remaining = $1, total_spent = $2, payment_count = $3, status = $4
                       WHERE session_id = $5""",
                    new_remaining,
                    new_total,
                    new_count,
                    new_status,
                    session_id,
                )
                await conn.execute(
                    """INSERT INTO mpp_payments
                       (payment_id, session_id, amount, currency, merchant, merchant_url,
                        status, tx_hash, chain, created_at, metadata)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)""",
                    payment_id,
                    session_id,
                    amount,
                    currency,
                    merchant,
                    merchant_url or "",
                    pay_status,
                    tx_hash,
                    chain,
                    created_at,
                    json.dumps(metadata),
                )
        return

    mem = _sessions.get(session_id)
    if not mem:
        return
    mem["remaining"] = new_remaining
    mem["total_spent"] = new_total
    mem["payment_count"] = new_count
    mem["status"] = new_status
    _payments.setdefault(session_id, []).append(
        {
            "payment_id": payment_id,
            "session_id": session_id,
            "amount": amount,
            "merchant": merchant,
            "status": pay_status,
            "tx_hash": tx_hash,
            "chain": chain,
            "created_at": created_at.isoformat(),
        }
    )


async def close_session_record(session_id: str, closed_at: datetime) -> None:
    pool = await get_db_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE mpp_sessions SET status = 'closed', closed_at = $1 WHERE session_id = $2",
                closed_at,
                session_id,
            )
        return

    mem = _sessions.get(session_id)
    if mem:
        mem["status"] = "closed"
        mem["closed_at"] = closed_at.isoformat()


def get_memory_session(session_id: str) -> dict[str, Any] | None:
    return _sessions.get(session_id)


def deduct_memory_session(session_id: str, amount: Decimal) -> None:
    session = _sessions.get(session_id)
    if not session:
        return
    session["remaining"] = session["remaining"] - amount
    session["total_spent"] = session["total_spent"] + amount
    session["payment_count"] += 1
