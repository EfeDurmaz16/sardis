"""Operator APIs for canonical reconciliation, drift, and audit evidence."""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Any, Optional
import csv
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_admin_principal

router = APIRouter(tags=["treasury-ops"])


@dataclass
class TreasuryOpsDependencies:
    canonical_repo: Any


def get_deps() -> TreasuryOpsDependencies:
    raise NotImplementedError("Dependency override required")


class ResolveReviewRequest(BaseModel):
    status: str = Field(pattern="^(in_review|resolved|dismissed)$")
    notes: Optional[str] = None


@router.get("/journeys")
async def list_canonical_journeys(
    rail: Optional[str] = Query(default=None),
    canonical_state: Optional[str] = Query(default=None),
    break_status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    deps: TreasuryOpsDependencies = Depends(get_deps),
    principal: Principal = Depends(require_admin_principal),
):
    rows = await deps.canonical_repo.list_journeys(
        principal.organization_id,
        rail=rail,
        canonical_state=canonical_state,
        break_status=break_status,
        limit=limit,
    )
    return {"items": rows, "count": len(rows)}


@router.get("/drift")
async def list_reconciliation_breaks(
    status_value: str = Query(default="open"),
    limit: int = Query(default=100, ge=1, le=1000),
    deps: TreasuryOpsDependencies = Depends(get_deps),
    principal: Principal = Depends(require_admin_principal),
):
    rows = await deps.canonical_repo.list_breaks(
        principal.organization_id,
        status_value=status_value,
        limit=limit,
    )
    return {"items": rows, "count": len(rows)}


@router.get("/returns")
async def list_return_code_journeys(
    codes: str = Query(default="R01,R09,R29"),
    limit: int = Query(default=200, ge=1, le=1000),
    deps: TreasuryOpsDependencies = Depends(get_deps),
    principal: Principal = Depends(require_admin_principal),
):
    requested_codes = {c.strip().upper() for c in codes.split(",") if c.strip()}
    journeys = await deps.canonical_repo.list_journeys(
        principal.organization_id,
        rail="fiat_ach",
        limit=limit,
    )
    filtered = [
        row for row in journeys
        if str(row.get("last_return_code", "")).upper() in requested_codes
    ]
    return {"items": filtered, "count": len(filtered), "codes": sorted(requested_codes)}


@router.get("/manual-reviews")
async def list_manual_reviews(
    status_value: str = Query(default="queued"),
    limit: int = Query(default=100, ge=1, le=1000),
    deps: TreasuryOpsDependencies = Depends(get_deps),
    principal: Principal = Depends(require_admin_principal),
):
    rows = await deps.canonical_repo.list_manual_reviews(
        principal.organization_id,
        status_value=status_value,
        limit=limit,
    )
    return {"items": rows, "count": len(rows)}


@router.post("/manual-reviews/{review_id}/resolve")
async def resolve_manual_review(
    review_id: str,
    body: ResolveReviewRequest,
    deps: TreasuryOpsDependencies = Depends(get_deps),
    principal: Principal = Depends(require_admin_principal),
):
    row = await deps.canonical_repo.resolve_manual_review(
        organization_id=principal.organization_id,
        review_id=review_id,
        status_value=body.status,
        notes=body.notes,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="manual_review_not_found")
    return row


@router.get("/audit-evidence/export")
async def export_audit_evidence(
    journey_id: Optional[str] = Query(default=None),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    limit: int = Query(default=500, ge=1, le=5000),
    deps: TreasuryOpsDependencies = Depends(get_deps),
    principal: Principal = Depends(require_admin_principal),
):
    evidence = await deps.canonical_repo.export_audit_evidence(
        principal.organization_id,
        journey_id=journey_id,
        limit=limit,
    )
    if format == "json":
        return JSONResponse(content=jsonable_encoder(evidence))

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "section",
            "id",
            "journey_id",
            "rail",
            "state_or_status",
            "amount_minor",
            "currency",
            "event_or_reason",
            "timestamp",
            "metadata",
        ]
    )
    for row in evidence.get("journeys", []):
        writer.writerow(
            [
                "journey",
                row.get("journey_id"),
                row.get("journey_id"),
                row.get("rail"),
                row.get("canonical_state"),
                row.get("expected_amount_minor"),
                row.get("currency"),
                row.get("external_reference"),
                row.get("updated_at") or row.get("last_event_at"),
                json.dumps(row.get("metadata") or {}, sort_keys=True),
            ]
        )
    for row in evidence.get("events", []):
        writer.writerow(
            [
                "event",
                row.get("id"),
                row.get("journey_id"),
                "",
                row.get("canonical_state"),
                row.get("amount_minor"),
                row.get("currency"),
                row.get("canonical_event_type") or row.get("provider_event_type"),
                row.get("event_ts"),
                json.dumps(row.get("metadata") or {}, sort_keys=True),
            ]
        )
    for row in evidence.get("breaks", []):
        writer.writerow(
            [
                "break",
                row.get("break_id"),
                row.get("journey_id"),
                "",
                row.get("status"),
                row.get("delta_minor"),
                "",
                row.get("break_type"),
                row.get("detected_at"),
                json.dumps(row.get("metadata") or {}, sort_keys=True),
            ]
        )
    for row in evidence.get("manual_reviews", []):
        writer.writerow(
            [
                "manual_review",
                row.get("review_id"),
                row.get("journey_id"),
                "",
                row.get("status"),
                "",
                "",
                row.get("reason_code"),
                row.get("created_at"),
                json.dumps(row.get("payload") or {}, sort_keys=True),
            ]
        )
    return PlainTextResponse(content=buf.getvalue(), media_type="text/csv")
