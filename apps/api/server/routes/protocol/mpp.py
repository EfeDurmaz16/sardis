"""MPP (Machine Payments Protocol) API endpoints.

NOTE: This is a Sardis-native session/budget-authority surface over Postgres,
NOT the MPP wire protocol. It is partial and not a conformance claim — see
docs/productization/research/PROTOCOL_STRATEGY.md (MPP, fix-then-keep / rename).

Provides session-based MPP payment management:
- Create MPP sessions with spending mandates
- Execute payments within sessions
- Close sessions and settle remaining
- Policy evaluation and dry-run simulation (/evaluate and /simulate route through
  the real SpendingPolicy engine — the same engine the PaymentOrchestrator uses —
  and are fail-closed: no agent_id / no policy / engine error => DENY)
- Virtual card issuance (EXPERIMENTAL / DEAD — depends on a `sardis_mpp` package
  that does not exist on disk; returns 503)

Persistence: Uses PostgreSQL (mpp_sessions + mpp_payments tables from migration 075)
when DATABASE_URL is set. Falls back to in-memory for dev/demo.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from server.authz import Principal, require_principal
from server.domains.mpp_session import (
    MPPBudgetExceededError,
    MPPSessionExpiredError,
    MPPSessionInactiveError,
    apply_payment_budget,
    create_session_record_payload,
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
from server.services.mpp_policy import evaluate_mpp_policy
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
    session_id = f"mpp_sess_{uuid4().hex[:16]}"
    now = datetime.now(UTC)
    new_session = create_session_record_payload(
        request=req,
        session_id=session_id,
        organization_id=principal.org_id,
        now=now,
    )
    await create_session_record(
        session=new_session.record,
        metadata=req.metadata or {},
        expires_at_dt=new_session.expires_at_dt,
    )
    logger.info("MPP session created: %s (limit=%s %s)", session_id, req.spending_limit, req.currency)

    return mpp_session_response_from_record(
        new_session.record,
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


async def _evaluate_against_real_policy(
    req: PolicyEvaluateRequest,
    request: Request,
    principal: Principal,
) -> PolicyEvaluateResponse:
    """Evaluate an MPP payment against the agent's real SpendingPolicy.

    Fail-closed: requires an agent_id and a resolvable policy. Any engine error,
    missing store, missing agent, or missing policy => DENY. There is no
    default-allow path. Delegates to the shared ``evaluate_mpp_policy`` engine
    (the single MPP policy source of truth) after enforcing org authorization.
    """
    policy_store = getattr(request.app.state, "policy_store", None)

    # Authorization: an org may only evaluate its own agents. This happens
    # before the shared evaluator (which performs no ownership check). We only
    # look the agent up when we have a real agent_id and store to act on.
    if req.agent_id:
        agent_repo = getattr(request.app.state, "agent_repo", None)
        if agent_repo is not None:
            agent = await agent_repo.get(req.agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            if not principal.is_admin and agent.owner_id != principal.org_id:
                raise HTTPException(status_code=403, detail="Access denied")

    decision = await evaluate_mpp_policy(
        policy_store=policy_store,
        agent_id=req.agent_id,
        amount=req.amount,
        merchant=req.merchant,
        currency=req.currency,
        network=req.network,
        merchant_category=req.merchant_category,
        mcc_code=req.mcc_code,
    )
    return PolicyEvaluateResponse(
        allowed=decision.allowed,
        reason=decision.reason,
        checks_passed=decision.checks_passed,
        checks_total=decision.checks_total,
    )


@router.post("/evaluate", response_model=PolicyEvaluateResponse)
async def evaluate_policy(
    req: PolicyEvaluateRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Evaluate an MPP payment against the agent's real SpendingPolicy.

    Routes through the same SpendingPolicy engine the PaymentOrchestrator uses
    (amount/scope/MCC/per-tx/total/window/merchant/drift/approval checks). It is
    fail-closed: no agent_id, no policy, or any engine error => DENY. There is
    no default-allow path.
    """
    return await _evaluate_against_real_policy(req, request, principal)


@router.post("/simulate", response_model=PolicyEvaluateResponse)
async def simulate_policy(
    req: PolicyEvaluateRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Dry-run policy check without executing payment (same engine as /evaluate)."""
    return await _evaluate_against_real_policy(req, request, principal)


# ── Virtual Card Issuance via Laso/Locus MPP ─────────────────────────


@router.post("/cards/issue", response_model=IssueCardResponse, status_code=status.HTTP_201_CREATED)
async def issue_virtual_card(
    req: IssueCardRequest,
    principal: Principal = Depends(require_principal),
):
    """Issue a virtual prepaid card. Amount must be between $5 and $1,000.

    Provider status (see PROTO_mpp_report.md, decision D1):
    - Sandbox / non-live mode (SARDIS_CHAIN_MODE != "live"): returns a simulated
      card (``sandbox=true``) — working, for development only.
    - Live mode: depends on a real MPP card issuer (Laso/Locus) that is NOT yet
      integrated (``sardis_mpp`` package does not exist). The live path therefore
      returns 503 — it never fakes a real card. Enabling live issuance requires a
      founder decision on the issuer integration.

    If session_id is provided, the card amount is checked against (and on success
    deducted from) the MPP session budget.
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
