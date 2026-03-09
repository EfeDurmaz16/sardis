"""Evidence API — retrieve proof artifacts for auditors and enterprise customers.

Provides endpoints to fetch execution traces, compliance decisions,
policy receipts, and webhook delivery audit trails.

All queries are scoped to the caller's organization to prevent cross-tenant
data exposure.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter()


class TransactionEvidenceResponse(BaseModel):
    """Full execution trace for a transaction."""
    tx_id: str
    receipt: dict[str, Any] | None = None
    ledger_entries: list[dict[str, Any]] = Field(default_factory=list)
    compliance_result: dict[str, Any] | None = None
    policy_evaluation: dict[str, Any] | None = None
    side_effects: list[dict[str, Any]] = Field(default_factory=list)
    idempotency_record: dict[str, Any] | None = None


class WebhookEvidenceResponse(BaseModel):
    """Webhook delivery audit trail."""
    event_id: str
    deliveries: list[dict[str, Any]] = Field(default_factory=list)


class PolicyDecisionSummary(BaseModel):
    """Summary of a policy decision for list endpoints."""
    decision_id: str
    agent_id: str
    mandate_id: str | None = None
    verdict: str
    evidence_hash: str
    created_at: str


class PolicyDecisionDetailResponse(BaseModel):
    """Full policy decision evidence bundle."""
    decision_id: str
    agent_id: str
    mandate_id: str | None = None
    policy_version_id: str | None = None
    verdict: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    evidence_hash: str
    group_hierarchy: list[str] | None = None
    created_at: str


def _serialize_datetimes(row_dict: dict) -> dict:
    """Convert datetime values to ISO strings in place."""
    for k, v in row_dict.items():
        if hasattr(v, "isoformat"):
            row_dict[k] = v.isoformat()
    return row_dict


async def _verify_agent_ownership(conn: Any, agent_id: str, org_id: str) -> bool:
    """Verify that an agent belongs to the given organization."""
    owner = await conn.fetchval(
        "SELECT owner_id FROM agents WHERE id = $1", agent_id,
    )
    return owner == org_id


@router.get("/transactions/{tx_id}", response_model=TransactionEvidenceResponse)
async def get_transaction_evidence(
    request: Request,
    tx_id: str,
    principal: Principal = Depends(require_principal),
):
    """Retrieve full execution trace for a transaction.

    Returns the execution receipt, ledger entries, compliance decision,
    policy evaluation, and side effect queue status.
    All results scoped to the caller's organization.
    """
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        org_id = principal.organization_id

        async with pool.acquire() as conn:
            # Ledger entries — scoped via wallet ownership
            ledger_rows = await conn.fetch(
                """
                SELECT le.entry_id, le.wallet_id, le.entry_type, le.amount,
                       le.currency, le.chain, le.chain_tx_hash, le.status,
                       le.created_at
                FROM ledger_entries le
                JOIN wallets w ON le.wallet_id = w.wallet_id
                WHERE (le.chain_tx_hash = $1 OR le.entry_id = $1)
                  AND w.organization_id = $2
                ORDER BY le.created_at
                """,
                tx_id,
                org_id,
            )
            ledger_entries = [_serialize_datetimes(dict(r)) for r in ledger_rows]

            if not ledger_entries:
                raise HTTPException(
                    status_code=404,
                    detail="Transaction not found or not accessible",
                )

            # Side effects — scoped via tx_id already validated by ledger ownership
            side_effects_rows = await conn.fetch(
                """
                SELECT id, effect_type, status, attempt_count, last_error,
                       created_at, processed_at
                FROM execution_side_effects
                WHERE tx_id = $1
                ORDER BY id
                """,
                tx_id,
            )
            side_effects = [_serialize_datetimes(dict(r)) for r in side_effects_rows]

            # Idempotency record — exact match only (no LIKE)
            idem_row = await conn.fetchrow(
                """
                SELECT idempotency_key, response_status, created_at, expires_at
                FROM idempotency_records
                WHERE idempotency_key = $1
                """,
                tx_id,
            )
            idem_record = None
            if idem_row:
                idem_record = _serialize_datetimes(dict(idem_row))

        return TransactionEvidenceResponse(
            tx_id=tx_id,
            ledger_entries=ledger_entries,
            side_effects=side_effects,
            idempotency_record=idem_record,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Evidence lookup failed for tx=%s: %s", tx_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evidence lookup failed",
        )


@router.get("/webhooks/{event_id}", response_model=WebhookEvidenceResponse)
async def get_webhook_evidence(
    request: Request,
    event_id: str,
    principal: Principal = Depends(require_principal),
):
    """Retrieve webhook delivery audit trail for an event.

    Scoped to the caller's organization via webhook subscription ownership.
    """
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        org_id = principal.organization_id

        async with pool.acquire() as conn:
            # Scope webhook deliveries through subscription ownership
            rows = await conn.fetch(
                """
                SELECT wd.id, wd.event_type, wd.url AS webhook_url,
                       wd.status_code, wd.attempt_number AS attempt_count,
                       wd.error AS last_error, wd.created_at,
                       wd.created_at AS delivered_at
                FROM webhook_deliveries wd
                JOIN webhook_subscriptions ws ON wd.subscription_id = ws.external_id
                WHERE wd.event_id = $1
                  AND ws.organization_id = $2
                ORDER BY wd.created_at
                """,
                event_id,
                org_id,
            )
            deliveries = [_serialize_datetimes(dict(r)) for r in rows]

        return WebhookEvidenceResponse(
            event_id=event_id,
            deliveries=deliveries,
        )

    except Exception as e:
        logger.exception("Webhook evidence lookup failed for event=%s: %s", event_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook evidence lookup failed",
        )


# ============ Policy Decision Evidence ============


@router.get("/decisions/{agent_id}", response_model=list[PolicyDecisionSummary])
async def list_policy_decisions(
    request: Request,
    agent_id: str,
    limit: int = 20,
    offset: int = 0,
    principal: Principal = Depends(require_principal),
):
    """List policy decisions for an agent with pagination.

    Verifies agent belongs to the caller's organization.
    """
    limit = min(limit, 100)
    offset = max(offset, 0)
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        org_id = principal.organization_id

        async with pool.acquire() as conn:
            if not await _verify_agent_ownership(conn, agent_id, org_id):
                raise HTTPException(status_code=404, detail="Agent not found")

            rows = await conn.fetch(
                """
                SELECT id, agent_id, mandate_id, verdict, evidence_hash, created_at
                FROM policy_decisions
                WHERE agent_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                agent_id,
                limit,
                offset,
            )
        return [
            PolicyDecisionSummary(
                decision_id=r["id"],
                agent_id=r["agent_id"],
                mandate_id=r["mandate_id"],
                verdict=r["verdict"],
                evidence_hash=r["evidence_hash"],
                created_at=r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
            )
            for r in rows
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Policy decisions lookup failed for agent=%s: %s", agent_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Policy decisions lookup failed",
        )


@router.get("/decisions/{agent_id}/{decision_id}", response_model=PolicyDecisionDetailResponse)
async def get_policy_decision(
    request: Request,
    agent_id: str,
    decision_id: str,
    principal: Principal = Depends(require_principal),
):
    """Retrieve full evidence bundle for a specific policy decision.

    Verifies agent belongs to the caller's organization.
    """
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        org_id = principal.organization_id

        async with pool.acquire() as conn:
            if not await _verify_agent_ownership(conn, agent_id, org_id):
                raise HTTPException(status_code=404, detail="Agent not found")

            row = await conn.fetchrow(
                """
                SELECT id, agent_id, mandate_id, policy_version_id,
                       verdict, steps_json, evidence_hash,
                       group_hierarchy, created_at
                FROM policy_decisions
                WHERE id = $1 AND agent_id = $2
                """,
                decision_id,
                agent_id,
            )

        if not row:
            raise HTTPException(status_code=404, detail="Decision not found")

        steps = row["steps_json"]
        if isinstance(steps, str):
            steps = json.loads(steps)

        return PolicyDecisionDetailResponse(
            decision_id=row["id"],
            agent_id=row["agent_id"],
            mandate_id=row["mandate_id"],
            policy_version_id=row["policy_version_id"],
            verdict=row["verdict"],
            steps=steps if isinstance(steps, list) else [],
            evidence_hash=row["evidence_hash"],
            group_hierarchy=list(row["group_hierarchy"]) if row["group_hierarchy"] else None,
            created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Decision lookup failed for %s/%s: %s", agent_id, decision_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Decision lookup failed",
        )


@router.get("/decisions/{agent_id}/{decision_id}/export")
async def export_policy_decision(
    request: Request,
    agent_id: str,
    decision_id: str,
    principal: Principal = Depends(require_principal),
):
    """Export policy decision as a downloadable JSON evidence bundle."""
    from fastapi.responses import JSONResponse

    detail_response = await get_policy_decision(request, agent_id, decision_id, principal)

    return JSONResponse(
        content=detail_response.model_dump(),
        headers={
            "Content-Disposition": f'attachment; filename="evidence_{decision_id}.json"',
        },
    )
