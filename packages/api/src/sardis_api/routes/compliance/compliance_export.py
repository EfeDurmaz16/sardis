"""Compliance Evidence Export — audit-ready data for enterprise compliance teams.

Exports policy decisions, ledger entries, KYC verifications, and sanctions
screenings as structured JSON. Enterprises need this for SOC2, PCI, and
internal audit requirements.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from sardis_api.authz import require_principal

logger = logging.getLogger("sardis.api.compliance_export")

router = APIRouter(
    prefix="/api/v2/compliance",
    tags=["compliance-export"],
    dependencies=[Depends(require_principal)],
)


class ComplianceExportResponse(BaseModel):
    """Structured compliance evidence package."""
    org_id: str
    export_period: dict[str, str]
    generated_at: str
    summary: dict[str, Any]
    policy_decisions: list[dict[str, Any]]
    ledger_entries: list[dict[str, Any]]
    kyc_verifications: list[dict[str, Any]]
    sanctions_screenings: list[dict[str, Any]]
    mandate_audit: list[dict[str, Any]]


@router.get("/export", response_model=ComplianceExportResponse)
async def export_compliance_evidence(
    org_id: str = Query(..., description="Organization ID"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Export compliance evidence for audit.

    Returns structured data covering:
    - Policy decisions (approve/deny with reasons)
    - Ledger entries (Merkle-anchored transactions)
    - KYC verification records
    - Sanctions screening results
    - Mandate usage audit trail

    Enterprise compliance teams use this for SOC2/PCI audits.
    """
    from sardis_v2_core.database import Database

    # Policy decisions
    policy_rows = await Database.fetch(
        """
        SELECT pd.id, pd.agent_id, pd.outcome, pd.reason_code, pd.reason,
               pd.amount, pd.vendor, pd.created_at
        FROM policy_decisions pd
        JOIN agents a ON a.id = pd.agent_id
        JOIN organizations o ON o.id = a.org_id
        WHERE o.external_id = $1
          AND pd.created_at >= $2::timestamptz
          AND pd.created_at <= $3::timestamptz
        ORDER BY pd.created_at DESC
        LIMIT 10000
        """,
        org_id, start_date, end_date,
    )

    # Ledger entries
    ledger_rows = await Database.fetch(
        """
        SELECT le.tx_id, le.from_wallet, le.to_wallet, le.amount, le.currency,
               le.chain, le.chain_tx_hash, le.status, le.audit_anchor, le.created_at
        FROM ledger_entries le
        JOIN wallets w ON w.id = le.wallet_id
        JOIN agents a ON a.id = w.agent_id
        JOIN organizations o ON o.id = a.org_id
        WHERE o.external_id = $1
          AND le.created_at >= $2::timestamptz
          AND le.created_at <= $3::timestamptz
        ORDER BY le.created_at DESC
        LIMIT 10000
        """,
        org_id, start_date, end_date,
    )

    # KYC verifications
    kyc_rows = await Database.fetch(
        """
        SELECT kv.external_id, kv.status, kv.provider, kv.risk_level,
               kv.created_at, kv.updated_at
        FROM kyc_verifications kv
        JOIN organizations o ON o.id = kv.org_id
        WHERE o.external_id = $1
          AND kv.created_at >= $2::timestamptz
          AND kv.created_at <= $3::timestamptz
        ORDER BY kv.created_at DESC
        """,
        org_id, start_date, end_date,
    )

    # Sanctions screenings
    sanctions_rows = await Database.fetch(
        """
        SELECT ss.id, ss.entity_name, ss.entity_type, ss.result,
               ss.risk_score, ss.provider, ss.created_at
        FROM sanctions_screenings ss
        WHERE ss.org_id = (SELECT id FROM organizations WHERE external_id = $1)
          AND ss.created_at >= $2::timestamptz
          AND ss.created_at <= $3::timestamptz
        ORDER BY ss.created_at DESC
        """,
        org_id, start_date, end_date,
    )

    # Mandate audit
    mandate_rows = await Database.fetch(
        """
        SELECT sm.external_id, sm.status, sm.principal_id, sm.agent_id,
               sm.amount_total, sm.spent_total, sm.created_at, sm.updated_at
        FROM spending_mandates sm
        WHERE sm.org_id = (SELECT id FROM organizations WHERE external_id = $1)
          AND sm.updated_at >= $2::timestamptz
          AND sm.updated_at <= $3::timestamptz
        ORDER BY sm.updated_at DESC
        """,
        org_id, start_date, end_date,
    )

    def _rows_to_dicts(rows: list) -> list[dict]:
        return [
            {k: (v.isoformat() if isinstance(v, datetime) else str(v) if v is not None else None)
             for k, v in dict(r).items()}
            for r in rows
        ]

    policy_dicts = _rows_to_dicts(policy_rows)
    ledger_dicts = _rows_to_dicts(ledger_rows)
    kyc_dicts = _rows_to_dicts(kyc_rows)
    sanctions_dicts = _rows_to_dicts(sanctions_rows)
    mandate_dicts = _rows_to_dicts(mandate_rows)

    # Summary stats
    total_approved = sum(1 for p in policy_dicts if p.get("outcome") == "APPROVED")
    total_blocked = sum(1 for p in policy_dicts if p.get("outcome") == "BLOCKED")

    return ComplianceExportResponse(
        org_id=org_id,
        export_period={"start": start_date, "end": end_date},
        generated_at=datetime.now(UTC).isoformat(),
        summary={
            "total_policy_decisions": len(policy_dicts),
            "approved": total_approved,
            "blocked": total_blocked,
            "approval_rate": f"{(total_approved / max(len(policy_dicts), 1)) * 100:.1f}%",
            "total_transactions": len(ledger_dicts),
            "total_kyc_checks": len(kyc_dicts),
            "total_sanctions_screenings": len(sanctions_dicts),
            "active_mandates": len(mandate_dicts),
        },
        policy_decisions=policy_dicts,
        ledger_entries=ledger_dicts,
        kyc_verifications=kyc_dicts,
        sanctions_screenings=sanctions_dicts,
        mandate_audit=mandate_dicts,
    )
