"""Read-only Guard risk surface for an agent.

Exposes the recent risk *decisions* the in-house Guard / RiskEngine produced for
an agent — the same engine the orchestrator consults pre-execution, so the
dashboard / Guard view reflects exactly what gated the money path.

This is read-only and signal/decision *evidence* only: it never moves money and
never alters the binding decision (Sardis owns the decision; this just surfaces
it).  When no RiskEngine is wired (dev / Phase 1.6 off) it returns an empty,
``risk_engine_enabled=false`` payload rather than failing — there is no money
path here to fail closed on.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from server.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


class RiskFeedSignal(BaseModel):
    provider: str
    score: float = Field(..., description="0-100 (higher = riskier)")
    recommended_action: str
    sandbox: bool
    ok: bool = Field(..., description="False when the feed errored (fail-closed)")
    error: str | None = None


class RiskSignalEntry(BaseModel):
    agent_id: str
    action: str = Field(..., description="allow | flag | require_approval | block")
    combined_score: float = Field(..., description="0-100")
    internal_score: float = Field(..., description="0-100 (in-house behavioral)")
    external_score: float = Field(..., description="0-100 (max across feeds)")
    internal_action: str
    reasons: list[str]
    feeds: list[RiskFeedSignal]
    amount: str | None = None
    counterparty: str | None = None
    timestamp: str


class AgentRiskSignalsResponse(BaseModel):
    agent_id: str
    risk_engine_enabled: bool
    feed_providers: list[str] = Field(
        default_factory=list,
        description="External fraud-signal feeds combined into each decision.",
    )
    count: int
    signals: list[RiskSignalEntry]


def _get_risk_engine(request: Request) -> Any | None:
    return getattr(request.app.state, "risk_engine", None)


@router.get(
    "/{agent_id}/risk-signals",
    response_model=AgentRiskSignalsResponse,
    tags=["guard"],
    summary="Recent Guard risk decisions for an agent (read-only)",
)
async def get_agent_risk_signals(
    agent_id: str,
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(require_principal),
) -> AgentRiskSignalsResponse:
    """Return the agent's most recent Guard risk decisions (newest first)."""
    engine = _get_risk_engine(request)
    if engine is None:
        return AgentRiskSignalsResponse(
            agent_id=agent_id,
            risk_engine_enabled=False,
            feed_providers=[],
            count=0,
            signals=[],
        )

    decisions = engine.recent_signals(agent_id, limit=limit)
    signals = [
        RiskSignalEntry(**decision.to_dict()) for decision in decisions
    ]
    return AgentRiskSignalsResponse(
        agent_id=agent_id,
        risk_engine_enabled=True,
        feed_providers=list(getattr(engine, "feed_providers", [])),
        count=len(signals),
        signals=signals,
    )
