"""Invoice management API endpoints."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sardis_v2_core.database import Database

from server.middleware.auth import APIKey, require_api_key

router = APIRouter()

SORTABLE_COLUMNS: frozenset[str] = frozenset({"created_at", "paid_at", "status", "amount"})


def _validate_sort_column(col: str) -> str:
    if col not in SORTABLE_COLUMNS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sort column: {col}")
    return col


# Request/Response Models
class CreateInvoiceRequest(BaseModel):
    amount: str = Field(..., pattern=r'^\d+(\.\d{1,18})?$', description="Payment amount as decimal string")
    currency: str = "USDC"
    description: str | None = None
    merchant_name: str | None = None
    payer_agent_id: str | None = None
    reference: str | None = None

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: str) -> str:
        from decimal import Decimal, InvalidOperation

        try:
            d = Decimal(v)
            if d <= 0:
                raise ValueError("Amount must be positive")
            return v
        except InvalidOperation:
            raise ValueError("Invalid amount format")


class InvoiceResponse(BaseModel):
    invoice_id: str
    organization_id: str
    merchant_name: str | None = None
    amount: str
    amount_paid: str = "0.00"
    currency: str = "USDC"
    description: str | None = None
    status: str = "pending"
    created_at: str
    paid_at: str | None = None
    payer_agent_id: str | None = None
    reference: str | None = None


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    request: CreateInvoiceRequest,
    api_key: APIKey = Depends(require_api_key),
):
    """Create a new invoice."""
    invoice_id = f"inv_{uuid4().hex[:12]}"
    now = datetime.now(UTC)

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


@router.get("", response_model=list[InvoiceResponse])
async def list_invoices(
    status_filter: str | None = Query(None, alias="status"),
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

    sort_col = _validate_sort_column("created_at")
    rows = await Database.fetch(
        f"SELECT * FROM invoices WHERE {where} ORDER BY {sort_col} DESC LIMIT ${idx} OFFSET ${idx + 1}",
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

    now = datetime.now(UTC)
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


async def reconcile_invoice_with_deposit(
    invoice_id: str,
    amount_paid: str,
    deposit_id: str,
) -> bool:
    """Reconcile an invoice with a confirmed inbound deposit.

    Called by InboundPaymentService when a deposit matches a payment request
    linked to an invoice. Updates invoice status from pending → paid/partial.
    """
    row = await Database.fetchrow(
        "SELECT invoice_id, amount, status FROM invoices WHERE invoice_id = $1",
        invoice_id,
    )
    if not row:
        return False

    if row["status"] == "paid":
        return True  # Already reconciled

    now = datetime.now(UTC)
    invoice_amount = Decimal(row["amount"])
    paid_amount = Decimal(amount_paid)

    new_status = "paid" if paid_amount >= invoice_amount else "partial"

    await Database.execute(
        """
        UPDATE invoices SET
            status = $2,
            amount_paid = $3,
            paid_at = $4,
            updated_at = $5
        WHERE invoice_id = $1
        """,
        invoice_id,
        new_status,
        amount_paid,
        now if new_status == "paid" else None,
        now,
    )
    return True
