"""Outcomes API — record real-world outcomes and query risk profiles.

Endpoints:
    POST /outcomes/{outcome_id}/resolve  — Record outcome for a decision
    GET  /risk/agent/{agent_id}          — Get agent risk profile
    GET  /risk/merchant/{merchant_id}    — Get merchant risk profile
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request/Response Models ──────────────────────────────────────────


class ResolveOutcomeRequest(BaseModel):
    """Request to record real-world outcome."""
    outcome_type: str = Field(..., description="completed, disputed, refunded, fraud_confirmed, false_positive")
    data: dict[str, Any] = Field(default_factory=dict)


class OutcomeResponse(BaseModel):
    """Outcome details."""
    outcome_id: str
    receipt_id: str
    intent_id: str
    decision: str
    decision_reason: str
    outcome_type: str
    resolved_at: Optional[str] = None
    agent_id: str
    org_id: str
    merchant_id: str
    amount: str
    anomaly_score: float
    confidence_score: float


class AgentRiskProfileResponse(BaseModel):
    """Agent risk profile."""
    agent_id: str
    org_id: str
    total_decisions: int
    total_approved: int
    total_denied: int
    total_flagged: int
    false_positive_count: int
    true_positive_count: int
    false_negative_count: int
    false_positive_rate: float
    false_negative_rate: float
    avg_anomaly_score: float
    avg_confidence_score: float
    last_updated: str


class MerchantRiskProfileResponse(BaseModel):
    """Merchant risk profile."""
    merchant_id: str
    total_transactions: int
    dispute_count: int
    refund_count: int
    fraud_count: int
    dispute_rate: float
    risk_tier: str
    first_seen: str
    last_transaction: Optional[str] = None
    last_updated: str


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/outcomes/{outcome_id}/resolve", response_model=OutcomeResponse)
async def resolve_outcome(
    outcome_id: str,
    body: ResolveOutcomeRequest,
    principal: Principal = Depends(require_principal),
):
    """Record the real-world outcome of a payment decision."""
    tracker = _get_outcome_tracker()

    try:
        await tracker.record_outcome(outcome_id, body.outcome_type, body.data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    outcome = await tracker.get_outcome(outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found after recording")

    return OutcomeResponse(
        outcome_id=outcome.outcome_id,
        receipt_id=outcome.receipt_id,
        intent_id=outcome.intent_id,
        decision=outcome.decision,
        decision_reason=outcome.decision_reason,
        outcome_type=outcome.outcome_type,
        resolved_at=outcome.resolved_at.isoformat() if outcome.resolved_at else None,
        agent_id=outcome.agent_id,
        org_id=outcome.org_id,
        merchant_id=outcome.merchant_id,
        amount=str(outcome.amount),
        anomaly_score=outcome.anomaly_score,
        confidence_score=outcome.confidence_score,
    )


@router.get("/risk/agent/{agent_id}", response_model=AgentRiskProfileResponse)
async def get_agent_risk_profile(
    agent_id: str,
    principal: Principal = Depends(require_principal),
):
    """Get the risk profile for an agent."""
    tracker = _get_outcome_tracker()
    profile = await tracker.get_agent_profile(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"No risk profile for agent: {agent_id}")

    return AgentRiskProfileResponse(**profile.to_dict())


@router.get("/risk/merchant/{merchant_id}", response_model=MerchantRiskProfileResponse)
async def get_merchant_risk_profile(
    merchant_id: str,
    principal: Principal = Depends(require_principal),
):
    """Get the risk profile for a merchant."""
    tracker = _get_outcome_tracker()
    profile = await tracker.get_merchant_profile(merchant_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"No risk profile for merchant: {merchant_id}")

    return MerchantRiskProfileResponse(**profile.to_dict())


# ── Helpers ──────────────────────────────────────────────────────────


_tracker_instance = None


def _get_outcome_tracker():
    global _tracker_instance
    if _tracker_instance is None:
        from sardis_v2_core.outcome_tracker import OutcomeTracker
        _tracker_instance = OutcomeTracker()
    return _tracker_instance


def set_outcome_tracker(tracker) -> None:
    """Override the outcome tracker (for production wiring)."""
    global _tracker_instance
    _tracker_instance = tracker
