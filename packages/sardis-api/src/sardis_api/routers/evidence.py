"""Evidence API — retrieve proof artifacts for auditors and enterprise customers.

Provides endpoints to fetch execution traces, compliance decisions,
policy receipts, and webhook delivery audit trails.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter()


class TransactionEvidenceResponse(BaseModel):
    """Full execution trace for a transaction."""
    tx_id: str
    receipt: Optional[dict[str, Any]] = None
    ledger_entries: list[dict[str, Any]] = Field(default_factory=list)
    compliance_result: Optional[dict[str, Any]] = None
    policy_evaluation: Optional[dict[str, Any]] = None
    side_effects: list[dict[str, Any]] = Field(default_factory=list)
    idempotency_record: Optional[dict[str, Any]] = None


class WebhookEvidenceResponse(BaseModel):
    """Webhook delivery audit trail."""
    event_id: str
    deliveries: list[dict[str, Any]] = Field(default_factory=list)


class PolicyDecisionSummary(BaseModel):
    """Summary of a policy decision for list endpoints."""
    decision_id: str
    agent_id: str
    mandate_id: Optional[str] = None
    verdict: str
    evidence_hash: str
    created_at: str


class PolicyDecisionDetailResponse(BaseModel):
    """Full policy decision evidence bundle."""
    decision_id: str
    agent_id: str
    mandate_id: Optional[str] = None
    policy_version_id: Optional[str] = None
    verdict: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    evidence_hash: str
    group_hierarchy: Optional[list[str]] = None
    created_at: str


@router.get("/transactions/{tx_id}", response_model=TransactionEvidenceResponse)
async def get_transaction_evidence(
    request: Request,
    tx_id: str,
    principal: Principal = Depends(require_principal),
):
    """Retrieve full execution trace for a transaction.

    Returns the execution receipt, ledger entries, compliance decision,
    policy evaluation, and side effect queue status.
    """
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            # Ledger entries
            ledger_rows = await conn.fetch(
                """
                SELECT entry_id, wallet_id, entry_type, amount, currency,
                       chain, chain_tx_hash, status, created_at
                FROM ledger_entries
                WHERE chain_tx_hash = $1 OR entry_id = $1
                ORDER BY created_at
                """,
                tx_id,
            )
            ledger_entries = [dict(r) for r in ledger_rows]
            # Serialize datetimes
            for entry in ledger_entries:
                for k, v in entry.items():
                    if hasattr(v, "isoformat"):
                        entry[k] = v.isoformat()

            # Side effects
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
            side_effects = [dict(r) for r in side_effects_rows]
            for se in side_effects:
                for k, v in se.items():
                    if hasattr(v, "isoformat"):
                        se[k] = v.isoformat()

            # Idempotency record
            idem_row = await conn.fetchrow(
                """
                SELECT idempotency_key, response_status, created_at, expires_at
                FROM idempotency_records
                WHERE idempotency_key LIKE '%' || $1 || '%'
                LIMIT 1
                """,
                tx_id,
            )
            idem_record = None
            if idem_row:
                idem_record = dict(idem_row)
                for k, v in idem_record.items():
                    if hasattr(v, "isoformat"):
                        idem_record[k] = v.isoformat()

        return TransactionEvidenceResponse(
            tx_id=tx_id,
            ledger_entries=ledger_entries,
            side_effects=side_effects,
            idempotency_record=idem_record,
        )

    except Exception as e:
        logger.exception("Evidence lookup failed for tx=%s: %s", tx_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evidence lookup failed: {e}",
        )


@router.get("/webhooks/{event_id}", response_model=WebhookEvidenceResponse)
async def get_webhook_evidence(
    request: Request,
    event_id: str,
    principal: Principal = Depends(require_principal),
):
    """Retrieve webhook delivery audit trail for an event."""
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, event_type, webhook_url, status_code,
                       attempt_count, last_error, created_at, delivered_at
                FROM webhook_deliveries
                WHERE event_id = $1
                ORDER BY created_at
                """,
                event_id,
            )
            deliveries = [dict(r) for r in rows]
            for d in deliveries:
                for k, v in d.items():
                    if hasattr(v, "isoformat"):
                        d[k] = v.isoformat()

        return WebhookEvidenceResponse(
            event_id=event_id,
            deliveries=deliveries,
        )

    except Exception as e:
        logger.exception("Webhook evidence lookup failed for event=%s: %s", event_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook evidence lookup failed: {e}",
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
    """List policy decisions for an agent with pagination."""
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
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

    except Exception as e:
        logger.exception("Policy decisions lookup failed for agent=%s: %s", agent_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy decisions lookup failed: {e}",
        )


@router.get("/decisions/{agent_id}/{decision_id}", response_model=PolicyDecisionDetailResponse)
async def get_policy_decision(
    request: Request,
    agent_id: str,
    decision_id: str,
    principal: Principal = Depends(require_principal),
):
    """Retrieve full evidence bundle for a specific policy decision."""
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
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
            detail=f"Decision lookup failed: {e}",
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
