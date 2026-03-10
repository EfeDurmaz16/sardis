"""Cross-rail fallback rules and degraded-mode policies.

Defines deterministic fallback behavior when a preferred payment rail fails,
is degraded, or becomes unsafe. Operators configure narrow rail-pair rules.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sardis_api.authz import require_principal

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_principal)])


class FallbackRule(BaseModel):
    id: str = ""
    name: str = Field(..., description="Rule name")
    primary_rail: str = Field(
        ...,
        description="Primary rail: stablecoin, virtual_card, x402, bank_transfer",
    )
    fallback_rail: str = Field(..., description="Fallback rail to use on failure")
    trigger: str = Field(
        default="failure",
        description="failure, degraded, timeout, unsafe",
    )
    behavior: str = Field(
        default="retry_then_fallback",
        description="retry_then_fallback, immediate_fallback, escalate, block",
    )
    max_retries: int = Field(default=2, ge=0, le=5)
    retry_delay_seconds: int = Field(default=5, ge=1, le=300)
    enabled: bool = True
    audit_log: bool = Field(default=True, description="Log fallback events to audit trail")


class DegradedModePolicy(BaseModel):
    rail: str
    mode: str = Field(
        default="normal",
        description="normal, degraded, maintenance, disabled",
    )
    reason: str | None = None
    max_amount_override: float | None = Field(
        default=None,
        description="Lower max amount during degraded mode",
    )
    require_approval: bool = Field(
        default=False,
        description="Require approval during degraded mode",
    )
    updated_at: str = ""


# ---------------------------------------------------------------------------
# In-memory stores (swappable for Postgres in a future migration)
# ---------------------------------------------------------------------------
_fallback_rules: dict[str, dict] = {}
_degraded_modes: dict[str, dict] = {
    "stablecoin": {
        "rail": "stablecoin",
        "mode": "normal",
        "reason": None,
        "max_amount_override": None,
        "require_approval": False,
        "updated_at": datetime.now(UTC).isoformat(),
    },
    "virtual_card": {
        "rail": "virtual_card",
        "mode": "normal",
        "reason": None,
        "max_amount_override": None,
        "require_approval": False,
        "updated_at": datetime.now(UTC).isoformat(),
    },
    "x402": {
        "rail": "x402",
        "mode": "normal",
        "reason": None,
        "max_amount_override": None,
        "require_approval": False,
        "updated_at": datetime.now(UTC).isoformat(),
    },
    "bank_transfer": {
        "rail": "bank_transfer",
        "mode": "normal",
        "reason": None,
        "max_amount_override": None,
        "require_approval": False,
        "updated_at": datetime.now(UTC).isoformat(),
    },
}

# Seed a default rule so the UI has something to show on first boot.
_default_rule_id = f"fbr_{uuid.uuid4().hex[:12]}"
_fallback_rules[_default_rule_id] = {
    "id": _default_rule_id,
    "name": "Stablecoin → Card Fallback",
    "primary_rail": "stablecoin",
    "fallback_rail": "virtual_card",
    "trigger": "failure",
    "behavior": "retry_then_fallback",
    "max_retries": 2,
    "retry_delay_seconds": 5,
    "enabled": True,
    "audit_log": True,
}


# ---------------------------------------------------------------------------
# Fallback Rules CRUD
# ---------------------------------------------------------------------------


@router.get("/rules", response_model=list[FallbackRule])
async def list_fallback_rules() -> list[FallbackRule]:
    """List all configured fallback rules."""
    return [FallbackRule(**r) for r in _fallback_rules.values()]


@router.post("/rules", response_model=FallbackRule, status_code=201)
async def create_fallback_rule(body: FallbackRule) -> FallbackRule:
    """Create a new cross-rail fallback rule."""
    rule_id = f"fbr_{uuid.uuid4().hex[:12]}"
    record = body.model_dump()
    record["id"] = rule_id
    _fallback_rules[rule_id] = record
    logger.info("Fallback rule created id=%s primary=%s fallback=%s", rule_id, body.primary_rail, body.fallback_rail)
    return FallbackRule(**record)


@router.put("/rules/{rule_id}", response_model=FallbackRule)
async def update_fallback_rule(rule_id: str, body: FallbackRule) -> FallbackRule:
    """Update an existing fallback rule."""
    if rule_id not in _fallback_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    record = body.model_dump()
    record["id"] = rule_id
    _fallback_rules[rule_id] = record
    logger.info("Fallback rule updated id=%s", rule_id)
    return FallbackRule(**record)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_fallback_rule(rule_id: str) -> None:
    """Delete a fallback rule."""
    if rule_id not in _fallback_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    del _fallback_rules[rule_id]
    logger.info("Fallback rule deleted id=%s", rule_id)


# ---------------------------------------------------------------------------
# Degraded Mode Controls
# ---------------------------------------------------------------------------


@router.get("/degraded-modes", response_model=list[DegradedModePolicy])
async def list_degraded_modes() -> list[DegradedModePolicy]:
    """List current degraded-mode status for all rails."""
    return [DegradedModePolicy(**d) for d in _degraded_modes.values()]


@router.put("/degraded-modes/{rail}", response_model=DegradedModePolicy)
async def set_degraded_mode(rail: str, body: DegradedModePolicy) -> DegradedModePolicy:
    """Set degraded-mode policy for a specific rail."""
    if rail not in _degraded_modes:
        raise HTTPException(status_code=404, detail=f"Unknown rail: {rail}")
    record = body.model_dump()
    record["rail"] = rail
    record["updated_at"] = datetime.now(UTC).isoformat()
    _degraded_modes[rail] = record
    logger.info("Degraded mode updated rail=%s mode=%s", rail, body.mode)
    return DegradedModePolicy(**record)
