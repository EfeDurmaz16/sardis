"""Reliability API — provider health scorecards.

Endpoints:
    GET /reliability/providers                    — All provider scorecards
    GET /reliability/providers/{provider}/{chain}  — Detailed scorecard
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Response Models ──────────────────────────────────────────────────


class ProviderScorecardResponse(BaseModel):
    """Provider reliability scorecard."""
    provider: str
    chain: str
    period: str
    total_calls: int
    success_count: int
    failure_count: int
    avg_latency_ms: float
    p95_latency_ms: float
    error_rate: float
    availability: float
    computed_at: str


class ProvidersListResponse(BaseModel):
    """All provider scorecards."""
    scorecards: list[ProviderScorecardResponse] = Field(default_factory=list)
    count: int = 0


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/providers", response_model=ProvidersListResponse)
async def list_provider_scorecards(
    principal: Principal = Depends(require_principal),
):
    """Get all provider reliability scorecards."""
    tracker = _get_provider_tracker()
    scorecards = await tracker.get_all_scorecards()

    return ProvidersListResponse(
        scorecards=[
            ProviderScorecardResponse(
                provider=c.provider,
                chain=c.chain,
                period=c.period,
                total_calls=c.total_calls,
                success_count=c.success_count,
                failure_count=c.failure_count,
                avg_latency_ms=round(c.avg_latency_ms, 1),
                p95_latency_ms=round(c.p95_latency_ms, 1),
                error_rate=round(c.error_rate, 4),
                availability=round(c.availability, 4),
                computed_at=c.computed_at.isoformat(),
            )
            for c in scorecards
        ],
        count=len(scorecards),
    )


@router.get("/providers/{provider}/{chain}", response_model=ProviderScorecardResponse)
async def get_provider_scorecard(
    provider: str,
    chain: str,
    period: str = "24h",
    principal: Principal = Depends(require_principal),
):
    """Get detailed scorecard for a specific provider and chain."""
    tracker = _get_provider_tracker()
    card = await tracker.get_scorecard(provider, chain, period)

    if card.total_calls == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No data for {provider}/{chain} in period {period}",
        )

    return ProviderScorecardResponse(
        provider=card.provider,
        chain=card.chain,
        period=card.period,
        total_calls=card.total_calls,
        success_count=card.success_count,
        failure_count=card.failure_count,
        avg_latency_ms=round(card.avg_latency_ms, 1),
        p95_latency_ms=round(card.p95_latency_ms, 1),
        error_rate=round(card.error_rate, 4),
        availability=round(card.availability, 4),
        computed_at=card.computed_at.isoformat(),
    )


# ── Helpers ──────────────────────────────────────────────────────────


_tracker_instance = None


def _get_provider_tracker():
    global _tracker_instance
    if _tracker_instance is None:
        from sardis_chain.provider_tracker import ProviderTracker
        _tracker_instance = ProviderTracker()
    return _tracker_instance


def set_provider_tracker(tracker) -> None:
    """Override the provider tracker (for production wiring)."""
    global _tracker_instance
    _tracker_instance = tracker
