"""Funding API endpoints.

UTXO-style funding commitments and cells for the Sardis payment protocol.
Funding cells are discrete, reserve-backed units that back payment objects.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class CreateCommitmentRequest(BaseModel):
    vault_ref: str = Field(..., description="On-chain vault or wallet reference")
    total_value: Decimal = Field(..., gt=0, description="Total value to commit")
    currency: str = Field(default="USDC")
    cell_strategy: str = Field(default="fixed", pattern="^(fixed|proportional)$")
    cell_denomination: Decimal | None = Field(
        default=None, gt=0,
        description="Fixed cell denomination (required for 'fixed' strategy)",
    )
    settlement_preferences: dict | None = None
    expires_in_seconds: int | None = Field(default=None, ge=3600, description="TTL in seconds")
    metadata: dict | None = None


class CommitmentResponse(BaseModel):
    commitment_id: str
    org_id: str
    vault_ref: str
    total_value: str
    remaining_value: str
    currency: str
    cell_strategy: str
    cell_denomination: str | None
    cell_count: int
    status: str
    expires_at: str | None
    created_at: str
    metadata: dict


class CellResponse(BaseModel):
    cell_id: str
    commitment_id: str
    value: str
    currency: str
    status: str
    owner_mandate_id: str | None
    payment_object_id: str | None
    claimed_at: str | None
    spent_at: str | None
    created_at: str


class CellListResponse(BaseModel):
    cells: list[CellResponse]
    total: int
    offset: int
    limit: int


class SplitCellRequest(BaseModel):
    amounts: list[Decimal] = Field(..., min_length=2, description="Split into these amounts")


class MergeCellsRequest(BaseModel):
    cell_ids: list[str] = Field(..., min_length=2, description="Cell IDs to merge")


# ---------------------------------------------------------------------------
# Commitment Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/funding/commit",
    response_model=CommitmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a funding commitment",
)
async def create_commitment(
    req: CreateCommitmentRequest,
    principal: Principal = Depends(require_principal),
) -> CommitmentResponse:
    """Create a funding commitment and mint initial funding cells."""
    from sardis_v2_core.database import Database

    if req.cell_strategy == "fixed" and req.cell_denomination is None:
        raise HTTPException(
            status_code=422,
            detail="cell_denomination required for 'fixed' strategy",
        )

    commitment_id = f"fcom_{uuid4().hex[:12]}"
    expires_at = None
    if req.expires_in_seconds:
        expires_at = datetime.now(UTC) + timedelta(seconds=req.expires_in_seconds)

    async with Database.transaction() as conn:
        # Create commitment
        await conn.execute(
            """INSERT INTO funding_commitments
               (commitment_id, org_id, vault_ref, total_value, remaining_value,
                currency, cell_strategy, cell_denomination, settlement_preferences,
                status, expires_at, metadata)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)""",
            commitment_id, principal.org_id, req.vault_ref,
            req.total_value, req.total_value, req.currency,
            req.cell_strategy, req.cell_denomination,
            req.settlement_preferences or {},
            "active", expires_at, req.metadata or {},
        )

        # Mint funding cells
        cell_count = 0
        if req.cell_strategy == "fixed" and req.cell_denomination:
            remaining = req.total_value
            while remaining > 0:
                cell_value = min(req.cell_denomination, remaining)
                cell_id = f"cell_{uuid4().hex[:12]}"
                await conn.execute(
                    """INSERT INTO funding_cells
                       (cell_id, commitment_id, value, currency, status)
                       VALUES ($1,$2,$3,$4,'available')""",
                    cell_id, commitment_id, cell_value, req.currency,
                )
                remaining -= cell_value
                cell_count += 1
        else:
            # Proportional: create a single cell with the full amount
            cell_id = f"cell_{uuid4().hex[:12]}"
            await conn.execute(
                """INSERT INTO funding_cells
                   (cell_id, commitment_id, value, currency, status)
                   VALUES ($1,$2,$3,$4,'available')""",
                cell_id, commitment_id, req.total_value, req.currency,
            )
            cell_count = 1

    logger.info(
        "Created commitment %s with %d cells totaling %s %s",
        commitment_id, cell_count, req.total_value, req.currency,
    )

    return CommitmentResponse(
        commitment_id=commitment_id,
        org_id=principal.org_id,
        vault_ref=req.vault_ref,
        total_value=str(req.total_value),
        remaining_value=str(req.total_value),
        currency=req.currency,
        cell_strategy=req.cell_strategy,
        cell_denomination=str(req.cell_denomination) if req.cell_denomination else None,
        cell_count=cell_count,
        status="active",
        expires_at=expires_at.isoformat() if expires_at else None,
        created_at=datetime.now(UTC).isoformat(),
        metadata=req.metadata or {},
    )


@router.get(
    "/funding/commitments",
    response_model=list[CommitmentResponse],
    summary="List funding commitments",
)
async def list_commitments(
    principal: Principal = Depends(require_principal),
    commitment_status: str | None = Query(default=None, alias="status"),
) -> list[CommitmentResponse]:
    from sardis_v2_core.database import Database

    if commitment_status:
        rows = await Database.fetch(
            """SELECT c.*, COUNT(f.cell_id) as cell_count
               FROM funding_commitments c
               LEFT JOIN funding_cells f ON f.commitment_id = c.commitment_id
               WHERE c.org_id = $1 AND c.status = $2
               GROUP BY c.commitment_id
               ORDER BY c.created_at DESC""",
            principal.org_id, commitment_status,
        )
    else:
        rows = await Database.fetch(
            """SELECT c.*, COUNT(f.cell_id) as cell_count
               FROM funding_commitments c
               LEFT JOIN funding_cells f ON f.commitment_id = c.commitment_id
               WHERE c.org_id = $1
               GROUP BY c.commitment_id
               ORDER BY c.created_at DESC""",
            principal.org_id,
        )

    return [_commitment_row_to_response(r) for r in rows]


# ---------------------------------------------------------------------------
# Cell Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/funding/cells",
    response_model=CellListResponse,
    summary="List funding cells",
)
async def list_cells(
    principal: Principal = Depends(require_principal),
    commitment_id: str | None = Query(default=None),
    cell_status: str | None = Query(default=None, alias="status"),
    currency: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> CellListResponse:
    from sardis_v2_core.database import Database

    conditions = ["c.org_id = $1"]
    params: list = [principal.org_id]
    idx = 2

    if commitment_id:
        conditions.append(f"f.commitment_id = ${idx}")
        params.append(commitment_id)
        idx += 1
    if cell_status:
        conditions.append(f"f.status = ${idx}")
        params.append(cell_status)
        idx += 1
    if currency:
        conditions.append(f"f.currency = ${idx}")
        params.append(currency)
        idx += 1

    where = " AND ".join(conditions)

    count = await Database.fetchval(
        f"""SELECT COUNT(*) FROM funding_cells f
            JOIN funding_commitments c ON c.commitment_id = f.commitment_id
            WHERE {where}""",
        *params,
    )
    rows = await Database.fetch(
        f"""SELECT f.* FROM funding_cells f
            JOIN funding_commitments c ON c.commitment_id = f.commitment_id
            WHERE {where}
            ORDER BY f.created_at DESC LIMIT ${idx} OFFSET ${idx + 1}""",
        *params, limit, offset,
    )

    return CellListResponse(
        cells=[_cell_row_to_response(r) for r in rows],
        total=count,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/funding/cells/{cell_id}/split",
    response_model=list[CellResponse],
    summary="Split a funding cell into smaller cells",
)
async def split_cell(
    cell_id: str,
    req: SplitCellRequest,
    principal: Principal = Depends(require_principal),
) -> list[CellResponse]:
    from sardis_v2_core.database import Database

    async with Database.transaction() as conn:
        row = await conn.fetchrow(
            """SELECT f.* FROM funding_cells f
               JOIN funding_commitments c ON c.commitment_id = f.commitment_id
               WHERE f.cell_id = $1 AND c.org_id = $2
               FOR UPDATE NOWAIT""",
            cell_id, principal.org_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Cell not found")
        if row["status"] != "available":
            raise HTTPException(status_code=409, detail=f"Cell is {row['status']}, must be available")

        total_split = sum(req.amounts)
        if total_split != row["value"]:
            raise HTTPException(
                status_code=422,
                detail=f"Split amounts ({total_split}) must equal cell value ({row['value']})",
            )

        # Mark original as merged
        await conn.execute(
            "UPDATE funding_cells SET status = 'merged', updated_at = now() WHERE cell_id = $1",
            cell_id,
        )

        # Create new cells
        new_cells = []
        for amount in req.amounts:
            new_id = f"cell_{uuid4().hex[:12]}"
            await conn.execute(
                """INSERT INTO funding_cells
                   (cell_id, commitment_id, value, currency, status)
                   VALUES ($1,$2,$3,$4,'available')""",
                new_id, row["commitment_id"], amount, row["currency"],
            )
            new_cells.append({
                "cell_id": new_id,
                "commitment_id": row["commitment_id"],
                "value": amount,
                "currency": row["currency"],
                "status": "available",
                "owner_mandate_id": None,
                "payment_object_id": None,
                "claimed_at": None,
                "spent_at": None,
                "created_at": datetime.now(UTC),
            })

    return [_cell_dict_to_response(c) for c in new_cells]


@router.post(
    "/funding/cells/merge",
    response_model=CellResponse,
    summary="Merge multiple funding cells into one",
)
async def merge_cells(
    req: MergeCellsRequest,
    principal: Principal = Depends(require_principal),
) -> CellResponse:
    from sardis_v2_core.database import Database

    async with Database.transaction() as conn:
        rows = await conn.fetch(
            """SELECT f.* FROM funding_cells f
               JOIN funding_commitments c ON c.commitment_id = f.commitment_id
               WHERE f.cell_id = ANY($1) AND c.org_id = $2
               FOR UPDATE NOWAIT""",
            req.cell_ids, principal.org_id,
        )
        if len(rows) != len(req.cell_ids):
            raise HTTPException(status_code=404, detail="One or more cells not found")

        # Validate all available and same currency/commitment
        currencies = {r["currency"] for r in rows}
        commitments = {r["commitment_id"] for r in rows}
        statuses = {r["status"] for r in rows}

        if statuses != {"available"}:
            raise HTTPException(status_code=409, detail="All cells must be available")
        if len(currencies) > 1:
            raise HTTPException(status_code=422, detail="All cells must have the same currency")
        if len(commitments) > 1:
            raise HTTPException(status_code=422, detail="All cells must be from the same commitment")

        total_value = sum(r["value"] for r in rows)
        commitment_id = rows[0]["commitment_id"]
        currency = rows[0]["currency"]

        # Mark originals as merged
        await conn.execute(
            "UPDATE funding_cells SET status = 'merged', updated_at = now() WHERE cell_id = ANY($1)",
            req.cell_ids,
        )

        # Create merged cell
        new_id = f"cell_{uuid4().hex[:12]}"
        await conn.execute(
            """INSERT INTO funding_cells
               (cell_id, commitment_id, value, currency, status)
               VALUES ($1,$2,$3,$4,'available')""",
            new_id, commitment_id, total_value, currency,
        )

    return CellResponse(
        cell_id=new_id,
        commitment_id=commitment_id,
        value=str(total_value),
        currency=currency,
        status="available",
        owner_mandate_id=None,
        payment_object_id=None,
        claimed_at=None,
        spent_at=None,
        created_at=datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _commitment_row_to_response(row) -> CommitmentResponse:
    return CommitmentResponse(
        commitment_id=row["commitment_id"],
        org_id=row["org_id"],
        vault_ref=row["vault_ref"],
        total_value=str(row["total_value"]),
        remaining_value=str(row["remaining_value"]),
        currency=row["currency"],
        cell_strategy=row["cell_strategy"],
        cell_denomination=str(row["cell_denomination"]) if row.get("cell_denomination") else None,
        cell_count=row.get("cell_count", 0),
        status=row["status"],
        expires_at=row["expires_at"].isoformat() if row.get("expires_at") else None,
        created_at=row["created_at"].isoformat(),
        metadata=row["metadata"] or {},
    )


def _cell_row_to_response(row) -> CellResponse:
    return CellResponse(
        cell_id=row["cell_id"],
        commitment_id=row["commitment_id"],
        value=str(row["value"]),
        currency=row["currency"],
        status=row["status"],
        owner_mandate_id=row.get("owner_mandate_id"),
        payment_object_id=row.get("payment_object_id"),
        claimed_at=row["claimed_at"].isoformat() if row.get("claimed_at") else None,
        spent_at=row["spent_at"].isoformat() if row.get("spent_at") else None,
        created_at=row["created_at"].isoformat(),
    )


def _cell_dict_to_response(d: dict) -> CellResponse:
    return CellResponse(
        cell_id=d["cell_id"],
        commitment_id=d["commitment_id"],
        value=str(d["value"]),
        currency=d["currency"],
        status=d["status"],
        owner_mandate_id=d.get("owner_mandate_id"),
        payment_object_id=d.get("payment_object_id"),
        claimed_at=d["claimed_at"].isoformat() if d.get("claimed_at") else None,
        spent_at=d["spent_at"].isoformat() if d.get("spent_at") else None,
        created_at=d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else d["created_at"],
    )
