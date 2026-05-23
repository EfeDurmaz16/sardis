"""Scoped Facility Gate abuse and approval-fatigue controls."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sardis.core.facility_gate import FacilityDecision

from server.repositories.facility_gate_repository import FacilityGateRepository


@dataclass(frozen=True)
class FacilityLimitDecision:
    allowed: bool
    reason: str | None = None
    count: int = 0
    threshold: int = 0


@dataclass(frozen=True)
class FacilityLimitThresholds:
    agent_merchant_requests: int = 10
    agent_requests: int = 50
    merchant_requests: int = 100
    step_up_fatigue: int = 20


class FacilityGateLimiter:
    """History-backed limiter used until a shared Redis/DB counter is wired."""

    def __init__(
        self,
        repository: FacilityGateRepository,
        *,
        thresholds: FacilityLimitThresholds | None = None,
    ) -> None:
        self._repository = repository
        self._thresholds = thresholds or FacilityLimitThresholds()

    async def check_request_allowed(
        self,
        *,
        organization_id: str,
        agent_id: str,
        merchant: str,
    ) -> FacilityLimitDecision:
        states = await self._repository.list_request_states(organization_id=organization_id, limit=500)
        merchant_normalized = merchant.lower()
        same_agent = [state for state in states if state.get("agent_id") == agent_id]
        same_merchant = [
            state for state in states
            if str(state.get("merchant", "")).lower() == merchant_normalized
        ]
        same_agent_merchant = [
            state for state in same_agent
            if str(state.get("merchant", "")).lower() == merchant_normalized
        ]
        checks = [
            (
                len(same_agent_merchant),
                self._thresholds.agent_merchant_requests,
                "facility_agent_merchant_rate_limit_exceeded",
            ),
            (len(same_agent), self._thresholds.agent_requests, "facility_agent_rate_limit_exceeded"),
            (
                len(same_merchant),
                self._thresholds.merchant_requests,
                "facility_merchant_rate_limit_exceeded",
            ),
        ]
        for count, threshold, reason in checks:
            if count >= threshold:
                return FacilityLimitDecision(
                    allowed=False,
                    reason=reason,
                    count=count,
                    threshold=threshold,
                )
        return FacilityLimitDecision(allowed=True)

    async def check_approval_fatigue(
        self,
        *,
        organization_id: str,
    ) -> FacilityLimitDecision:
        states = await self._repository.list_request_states(organization_id=organization_id, limit=500)
        step_up_count = sum(
            1
            for state in states
            if state.get("latest_verdict") == FacilityDecision.STEP_UP_REQUIRED.value
        )
        threshold = self._thresholds.step_up_fatigue
        if step_up_count >= threshold:
            return FacilityLimitDecision(
                allowed=False,
                reason="facility_approval_fatigue_limit_exceeded",
                count=step_up_count,
                threshold=threshold,
            )
        return FacilityLimitDecision(allowed=True, count=step_up_count, threshold=threshold)

    async def summary(self, *, organization_id: str) -> dict[str, Any]:
        states = await self._repository.list_request_states(organization_id=organization_id, limit=500)
        return {
            "schema_version": "facility_gate_limiter_summary_v1",
            "organization_id": organization_id,
            "request_count": len(states),
            "step_up_count": sum(
                1
                for state in states
                if state.get("latest_verdict") == FacilityDecision.STEP_UP_REQUIRED.value
            ),
            "thresholds": self._thresholds.__dict__,
        }

