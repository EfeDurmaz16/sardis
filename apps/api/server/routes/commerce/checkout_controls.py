"""Checkout operator controls — tie checkout sessions into approvals and evidence.

Ensures hosted checkout inherits the same trust workflow as the core control plane.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.authz import require_principal

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


# Cached in-memory; synced to DB on writes.
_checkout_config = CheckoutControlConfig()


async def _load_checkout_config() -> CheckoutControlConfig:
    """Load config from DB, falling back to in-memory default."""
    global _checkout_config
    try:
        import json

        from sardis.core.database import Database
        row = await Database.fetchrow(
            "SELECT value FROM operator_config WHERE key = 'checkout_controls'"
        )
        if row:
            _checkout_config = CheckoutControlConfig(**json.loads(row["value"]))
    except Exception:
        pass  # Use cached value
    return _checkout_config


async def _save_checkout_config(config: CheckoutControlConfig) -> None:
    """Persist config to DB."""
    global _checkout_config
    _checkout_config = config
    try:
        import json

        from sardis.core.database import Database
        await Database.execute(
            """INSERT INTO operator_config (key, value, updated_at)
               VALUES ('checkout_controls', $1, NOW())
               ON CONFLICT (key) DO UPDATE SET value = $1, updated_at = NOW()""",
            json.dumps(config.model_dump(), default=str),
        )
    except Exception as exc:
        logger.warning("Failed to persist checkout config to DB: %s", exc)


@router.get("/config", response_model=CheckoutControlConfig)
async def get_checkout_controls():
    """Get current checkout control configuration."""
    return await _load_checkout_config()


@router.put("/config", response_model=CheckoutControlConfig)
async def update_checkout_controls(config: CheckoutControlConfig):
    """Update checkout control configuration."""
    await _save_checkout_config(config)
    logger.info("Checkout controls updated: %s", config.model_dump())
    return config


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


_incidents: list[dict] = []  # process-local cache


async def _persist_incident(incident: dict) -> None:
    """Write incident to DB; keep local cache for reads."""
    _incidents.append(incident)
    try:
        import json

        from sardis.core.database import Database
        await Database.execute(
            """INSERT INTO checkout_incidents (incident_id, session_id, data, created_at)
               VALUES ($1, $2, $3, NOW())""",
            incident["incident_id"], incident["session_id"],
            json.dumps(incident, default=str),
        )
    except Exception as exc:
        logger.warning("Failed to persist checkout incident to DB: %s", exc)


async def _load_incidents(limit: int = 50) -> list[dict]:
    """Load incidents from DB, falling back to local cache."""
    try:
        import json

        from sardis.core.database import Database
        rows = await Database.fetch(
            "SELECT data FROM checkout_incidents ORDER BY created_at DESC LIMIT $1",
            limit,
        )
        if rows:
            return [json.loads(r["data"]) if isinstance(r["data"], str) else r["data"] for r in reversed(rows)]
    except Exception:
        pass
    return _incidents[-limit:]


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
    await _persist_incident(incident)
    return CheckoutIncidentResponse(**incident)


@router.get("/incidents", response_model=list[CheckoutIncidentResponse])
async def list_checkout_incidents(limit: int = 50):
    """List checkout incidents."""
    incidents = await _load_incidents(limit)
    return [CheckoutIncidentResponse(**i) for i in incidents]
