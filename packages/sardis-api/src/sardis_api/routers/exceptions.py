"""
Exception management API endpoints.

Provides REST endpoints for listing, inspecting, and acting on payment
exceptions raised by the control plane.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sardis_v2_core.exception_workflows import (
    ExceptionWorkflowEngine,
    PaymentException,
    ResolutionStrategy,
)

from sardis_api.authz import require_principal

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])

# NOTE: In-memory only — data is lost on restart. See #80.
# TODO: Replace with database-backed persistence when exception workflows are promoted to production.
_engine = ExceptionWorkflowEngine()


# ============================================================================
# Request / Response models
# ============================================================================


class ExceptionResponse(BaseModel):
    """Serialized PaymentException."""

    exception_id: str
    transaction_id: str
    agent_id: str
    exception_type: str
    status: str
    description: str
    original_amount: str
    currency: str
    merchant_id: str | None = None
    retry_count: int
    max_retries: int
    suggested_strategy: str | None = None
    resolution_notes: str | None = None
    resolved_at: str | None = None
    resolved_by: str | None = None
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_exc(cls, exc: PaymentException) -> ExceptionResponse:
        return cls(
            exception_id=exc.exception_id,
            transaction_id=exc.transaction_id,
            agent_id=exc.agent_id,
            exception_type=exc.exception_type.value,
            status=exc.status.value,
            description=exc.description,
            original_amount=str(exc.original_amount),
            currency=exc.currency,
            merchant_id=exc.merchant_id,
            retry_count=exc.retry_count,
            max_retries=exc.max_retries,
            suggested_strategy=(
                exc.suggested_strategy.value if exc.suggested_strategy else None
            ),
            resolution_notes=exc.resolution_notes,
            resolved_at=(
                exc.resolved_at.isoformat() if exc.resolved_at else None
            ),
            resolved_by=exc.resolved_by,
            created_at=exc.created_at.isoformat(),
            updated_at=exc.updated_at.isoformat(),
            metadata=exc.metadata,
        )


class ResolveRequest(BaseModel):
    notes: str | None = Field(None, description="Resolution notes")
    resolved_by: str = Field(..., description="Identifier of the person resolving")


class EscalateRequest(BaseModel):
    reason: str = Field(..., description="Reason for escalation")


class RetryRequest(BaseModel):
    strategy: str | None = Field(
        None,
        description=(
            "Override strategy: retry | retry_with_backoff | wait_and_retry. "
            "Defaults to the exception's suggested strategy."
        ),
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/exceptions",
    response_model=list[ExceptionResponse],
    summary="List open payment exceptions",
    tags=["exceptions"],
)
async def list_exceptions(
    agent_id: str | None = Query(
        None, description="Filter exceptions to a specific agent"
    ),
) -> list[ExceptionResponse]:
    """Return all open (OPEN or IN_PROGRESS) payment exceptions.

    Pass `agent_id` to narrow results to a single agent.
    """
    exceptions = _engine.get_open_exceptions(agent_id=agent_id)
    return [ExceptionResponse.from_exc(exc) for exc in exceptions]


@router.get(
    "/exceptions/{exception_id}",
    response_model=ExceptionResponse,
    summary="Get a specific payment exception",
    tags=["exceptions"],
)
async def get_exception(exception_id: str) -> ExceptionResponse:
    """Retrieve a single exception by ID regardless of status."""
    exc = _engine.get_exception(exception_id)
    if exc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )
    return ExceptionResponse.from_exc(exc)


@router.post(
    "/exceptions/{exception_id}/resolve",
    response_model=ExceptionResponse,
    summary="Manually resolve a payment exception",
    tags=["exceptions"],
)
async def resolve_exception(
    exception_id: str,
    body: ResolveRequest,
) -> ExceptionResponse:
    """Mark an exception as resolved with optional notes."""
    try:
        exc = _engine.resolve(
            exception_id,
            resolved_by=body.resolved_by,
            notes=body.notes,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )
    return ExceptionResponse.from_exc(exc)


@router.post(
    "/exceptions/{exception_id}/escalate",
    response_model=ExceptionResponse,
    summary="Escalate a payment exception to human review",
    tags=["exceptions"],
)
async def escalate_exception(
    exception_id: str,
    body: EscalateRequest,
) -> ExceptionResponse:
    """Escalate an exception, providing a reason for the escalation."""
    try:
        exc = _engine.escalate(exception_id, reason=body.reason)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )
    return ExceptionResponse.from_exc(exc)


@router.post(
    "/exceptions/{exception_id}/retry",
    response_model=ExceptionResponse,
    summary="Retry a failed payment",
    tags=["exceptions"],
)
async def retry_exception(
    exception_id: str,
    body: RetryRequest,
) -> ExceptionResponse:
    """Execute the retry strategy for a payment exception.

    No live retry function is attached server-side; this transitions the
    exception state according to the strategy and logs intent. A real
    integration would wire in the original payment callable.
    """
    exc = _engine.get_exception(exception_id)
    if exc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )

    # Parse optional strategy override
    strategy: ResolutionStrategy | None = None
    if body.strategy:
        try:
            strategy = ResolutionStrategy(body.strategy)
        except ValueError:
            valid = [s.value for s in ResolutionStrategy]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid strategy '{body.strategy}'. Valid values: {valid}",
            )

    # Only retry-flavoured strategies are meaningful here
    retry_strategies = {
        ResolutionStrategy.RETRY,
        ResolutionStrategy.RETRY_WITH_BACKOFF,
        ResolutionStrategy.WAIT_AND_RETRY,
    }
    effective_strategy = strategy or exc.suggested_strategy
    if effective_strategy and effective_strategy not in retry_strategies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Strategy '{effective_strategy.value}' is not a retry strategy. "
                f"Use /resolve or /escalate instead."
            ),
        )

    try:
        updated_exc = await _engine.execute_strategy(
            exception_id,
            strategy=effective_strategy,
            retry_fn=None,  # No live callable in API layer; state transition only
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )

    logger.info(
        "Retry triggered for exception %s via API, new status=%s",
        exception_id,
        updated_exc.status.value,
    )
    return ExceptionResponse.from_exc(updated_exc)
