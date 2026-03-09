"""Simulation API — dry-run payment intents without executing on chain.

Enterprise customers can test "What would this policy allow?" scenarios.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter()


class SimulateRequest(BaseModel):
    """Request to simulate a payment intent."""
    amount: str = Field(..., description="Payment amount (e.g. '100.00')")
    currency: str = Field(default="USDC")
    chain: str = Field(default="base")
    sender_agent_id: str = Field(default="")
    sender_wallet_id: str = Field(default="")
    recipient_wallet_id: str = Field(default="")
    recipient_address: str = Field(default="")
    source: str = Field(default="a2a", description="Payment rail: a2a, ap2, checkout")


class SimulateResponse(BaseModel):
    """Result of a simulation."""
    intent_id: str
    would_succeed: bool
    failure_reasons: list[str] = Field(default_factory=list)
    policy_result: dict[str, Any] | None = None
    compliance_result: dict[str, Any] | None = None
    cap_check: dict[str, Any] | None = None
    kill_switch_status: dict[str, Any] | None = None


@router.post("/", response_model=SimulateResponse)
async def simulate_payment(
    body: SimulateRequest,
    principal: Principal = Depends(require_principal),
):
    """Simulate a payment intent through the full pipeline without executing.

    Returns all reachable failure reasons (policy, compliance, caps, kill switches).
    """
    from sardis_v2_core.control_plane import ControlPlane
    from sardis_v2_core.execution_intent import ExecutionIntent, IntentSource

    try:
        source = IntentSource(body.source)
    except ValueError:
        source = IntentSource.A2A

    intent = ExecutionIntent(
        source=source,
        org_id=principal.organization_id,
        agent_id=body.sender_agent_id,
        amount=Decimal(body.amount),
        currency=body.currency,
        chain=body.chain,
        sender_wallet_id=body.sender_wallet_id,
        recipient_wallet_id=body.recipient_wallet_id,
        recipient_address=body.recipient_address,
    )

    # Build control plane with available services
    control_plane = ControlPlane()
    result = await control_plane.simulate(intent)

    return SimulateResponse(
        intent_id=result.intent_id,
        would_succeed=result.would_succeed,
        failure_reasons=result.failure_reasons,
        policy_result=result.policy_result,
        compliance_result=result.compliance_result,
        cap_check=result.cap_check,
        kill_switch_status=result.kill_switch_status,
    )
