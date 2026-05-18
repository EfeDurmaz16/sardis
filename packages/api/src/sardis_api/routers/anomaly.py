"""Anomaly Engine API — real-time risk scoring for agent transactions.

Exposes the guardrails anomaly engine so that operators can assess risk for
hypothetical transactions, review recent anomaly events, and tune thresholds.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------


@dataclass
class AnomalyDependencies:
    anomaly_engine: Any
    db: Any = None


def get_deps() -> AnomalyDependencies:
    raise RuntimeError("AnomalyDependencies not configured")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AssessRequest(BaseModel):
    """Risk assessment request for a hypothetical transaction."""

    agent_id: str = Field(..., description="Agent identifier to assess")
    amount: str = Field(..., description="Transaction amount (e.g. '250.00')")
    merchant_id: str | None = Field(None, description="Optional merchant identifier")
    mcc_code: str | None = Field(None, description="Optional merchant category code / slug")


class SignalOut(BaseModel):
    """Individual risk signal in an assessment response."""

    signal_type: str
    weight: float
    score: float
    description: str


class AssessResponse(BaseModel):
    """Risk assessment result."""

    overall_score: float = Field(..., description="Aggregated risk score (0.0–1.0)")
    action: str = Field(..., description="Recommended control-plane action")
    signals: list[SignalOut]
    timestamp: datetime


class AnomalyEventOut(BaseModel):
    """Serialised risk assessment for list endpoints."""

    agent_id: str
    overall_score: float
    action: str
    signals: list[SignalOut]
    timestamp: datetime
    transaction_amount: str | None = None
    transaction_merchant: str | None = None


class ThresholdsConfig(BaseModel):
    allow: float = 0.3
    flag: float = 0.6
    require_approval: float = 0.8
    freeze_agent: float = 0.95


class SignalWeightsConfig(BaseModel):
    amount_anomaly: float = 0.30
    velocity: float = 0.25
    new_merchant: float = 0.15
    time_anomaly: float = 0.10
    merchant_category: float = 0.10
    behavioral_alerts: float = 0.10


class AnomalyConfig(BaseModel):
    """Current anomaly engine configuration."""

    thresholds: ThresholdsConfig
    signal_weights: SignalWeightsConfig


class UpdateConfigRequest(BaseModel):
    """Partial update to anomaly engine configuration."""

    thresholds: ThresholdsConfig | None = None
    signal_weights: SignalWeightsConfig | None = None


# In-memory event log (bounded ring buffer — max 500 entries)
_event_log: list[dict[str, Any]] = []
_MAX_EVENTS = 500

# Mutable config (runtime overrides; engine weights are updated in-place)
_config = AnomalyConfig(
    thresholds=ThresholdsConfig(),
    signal_weights=SignalWeightsConfig(),
)


def _assessment_to_event(assessment: Any) -> dict[str, Any]:
    return {
        "agent_id": assessment.agent_id,
        "overall_score": assessment.overall_score,
        "action": assessment.action.value,
        "signals": [
            {
                "signal_type": s.signal_type,
                "weight": s.weight,
                "score": s.score,
                "description": s.description,
            }
            for s in assessment.signals
        ],
        "timestamp": assessment.timestamp,
        "transaction_amount": str(assessment.transaction_amount)
        if assessment.transaction_amount is not None
        else None,
        "transaction_merchant": assessment.transaction_merchant,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/assess", response_model=AssessResponse)
async def assess_risk(
    body: AssessRequest,
    principal: Principal = Depends(require_principal),
    deps: AnomalyDependencies = Depends(get_deps),
):
    """Assess risk for a hypothetical transaction without executing it.

    Returns a detailed breakdown of every risk signal so operators can
    understand which factors drove the overall score and recommended action.
    """
    try:
        amount = Decimal(body.amount)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid amount — must be a numeric string.")

    try:
        assessment = deps.anomaly_engine.assess_risk(
            agent_id=body.agent_id,
            amount=amount,
            merchant_id=body.merchant_id,
            merchant_category=body.mcc_code,
        )
    except Exception as exc:
        logger.exception("anomaly_engine.assess_risk failed: %s", exc)
        raise HTTPException(status_code=500, detail="Risk assessment failed.")

    # Persist to in-memory event log
    event = _assessment_to_event(assessment)
    _event_log.append(event)
    if len(_event_log) > _MAX_EVENTS:
        _event_log.pop(0)

    return AssessResponse(
        overall_score=assessment.overall_score,
        action=assessment.action.value,
        signals=[
            SignalOut(
                signal_type=s.signal_type,
                weight=s.weight,
                score=s.score,
                description=s.description,
            )
            for s in assessment.signals
        ],
        timestamp=assessment.timestamp,
    )


@router.get("/events", response_model=list[AnomalyEventOut])
async def list_events(
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    min_score: float | None = Query(None, ge=0.0, le=1.0, description="Minimum overall score"),
    action: str | None = Query(None, description="Filter by action (e.g. 'flag')"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    principal: Principal = Depends(require_principal),
):
    """List recent anomaly events from the in-memory event log.

    Results are returned most-recent-first and support optional filters on
    agent, minimum risk score, and recommended action.
    """
    events = list(reversed(_event_log))

    if agent_id:
        events = [e for e in events if e["agent_id"] == agent_id]
    if min_score is not None:
        events = [e for e in events if e["overall_score"] >= min_score]
    if action:
        events = [e for e in events if e["action"] == action.lower()]

    return [AnomalyEventOut(**e) for e in events[:limit]]


@router.get("/config", response_model=AnomalyConfig)
async def get_config(
    principal: Principal = Depends(require_principal),
):
    """Return current anomaly engine thresholds and signal weights."""
    return _config


@router.put("/config", response_model=AnomalyConfig)
async def update_config(
    body: UpdateConfigRequest,
    principal: Principal = Depends(require_principal),
    deps: AnomalyDependencies = Depends(get_deps),
):
    """Update anomaly engine thresholds and/or signal weights.

    Accepts partial updates — omit a block to leave it unchanged.
    Weight changes are applied to the live engine immediately.
    """
    global _config

    if body.thresholds is not None:
        _config = AnomalyConfig(thresholds=body.thresholds, signal_weights=_config.signal_weights)

    if body.signal_weights is not None:
        weights = body.signal_weights.model_dump()
        total = sum(weights.values())
        if total <= 0:
            raise HTTPException(status_code=422, detail="Signal weights must sum to a positive value.")
        # Normalise to 1.0 and push to live engine
        normalised = {k: v / total for k, v in weights.items()}
        deps.anomaly_engine.WEIGHTS.update(normalised)
        _config = AnomalyConfig(
            thresholds=_config.thresholds,
            signal_weights=SignalWeightsConfig(**normalised),
        )

    logger.info("Anomaly engine config updated by %s", principal.organization_id)
    return _config
