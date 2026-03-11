"""Checkout operator controls — tie checkout sessions into approvals and evidence.

Ensures hosted checkout inherits the same trust workflow as the core control plane.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sardis_api.authz import require_principal

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_principal)])


class CheckoutControlConfig(BaseModel):
    """Operator configuration for checkout controls."""
    require_approval_above: float | None = Field(default=None, description="Require approval for checkout amounts above this")
    require_kyc: bool = Field(default=False, description="Require KYC verification before checkout")
    allowed_chains: list[str] = Field(default_factory=lambda: ["base"], description="Chains allowed for checkout")
    allowed_tokens: list[str] = Field(default_factory=lambda: ["USDC"], description="Tokens allowed for checkout")
    max_session_amount: float | None = Field(default=None, description="Maximum amount per checkout session")
    evidence_export_auto: bool = Field(default=True, description="Auto-generate evidence bundle on completion")
    incident_webhook_url: str | None = Field(default=None, description="Webhook for checkout incidents")
    freeze_on_dispute: bool = Field(default=True, description="Auto-freeze wallet on dispute")


# In-memory config
_checkout_config = CheckoutControlConfig()


@router.get("/config", response_model=CheckoutControlConfig)
async def get_checkout_controls():
    """Get current checkout control configuration."""
    return _checkout_config


@router.put("/config", response_model=CheckoutControlConfig)
async def update_checkout_controls(config: CheckoutControlConfig):
    """Update checkout control configuration."""
    global _checkout_config
    _checkout_config = config
    logger.info("Checkout controls updated: %s", config.model_dump())
    return _checkout_config


class CheckoutIncident(BaseModel):
    session_id: str
    incident_type: str  # "dispute", "timeout", "fraud_flag", "settlement_failure"
    severity: str = "medium"  # "low", "medium", "high", "critical"
    description: str
    auto_actions_taken: list[str] = Field(default_factory=list)


class CheckoutIncidentResponse(BaseModel):
    incident_id: str
    session_id: str
    incident_type: str
    severity: str
    status: str  # "open", "investigating", "resolved"
    description: str
    auto_actions_taken: list[str]
    created_at: str


_incidents: list[dict] = []


@router.post("/incidents", response_model=CheckoutIncidentResponse, status_code=201)
async def report_checkout_incident(body: CheckoutIncident):
    """Report a checkout incident for operator review."""
    import uuid
    from datetime import UTC, datetime

    incident = {
        "incident_id": f"cinc_{uuid.uuid4().hex[:12]}",
        "session_id": body.session_id,
        "incident_type": body.incident_type,
        "severity": body.severity,
        "status": "open",
        "description": body.description,
        "auto_actions_taken": body.auto_actions_taken,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _incidents.append(incident)
    return CheckoutIncidentResponse(**incident)


@router.get("/incidents", response_model=list[CheckoutIncidentResponse])
async def list_checkout_incidents(limit: int = 50):
    """List checkout incidents."""
    return [CheckoutIncidentResponse(**i) for i in _incidents[-limit:]]
