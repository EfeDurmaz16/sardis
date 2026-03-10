"""
Exception management API endpoints.

Provides REST endpoints for listing, inspecting, and acting on payment
exceptions raised by the control plane.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sardis_v2_core.exception_workflows import (
    ExceptionWorkflowEngine,
    ExceptionStatus,
    PaymentException,
    ResolutionStrategy,
)

from sardis_api.authz import require_principal

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])

# NOTE: In-memory only — data is lost on restart. See #80.
# TODO: Replace with database-backed persistence when exception workflows are promoted to production.
_engine = ExceptionWorkflowEngine()

SUPPORTED_POLICY_EXCEPTION_TYPES = {
    "chain_failure",
    "timeout",
    "kill_switch_active",
}

POLICY_EXCEPTION_TYPE_ALIASES = {
    "rpc_timeout": "timeout",
    "settlement_failure": "chain_failure",
    "insufficient_gas": "chain_failure",
    "nonce_error": "chain_failure",
}

STRATEGY_BY_EXCEPTION_TYPE = {
    "chain_failure": ResolutionStrategy.RETRY_WITH_BACKOFF,
    "timeout": ResolutionStrategy.RETRY_WITH_BACKOFF,
    "kill_switch_active": ResolutionStrategy.WAIT_AND_RETRY,
}


# ============================================================================
# Retry Policy models and store
# ============================================================================


class RetryPolicy(BaseModel):
    id: str = ""
    name: str
    exception_type: str  # "insufficient_gas", "rpc_timeout", "settlement_failure", "nonce_error"
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=10, ge=1, le=600)
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=5.0)
    fallback_action: str = Field(
        default="escalate",
        description="escalate, block, alternative_rail, manual_review",
    )
    fallback_rail: str | None = Field(
        default=None,
        description="Rail to use if fallback_action is alternative_rail",
    )
    enabled: bool = True
    audit_trail: bool = Field(default=True, description="Log every retry attempt")
    safeguards: dict = Field(
        default_factory=lambda: {
            "max_total_amount": None,
            "require_approval_on_fallback": True,
        }
    )


# In-memory retry policy store with 3 defaults
_retry_policies: dict[str, RetryPolicy] = {}


def _seed_default_policies() -> None:
    defaults = [
        RetryPolicy(
            name="Chain Failure Retry",
            exception_type="chain_failure",
            max_retries=3,
            retry_delay_seconds=10,
            backoff_multiplier=2.0,
            fallback_action="escalate",
            fallback_rail=None,
            enabled=True,
            audit_trail=True,
            safeguards={"max_total_amount": None, "require_approval_on_fallback": True},
        ),
        RetryPolicy(
            name="Timeout Retry",
            exception_type="timeout",
            max_retries=2,
            retry_delay_seconds=5,
            backoff_multiplier=1.5,
            fallback_action="alternative_rail",
            fallback_rail="backup_rpc",
            enabled=True,
            audit_trail=True,
            safeguards={"max_total_amount": None, "require_approval_on_fallback": True},
        ),
        RetryPolicy(
            name="Kill Switch Cooldown",
            exception_type="kill_switch_active",
            max_retries=1,
            retry_delay_seconds=30,
            backoff_multiplier=1.0,
            fallback_action="manual_review",
            fallback_rail=None,
            enabled=True,
            audit_trail=True,
            safeguards={"max_total_amount": None, "require_approval_on_fallback": True},
        ),
    ]
    for policy in defaults:
        policy_id = str(uuid.uuid4())
        policy.id = policy_id
        _retry_policies[policy_id] = policy


_seed_default_policies()


def _normalize_policy_exception_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return POLICY_EXCEPTION_TYPE_ALIASES.get(normalized, normalized)


def _validate_retry_policy(body: RetryPolicy) -> RetryPolicy:
    body.exception_type = _normalize_policy_exception_type(body.exception_type)

    if body.fallback_action == "alternative_rail" and not body.fallback_rail:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fallback_rail_required_for_alternative_rail",
        )

    if body.exception_type not in SUPPORTED_POLICY_EXCEPTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "unsupported_exception_type_for_recovery_policy: "
                f"{body.exception_type}. Supported types: {sorted(SUPPORTED_POLICY_EXCEPTION_TYPES)}"
            ),
        )

    return body


def _append_recovery_audit(exc: PaymentException, entry: dict[str, Any]) -> None:
    history = list(exc.metadata.get("recovery_automation", []))
    history.append(entry)
    exc.metadata["recovery_automation"] = history[-25:]
    exc.updated_at = datetime.now(UTC)


def _find_matching_retry_policy(exc: PaymentException) -> RetryPolicy | None:
    exception_type = _normalize_policy_exception_type(exc.exception_type.value)
    for policy in _retry_policies.values():
        if not policy.enabled:
            continue
        if _normalize_policy_exception_type(policy.exception_type) == exception_type:
            return policy
    return None


def _list_exceptions(
    *,
    agent_id: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
) -> list[PaymentException]:
    results = list(_engine._exceptions.values())
    if agent_id:
        results = [exc for exc in results if exc.agent_id == agent_id]
    if status_filter:
        normalized = status_filter.strip().lower()
        valid_statuses = {item.value for item in ExceptionStatus}
        if normalized in valid_statuses:
            results = [exc for exc in results if exc.status.value == normalized]
    results.sort(key=lambda exc: exc.created_at, reverse=True)
    return results[:limit]


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
    resolved_by: str = Field(default="dashboard", description="Identifier of the person resolving")


class EscalateRequest(BaseModel):
    reason: str = Field(default="Escalated for operator review", description="Reason for escalation")


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
    status_filter: str | None = Query(
        None, alias="status", description="Optional exception status filter"
    ),
    limit: int = Query(100, ge=1, le=500),
) -> list[ExceptionResponse]:
    """Return payment exceptions visible in the operator workflow."""
    exceptions = _list_exceptions(
        agent_id=agent_id,
        status_filter=status_filter,
        limit=limit,
    )
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
    body: RetryRequest | None = None,
) -> ExceptionResponse:
    """Evaluate retry or fallback policy for a payment exception.

    The API is intentionally honest: it records deterministic recovery
    decisions and audit entries, but does not claim to have a live retry
    executor unless one is explicitly wired in.
    """
    exc = _engine.get_exception(exception_id)
    if exc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )

    body = body or RetryRequest()
    matching_policy = _find_matching_retry_policy(exc)
    exception_type = _normalize_policy_exception_type(exc.exception_type.value)
    audit_entry: dict[str, Any] = {
        "evaluated_at": datetime.now(UTC).isoformat(),
        "exception_type": exception_type,
        "policy_id": matching_policy.id if matching_policy else None,
        "executed": False,
    }

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

    if matching_policy:
        if exc.metadata.get("provider_changed_since_exception"):
            audit_entry["reason"] = "provider_changed_since_exception"
            _append_recovery_audit(exc, audit_entry)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="provider_changed_since_exception",
            )
        if exc.metadata.get("policy_changed_since_exception"):
            audit_entry["reason"] = "policy_changed_since_exception"
            _append_recovery_audit(exc, audit_entry)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="policy_changed_since_exception",
            )
        max_total_amount = matching_policy.safeguards.get("max_total_amount")
        if max_total_amount is not None and exc.original_amount > Decimal(str(max_total_amount)):
            audit_entry["reason"] = "max_total_amount_guardrail"
            _append_recovery_audit(exc, audit_entry)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="max_total_amount_guardrail",
            )
        if (
            matching_policy.fallback_action == "alternative_rail"
            and not matching_policy.fallback_rail
        ):
            audit_entry["reason"] = "missing_fallback_rail"
            _append_recovery_audit(exc, audit_entry)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="missing_fallback_rail",
            )

    if strategy is None:
        strategy = STRATEGY_BY_EXCEPTION_TYPE.get(exception_type)

    if strategy is None:
        audit_entry["reason"] = "no_supported_live_recovery_path"
        _append_recovery_audit(exc, audit_entry)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="no_supported_live_recovery_path",
        )

    audit_entry["strategy"] = strategy.value
    if matching_policy:
        audit_entry["fallback_action"] = matching_policy.fallback_action
        audit_entry["fallback_rail"] = matching_policy.fallback_rail
        audit_entry["max_retries"] = matching_policy.max_retries

    # No live retry callable is wired into the API layer yet. Record that
    # the policy was evaluated and surface the recommended next step.
    audit_entry["reason"] = "live_retry_executor_not_configured"
    _append_recovery_audit(exc, audit_entry)

    if matching_policy and matching_policy.fallback_action == "alternative_rail":
        exc.resolution_notes = (
            "Recovery policy evaluated. Live retry executor is not configured, "
            f"but policy recommends fallback rail '{matching_policy.fallback_rail}'."
        )
    else:
        exc.resolution_notes = (
            "Recovery policy evaluated. Live retry executor is not configured, "
            "so no automated retry was executed."
        )
    exc.updated_at = datetime.now(UTC)
    return ExceptionResponse.from_exc(exc)


# ============================================================================
# Retry Policy endpoints
# ============================================================================


@router.get(
    "/exceptions/retry-policies",
    response_model=list[RetryPolicy],
    summary="List retry policies",
    tags=["exceptions"],
)
async def list_retry_policies() -> list[RetryPolicy]:
    """Return all configured retry policies."""
    return list(_retry_policies.values())


@router.post(
    "/exceptions/retry-policies",
    response_model=RetryPolicy,
    status_code=201,
    summary="Create a retry policy",
    tags=["exceptions"],
)
async def create_retry_policy(body: RetryPolicy) -> RetryPolicy:
    """Create a new retry policy."""
    body = _validate_retry_policy(body)
    policy_id = str(uuid.uuid4())
    body.id = policy_id
    _retry_policies[policy_id] = body
    logger.info("Created retry policy %s (%s)", policy_id, body.name)
    return body


@router.put(
    "/exceptions/retry-policies/{policy_id}",
    response_model=RetryPolicy,
    summary="Update a retry policy",
    tags=["exceptions"],
)
async def update_retry_policy(policy_id: str, body: RetryPolicy) -> RetryPolicy:
    """Replace an existing retry policy by ID."""
    if policy_id not in _retry_policies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Retry policy {policy_id} not found",
        )
    body = _validate_retry_policy(body)
    body.id = policy_id
    _retry_policies[policy_id] = body
    logger.info("Updated retry policy %s", policy_id)
    return body


@router.delete(
    "/exceptions/retry-policies/{policy_id}",
    status_code=204,
    summary="Delete a retry policy",
    tags=["exceptions"],
)
async def delete_retry_policy(policy_id: str) -> None:
    """Delete a retry policy by ID."""
    if policy_id not in _retry_policies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Retry policy {policy_id} not found",
        )
    del _retry_policies[policy_id]
    logger.info("Deleted retry policy %s", policy_id)
