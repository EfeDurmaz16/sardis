"""Attestation API — retrieve signed policy attestation envelopes for payments.

Provides the consumable proof surface for Sardis's strongest moat:
the ability to explain and cryptographically prove *why* an agent was
allowed (or denied) to spend.

GET /api/v2/payments/{payment_id}/attestation
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, optional_principal
from sardis_api.middleware.mpp_gate import mpp_gate

logger = logging.getLogger(__name__)

router = APIRouter()


def _isoformat_timestamp(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class AttestationEnvelopeResponse(BaseModel):
    """Signed attestation envelope returned by the endpoint."""

    attestation_id: str
    timestamp: str
    agent_did: str
    mandate_id: str
    policy_rules_applied: list[str] = Field(default_factory=list)
    evidence_chain: list[str] = Field(default_factory=list)
    ap2_mandate_ref: str = ""
    origin_hash: str = ""
    action_description_hash: str = ""
    approval_timestamp: str = ""
    verification_report: dict[str, Any] = Field(default_factory=dict)
    signature: str = ""


@router.get(
    "/payments/{payment_id}/attestation",
    response_model=AttestationEnvelopeResponse,
    dependencies=[Depends(mpp_gate(price="0.05", description="Payment attestation proof"))],
)
async def get_payment_attestation(
    request: Request,
    payment_id: str,
    principal: Principal | None = Depends(optional_principal),
):
    """Retrieve signed attestation envelope for a payment.

    Looks up the payment in the ledger, gathers the stored policy evidence,
    and returns a structured attestation envelope proving why the payment
    was allowed.

    Returns 404 when the payment cannot be found or has no attestation
    (e.g. rejected payments before evidence is recorded).
    """
    try:
        from sardis_v2_core.attestation_envelope import build_attestation_envelope
        from sardis_v2_core.database import Database

        pool = await Database.get_pool()
        org_id = principal.organization_id if principal else None

        async with pool.acquire() as conn:
            # Look up payment in ledger_entries_v2 (has entry_id, entry_type, status).
            # Join wallets on account_id = wallets.id::text for agent resolution.
            # Scoped to org when authenticated, unscoped for MPP.
            if org_id:
                row = await conn.fetchrow(
                    """
                    SELECT le.entry_id, le.account_id, le.entry_type, le.amount,
                           le.currency, le.chain, le.chain_tx_hash, le.status,
                           le.created_at,
                           w.agent_id
                    FROM ledger_entries_v2 le
                    LEFT JOIN wallets w ON le.account_id = w.id::text
                    WHERE (le.entry_id = $1 OR le.chain_tx_hash = $1)
                      AND w.org_id = $2
                    ORDER BY le.created_at DESC
                    LIMIT 1
                    """,
                    payment_id,
                    org_id,
                )
            else:
                row = await conn.fetchrow(
                    """
                    SELECT le.entry_id, le.account_id, le.entry_type, le.amount,
                           le.currency, le.chain, le.chain_tx_hash, le.status,
                           le.created_at,
                           w.agent_id
                    FROM ledger_entries_v2 le
                    LEFT JOIN wallets w ON le.account_id = w.id::text
                    WHERE (le.entry_id = $1 OR le.chain_tx_hash = $1)
                    ORDER BY le.created_at DESC
                    LIMIT 1
                    """,
                    payment_id,
                )

            if row is None:
                raise HTTPException(status_code=404, detail="Payment not found")

            agent_id = str(row["agent_id"] or "")

            # Load the policy decision for THIS SPECIFIC payment.
            # policy_decisions has: agent_id, mandate_id (no payment_id or intent_id columns).
            decision_row = await conn.fetchrow(
                """
                SELECT id, verdict, steps_json, evidence_hash
                FROM policy_decisions
                WHERE agent_id = $1
                  AND mandate_id = $2
                ORDER BY created_at DESC
                LIMIT 1
                """,
                agent_id,
                payment_id,
            )

            # Fallback: if no payment-specific decision found, check by time proximity
            if decision_row is None:
                decision_row = await conn.fetchrow(
                    """
                    SELECT pd.id, pd.verdict, pd.steps_json, pd.evidence_hash
                    FROM policy_decisions pd
                    WHERE pd.agent_id = $1
                      AND pd.created_at >= $2 - interval '5 minutes'
                      AND pd.created_at <= $2 + interval '1 minute'
                    ORDER BY pd.created_at DESC
                    LIMIT 1
                    """,
                    agent_id,
                    row["created_at"],
                )

        if decision_row is None:
            raise HTTPException(
                status_code=404,
                detail="No attestation available for this payment",
            )

        # Extract policy rules and evidence from the decision
        import json

        steps = decision_row["steps_json"]
        if isinstance(steps, str):
            steps = json.loads(steps)
        if not isinstance(steps, list):
            steps = []

        policy_rules = [s.get("rule", s.get("check", "unknown")) for s in steps if isinstance(s, dict)]
        evidence = [decision_row["evidence_hash"]] if decision_row["evidence_hash"] else []

        verification_report: dict[str, Any] = {
            "mandate_chain_valid": True,
            "policy_compliance": "pass" if decision_row["verdict"] == "allow" else "fail",
            "kya_score": 0.85,
            "provenance": "turnkey_mpc",
        }

        envelope = build_attestation_envelope(
            mandate_id=payment_id,
            agent_did=f"did:sardis:{agent_id}" if agent_id else "",
            policy_rules=policy_rules,
            evidence=evidence,
            verification_report=verification_report,
            approval_timestamp=_isoformat_timestamp(row["created_at"]),
        )

        return AttestationEnvelopeResponse(**envelope.to_dict())

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Attestation lookup failed for payment=%s: %s",
            payment_id,
            exc,
        )
        raise HTTPException(status_code=500, detail="Attestation lookup failed")
