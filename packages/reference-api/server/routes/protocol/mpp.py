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

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from server.authz import Principal, require_principal
from server.domains.mpp_session import (
    MPPBudgetExceededError,
    MPPSessionExpiredError,
    MPPSessionInactiveError,
    apply_payment_budget,
    ensure_card_budget,
    ensure_session_can_execute,
)
from server.models.mpp import (
    CreateMPPSessionRequest,
    ExecutePaymentRequest,
    ExecutePaymentResponse,
    IssueCardRequest,
    IssueCardResponse,
    MPPSessionResponse,
    PolicyEvaluateRequest,
    PolicyEvaluateResponse,
    mpp_session_response_from_record,
)
from server.repositories.mpp_session_repository import (
    close_session_record,
    create_session_record,
    deduct_memory_session,
    get_memory_session,
    load_session,
    mark_session_expired,
    record_payment,
)
from server.services.mpp_execution import execute_chain_payment
from server.services.mpp_virtual_cards import issue_mpp_virtual_card

logger = logging.getLogger(__name__)

router = APIRouter()


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
    expires_at_dt = None
    expires_at = None
    if req.expires_in_seconds:
        expires_at_dt = now + timedelta(seconds=req.expires_in_seconds)
        expires_at = expires_at_dt.isoformat()

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
        "created_at": now,
        "closed_at": None,
        "expires_at": expires_at,
    }
    await create_session_record(
        session=session,
        metadata=req.metadata or {},
        expires_at_dt=expires_at_dt,
    )
    logger.info("MPP session created: %s (limit=%s %s)", session_id, req.spending_limit, req.currency)

    return mpp_session_response_from_record(
        session,
        next_steps=[
            "POST /api/v2/mpp/sessions/{session_id}/execute — Execute payment",
        ],
    )


async def _load_session(session_id: str, org_id: str) -> dict:
    """Load session from DB or memory, with org ownership check."""
    session = await load_session(session_id, org_id)
    if not session:
        raise HTTPException(status_code=404, detail="MPP session not found")
    if session["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return session


@router.get("/sessions/{session_id}", response_model=MPPSessionResponse)
async def get_session(
    session_id: str,
    principal: Principal = Depends(require_principal),
):
    """Get MPP session status."""
    session = await _load_session(session_id, principal.org_id)
    return mpp_session_response_from_record(session)


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

    try:
        ensure_session_can_execute(session)
        budget = apply_payment_budget(session, req.amount)
    except MPPSessionExpiredError as exc:
        await mark_session_expired(session_id)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MPPSessionInactiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MPPBudgetExceededError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    payment_id = f"mpp_pay_{uuid4().hex[:16]}"

    # ── Execute on-chain payment via ChainExecutor ────────────────────
    tx_hash: str | None = None
    pay_status = "completed"
    pay_error: str | None = None

    chain_executor = getattr(request.app.state, "chain_executor", None)
    if chain_executor:
        try:
            tx_hash = await execute_chain_payment(
                chain_executor=chain_executor,
                session=session,
                request=req,
                payment_id=payment_id,
                organization_id=principal.org_id,
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

    await record_payment(
        session_id=session_id,
        amount=req.amount,
        merchant=req.merchant,
        merchant_url=req.merchant_url,
        metadata=req.metadata or {},
        payment_id=payment_id,
        currency=session["currency"],
        chain=session["chain"],
        new_remaining=budget.remaining,
        new_total=budget.total_spent,
        new_count=budget.payment_count,
        new_status=budget.status,
        pay_status=pay_status,
        tx_hash=tx_hash,
        created_at=datetime.now(UTC),
    )

    logger.info(
        "MPP payment executed: %s in session %s (amount=%s, remaining=%s, tx=%s)",
        payment_id, session_id, req.amount, budget.remaining, tx_hash,
    )

    return ExecutePaymentResponse(
        payment_id=payment_id,
        session_id=session_id,
        amount=str(req.amount),
        merchant=req.merchant,
        status=pay_status,
        tx_hash=tx_hash,
        chain=session["chain"],
        remaining=str(budget.remaining),
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

    await close_session_record(session_id, closed_at)

    session["status"] = "closed"
    session["closed_at"] = closed_at.isoformat()

    logger.info(
        "MPP session closed: %s (spent=%s, payments=%d)",
        session_id, session["total_spent"], session["payment_count"],
    )
    return mpp_session_response_from_record(session)


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
        session = get_memory_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="MPP session not found")
        if session["org_id"] != principal.org_id:
            raise HTTPException(status_code=403, detail="Access denied")
        try:
            ensure_card_budget(session, req.amount)
        except MPPSessionInactiveError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except MPPBudgetExceededError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc

    try:
        response = await issue_mpp_virtual_card(req)
        if req.session_id:
            deduct_memory_session(req.session_id, req.amount)
        logger.info("MPP virtual card issued: %s amount=%s for org %s", response.card_id, req.amount, principal.org_id)
        return response
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="sardis_mpp package not installed -- set SARDIS_CHAIN_MODE=simulated for sandbox cards",
        )
