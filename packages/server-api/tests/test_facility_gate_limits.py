from __future__ import annotations

import pytest
from sardis_v2_core.facility_gate import FacilityEventType

from sardis_server.repositories.facility_gate_repository import FacilityGateRepository
from sardis_server.services.facility_gate_limits import FacilityGateLimiter, FacilityLimitThresholds


async def _append_request(repo: FacilityGateRepository, idx: int, *, verdict: str | None = None) -> None:
    request_id = f"fac_req_{idx}"
    await repo.append_event(
        organization_id="org_1",
        aggregate_id=request_id,
        event_type=FacilityEventType.REQUEST_CREATED,
        payload={
            "request": {
                "request_id": request_id,
                "organization_id": "org_1",
                "facility_id": "fac_1",
                "agent_id": "agent_1",
                "mandate_id": "mandate_1",
                "merchant": "aws.amazon.com",
                "amount_minor": 75000,
                "currency": "USD",
            }
        },
    )
    if verdict:
        event_type = {
            "approved": FacilityEventType.AUTH_APPROVED,
            "denied": FacilityEventType.AUTH_DENIED,
            "step_up_required": FacilityEventType.AUTH_STEP_UP_REQUIRED,
        }[verdict]
        await repo.append_event(
            organization_id="org_1",
            aggregate_id=request_id,
            event_type=event_type,
            payload={"decision": {"decision_id": f"fac_dec_{idx}", "verdict": verdict}},
        )


@pytest.mark.asyncio
async def test_facility_limiter_blocks_repeated_agent_merchant_requests() -> None:
    repo = FacilityGateRepository(dsn="memory://")
    limiter = FacilityGateLimiter(
        repo,
        thresholds=FacilityLimitThresholds(agent_merchant_requests=2),
    )
    await _append_request(repo, 1)
    await _append_request(repo, 2)

    decision = await limiter.check_request_allowed(
        organization_id="org_1",
        agent_id="agent_1",
        merchant="aws.amazon.com",
    )

    assert decision.allowed is False
    assert decision.reason == "facility_agent_merchant_rate_limit_exceeded"
    assert decision.count == 2


@pytest.mark.asyncio
async def test_facility_limiter_detects_approval_fatigue() -> None:
    repo = FacilityGateRepository(dsn="memory://")
    limiter = FacilityGateLimiter(repo, thresholds=FacilityLimitThresholds(step_up_fatigue=2))
    await _append_request(repo, 1, verdict="step_up_required")
    await _append_request(repo, 2, verdict="step_up_required")

    decision = await limiter.check_approval_fatigue(organization_id="org_1")

    assert decision.allowed is False
    assert decision.reason == "facility_approval_fatigue_limit_exceeded"
    assert decision.count == 2

