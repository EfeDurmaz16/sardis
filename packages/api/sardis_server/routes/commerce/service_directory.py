"""Agent Service Directory — discoverable merchant API registry.

Agents search this directory to find APIs they can pay for.
sardis-connect merchants auto-register their endpoints here.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("sardis_server.api.service_directory")

# Public router — no auth required for discovery
router = APIRouter(prefix="/api/v2/directory", tags=["service-directory"])


class ServiceEntry(BaseModel):
    """A service in the directory."""
    service_id: str
    merchant_id: str
    service_name: str
    description: str | None = None
    base_url: str
    category: str | None = None
    pricing_model: str = "per_call"
    min_price: str | None = None
    currency: str = "USD"
    accepts: list[str] = Field(default_factory=list)
    endpoints: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    verified: bool = False


class DirectoryResponse(BaseModel):
    """Search results from the directory."""
    services: list[ServiceEntry]
    total: int
    page: int
    page_size: int


class RegisterServiceRequest(BaseModel):
    """Register a service in the directory (auto-called by sardis-connect)."""
    service_name: str = Field(..., max_length=255)
    description: str | None = None
    base_url: str
    category: str | None = None
    pricing_model: str = "per_call"
    min_price: str | None = None
    currency: str = "USD"
    endpoints: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


@router.get("", response_model=DirectoryResponse)
async def search_directory(
    q: str | None = Query(default=None, description="Search query (name, description, tags)"),
    category: str | None = Query(default=None, description="Filter by category (ai, compute, data, etc.)"),
    pricing: str | None = Query(default=None, description="Filter by pricing model (per_call, per_unit)"),
    max_price: float | None = Query(default=None, description="Maximum price per unit/call"),
    protocol: str | None = Query(default=None, description="Filter by accepted protocol (sardis, x402, mpp)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Search the agent service directory.

    Agents call this to discover APIs they can pay for.
    Supports filtering by category, pricing, and protocol.

    Example:
        GET /api/v2/directory?category=ai&max_price=0.01
        GET /api/v2/directory?q=text+generation&protocol=mpp
    """
    from sardis_v2_core.database import Database

    conditions = ["s.is_active = TRUE"]
    params: list[Any] = []
    idx = 1

    if q:
        conditions.append(f"(s.service_name ILIKE ${idx} OR s.description ILIKE ${idx} OR ${idx} = ANY(s.tags))")
        params.append(f"%{q}%")
        idx += 1

    if category:
        conditions.append(f"s.category = ${idx}")
        params.append(category)
        idx += 1

    if pricing:
        conditions.append(f"s.pricing_model = ${idx}")
        params.append(pricing)
        idx += 1

    if max_price is not None:
        conditions.append(f"s.min_price <= ${idx}")
        params.append(max_price)
        idx += 1

    if protocol:
        conditions.append(f"s.accepts @> ${idx}::jsonb")
        params.append(f'["{protocol}"]')
        idx += 1

    where = " AND ".join(conditions)
    offset = (page - 1) * page_size

    # Count
    count_row = await Database.fetchrow(
        f"SELECT COUNT(*) as total FROM service_directory s WHERE {where}",
        *params,
    )
    total = count_row["total"] if count_row else 0

    # Fetch
    params.extend([page_size, offset])
    rows = await Database.fetch(
        f"""
        SELECT s.id, m.external_id as merchant_id, s.service_name, s.description,
            s.base_url, s.category, s.pricing_model, s.min_price, s.currency,
            s.accepts, s.endpoints, s.tags, s.verified
        FROM service_directory s
        JOIN merchants m ON m.id = s.merchant_id
        WHERE {where}
        ORDER BY s.verified DESC, s.created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
    )

    services = [
        ServiceEntry(
            service_id=str(r["id"]),
            merchant_id=r["merchant_id"],
            service_name=r["service_name"],
            description=r.get("description"),
            base_url=r["base_url"],
            category=r.get("category"),
            pricing_model=r.get("pricing_model", "per_call"),
            min_price=str(r["min_price"]) if r.get("min_price") else None,
            currency=r.get("currency", "USD"),
            accepts=r.get("accepts", []),
            endpoints=r.get("endpoints", []),
            tags=list(r.get("tags", [])),
            verified=r.get("verified", False),
        )
        for r in rows
    ]

    return DirectoryResponse(
        services=services,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ServiceEntry, status_code=201)
async def register_service(body: RegisterServiceRequest):
    """Register a service in the directory.

    Called automatically by sardis-connect when a merchant starts their server.
    Can also be called manually via the API.
    """
    import json
    import uuid

    from sardis_v2_core.database import Database

    service_id = str(uuid.uuid4())

    await Database.execute(
        """
        INSERT INTO service_directory
            (id, merchant_id, service_name, description, base_url, category,
             pricing_model, min_price, currency, endpoints, tags)
        VALUES ($1,
            (SELECT id FROM merchants WHERE external_id = $2 LIMIT 1),
            $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11)
        ON CONFLICT (id) DO NOTHING
        """,
        service_id,
        body.base_url,  # fallback merchant lookup
        body.service_name,
        body.description,
        body.base_url,
        body.category,
        body.pricing_model,
        float(body.min_price) if body.min_price else None,
        body.currency,
        json.dumps(body.endpoints),
        body.tags,
    )

    return ServiceEntry(
        service_id=service_id,
        merchant_id="",
        service_name=body.service_name,
        description=body.description,
        base_url=body.base_url,
        category=body.category,
        pricing_model=body.pricing_model,
        min_price=body.min_price,
        currency=body.currency,
        endpoints=body.endpoints,
        tags=body.tags,
    )
