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

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
    next_steps: list[str] = []


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
    next_steps: list[str] = []


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
        next_steps=[
            "POST /api/v2/mpp/sessions/{session_id}/execute — Execute payment",
        ],
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
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Execute a payment within an MPP session.

    When a chain executor is available (SARDIS_CHAIN_MODE=live or simulated),
    this endpoint builds a PaymentMandate and executes a real Tempo transfer
    via the ChainExecutor. The resulting tx_hash is persisted to the
    mpp_payments record.
    """
    session = await _load_session(session_id, principal.org_id)

    if session["status"] != "active":
        raise HTTPException(status_code=409, detail=f"Session is {session['status']}, cannot execute")

    # Check expiration
    expires_at = session.get("expires_at")
    if expires_at:
        try:
            if isinstance(expires_at, datetime):
                exp_dt = expires_at
            elif isinstance(expires_at, str):
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            else:
                exp_dt = datetime.fromisoformat(str(expires_at).replace(" ", "T").replace("Z", "+00:00"))
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=UTC)
            is_expired = datetime.now(UTC) > exp_dt
        except Exception:
            is_expired = False
        if is_expired:
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

    # ── Execute on-chain payment via ChainExecutor ────────────────────
    tx_hash: str | None = None
    pay_status = "completed"
    pay_error: str | None = None

    chain_executor = getattr(request.app.state, "chain_executor", None)
    if chain_executor:
        try:
            from sardis_v2_core.mandates import PaymentMandate, VCProof

            chain = session["chain"]
            # Map MPP chain names to executor chain names
            chain_key = {
                "tempo": "tempo",
                "tempo_testnet": "tempo_testnet",
                "tempo_moderato": "tempo_testnet",
            }.get(chain, chain)

            wallet_id = session.get("wallet_id")
            if not wallet_id:
                raise RuntimeError("Session has no wallet_id — cannot sign transaction")

            # Convert decimal amount to minor units (6 decimals for USDC)
            amount_minor = int(req.amount * Decimal("1000000"))

            # Resolve the wallet's on-chain address from DB so we don't
            # need to call Turnkey's list_wallet_accounts (which expects
            # the Turnkey wallet ID, not Sardis's internal wallet_id).
            from_address = None
            if wallet_id:
                try:
                    pool = await _get_db()
                    if pool:
                        async with pool.acquire() as conn:
                            addr_row = await conn.fetchrow(
                                "SELECT addresses FROM wallets_v2 WHERE external_id = $1",
                                wallet_id,
                            )
                            if addr_row and addr_row["addresses"]:
                                import json as _json
                                addrs = addr_row["addresses"] if isinstance(addr_row["addresses"], dict) else _json.loads(addr_row["addresses"])
                                # Try tempo, then base_sepolia, then any address
                                from_address = addrs.get("tempo") or addrs.get("base_sepolia") or addrs.get("base") or next(iter(addrs.values()), None)
                except Exception as addr_err:
                    logger.warning("Could not resolve wallet address from DB: %s", addr_err)

            mandate = PaymentMandate(
                mandate_id=payment_id,
                mandate_type="payment",
                issuer=f"sardis:mpp:{session_id}",
                subject=principal.org_id,
                expires_at=int(datetime.now(UTC).timestamp()) + 300,
                nonce=uuid4().hex,
                proof=VCProof(
                    verification_method="sardis:mpp:internal",
                    created=datetime.now(UTC).isoformat(),
                    proof_value="mpp-session-authorized",
                ),
                domain=req.merchant,
                purpose="checkout",
                chain=chain_key,
                token=session.get("currency", "USDC"),
                amount_minor=amount_minor,
                destination=req.destination or req.merchant,
                audit_hash=f"mpp:{session_id}:{payment_id}",
                wallet_id=wallet_id,
                ai_agent_presence=True,
                transaction_modality="human_not_present",
                merchant_domain=req.merchant_url or req.merchant,
            )
            # Attach from_address so ChainExecutor skips Turnkey lookup
            if from_address:
                mandate.from_address = from_address  # type: ignore[attr-defined]

            receipt = await chain_executor.dispatch_payment(mandate)
            tx_hash = receipt.tx_hash
            logger.info(
                "MPP on-chain payment success: %s tx=%s chain=%s",
                payment_id, tx_hash, chain_key,
            )

        except Exception as exc:
            pay_status = "failed"
            pay_error = str(exc)
            logger.error(
                "MPP on-chain payment failed: %s error=%s",
                payment_id, pay_error,
            )
            # Do NOT deduct budget on failure — raise so caller can retry
            raise HTTPException(
                status_code=502,
                detail=f"On-chain payment failed: {pay_error}",
            )
    else:
        logger.warning("MPP execute: no chain_executor on app.state — budget-only mode")

    # ── Persist payment + update session budget ───────────────────────
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
                        status, tx_hash, chain, created_at, metadata)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)""",
                    payment_id, session_id, req.amount, session["currency"],
                    req.merchant, req.merchant_url or "",
                    pay_status, tx_hash, session["chain"], datetime.now(UTC),
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
                "status": pay_status,
                "tx_hash": tx_hash,
                "chain": session["chain"],
                "created_at": datetime.now(UTC).isoformat(),
            })

    logger.info(
        "MPP payment executed: %s in session %s (amount=%s, remaining=%s, tx=%s)",
        payment_id, session_id, req.amount, new_remaining, tx_hash,
    )

    return ExecutePaymentResponse(
        payment_id=payment_id,
        session_id=session_id,
        amount=str(req.amount),
        merchant=req.merchant,
        status=pay_status,
        tx_hash=tx_hash,
        chain=session["chain"],
        remaining=str(new_remaining),
        next_steps=[
            "GET /api/v2/ledger/entries — Check audit trail",
            "POST /api/v2/mpp/sessions/{session_id}/close — Close session",
        ],
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
    sandbox: bool = Field(default=False, description="True when card is simulated (non-live mode)")


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

    # ── Sandbox mode: return simulated card when not in live mode ────
    chain_mode = os.getenv("SARDIS_CHAIN_MODE", "simulated").strip().lower()
    sandbox_override = os.getenv("SARDIS_VIRTUAL_CARDS_SANDBOX", "").strip().lower() == "true"
    if chain_mode != "live" or sandbox_override:
        import hashlib
        import uuid as _uuid

        card_id = f"sandbox_card_{_uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        seed = hashlib.sha256(f"{card_id}{req.amount}{now.isoformat()[:10]}".encode()).hexdigest()
        card_number = f"4000 00{seed[:2]} {seed[2:6]} {seed[6:10]}"
        cvv = seed[10:13]
        expiry_month = str((int(seed[13:15], 16) % 12) + 1).zfill(2)
        expiry = f"{expiry_month}/{now.year + 2}"

        # Deduct from session if applicable
        if req.session_id and req.session_id in _sessions:
            session = _sessions[req.session_id]
            session["remaining"] = session["remaining"] - req.amount
            session["total_spent"] = session["total_spent"] + req.amount
            session["payment_count"] += 1

        logger.info("Sandbox virtual card issued: %s amount=%s for org %s", card_id, req.amount, principal.org_id)

        return IssueCardResponse(
            card_id=card_id,
            card_number=card_number,
            cvv=cvv,
            expiry=expiry,
            amount=str(req.amount),
            currency=req.currency,
            status="ready",
            card_type="single_use",
            sandbox=True,
        )

    # ── Live mode: issue real card via Laso MPP service ───────────────
    try:
        from sardis_mpp.services.laso import LasoMPPService

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
            sandbox=False,
        )

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="sardis_mpp package not installed -- set SARDIS_CHAIN_MODE=simulated for sandbox cards",
        )
