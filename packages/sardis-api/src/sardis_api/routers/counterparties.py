"""Trusted counterparties — approved vendors, merchants, and agent peers.

Provides a registry of known counterparties that policies can reference
by name instead of raw addresses.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_principal)])

# In-memory store (replace with DB)
_counterparties: dict[str, dict] = {}


class CounterpartyCreate(BaseModel):
    name: str = Field(..., description="Display name")
    type: str = Field(default="merchant", description="merchant, vendor, agent, service")
    identifier: str = Field(..., description="Wallet address, domain, or agent ID")
    category: str | None = Field(default=None, description="E.g., cloud, api, saas, travel")
    trust_status: str = Field(default="pending", description="pending, approved, blocked")
    approval_required: bool = Field(default=False, description="Require approval for payments to this counterparty")
    metadata: dict | None = Field(default=None)


class CounterpartyResponse(BaseModel):
    id: str
    name: str
    type: str
    identifier: str
    category: str | None = None
    trust_status: str
    approval_required: bool
    metadata: dict = {}
    created_at: str
    updated_at: str


class CounterpartyUpdate(BaseModel):
    name: str | None = None
    trust_status: str | None = None
    approval_required: bool | None = None
    category: str | None = None
    metadata: dict | None = None


class TrustProfileResponse(BaseModel):
    counterparty_id: str
    name: str
    trust_score: float  # 0.0 - 1.0
    policy_compatible: bool
    proof_status: str  # "verified", "partial", "none"
    settlement_preference: str  # "usdc", "card", "bank"
    total_transactions: int
    total_volume: str
    success_rate: float
    avg_settlement_time: str
    last_transaction: str | None = None
    flags: list[str] = []  # e.g., ["new_merchant", "high_volume"]


@router.post("/", response_model=CounterpartyResponse, status_code=201)
async def create_counterparty(body: CounterpartyCreate, principal: Principal = Depends(require_principal)):
    cpty_id = f"cpty_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()
    record = {
        "id": cpty_id,
        "name": body.name,
        "type": body.type,
        "identifier": body.identifier,
        "category": body.category,
        "trust_status": body.trust_status,
        "approval_required": body.approval_required,
        "metadata": body.metadata or {},
        "created_at": now,
        "updated_at": now,
    }
    _counterparties[cpty_id] = record
    logger.info("Created counterparty id=%s name=%s type=%s", cpty_id, body.name, body.type)
    return CounterpartyResponse(**record)


@router.get("/", response_model=list[CounterpartyResponse])
async def list_counterparties(
    type: str | None = Query(default=None),
    trust_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    results = list(_counterparties.values())
    if type:
        results = [c for c in results if c["type"] == type]
    if trust_status:
        results = [c for c in results if c["trust_status"] == trust_status]
    return [CounterpartyResponse(**c) for c in results[:limit]]


@router.get("/{cpty_id}", response_model=CounterpartyResponse)
async def get_counterparty(cpty_id: str):
    if cpty_id not in _counterparties:
        raise HTTPException(status_code=404, detail=f"Counterparty {cpty_id} not found")
    return CounterpartyResponse(**_counterparties[cpty_id])


@router.patch("/{cpty_id}", response_model=CounterpartyResponse)
async def update_counterparty(cpty_id: str, body: CounterpartyUpdate):
    if cpty_id not in _counterparties:
        raise HTTPException(status_code=404, detail=f"Counterparty {cpty_id} not found")
    record = _counterparties[cpty_id]
    for field, value in body.model_dump(exclude_unset=True).items():
        record[field] = value
    record["updated_at"] = datetime.now(UTC).isoformat()
    logger.info("Updated counterparty id=%s", cpty_id)
    return CounterpartyResponse(**record)


@router.get("/{cpty_id}/trust-profile", response_model=TrustProfileResponse)
async def get_trust_profile(cpty_id: str):
    """Get trust profile for a counterparty including reliability and policy compatibility."""
    if cpty_id not in _counterparties:
        raise HTTPException(status_code=404, detail=f"Counterparty {cpty_id} not found")

    cpty = _counterparties[cpty_id]
    trust_status = cpty.get("trust_status", "pending")

    # Derive mock trust score from trust_status
    if trust_status == "approved":
        trust_score = 0.85
        policy_compatible = True
        proof_status = "verified"
        flags: list[str] = []
    elif trust_status == "blocked":
        trust_score = 0.10
        policy_compatible = False
        proof_status = "none"
        flags = ["blocked"]
    else:
        trust_score = 0.50
        policy_compatible = True
        proof_status = "partial"
        flags = ["new_merchant"]

    # Derive settlement preference from category
    category = (cpty.get("category") or "").lower()
    if category in ("cloud", "api", "saas"):
        settlement_preference = "usdc"
    elif category in ("travel", "retail"):
        settlement_preference = "card"
    else:
        settlement_preference = "usdc"

    return TrustProfileResponse(
        counterparty_id=cpty_id,
        name=cpty["name"],
        trust_score=trust_score,
        policy_compatible=policy_compatible,
        proof_status=proof_status,
        settlement_preference=settlement_preference,
        total_transactions=0,
        total_volume="$0.00",
        success_rate=1.0 if trust_status == "approved" else 0.0,
        avg_settlement_time="< 1 min",
        last_transaction=None,
        flags=flags,
    )


@router.delete("/{cpty_id}", status_code=204)
async def delete_counterparty(cpty_id: str):
    if cpty_id not in _counterparties:
        raise HTTPException(status_code=404, detail=f"Counterparty {cpty_id} not found")
    del _counterparties[cpty_id]
    logger.info("Deleted counterparty id=%s", cpty_id)
