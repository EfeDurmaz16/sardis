"""Mandate Delegation API endpoints.

Hierarchical mandate trees — parent mandates delegate to children
with inherited, narrowing bounds.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class DelegateRequest(BaseModel):
    agent_id: str | None = Field(default=None, description="Agent to delegate to")
    purpose_scope: str | None = Field(default=None, description="Narrowed purpose")
    amount_per_tx: Decimal | None = Field(default=None, gt=0)
    amount_daily: Decimal | None = Field(default=None, gt=0)
    amount_weekly: Decimal | None = Field(default=None, gt=0)
    amount_monthly: Decimal | None = Field(default=None, gt=0)
    amount_total: Decimal | None = Field(default=None, gt=0)
    merchant_scope: dict | None = None
    allowed_rails: list[str] | None = None
    allowed_chains: list[str] | None = None
    allowed_tokens: list[str] | None = None
    expires_at: str | None = None
    approval_mode: str = Field(default="auto", pattern="^(auto|threshold|always_human)$")
    approval_threshold: Decimal | None = None
    metadata: dict | None = None


class MandateNodeResponse(BaseModel):
    id: str
    parent_mandate_id: str | None
    agent_id: str | None
    principal_id: str
    purpose_scope: str | None
    amount_per_tx: str | None
    amount_total: str | None
    spent_total: str
    status: str
    delegation_depth: int
    children: list[MandateNodeResponse] = []
    created_at: str


class DelegationResponse(BaseModel):
    child_mandate_id: str
    parent_mandate_id: str
    delegation_depth: int
    status: str
    created_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/mandates/{mandate_id}/delegate",
    response_model=DelegationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a child mandate via delegation",
)
async def delegate_mandate(
    mandate_id: str,
    req: DelegateRequest,
    principal: Principal = Depends(require_principal),
) -> DelegationResponse:
    """Delegate a spending mandate to a child with narrowed bounds."""
    from sardis_v2_core.database import Database
    from sardis_v2_core.mandate_tree import MandateTreeValidator
    from sardis_v2_core.spending_mandate import ApprovalMode, MandateStatus, SpendingMandate

    # Fetch parent
    parent_row = await Database.fetchrow(
        "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2",
        mandate_id, principal.org_id,
    )
    if not parent_row:
        raise HTTPException(status_code=404, detail="Parent mandate not found")

    # Reconstruct parent as SpendingMandate
    parent = SpendingMandate(
        principal_id=parent_row["principal_id"],
        issuer_id=parent_row["issuer_id"],
        org_id=parent_row["org_id"],
        agent_id=parent_row.get("agent_id"),
        wallet_id=parent_row.get("wallet_id"),
        id=parent_row["id"],
        merchant_scope=parent_row.get("merchant_scope") or {},
        purpose_scope=parent_row.get("purpose_scope"),
        amount_per_tx=parent_row.get("amount_per_tx"),
        amount_daily=parent_row.get("amount_daily"),
        amount_weekly=parent_row.get("amount_weekly"),
        amount_monthly=parent_row.get("amount_monthly"),
        amount_total=parent_row.get("amount_total"),
        currency=parent_row.get("currency", "USDC"),
        spent_total=parent_row.get("spent_total") or Decimal("0"),
        allowed_rails=parent_row.get("allowed_rails") or ["card", "usdc", "bank"],
        allowed_chains=parent_row.get("allowed_chains"),
        allowed_tokens=parent_row.get("allowed_tokens"),
        expires_at=parent_row.get("expires_at"),
        approval_threshold=parent_row.get("approval_threshold"),
        approval_mode=ApprovalMode(parent_row.get("approval_mode", "auto")),
        status=MandateStatus(parent_row.get("status", "active")),
    )
    parent.delegation_depth = parent_row.get("delegation_depth") or 0

    # Build child
    child_id = f"mandate_{uuid4().hex[:12]}"
    expires_at = None
    if req.expires_at:
        expires_at = datetime.fromisoformat(req.expires_at)

    child = SpendingMandate(
        principal_id=principal.principal_id,
        issuer_id=principal.principal_id,
        org_id=principal.org_id,
        agent_id=req.agent_id,
        id=child_id,
        merchant_scope=req.merchant_scope or parent.merchant_scope,
        purpose_scope=req.purpose_scope or parent.purpose_scope,
        amount_per_tx=req.amount_per_tx or parent.amount_per_tx,
        amount_daily=req.amount_daily or parent.amount_daily,
        amount_weekly=req.amount_weekly or parent.amount_weekly,
        amount_monthly=req.amount_monthly or parent.amount_monthly,
        amount_total=req.amount_total or parent.amount_total,
        currency=parent.currency,
        allowed_rails=req.allowed_rails or parent.allowed_rails,
        allowed_chains=req.allowed_chains or parent.allowed_chains,
        allowed_tokens=req.allowed_tokens or parent.allowed_tokens,
        expires_at=expires_at or parent.expires_at,
        approval_threshold=req.approval_threshold or parent.approval_threshold,
        approval_mode=ApprovalMode(req.approval_mode),
    )

    # Validate delegation
    validator = MandateTreeValidator()
    result = validator.validate_delegation(parent, child)
    if not result.valid:
        raise HTTPException(
            status_code=422,
            detail={
                "message": result.reason,
                "error_code": result.error_code,
                "violations": result.violations,
            },
        )

    depth = parent.delegation_depth + 1
    root_id = parent_row.get("root_mandate_id") or parent.id

    # Persist
    await Database.execute(
        """INSERT INTO spending_mandates
           (id, org_id, agent_id, principal_id, issuer_id,
            merchant_scope, purpose_scope,
            amount_per_tx, amount_daily, amount_weekly, amount_monthly, amount_total,
            currency, allowed_rails, allowed_chains, allowed_tokens,
            expires_at, approval_threshold, approval_mode, status,
            parent_mandate_id, delegation_depth, root_mandate_id, metadata)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24)""",
        child_id, principal.org_id, req.agent_id, principal.principal_id,
        principal.principal_id,
        child.merchant_scope, child.purpose_scope,
        child.amount_per_tx, child.amount_daily, child.amount_weekly,
        child.amount_monthly, child.amount_total,
        child.currency, child.allowed_rails, child.allowed_chains,
        child.allowed_tokens,
        child.expires_at, child.approval_threshold, req.approval_mode,
        "active", mandate_id, depth, root_id, req.metadata or {},
    )

    logger.info("Delegated mandate %s → %s (depth %d)", mandate_id, child_id, depth)

    return DelegationResponse(
        child_mandate_id=child_id,
        parent_mandate_id=mandate_id,
        delegation_depth=depth,
        status="active",
        created_at=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/mandates/{mandate_id}/tree",
    response_model=MandateNodeResponse,
    summary="Get the delegation tree for a mandate",
)
async def get_mandate_tree(
    mandate_id: str,
    principal: Principal = Depends(require_principal),
) -> MandateNodeResponse:
    """Get the full delegation tree rooted at this mandate."""
    from sardis_v2_core.database import Database

    # Find the root
    root_row = await Database.fetchrow(
        "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2",
        mandate_id, principal.org_id,
    )
    if not root_row:
        raise HTTPException(status_code=404, detail="Mandate not found")

    # Fetch all descendants
    root_id = root_row.get("root_mandate_id") or mandate_id
    all_rows = await Database.fetch(
        """SELECT * FROM spending_mandates
           WHERE (root_mandate_id = $1 OR id = $1) AND org_id = $2
           ORDER BY delegation_depth ASC, created_at ASC""",
        root_id, principal.org_id,
    )

    # Build tree
    nodes: dict[str, MandateNodeResponse] = {}
    for row in all_rows:
        node = MandateNodeResponse(
            id=row["id"],
            parent_mandate_id=row.get("parent_mandate_id"),
            agent_id=row.get("agent_id"),
            principal_id=row["principal_id"],
            purpose_scope=row.get("purpose_scope"),
            amount_per_tx=str(row["amount_per_tx"]) if row.get("amount_per_tx") else None,
            amount_total=str(row["amount_total"]) if row.get("amount_total") else None,
            spent_total=str(row.get("spent_total") or 0),
            status=row["status"],
            delegation_depth=row.get("delegation_depth") or 0,
            created_at=row["created_at"].isoformat(),
        )
        nodes[row["id"]] = node

    # Wire parent → children
    for node in nodes.values():
        if node.parent_mandate_id and node.parent_mandate_id in nodes:
            nodes[node.parent_mandate_id].children.append(node)

    root_node = nodes.get(mandate_id)
    if not root_node:
        raise HTTPException(status_code=404, detail="Mandate not in tree")

    return root_node
