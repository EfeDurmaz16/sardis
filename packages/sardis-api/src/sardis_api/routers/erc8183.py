"""ERC-8183 Agentic Commerce — job lifecycle API router.

Three-party job primitive: Client creates a job, Provider submits a
deliverable, and an independent Evaluator approves or rejects.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["erc8183"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CreateJobRequest(BaseModel):
    provider_agent_id: str
    evaluator_agent_id: str
    amount: str = Field(description="Job payment amount as a decimal string")
    token: str = "USDC"
    chain: str = "base"
    deadline_hours: int = Field(default=72, ge=1, le=720)
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateJobResponse(BaseModel):
    job_id: str
    state: str
    created_at: str
    deadline: str


class JobResponse(BaseModel):
    id: str
    client_agent_id: str
    provider_agent_id: str
    evaluator_agent_id: str
    amount: str
    token: str
    chain: str
    state: str
    description: str
    created_at: str
    deadline: str
    funded_at: str | None = None
    funding_tx_hash: str | None = None
    deliverable_uri: str | None = None
    deliverable_hash: str | None = None
    submitted_at: str | None = None
    evaluation_result: str | None = None
    evaluation_reason: str | None = None
    evaluated_at: str | None = None
    evaluation_tx_hash: str | None = None
    settlement_tx_hash: str | None = None
    settled_at: str | None = None
    onchain_job_id: int | None = None
    contract_address: str | None = None
    hook_contract_address: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FundJobRequest(BaseModel):
    tx_hash: str = ""


class SubmitJobRequest(BaseModel):
    deliverable_uri: str
    deliverable_hash: str = ""


class EvaluateJobRequest(BaseModel):
    approved: bool
    reason: str = ""
    evidence_uri: str = ""


class DisputeJobRequest(BaseModel):
    reason: str


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


class EvaluationResponse(BaseModel):
    id: str
    job_id: str
    evaluator_agent_id: str
    result: str
    reason: str | None = None
    evidence_uri: str | None = None
    trust_score_at_eval: float | None = None
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_STATES = {"open", "funded", "submitted", "completed", "rejected", "expired", "disputed"}

_STATE_TRANSITIONS: dict[str, set[str]] = {
    "open": {"funded", "expired"},
    "funded": {"submitted", "expired", "disputed"},
    "submitted": {"completed", "rejected", "disputed"},
}


def _ts(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _gen_id(prefix: str = "job") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _row_to_response(row: dict[str, Any]) -> JobResponse:
    return JobResponse(
        id=row["id"],
        client_agent_id=row["client_agent_id"],
        provider_agent_id=row["provider_agent_id"],
        evaluator_agent_id=row["evaluator_agent_id"],
        amount=str(row["amount"]),
        token=row["token"],
        chain=row["chain"],
        state=row["state"],
        description=row.get("description") or "",
        created_at=_ts(row["created_at"]) or "",
        deadline=_ts(row["deadline"]) or "",
        funded_at=_ts(row.get("funded_at")),
        funding_tx_hash=row.get("funding_tx_hash"),
        deliverable_uri=row.get("deliverable_uri"),
        deliverable_hash=row.get("deliverable_hash"),
        submitted_at=_ts(row.get("submitted_at")),
        evaluation_result=row.get("evaluation_result"),
        evaluation_reason=row.get("evaluation_reason"),
        evaluated_at=_ts(row.get("evaluated_at")),
        evaluation_tx_hash=row.get("evaluation_tx_hash"),
        settlement_tx_hash=row.get("settlement_tx_hash"),
        settled_at=_ts(row.get("settled_at")),
        onchain_job_id=row.get("onchain_job_id"),
        contract_address=row.get("contract_address"),
        hook_contract_address=row.get("hook_contract_address"),
        metadata=row.get("metadata") or {},
    )


async def _get_pool(request: Any) -> Any:
    """Retrieve the asyncpg connection pool from app state."""
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database pool not available",
        )
    return pool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/erc8183/jobs", response_model=CreateJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: CreateJobRequest,
    request: Any = Depends(lambda r: r),
    principal: Principal = Depends(require_principal),
) -> CreateJobResponse:
    """Create a new ERC-8183 job as the client agent."""
    from fastapi import Request as _Req  # noqa: F811
    request: _Req = request  # type: ignore[no-redef]

    # Validate amount
    try:
        amount = Decimal(body.amount)
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount must be a positive decimal string",
        )

    client_agent_id = principal.user_id

    if client_agent_id == body.provider_agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client and provider must be different agents",
        )
    if body.evaluator_agent_id in (client_agent_id, body.provider_agent_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evaluator must be different from both client and provider",
        )

    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=body.deadline_hours)
    job_id = _gen_id("job")

    pool = await _get_pool(request)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO erc8183_jobs
                (id, client_agent_id, provider_agent_id, evaluator_agent_id,
                 amount, token, chain, state, description, created_at, deadline, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'open', $8, $9, $10, $11)
            """,
            job_id,
            client_agent_id,
            body.provider_agent_id,
            body.evaluator_agent_id,
            amount,
            body.token,
            body.chain,
            body.description,
            now,
            deadline,
            body.metadata or {},
        )

    logger.info("ERC-8183 job created: %s by %s", job_id, client_agent_id)
    return CreateJobResponse(
        job_id=job_id,
        state="open",
        created_at=now.isoformat(),
        deadline=deadline.isoformat(),
    )


@router.get("/erc8183/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    request: Any = Depends(lambda r: r),
    principal: Principal = Depends(require_principal),
) -> JobResponse:
    """Get job details by ID."""
    pool = await _get_pool(request)
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM erc8183_jobs WHERE id = $1", job_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _row_to_response(dict(row))


@router.get("/erc8183/jobs", response_model=JobListResponse)
async def list_jobs(
    request: Any = Depends(lambda r: r),
    principal: Principal = Depends(require_principal),
    role: str | None = Query(None, description="Filter by role: client, provider, evaluator"),
    state: str | None = Query(None, description="Filter by job state"),
    agent_id: str | None = Query(None, description="Agent ID to filter for"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> JobListResponse:
    """List jobs with optional filters."""
    conditions: list[str] = []
    params: list[Any] = []
    idx = 1

    target_agent = agent_id or principal.user_id

    if role:
        role = role.lower()
        if role == "client":
            conditions.append(f"client_agent_id = ${idx}")
        elif role == "provider":
            conditions.append(f"provider_agent_id = ${idx}")
        elif role == "evaluator":
            conditions.append(f"evaluator_agent_id = ${idx}")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="role must be one of: client, provider, evaluator",
            )
        params.append(target_agent)
        idx += 1
    else:
        # Show all jobs where agent is involved
        conditions.append(
            f"(client_agent_id = ${idx} OR provider_agent_id = ${idx} OR evaluator_agent_id = ${idx})"
        )
        params.append(target_agent)
        idx += 1

    if state:
        if state not in _VALID_STATES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state. Must be one of: {', '.join(sorted(_VALID_STATES))}",
            )
        conditions.append(f"state = ${idx}")
        params.append(state)
        idx += 1

    where = " AND ".join(conditions) if conditions else "TRUE"

    pool = await _get_pool(request)
    async with pool.acquire() as conn:
        count_row = await conn.fetchrow(f"SELECT COUNT(*) as total FROM erc8183_jobs WHERE {where}", *params)
        total = count_row["total"] if count_row else 0

        rows = await conn.fetch(
            f"SELECT * FROM erc8183_jobs WHERE {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
            *params,
            limit,
            offset,
        )

    return JobListResponse(
        jobs=[_row_to_response(dict(r)) for r in rows],
        total=total,
    )


@router.post("/erc8183/jobs/{job_id}/fund", response_model=JobResponse)
async def fund_job(
    job_id: str,
    body: FundJobRequest,
    request: Any = Depends(lambda r: r),
    principal: Principal = Depends(require_principal),
) -> JobResponse:
    """Fund a job (transitions open -> funded)."""
    pool = await _get_pool(request)
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM erc8183_jobs WHERE id = $1", job_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        job = dict(row)
        if job["state"] != "open":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job is in state '{job['state']}', expected 'open'",
            )
        if job["client_agent_id"] != principal.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the client agent can fund a job",
            )

        await conn.execute(
            """
            UPDATE erc8183_jobs
            SET state = 'funded', funded_at = $2, funding_tx_hash = $3, updated_at = $2
            WHERE id = $1
            """,
            job_id,
            now,
            body.tx_hash or None,
        )
        job["state"] = "funded"
        job["funded_at"] = now
        job["funding_tx_hash"] = body.tx_hash or None
        job["updated_at"] = now

    logger.info("ERC-8183 job funded: %s", job_id)
    return _row_to_response(job)


@router.post("/erc8183/jobs/{job_id}/submit", response_model=JobResponse)
async def submit_deliverable(
    job_id: str,
    body: SubmitJobRequest,
    request: Any = Depends(lambda r: r),
    principal: Principal = Depends(require_principal),
) -> JobResponse:
    """Submit a deliverable for a job (transitions funded -> submitted)."""
    pool = await _get_pool(request)
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM erc8183_jobs WHERE id = $1", job_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        job = dict(row)
        if job["state"] != "funded":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job is in state '{job['state']}', expected 'funded'",
            )
        if job["provider_agent_id"] != principal.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the provider agent can submit deliverables",
            )

        await conn.execute(
            """
            UPDATE erc8183_jobs
            SET state = 'submitted', deliverable_uri = $2, deliverable_hash = $3,
                submitted_at = $4, updated_at = $4
            WHERE id = $1
            """,
            job_id,
            body.deliverable_uri,
            body.deliverable_hash or None,
            now,
        )
        job["state"] = "submitted"
        job["deliverable_uri"] = body.deliverable_uri
        job["deliverable_hash"] = body.deliverable_hash or None
        job["submitted_at"] = now
        job["updated_at"] = now

    logger.info("ERC-8183 deliverable submitted: %s", job_id)
    return _row_to_response(job)


@router.post("/erc8183/jobs/{job_id}/evaluate", response_model=JobResponse)
async def evaluate_job(
    job_id: str,
    body: EvaluateJobRequest,
    request: Any = Depends(lambda r: r),
    principal: Principal = Depends(require_principal),
) -> JobResponse:
    """Evaluate a submitted deliverable (transitions submitted -> completed/rejected)."""
    pool = await _get_pool(request)
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM erc8183_jobs WHERE id = $1", job_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        job = dict(row)
        if job["state"] != "submitted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job is in state '{job['state']}', expected 'submitted'",
            )
        if job["evaluator_agent_id"] != principal.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the evaluator agent can evaluate a job",
            )

        new_state = "completed" if body.approved else "rejected"
        result = "approved" if body.approved else "rejected"

        eval_id = _gen_id("eval")
        await conn.execute(
            """
            INSERT INTO erc8183_evaluations
                (id, job_id, evaluator_agent_id, result, reason, evidence_uri, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            eval_id,
            job_id,
            principal.user_id,
            result,
            body.reason or None,
            body.evidence_uri or None,
            now,
        )

        await conn.execute(
            """
            UPDATE erc8183_jobs
            SET state = $2, evaluation_result = $3, evaluation_reason = $4,
                evaluated_at = $5, updated_at = $5
            WHERE id = $1
            """,
            job_id,
            new_state,
            result,
            body.reason or None,
            now,
        )
        job["state"] = new_state
        job["evaluation_result"] = result
        job["evaluation_reason"] = body.reason or None
        job["evaluated_at"] = now
        job["updated_at"] = now

    logger.info("ERC-8183 job evaluated: %s -> %s", job_id, new_state)
    return _row_to_response(job)


@router.post("/erc8183/jobs/{job_id}/dispute", response_model=JobResponse)
async def dispute_job(
    job_id: str,
    body: DisputeJobRequest,
    request: Any = Depends(lambda r: r),
    principal: Principal = Depends(require_principal),
) -> JobResponse:
    """Raise a dispute on a funded or submitted job."""
    pool = await _get_pool(request)
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM erc8183_jobs WHERE id = $1", job_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        job = dict(row)
        if job["state"] not in ("funded", "submitted"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot dispute a job in state '{job['state']}'",
            )

        # Only client or provider can dispute
        if principal.user_id not in (job["client_agent_id"], job["provider_agent_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the client or provider agent can raise a dispute",
            )

        await conn.execute(
            """
            UPDATE erc8183_jobs
            SET state = 'disputed', metadata = metadata || $2::jsonb, updated_at = $3
            WHERE id = $1
            """,
            job_id,
            {"dispute_reason": body.reason, "disputed_by": principal.user_id, "disputed_at": now.isoformat()},
            now,
        )
        job["state"] = "disputed"
        job["updated_at"] = now
        job["metadata"] = {
            **(job.get("metadata") or {}),
            "dispute_reason": body.reason,
            "disputed_by": principal.user_id,
            "disputed_at": now.isoformat(),
        }

    logger.info("ERC-8183 job disputed: %s by %s", job_id, principal.user_id)
    return _row_to_response(job)


@router.post("/erc8183/jobs/{job_id}/expire", response_model=JobResponse)
async def expire_job(
    job_id: str,
    request: Any = Depends(lambda r: r),
    principal: Principal = Depends(require_principal),
) -> JobResponse:
    """Force-expire a job past its deadline."""
    pool = await _get_pool(request)
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM erc8183_jobs WHERE id = $1", job_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        job = dict(row)
        if job["state"] not in ("open", "funded", "submitted"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot expire a job in state '{job['state']}'",
            )
        if job["deadline"] > now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job deadline has not passed yet",
            )

        await conn.execute(
            """
            UPDATE erc8183_jobs SET state = 'expired', updated_at = $2 WHERE id = $1
            """,
            job_id,
            now,
        )
        job["state"] = "expired"
        job["updated_at"] = now

    logger.info("ERC-8183 job expired: %s", job_id)
    return _row_to_response(job)


@router.get("/erc8183/jobs/{job_id}/evaluations", response_model=list[EvaluationResponse])
async def list_evaluations(
    job_id: str,
    request: Any = Depends(lambda r: r),
    principal: Principal = Depends(require_principal),
) -> list[EvaluationResponse]:
    """Get evaluation history for a job."""
    pool = await _get_pool(request)
    async with pool.acquire() as conn:
        # Verify job exists
        exists = await conn.fetchval("SELECT 1 FROM erc8183_jobs WHERE id = $1", job_id)
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        rows = await conn.fetch(
            "SELECT * FROM erc8183_evaluations WHERE job_id = $1 ORDER BY created_at DESC",
            job_id,
        )

    return [
        EvaluationResponse(
            id=r["id"],
            job_id=r["job_id"],
            evaluator_agent_id=r["evaluator_agent_id"],
            result=r["result"],
            reason=r.get("reason"),
            evidence_uri=r.get("evidence_uri"),
            trust_score_at_eval=float(r["trust_score_at_eval"]) if r.get("trust_score_at_eval") else None,
            created_at=_ts(r["created_at"]) or "",
        )
        for r in rows
    ]
