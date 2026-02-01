"""Invoice management API endpoints."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_v2_core.database import Database
from sardis_api.middleware.auth import require_api_key, APIKey

router = APIRouter()


# Request/Response Models
class CreateInvoiceRequest(BaseModel):
    amount: str
    currency: str = "USDC"
    description: Optional[str] = None
    merchant_name: Optional[str] = None
    payer_agent_id: Optional[str] = None
    reference: Optional[str] = None


class InvoiceResponse(BaseModel):
    invoice_id: str
    organization_id: str
    merchant_name: Optional[str] = None
    amount: str
    amount_paid: str = "0.00"
    currency: str = "USDC"
    description: Optional[str] = None
    status: str = "pending"
    created_at: str
    paid_at: Optional[str] = None
    payer_agent_id: Optional[str] = None
    reference: Optional[str] = None


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    request: CreateInvoiceRequest,
    api_key: APIKey = Depends(require_api_key),
):
    """Create a new invoice."""
    invoice_id = f"inv_{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    await Database.execute(
        """
        INSERT INTO invoices (
            invoice_id, organization_id, merchant_name, amount, amount_paid,
            currency, description, status, payer_agent_id, reference, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
        invoice_id,
        api_key.organization_id,
        request.merchant_name,
        request.amount,
        "0.00",
        request.currency,
        request.description,
        "pending",
        request.payer_agent_id,
        request.reference,
        now,
    )

    return InvoiceResponse(
        invoice_id=invoice_id,
        organization_id=api_key.organization_id,
        merchant_name=request.merchant_name,
        amount=request.amount,
        amount_paid="0.00",
        currency=request.currency,
        description=request.description,
        status="pending",
        created_at=now.isoformat(),
        payer_agent_id=request.payer_agent_id,
        reference=request.reference,
    )


@router.get("", response_model=List[InvoiceResponse])
async def list_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    api_key: APIKey = Depends(require_api_key),
):
    """List invoices for the authenticated organization."""
    conditions = ["organization_id = $1"]
    args: list = [api_key.organization_id]
    idx = 2

    if status_filter:
        conditions.append(f"status = ${idx}")
        args.append(status_filter)
        idx += 1

    where = " AND ".join(conditions)
    args.extend([limit, offset])

    rows = await Database.fetch(
        f"SELECT * FROM invoices WHERE {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
        *args,
    )

    return [
        InvoiceResponse(
            invoice_id=r["invoice_id"],
            organization_id=r["organization_id"],
            merchant_name=r.get("merchant_name"),
            amount=r["amount"],
            amount_paid=r.get("amount_paid", "0.00"),
            currency=r["currency"],
            description=r.get("description"),
            status=r["status"],
            created_at=r["created_at"].isoformat() if r["created_at"] else "",
            paid_at=r["paid_at"].isoformat() if r.get("paid_at") else None,
            payer_agent_id=r.get("payer_agent_id"),
            reference=r.get("reference"),
        )
        for r in rows
    ]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    api_key: APIKey = Depends(require_api_key),
):
    """Get invoice details."""
    row = await Database.fetchrow(
        "SELECT * FROM invoices WHERE invoice_id = $1 AND organization_id = $2",
        invoice_id,
        api_key.organization_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return InvoiceResponse(
        invoice_id=row["invoice_id"],
        organization_id=row["organization_id"],
        merchant_name=row.get("merchant_name"),
        amount=row["amount"],
        amount_paid=row.get("amount_paid", "0.00"),
        currency=row["currency"],
        description=row.get("description"),
        status=row["status"],
        created_at=row["created_at"].isoformat() if row["created_at"] else "",
        paid_at=row["paid_at"].isoformat() if row.get("paid_at") else None,
        payer_agent_id=row.get("payer_agent_id"),
        reference=row.get("reference"),
    )


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice_status(
    invoice_id: str,
    status_update: str = Query(..., alias="status"),
    api_key: APIKey = Depends(require_api_key),
):
    """Update invoice status (e.g., cancel)."""
    valid_statuses = {"pending", "paid", "partial", "cancelled", "overdue"}
    if status_update not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    row = await Database.fetchrow(
        "SELECT * FROM invoices WHERE invoice_id = $1 AND organization_id = $2",
        invoice_id,
        api_key.organization_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")

    now = datetime.now(timezone.utc)
    paid_at = now if status_update == "paid" else row.get("paid_at")

    await Database.execute(
        "UPDATE invoices SET status = $1, paid_at = $2, updated_at = $3 WHERE invoice_id = $4",
        status_update,
        paid_at,
        now,
        invoice_id,
    )

    return InvoiceResponse(
        invoice_id=row["invoice_id"],
        organization_id=row["organization_id"],
        merchant_name=row.get("merchant_name"),
        amount=row["amount"],
        amount_paid=row.get("amount_paid", "0.00"),
        currency=row["currency"],
        description=row.get("description"),
        status=status_update,
        created_at=row["created_at"].isoformat() if row["created_at"] else "",
        paid_at=paid_at.isoformat() if paid_at else None,
        payer_agent_id=row.get("payer_agent_id"),
        reference=row.get("reference"),
    )
