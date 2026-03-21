"""Spending Mandate API — CRUD and lifecycle management.

Provides endpoints for creating, managing, and revoking spending mandates
that define the scoped authority AI agents have to spend money.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateMandateRequest(BaseModel):
    agent_id: str | None = None
    wallet_id: str | None = None
    purpose_scope: str | None = None
    merchant_scope: dict | None = None
    amount_per_tx: Decimal | None = None
    amount_daily: Decimal | None = None
    amount_weekly: Decimal | None = None
    amount_monthly: Decimal | None = None
    amount_total: Decimal | None = None
    currency: str = "USDC"
    allowed_rails: list[str] = Field(default_factory=lambda: ["card", "usdc", "bank"])
    allowed_chains: list[str] | None = None
    allowed_tokens: list[str] | None = None
    approval_threshold: Decimal | None = None
    approval_mode: str = "auto"
    expires_at: str | None = None
    initial_status: str = "active"
    metadata: dict | None = None


class MandateResponse(BaseModel):
    id: str
    org_id: str
    agent_id: str | None = None
    wallet_id: str | None = None
    principal_id: str
    issuer_id: str
    purpose_scope: str | None = None
    merchant_scope: dict | None = None
    amount_per_tx: str | None = None
    amount_daily: str | None = None
    amount_weekly: str | None = None
    amount_monthly: str | None = None
    amount_total: str | None = None
    currency: str
    spent_total: str
    allowed_rails: list[str]
    allowed_chains: list[str] | None = None
    allowed_tokens: list[str] | None = None
    approval_threshold: str | None = None
    approval_mode: str
    status: str
    version: int
    policy_hash: str | None = None
    expires_at: str | None = None
    created_at: str
    updated_at: str
    next_steps: list[str] = []


class TransitionRequest(BaseModel):
    reason: str | None = None


class TransitionResponse(BaseModel):
    id: str
    mandate_id: str
    from_status: str
    to_status: str
    changed_by: str
    reason: str | None = None
    created_at: str


def _policy_hash(data: dict) -> str:
    rules = {k: str(data.get(k)) for k in sorted(data) if data.get(k) is not None}
    return hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()


VALID_TRANSITIONS = {
    ("draft", "active"), ("active", "suspended"), ("suspended", "active"),
    ("active", "revoked"), ("suspended", "revoked"),
    ("active", "expired"), ("active", "consumed"),
}


def _row_to_response(r) -> MandateResponse:
    return MandateResponse(
        id=r["id"], org_id=r["org_id"], agent_id=r["agent_id"],
        wallet_id=r["wallet_id"], principal_id=r["principal_id"],
        issuer_id=r["issuer_id"], purpose_scope=r["purpose_scope"],
        merchant_scope=r["merchant_scope"] if r["merchant_scope"] else None,
        amount_per_tx=str(r["amount_per_tx"]) if r["amount_per_tx"] else None,
        amount_daily=str(r["amount_daily"]) if r["amount_daily"] else None,
        amount_weekly=str(r["amount_weekly"]) if r["amount_weekly"] else None,
        amount_monthly=str(r["amount_monthly"]) if r["amount_monthly"] else None,
        amount_total=str(r["amount_total"]) if r["amount_total"] else None,
        currency=r["currency"], spent_total=str(r.get("spent_total", 0)),
        allowed_rails=r["allowed_rails"] or [],
        allowed_chains=r["allowed_chains"], allowed_tokens=r["allowed_tokens"],
        approval_threshold=str(r["approval_threshold"]) if r["approval_threshold"] else None,
        approval_mode=r["approval_mode"], status=r["status"],
        version=r["version"], policy_hash=r["policy_hash"],
        expires_at=r["expires_at"].isoformat() if r["expires_at"] else None,
        created_at=r["created_at"].isoformat(), updated_at=r["updated_at"].isoformat(),
    )


@router.post("", response_model=MandateResponse, status_code=status.HTTP_201_CREATED)
async def create_mandate(body: CreateMandateRequest, principal: Principal = Depends(require_principal)):
    """Create a new spending mandate."""
    mandate_id = f"mandate_{uuid4().hex[:12]}"
    now = datetime.now(UTC)
    ph = _policy_hash({
        "merchant_scope": body.merchant_scope, "purpose_scope": body.purpose_scope,
        "amount_per_tx": body.amount_per_tx, "amount_daily": body.amount_daily,
        "amount_weekly": body.amount_weekly, "amount_monthly": body.amount_monthly,
        "amount_total": body.amount_total, "allowed_rails": body.allowed_rails,
        "approval_threshold": body.approval_threshold, "approval_mode": body.approval_mode,
    })

    try:
        from sardis_v2_core.database import Database
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO spending_mandates
                    (id, org_id, agent_id, wallet_id, principal_id, issuer_id,
                     purpose_scope, merchant_scope, amount_per_tx, amount_daily,
                     amount_weekly, amount_monthly, amount_total, currency,
                     allowed_rails, allowed_chains, allowed_tokens,
                     approval_threshold, approval_mode, status, policy_hash,
                     expires_at, metadata, created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23::jsonb,$24,$25)""",
                mandate_id, principal.organization_id, body.agent_id, body.wallet_id,
                principal.user_id, principal.user_id, body.purpose_scope,
                json.dumps(body.merchant_scope or {}),
                body.amount_per_tx, body.amount_daily, body.amount_weekly,
                body.amount_monthly, body.amount_total, body.currency,
                body.allowed_rails, body.allowed_chains, body.allowed_tokens,
                body.approval_threshold, body.approval_mode, body.initial_status,
                ph, body.expires_at, json.dumps(body.metadata or {}), now, now,
            )
    except Exception as exc:
        logger.error("Failed to create mandate: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create mandate")

    return MandateResponse(
        id=mandate_id, org_id=principal.organization_id, agent_id=body.agent_id,
        wallet_id=body.wallet_id, principal_id=principal.user_id, issuer_id=principal.user_id,
        purpose_scope=body.purpose_scope, merchant_scope=body.merchant_scope,
        amount_per_tx=str(body.amount_per_tx) if body.amount_per_tx else None,
        amount_daily=str(body.amount_daily) if body.amount_daily else None,
        amount_weekly=str(body.amount_weekly) if body.amount_weekly else None,
        amount_monthly=str(body.amount_monthly) if body.amount_monthly else None,
        amount_total=str(body.amount_total) if body.amount_total else None,
        currency=body.currency, spent_total="0", allowed_rails=body.allowed_rails,
        allowed_chains=body.allowed_chains, allowed_tokens=body.allowed_tokens,
        approval_threshold=str(body.approval_threshold) if body.approval_threshold else None,
        approval_mode=body.approval_mode, status=body.initial_status,
        version=1, policy_hash=ph, expires_at=body.expires_at,
        created_at=now.isoformat(), updated_at=now.isoformat(),
        next_steps=[
            "POST /api/v2/agents — Create an AI agent",
            "POST /api/v2/mpp/sessions — Start MPP payment session",
        ],
    )


@router.get("", response_model=list[MandateResponse])
async def list_mandates(
    status_filter: str | None = None, agent_id: str | None = None,
    principal: Principal = Depends(require_principal),
):
    """List spending mandates for the organization."""
    try:
        from sardis_v2_core.database import Database
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            q = "SELECT * FROM spending_mandates WHERE org_id = $1"
            p: list = [principal.organization_id]
            if status_filter:
                q += f" AND status = ${len(p)+1}"; p.append(status_filter)
            if agent_id:
                q += f" AND agent_id = ${len(p)+1}"; p.append(agent_id)
            q += " ORDER BY created_at DESC LIMIT 100"
            rows = await conn.fetch(q, *p)
    except Exception as exc:
        logger.error("Failed to list mandates: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list mandates")
    return [_row_to_response(r) for r in rows]


@router.get("/{mandate_id}", response_model=MandateResponse)
async def get_mandate(mandate_id: str, principal: Principal = Depends(require_principal)):
    """Get a specific spending mandate."""
    try:
        from sardis_v2_core.database import Database
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            r = await conn.fetchrow(
                "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2",
                mandate_id, principal.organization_id,
            )
    except Exception as exc:
        logger.error("Failed to get mandate: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to get mandate")
    if not r:
        raise HTTPException(status_code=404, detail="Mandate not found")
    return _row_to_response(r)


@router.post("/{mandate_id}/revoke", response_model=TransitionResponse)
async def revoke_mandate(mandate_id: str, body: TransitionRequest, principal: Principal = Depends(require_principal)):
    """Permanently revoke a spending mandate."""
    return await _do_transition(mandate_id, "revoked", principal, body.reason)


@router.post("/{mandate_id}/suspend", response_model=TransitionResponse)
async def suspend_mandate(mandate_id: str, body: TransitionRequest, principal: Principal = Depends(require_principal)):
    """Temporarily suspend a mandate."""
    return await _do_transition(mandate_id, "suspended", principal, body.reason)


@router.post("/{mandate_id}/resume", response_model=TransitionResponse)
async def resume_mandate(mandate_id: str, body: TransitionRequest, principal: Principal = Depends(require_principal)):
    """Resume a suspended mandate."""
    return await _do_transition(mandate_id, "active", principal, body.reason)


@router.post("/{mandate_id}/activate", response_model=TransitionResponse)
async def activate_mandate(mandate_id: str, body: TransitionRequest, principal: Principal = Depends(require_principal)):
    """Activate a draft mandate."""
    return await _do_transition(mandate_id, "active", principal, body.reason)


@router.get("/{mandate_id}/transitions", response_model=list[TransitionResponse])
async def list_transitions(mandate_id: str, principal: Principal = Depends(require_principal)):
    """View state transition history."""
    try:
        from sardis_v2_core.database import Database
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            m = await conn.fetchrow("SELECT org_id FROM spending_mandates WHERE id=$1 AND org_id=$2", mandate_id, principal.organization_id)
            if not m:
                raise HTTPException(status_code=404, detail="Mandate not found")
            rows = await conn.fetch("SELECT * FROM mandate_state_transitions WHERE mandate_id=$1 ORDER BY created_at DESC", mandate_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list transitions: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list transitions")
    return [TransitionResponse(id=r["id"], mandate_id=r["mandate_id"], from_status=r["from_status"], to_status=r["to_status"], changed_by=r["changed_by"], reason=r["reason"], created_at=r["created_at"].isoformat()) for r in rows]


async def _do_transition(mandate_id: str, to_status: str, principal: Principal, reason: str | None) -> TransitionResponse:
    try:
        from sardis_v2_core.database import Database
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT id, status FROM spending_mandates WHERE id=$1 AND org_id=$2", mandate_id, principal.organization_id)
            if not row:
                raise HTTPException(status_code=404, detail="Mandate not found")
            from_status = row["status"]
            if (from_status, to_status) not in VALID_TRANSITIONS:
                raise HTTPException(status_code=400, detail=f"Invalid transition: {from_status} -> {to_status}")
            now = datetime.now(UTC)
            tid = f"mst_{uuid4().hex[:16]}"
            if to_status == "revoked":
                await conn.execute("UPDATE spending_mandates SET status=$1, revoked_at=$2, revoked_by=$3, revocation_reason=$4, updated_at=$5 WHERE id=$6", to_status, now, principal.user_id, reason, now, mandate_id)
            else:
                await conn.execute("UPDATE spending_mandates SET status=$1, updated_at=$2 WHERE id=$3", to_status, now, mandate_id)
            await conn.execute("INSERT INTO mandate_state_transitions (id,mandate_id,from_status,to_status,changed_by,reason,created_at) VALUES ($1,$2,$3,$4,$5,$6,$7)", tid, mandate_id, from_status, to_status, principal.user_id, reason, now)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Mandate transition failed: %s", exc)
        raise HTTPException(status_code=500, detail="Transition failed")
    logger.info("Mandate %s: %s -> %s by %s", mandate_id, from_status, to_status, principal.user_id)
    return TransitionResponse(id=tid, mandate_id=mandate_id, from_status=from_status, to_status=to_status, changed_by=principal.user_id, reason=reason, created_at=now.isoformat())
