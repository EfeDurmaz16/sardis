"""Cross-rail fallback rules and degraded-mode policies.

Defines deterministic fallback behavior when a preferred payment rail fails,
is degraded, or becomes unsafe. Operators configure narrow rail-pair rules.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sardis_api.authz import require_principal

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_principal)])
_ALLOWED_RAILS = {"stablecoin", "virtual_card", "x402", "bank_transfer"}


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
# Stores — DB-backed with in-memory cache
# ---------------------------------------------------------------------------
_fallback_rules: dict[str, dict] = {}  # process-local cache
_degraded_modes: dict[str, dict] = {}
_operator_config_loaded = False


async def _load_operator_config() -> None:
    """Hydrate fallback/degraded-mode state from durable storage once."""
    global _operator_config_loaded
    if _operator_config_loaded:
        return

    _operator_config_loaded = True
    try:
        from sardis_v2_core.database import Database
        rows = await Database.fetch(
            """
            SELECT key, value
            FROM operator_config
            WHERE key LIKE 'fallback_rule:%' OR key LIKE 'degraded_mode:%'
            """
        )
    except Exception as exc:
        logger.warning("Failed to load fallback operator config from DB: %s", exc)
        return

    for row in rows:
        key = str(row.get("key") or "")
        raw_value = row.get("value")
        if isinstance(raw_value, str):
            try:
                value = json.loads(raw_value)
            except json.JSONDecodeError:
                logger.warning("Skipping invalid operator_config JSON for key %s", key)
                continue
        else:
            value = raw_value

        if not isinstance(value, dict):
            logger.warning("Skipping non-object operator_config payload for key %s", key)
            continue

        if key.startswith("fallback_rule:"):
            rule_id = key.split(":", 1)[1]
            value["id"] = value.get("id") or rule_id
            _fallback_rules[rule_id] = value
        elif key.startswith("degraded_mode:"):
            rail = key.split(":", 1)[1]
            value["rail"] = value.get("rail") or rail
            _degraded_modes[rail] = value


async def _persist_rule(rule_id: str, record: dict) -> None:
    """Write fallback rule to DB."""
    _fallback_rules[rule_id] = record
    try:
        from sardis_v2_core.database import Database
        await Database.execute(
            """INSERT INTO operator_config (key, value, updated_at)
               VALUES ($1, $2, NOW())
               ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()""",
            f"fallback_rule:{rule_id}", json.dumps(record, default=str),
        )
    except Exception as exc:
        logger.warning("Failed to persist fallback rule %s to DB: %s", rule_id, exc)


async def _delete_rule_from_db(rule_id: str) -> None:
    """Remove rule from DB."""
    _fallback_rules.pop(rule_id, None)
    try:
        from sardis_v2_core.database import Database
        await Database.execute(
            "DELETE FROM operator_config WHERE key = $1", f"fallback_rule:{rule_id}",
        )
    except Exception as exc:
        logger.warning("Failed to delete fallback rule %s from DB: %s", rule_id, exc)


async def _persist_degraded_mode(rail: str, record: dict) -> None:
    """Write degraded mode to DB."""
    _degraded_modes[rail] = record
    try:
        from sardis_v2_core.database import Database
        await Database.execute(
            """INSERT INTO operator_config (key, value, updated_at)
               VALUES ($1, $2, NOW())
               ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()""",
            f"degraded_mode:{rail}", json.dumps(record, default=str),
        )
    except Exception as exc:
        logger.warning("Failed to persist degraded mode %s to DB: %s", rail, exc)


# ---------------------------------------------------------------------------
# Fallback Rules CRUD
# ---------------------------------------------------------------------------


@router.get("/rules", response_model=list[FallbackRule])
async def list_fallback_rules() -> list[FallbackRule]:
    """List all configured fallback rules."""
    await _load_operator_config()
    return [FallbackRule(**r) for r in _fallback_rules.values()]


@router.post("/rules", response_model=FallbackRule, status_code=201)
async def create_fallback_rule(body: FallbackRule) -> FallbackRule:
    """Create a new cross-rail fallback rule."""
    await _load_operator_config()
    rule_id = f"fbr_{uuid.uuid4().hex[:12]}"
    record = body.model_dump()
    record["id"] = rule_id
    await _persist_rule(rule_id, record)
    logger.info("Fallback rule created id=%s primary=%s fallback=%s", rule_id, body.primary_rail, body.fallback_rail)
    return FallbackRule(**record)


@router.put("/rules/{rule_id}", response_model=FallbackRule)
async def update_fallback_rule(rule_id: str, body: FallbackRule) -> FallbackRule:
    """Update an existing fallback rule."""
    await _load_operator_config()
    if rule_id not in _fallback_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    record = body.model_dump()
    record["id"] = rule_id
    await _persist_rule(rule_id, record)
    logger.info("Fallback rule updated id=%s", rule_id)
    return FallbackRule(**record)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_fallback_rule(rule_id: str) -> None:
    """Delete a fallback rule."""
    await _load_operator_config()
    if rule_id not in _fallback_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    await _delete_rule_from_db(rule_id)
    logger.info("Fallback rule deleted id=%s", rule_id)


# ---------------------------------------------------------------------------
# Degraded Mode Controls
# ---------------------------------------------------------------------------


@router.get("/degraded-modes", response_model=list[DegradedModePolicy])
async def list_degraded_modes() -> list[DegradedModePolicy]:
    """List current degraded-mode status for all rails."""
    await _load_operator_config()
    return [DegradedModePolicy(**d) for d in _degraded_modes.values()]


@router.put("/degraded-modes/{rail}", response_model=DegradedModePolicy)
async def set_degraded_mode(rail: str, body: DegradedModePolicy) -> DegradedModePolicy:
    """Set degraded-mode policy for a specific rail."""
    await _load_operator_config()
    if rail not in _ALLOWED_RAILS:
        raise HTTPException(status_code=404, detail=f"Unknown rail: {rail}")
    record = body.model_dump()
    record["rail"] = rail
    record["updated_at"] = datetime.now(UTC).isoformat()
    await _persist_degraded_mode(rail, record)
    logger.info("Degraded mode updated rail=%s mode=%s", rail, body.mode)
    return DegradedModePolicy(**record)
