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
