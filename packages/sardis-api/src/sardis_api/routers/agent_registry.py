"""Agent Identity Registry — public agent profiles for trust verification.

Agents register their identity, capabilities, and spending authority.
Merchants and other agents verify identity before transacting.

Implements concepts from:
- Amex ACE (agent registration)
- Visa ICC (agent identity)
- Mastercard Verifiable Intent
- Sardis KYA (Know Your Agent)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger("sardis.api.agent_registry")

# Public endpoints for lookup, auth-required for registration
router = APIRouter(prefix="/api/v2/agents/registry", tags=["agent-registry"])
public_router = APIRouter(prefix="/api/v2/agents/registry", tags=["agent-registry"])


class AgentRegistration(BaseModel):
    """Register an agent in the public registry."""
    name: str = Field(..., max_length=255)
    description: str | None = None
    capabilities: list[str] = Field(
        default_factory=list,
        description="What the agent can do: purchase, subscribe, transfer, browse, etc.",
    )
    max_authority: str | None = Field(
        default=None,
        description="Maximum spending authority (e.g., '$10000/month')",
    )
    supported_protocols: list[str] = Field(
        default_factory=lambda: ["sardis", "x402", "mpp"],
    )
    website: str | None = None
    contact_email: str | None = None


class AgentProfile(BaseModel):
    """Public agent profile."""
    agent_id: str
    name: str
    description: str | None = None
    principal_id: str | None = None
    org_id: str | None = None
    capabilities: list[str] = []
    max_authority: str | None = None
    supported_protocols: list[str] = []
    trust_score: float | None = None
    verified: bool = False
    kya_status: str = "unverified"
    total_transactions: int = 0
    registered_at: str | None = None


class RegistrySearchResponse(BaseModel):
    agents: list[AgentProfile]
    total: int


@router.post("", response_model=AgentProfile, status_code=201)
async def register_agent(
    body: AgentRegistration,
    principal: Principal = Depends(require_principal),
):
    """Register an agent in the public identity registry.

    Creates a public profile that merchants and other agents can verify.
    Combines with KYA (Know Your Agent) attestation for trust scoring.
    """

    from sardis_v2_core.database import Database

    agent_id = f"agent_{__import__('secrets').token_hex(12)}"

    await Database.execute(
        """
        INSERT INTO agent_registry
            (agent_id, name, description, principal_id, org_id,
             capabilities, max_authority, supported_protocols, website, contact_email)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (agent_id) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            capabilities = EXCLUDED.capabilities,
            max_authority = EXCLUDED.max_authority,
            supported_protocols = EXCLUDED.supported_protocols,
            updated_at = NOW()
        """,
        agent_id,
        body.name,
        body.description,
        principal.subject_id,
        principal.organization_id,
        body.capabilities,
        body.max_authority,
        body.supported_protocols,
        body.website,
        body.contact_email,
    )

    return AgentProfile(
        agent_id=agent_id,
        name=body.name,
        description=body.description,
        principal_id=principal.subject_id,
        org_id=principal.organization_id,
        capabilities=body.capabilities,
        max_authority=body.max_authority,
        supported_protocols=body.supported_protocols,
    )


@public_router.get("/{agent_id}", response_model=AgentProfile)
async def get_agent_profile(agent_id: str):
    """Get a public agent profile by ID.

    Merchants verify agent identity before accepting payments.
    No authentication required — profiles are public.
    """
    from sardis_v2_core.database import Database

    row = await Database.fetchrow(
        """
        SELECT agent_id, name, description, principal_id, org_id,
               capabilities, max_authority, supported_protocols,
               trust_score, verified, kya_status, total_transactions,
               created_at
        FROM agent_registry
        WHERE agent_id = $1
        """,
        agent_id,
    )

    if not row:
        raise HTTPException(status_code=404, detail="Agent not found in registry")

    return AgentProfile(
        agent_id=row["agent_id"],
        name=row["name"],
        description=row.get("description"),
        principal_id=row.get("principal_id"),
        org_id=row.get("org_id"),
        capabilities=list(row.get("capabilities", [])),
        max_authority=row.get("max_authority"),
        supported_protocols=list(row.get("supported_protocols", [])),
        trust_score=row.get("trust_score"),
        verified=row.get("verified", False),
        kya_status=row.get("kya_status", "unverified"),
        total_transactions=row.get("total_transactions", 0),
        registered_at=row["created_at"].isoformat() if row.get("created_at") else None,
    )


@public_router.get("", response_model=RegistrySearchResponse)
async def search_agents(
    q: str | None = Query(default=None, description="Search by name or description"),
    capability: str | None = Query(default=None, description="Filter by capability"),
    verified_only: bool = Query(default=False, description="Only show KYA-verified agents"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Search the agent registry.

    Merchants use this to discover agents that want to pay for their services.
    """
    from sardis_v2_core.database import Database

    conditions = ["1=1"]
    params: list[Any] = []
    idx = 1

    if q:
        conditions.append(f"(name ILIKE ${idx} OR description ILIKE ${idx})")
        params.append(f"%{q}%")
        idx += 1

    if capability:
        conditions.append(f"${idx} = ANY(capabilities)")
        params.append(capability)
        idx += 1

    if verified_only:
        conditions.append("verified = TRUE")

    where = " AND ".join(conditions)
    params.append(limit)

    rows = await Database.fetch(
        f"""
        SELECT agent_id, name, description, capabilities, max_authority,
               supported_protocols, trust_score, verified, kya_status,
               total_transactions, created_at
        FROM agent_registry
        WHERE {where}
        ORDER BY verified DESC, trust_score DESC NULLS LAST, created_at DESC
        LIMIT ${idx}
        """,
        *params,
    )

    agents = [
        AgentProfile(
            agent_id=r["agent_id"],
            name=r["name"],
            description=r.get("description"),
            capabilities=list(r.get("capabilities", [])),
            max_authority=r.get("max_authority"),
            supported_protocols=list(r.get("supported_protocols", [])),
            trust_score=r.get("trust_score"),
            verified=r.get("verified", False),
            kya_status=r.get("kya_status", "unverified"),
            total_transactions=r.get("total_transactions", 0),
            registered_at=r["created_at"].isoformat() if r.get("created_at") else None,
        )
        for r in rows
    ]

    return RegistrySearchResponse(agents=agents, total=len(agents))
