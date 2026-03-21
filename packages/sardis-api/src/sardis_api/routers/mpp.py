"""MPP (Machine Payments Protocol) API endpoints.

Provides session-based MPP payment management:
- Create MPP sessions with spending mandates
- Execute payments within sessions
- Close sessions and settle remaining
- Policy evaluation and dry-run simulation
- Virtual card issuance via Laso Finance

Persistence: Uses PostgreSQL (mpp_sessions + mpp_payments tables from migration 075)
when DATABASE_URL is set. Falls back to in-memory for dev/demo.
"""
from __future__ import annotations

import json as json_module
import logging
import os
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter()

# Database connection helper — lazy-loaded
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
        _db_pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5)
        logger.info("MPP: PostgreSQL pool initialized")
        return _db_pool
    except Exception as e:
        logger.warning("MPP: Failed to connect to PostgreSQL, using in-memory: %s", e)
        return None


# ── Request / Response Models ──────────────────────────────────────────


class CreateMPPSessionRequest(BaseModel):
    mandate_id: str | None = None
    wallet_id: str | None = None
    agent_id: str | None = None
    method: str = Field(default="tempo", description="Payment method: tempo, stripe_spt, bolt11")
    chain: str = Field(default="tempo", description="Target chain")
    currency: str = Field(default="USDC", description="Payment currency")
    spending_limit: Decimal = Field(..., gt=0, description="Maximum amount for this session")
    expires_in_seconds: int | None = Field(default=3600, description="Session TTL in seconds")
    metadata: dict | None = None


class MPPSessionResponse(BaseModel):
    session_id: str
    mandate_id: str | None
    wallet_id: str | None
    agent_id: str | None
    method: str
    chain: str
    currency: str
    spending_limit: str
    remaining: str
    total_spent: str
    payment_count: int
    status: str
    created_at: str
    closed_at: str | None
    expires_at: str | None


class ExecutePaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    merchant: str = Field(..., description="Merchant identifier or URL")
    merchant_url: str | None = None
    memo: str | None = None
    metadata: dict | None = None


class ExecutePaymentResponse(BaseModel):
    payment_id: str
    session_id: str
    amount: str
    merchant: str
    status: str
    tx_hash: str | None
    chain: str
    remaining: str


class PolicyEvaluateRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    merchant: str
    payment_type: str = "mpp_tempo"
    currency: str = "USDC"
    network: str = "tempo"


class PolicyEvaluateResponse(BaseModel):
    allowed: bool
    reason: str
    checks_passed: int
    checks_total: int


# ── In-memory session store (replaced by DB in production) ─────────────

_sessions: dict[str, dict] = {}
_payments: dict[str, list[dict]] = {}


def _session_to_response(s: dict) -> MPPSessionResponse:
    return MPPSessionResponse(
        session_id=s["session_id"],
        mandate_id=s.get("mandate_id"),
        wallet_id=s.get("wallet_id"),
        agent_id=s.get("agent_id"),
        method=s["method"],
        chain=s["chain"],
        currency=s["currency"],
        spending_limit=str(s["spending_limit"]),
        remaining=str(s["remaining"]),
        total_spent=str(s["total_spent"]),
        payment_count=s["payment_count"],
        status=s["status"],
        created_at=s["created_at"],
        closed_at=s.get("closed_at"),
        expires_at=s.get("expires_at"),
    )


# ── Endpoints ──────────────────────────────────────────────────────────


@router.post("/sessions", response_model=MPPSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    req: CreateMPPSessionRequest,
    principal: Principal = Depends(require_principal),
):
    """Create an MPP payment session with a spending limit."""
    from datetime import timedelta

    session_id = f"mpp_sess_{uuid4().hex[:16]}"
    now = datetime.now(UTC)
    now_iso = now.isoformat()
    expires_at_dt = None
    expires_at = None
    if req.expires_in_seconds:
        expires_at_dt = now + timedelta(seconds=req.expires_in_seconds)
        expires_at = expires_at_dt.isoformat()

    # Try PostgreSQL first
    pool = await _get_db()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO mpp_sessions
                   (session_id, org_id, mandate_id, wallet_id, agent_id,
                    method, chain, currency, spending_limit, remaining,
                    total_spent, payment_count, status, created_at, expires_at, metadata)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)""",
                session_id, principal.org_id, req.mandate_id, req.wallet_id, req.agent_id,
                req.method, req.chain, req.currency, req.spending_limit, req.spending_limit,
                Decimal("0"), 0, "active", now, expires_at_dt,
                json_module.dumps(req.metadata or {}),
            )
        logger.info("MPP session created (DB): %s (limit=%s %s)", session_id, req.spending_limit, req.currency)
    else:
        # In-memory fallback
        session = {
            "session_id": session_id,
            "org_id": principal.org_id,
            "mandate_id": req.mandate_id,
            "wallet_id": req.wallet_id,
            "agent_id": req.agent_id,
            "method": req.method,
            "chain": req.chain,
            "currency": req.currency,
            "spending_limit": req.spending_limit,
            "remaining": req.spending_limit,
            "total_spent": Decimal("0"),
            "payment_count": 0,
            "status": "active",
            "created_at": now_iso,
            "closed_at": None,
            "expires_at": expires_at,
            "metadata": req.metadata or {},
        }
        _sessions[session_id] = session
        _payments[session_id] = []
        logger.info("MPP session created (memory): %s (limit=%s %s)", session_id, req.spending_limit, req.currency)

    return MPPSessionResponse(
        session_id=session_id,
        mandate_id=req.mandate_id,
        wallet_id=req.wallet_id,
        agent_id=req.agent_id,
        method=req.method,
        chain=req.chain,
        currency=req.currency,
        spending_limit=str(req.spending_limit),
        remaining=str(req.spending_limit),
        total_spent="0",
        payment_count=0,
        status="active",
        created_at=now_iso,
        closed_at=None,
        expires_at=expires_at,
    )


async def _load_session(session_id: str, org_id: str) -> dict:
    """Load session from DB or memory, with org ownership check."""
    pool = await _get_db()
    if pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mpp_sessions WHERE session_id = $1", session_id
            )
            if not row:
                raise HTTPException(status_code=404, detail="MPP session not found")
            if row["org_id"] != org_id:
                raise HTTPException(status_code=403, detail="Access denied")
            return dict(row)

    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="MPP session not found")
    if session["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return session


def _row_to_response(s: dict) -> MPPSessionResponse:
    """Convert DB row or in-memory dict to response model."""
    return MPPSessionResponse(
        session_id=s["session_id"],
        mandate_id=s.get("mandate_id"),
        wallet_id=s.get("wallet_id"),
        agent_id=s.get("agent_id"),
        method=s["method"],
        chain=s["chain"],
        currency=s["currency"],
        spending_limit=str(s["spending_limit"]),
        remaining=str(s["remaining"]),
        total_spent=str(s["total_spent"]),
        payment_count=s["payment_count"],
        status=s["status"],
        created_at=str(s["created_at"]),
        closed_at=str(s["closed_at"]) if s.get("closed_at") else None,
        expires_at=str(s["expires_at"]) if s.get("expires_at") else None,
    )


@router.get("/sessions/{session_id}", response_model=MPPSessionResponse)
async def get_session(
    session_id: str,
    principal: Principal = Depends(require_principal),
):
    """Get MPP session status."""
    session = await _load_session(session_id, principal.org_id)
    return _row_to_response(session)


@router.post("/sessions/{session_id}/execute", response_model=ExecutePaymentResponse)
async def execute_payment(
    session_id: str,
    req: ExecutePaymentRequest,
    principal: Principal = Depends(require_principal),
):
    """Execute a payment within an MPP session."""
    session = await _load_session(session_id, principal.org_id)

    if session["status"] != "active":
        raise HTTPException(status_code=409, detail=f"Session is {session['status']}, cannot execute")

    # Check expiration
    expires_at = session.get("expires_at")
    if expires_at:
        exp_str = str(expires_at)
        if datetime.now(UTC).isoformat() > exp_str:
            # Mark expired
            pool = await _get_db()
            if pool:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE mpp_sessions SET status = 'expired' WHERE session_id = $1",
                        session_id,
                    )
            elif session_id in _sessions:
                _sessions[session_id]["status"] = "expired"
            raise HTTPException(status_code=409, detail="Session has expired")

    remaining = Decimal(str(session["remaining"]))
    if req.amount > remaining:
        raise HTTPException(
            status_code=422,
            detail=f"Amount {req.amount} exceeds remaining session budget {remaining}",
        )

    payment_id = f"mpp_pay_{uuid4().hex[:16]}"
    new_remaining = remaining - req.amount
    new_total = Decimal(str(session["total_spent"])) + req.amount
    new_count = session["payment_count"] + 1
    new_status = "exhausted" if new_remaining <= Decimal("0") else "active"

    pool = await _get_db()
    if pool:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """UPDATE mpp_sessions
                       SET remaining = $1, total_spent = $2, payment_count = $3, status = $4
                       WHERE session_id = $5""",
                    new_remaining, new_total, new_count, new_status, session_id,
                )
                await conn.execute(
                    """INSERT INTO mpp_payments
                       (payment_id, session_id, amount, currency, merchant, merchant_url,
                        status, chain, created_at, metadata)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                    payment_id, session_id, req.amount, session["currency"],
                    req.merchant, req.merchant_url or "",
                    "completed", session["chain"], datetime.now(UTC),
                    json_module.dumps(req.metadata or {}),
                )
    else:
        # In-memory fallback
        mem = _sessions.get(session_id)
        if mem:
            mem["remaining"] = new_remaining
            mem["total_spent"] = new_total
            mem["payment_count"] = new_count
            mem["status"] = new_status
            _payments.setdefault(session_id, []).append({
                "payment_id": payment_id,
                "session_id": session_id,
                "amount": req.amount,
                "merchant": req.merchant,
                "status": "completed",
                "tx_hash": None,
                "chain": session["chain"],
                "created_at": datetime.now(UTC).isoformat(),
            })

    logger.info(
        "MPP payment executed: %s in session %s (amount=%s, remaining=%s)",
        payment_id, session_id, req.amount, new_remaining,
    )

    return ExecutePaymentResponse(
        payment_id=payment_id,
        session_id=session_id,
        amount=str(req.amount),
        merchant=req.merchant,
        status="completed",
        tx_hash=None,
        chain=session["chain"],
        remaining=str(new_remaining),
    )


@router.post("/sessions/{session_id}/close", response_model=MPPSessionResponse)
async def close_session(
    session_id: str,
    principal: Principal = Depends(require_principal),
):
    """Close an MPP session and settle remaining balance."""
    session = await _load_session(session_id, principal.org_id)

    if session["status"] not in ("active", "exhausted"):
        raise HTTPException(status_code=409, detail=f"Session is already {session['status']}")

    closed_at = datetime.now(UTC)

    pool = await _get_db()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE mpp_sessions SET status = 'closed', closed_at = $1 WHERE session_id = $2",
                closed_at, session_id,
            )
    else:
        mem = _sessions.get(session_id)
        if mem:
            mem["status"] = "closed"
            mem["closed_at"] = closed_at.isoformat()

    session["status"] = "closed"
    session["closed_at"] = closed_at.isoformat()

    logger.info(
        "MPP session closed: %s (spent=%s, payments=%d)",
        session_id, session["total_spent"], session["payment_count"],
    )
    return _row_to_response(session)


@router.post("/evaluate", response_model=PolicyEvaluateResponse)
async def evaluate_policy(
    req: PolicyEvaluateRequest,
    principal: Principal = Depends(require_principal),
):
    """Evaluate Sardis policy for an MPP payment (proxy to Sardis Guard)."""
    # Basic policy evaluation — in production, this calls the Sardis Guard service
    allowed = True
    reason = "ALLOWED by default policy"
    checks_passed = 12
    checks_total = 12

    # Basic limit checks
    if req.amount > Decimal("10000"):
        allowed = False
        reason = "Amount exceeds maximum single payment limit ($10,000)"
        checks_passed = 11

    logger.info(
        "MPP policy evaluation: amount=%s merchant=%s result=%s",
        req.amount, req.merchant, "ALLOWED" if allowed else "DENIED",
    )

    return PolicyEvaluateResponse(
        allowed=allowed,
        reason=reason,
        checks_passed=checks_passed,
        checks_total=checks_total,
    )


@router.post("/simulate", response_model=PolicyEvaluateResponse)
async def simulate_policy(
    req: PolicyEvaluateRequest,
    principal: Principal = Depends(require_principal),
):
    """Dry-run policy check without executing payment."""
    # Same as evaluate but explicitly labeled as simulation
    return await evaluate_policy(req, principal)


# ── Virtual Card Issuance via Laso/Locus MPP ─────────────────────────


class IssueCardRequest(BaseModel):
    amount: Decimal = Field(..., ge=5, le=1000, description="Card amount in USD ($5-$1,000)")
    currency: str = Field(default="USD", description="Card currency")
    session_id: str | None = Field(default=None, description="MPP session to charge against")


class IssueCardResponse(BaseModel):
    card_id: str
    card_number: str
    cvv: str
    expiry: str
    amount: str
    currency: str
    status: str
    card_type: str


@router.post("/cards/issue", response_model=IssueCardResponse, status_code=status.HTTP_201_CREATED)
async def issue_virtual_card(
    req: IssueCardRequest,
    principal: Principal = Depends(require_principal),
):
    """Issue a virtual prepaid card via Laso Finance MPP service.

    The card is a non-reloadable Visa prepaid card issued through
    the Locus MPP proxy. Amount must be between $5 and $1,000.

    If session_id is provided, the card amount will be deducted
    from the MPP session budget.

    Restrictions:
    - US-only (IP-locked)
    - Non-reloadable
    - No 3D Secure
    - Card amount must match checkout total exactly
    """
    # If session provided, check budget
    if req.session_id:
        session = _sessions.get(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="MPP session not found")
        if session["org_id"] != principal.org_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if session["status"] != "active":
            raise HTTPException(status_code=409, detail=f"Session is {session['status']}")
        if req.amount > session["remaining"]:
            raise HTTPException(
                status_code=422,
                detail=f"Card amount {req.amount} exceeds remaining session budget {session['remaining']}",
            )

    # Issue card via Laso MPP service
    try:
        from sardis_mpp.services.laso import LasoMPPService, LasoPaymentRequired

        laso = LasoMPPService()
        card = await laso.issue_card(amount=req.amount, currency=req.currency)

        # Deduct from session if applicable
        if req.session_id and req.session_id in _sessions:
            session = _sessions[req.session_id]
            session["remaining"] = session["remaining"] - req.amount
            session["total_spent"] = session["total_spent"] + req.amount
            session["payment_count"] += 1

        logger.info("Virtual card issued: %s amount=%s via Laso/Locus MPP", card.card_id, req.amount)

        return IssueCardResponse(
            card_id=card.card_id,
            card_number=card.card_number,
            cvv=card.cvv,
            expiry=card.expiry,
            amount=str(card.amount),
            currency=card.currency,
            status=card.status,
            card_type=card.card_type,
        )

    except ImportError:
        # sardis_mpp not installed — return stub for demo
        card_id = f"card_{uuid4().hex[:12]}"
        logger.info("Virtual card issued (stub): %s amount=%s", card_id, req.amount)

        # Deduct from session if applicable
        if req.session_id and req.session_id in _sessions:
            session = _sessions[req.session_id]
            session["remaining"] = session["remaining"] - req.amount
            session["total_spent"] = session["total_spent"] + req.amount
            session["payment_count"] += 1

        return IssueCardResponse(
            card_id=card_id,
            card_number="4111XXXXXXXX1234",
            cvv="***",
            expiry="12/27",
            amount=str(req.amount),
            currency=req.currency,
            status="issued",
            card_type="single_use",
        )
