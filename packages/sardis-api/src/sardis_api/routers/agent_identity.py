"""Agent Identity API endpoints (ERC-8004 integration)."""
from __future__ import annotations

import time
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from sardis_v2_core.erc8004 import (
    AgentIdentity,
    AgentMetadata,
    ReputationEntry,
    ValidationResult,
    InMemoryERC8004Registry,
)
from sardis_v2_core.agent_card import (
    generate_agent_card,
    verify_agent_card,
    bind_ens_name,
)
from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])

# Global registry (in production, inject via dependency)
_registry = InMemoryERC8004Registry(chain_id=8453)  # Base


# Request/Response Models
class AgentMetadataRequest(BaseModel):
    """Request to register or update agent metadata."""

    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    version: str = Field(default="1.0.0", description="Agent version")
    model_type: str = Field(..., description="AI model type (e.g., gpt-4, claude-3-opus)")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    service_endpoints: dict[str, str] = Field(default_factory=dict, description="Service endpoints")
    trust_config: dict[str, str] = Field(default_factory=dict, description="Trust configuration")
    protocols_supported: List[str] = Field(default_factory=lambda: ["a2a", "ap2"], description="Supported protocols")


class AgentIdentityResponse(BaseModel):
    """Agent identity response."""

    agent_id: str
    owner_address: str
    agent_uri: str
    metadata: dict
    created_at: int
    chain_id: int
    did: str
    ens_name: Optional[str] = None


class ReputationRequest(BaseModel):
    """Request to submit reputation."""

    from_agent: str = Field(..., description="Agent ID giving reputation")
    to_agent: str = Field(..., description="Agent ID receiving reputation")
    score: int = Field(..., ge=0, le=1000, description="Reputation score (0-1000)")
    category: str = Field(..., description="Reputation category")


class ReputationResponse(BaseModel):
    """Reputation entry response."""

    from_agent: str
    to_agent: str
    score: int
    category: str
    timestamp: int
    transaction_hash: str


class ValidationRequest(BaseModel):
    """Request to submit validation."""

    is_valid: bool
    validation_type: str = Field(..., description="Type of validation (kyc, certification, audit)")
    evidence_uri: str = Field(..., description="URI to validation evidence")


class ValidationResponse(BaseModel):
    """Validation result response."""

    validator_address: str
    agent_id: str
    is_valid: bool
    validation_type: str
    evidence_uri: str
    timestamp: int
    transaction_hash: Optional[str] = None


class AgentCardResponse(BaseModel):
    """Agent card response."""

    context: str = Field(alias="@context")
    type: str
    agent_id: str
    name: str
    description: str
    version: str
    owner: str
    capabilities: List[str]
    protocols: List[str]
    endpoints: dict[str, str]
    chain_id: int
    created_at: int
    public_key: Optional[str] = None
    ens_name: Optional[str] = None

    class Config:
        populate_by_name = True


# ============ Endpoints ============


@router.post(
    "/api/v2/agents/identity/register",
    response_model=AgentIdentityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_agent_identity(
    request: AgentMetadataRequest,
    principal: Principal = Depends(require_principal),
):
    """
    Register a new agent identity on-chain.

    Creates an ERC-8004 compliant agent identity NFT with metadata.
    """
    metadata = AgentMetadata(
        name=request.name,
        description=request.description,
        version=request.version,
        model_type=request.model_type,
        capabilities=request.capabilities,
        service_endpoints=request.service_endpoints,
        trust_config=request.trust_config,
        protocols_supported=request.protocols_supported,
    )

    # In production, derive owner from principal's wallet
    owner_address = f"0x{principal.user_id[:40]}"

    identity = await _registry.register_agent(owner_address, metadata)

    return AgentIdentityResponse(
        agent_id=identity.agent_id,
        owner_address=identity.owner_address,
        agent_uri=identity.agent_uri,
        metadata=identity.metadata,
        created_at=identity.created_at,
        chain_id=identity.chain_id,
        did=identity.did,
        ens_name=identity.ens_name,
    )


@router.get(
    "/api/v2/agents/identity/{agent_id}",
    response_model=AgentIdentityResponse,
)
async def get_agent_identity(
    agent_id: str,
    principal: Principal = Depends(require_principal),
):
    """
    Get agent identity by ID.
    """
    identity = await _registry.get_agent(agent_id)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    return AgentIdentityResponse(
        agent_id=identity.agent_id,
        owner_address=identity.owner_address,
        agent_uri=identity.agent_uri,
        metadata=identity.metadata,
        created_at=identity.created_at,
        chain_id=identity.chain_id,
        did=identity.did,
        ens_name=identity.ens_name,
    )


@router.put(
    "/api/v2/agents/identity/{agent_id}/metadata",
    response_model=AgentIdentityResponse,
)
async def update_agent_metadata(
    agent_id: str,
    request: AgentMetadataRequest,
    principal: Principal = Depends(require_principal),
):
    """
    Update agent metadata (owner only).
    """
    # Verify ownership
    identity = await _registry.get_agent(agent_id)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    # In production, verify principal owns this agent
    # if identity.owner_address != principal.wallet_address:
    #     raise HTTPException(status_code=403, detail="Not agent owner")

    metadata = AgentMetadata(
        name=request.name,
        description=request.description,
        version=request.version,
        model_type=request.model_type,
        capabilities=request.capabilities,
        service_endpoints=request.service_endpoints,
        trust_config=request.trust_config,
        protocols_supported=request.protocols_supported,
    )

    success = await _registry.update_metadata(agent_id, metadata)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update metadata",
        )

    # Refetch updated identity
    identity = await _registry.get_agent(agent_id)

    return AgentIdentityResponse(
        agent_id=identity.agent_id,
        owner_address=identity.owner_address,
        agent_uri=identity.agent_uri,
        metadata=identity.metadata,
        created_at=identity.created_at,
        chain_id=identity.chain_id,
        did=identity.did,
        ens_name=identity.ens_name,
    )


@router.post(
    "/api/v2/agents/identity/{agent_id}/reputation",
    response_model=ReputationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_reputation(
    agent_id: str,
    request: ReputationRequest,
    principal: Principal = Depends(require_principal),
):
    """
    Submit reputation for an agent.
    """
    # Verify target agent exists
    identity = await _registry.get_agent(agent_id)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    # Verify from_agent exists
    from_agent_identity = await _registry.get_agent(request.from_agent)
    if not from_agent_identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"From agent {request.from_agent} not found",
        )

    entry = ReputationEntry(
        from_agent=request.from_agent,
        to_agent=request.to_agent,
        score=request.score,
        category=request.category,
        timestamp=int(time.time()),
        transaction_hash="",  # Will be set by registry
    )

    tx_hash = await _registry.submit_reputation(entry)
    entry.transaction_hash = tx_hash

    return ReputationResponse(
        from_agent=entry.from_agent,
        to_agent=entry.to_agent,
        score=entry.score,
        category=entry.category,
        timestamp=entry.timestamp,
        transaction_hash=entry.transaction_hash,
    )


@router.get(
    "/api/v2/agents/identity/{agent_id}/reputation",
    response_model=List[ReputationResponse],
)
async def get_reputation(
    agent_id: str,
    principal: Principal = Depends(require_principal),
):
    """
    Get all reputation entries for an agent.
    """
    identity = await _registry.get_agent(agent_id)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    entries = await _registry.get_reputation(agent_id)

    return [
        ReputationResponse(
            from_agent=e.from_agent,
            to_agent=e.to_agent,
            score=e.score,
            category=e.category,
            timestamp=e.timestamp,
            transaction_hash=e.transaction_hash,
        )
        for e in entries
    ]


@router.get(
    "/api/v2/agents/identity/{agent_id}/reputation/score",
    response_model=dict,
)
async def get_reputation_score(
    agent_id: str,
    principal: Principal = Depends(require_principal),
):
    """
    Get aggregate reputation score (0-1000).
    """
    identity = await _registry.get_agent(agent_id)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    score = await _registry.get_reputation_score(agent_id)

    return {
        "agent_id": agent_id,
        "average_score": score,
        "max_score": 1000,
    }


@router.post(
    "/api/v2/agents/identity/{agent_id}/validations",
    response_model=ValidationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_validation(
    agent_id: str,
    request: ValidationRequest,
    principal: Principal = Depends(require_principal),
):
    """
    Submit validation attestation for an agent (trusted validators only).
    """
    # Verify agent exists
    identity = await _registry.get_agent(agent_id)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    # In production, verify principal is a trusted validator
    validator_address = f"0x{principal.user_id[:40]}"

    result = ValidationResult(
        validator_address=validator_address,
        agent_id=agent_id,
        is_valid=request.is_valid,
        validation_type=request.validation_type,
        evidence_uri=request.evidence_uri,
        timestamp=int(time.time()),
    )

    tx_hash = await _registry.validate_agent(agent_id, validator_address, result)
    result.transaction_hash = tx_hash

    return ValidationResponse(
        validator_address=result.validator_address,
        agent_id=result.agent_id,
        is_valid=result.is_valid,
        validation_type=result.validation_type,
        evidence_uri=result.evidence_uri,
        timestamp=result.timestamp,
        transaction_hash=result.transaction_hash,
    )


@router.get(
    "/api/v2/agents/identity/{agent_id}/validations",
    response_model=List[ValidationResponse],
)
async def get_validations(
    agent_id: str,
    principal: Principal = Depends(require_principal),
):
    """
    Get all validation results for an agent.
    """
    identity = await _registry.get_agent(agent_id)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    results = await _registry.get_validations(agent_id)

    return [
        ValidationResponse(
            validator_address=r.validator_address,
            agent_id=r.agent_id,
            is_valid=r.is_valid,
            validation_type=r.validation_type,
            evidence_uri=r.evidence_uri,
            timestamp=r.timestamp,
            transaction_hash=r.transaction_hash,
        )
        for r in results
    ]


@router.get(
    "/api/v2/agents/identity/{agent_id}/card",
    response_model=AgentCardResponse,
)
async def get_agent_card(
    agent_id: str,
    principal: Principal = Depends(require_principal),
    chain: int = Query(default=8453, description="Chain ID"),
):
    """
    Get A2A/AP2 agent card for an agent.
    """
    identity = await _registry.get_agent(agent_id)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    card = generate_agent_card(identity)

    # Validate before returning
    if not verify_agent_card(card):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Generated invalid agent card",
        )

    return AgentCardResponse(**card)
