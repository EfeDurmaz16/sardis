"""Agent API endpoints."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from sardis_v2_core import Agent, AgentPolicy, SpendingLimits, AgentRepository, WalletRepository
from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])


# Request/Response Models
class SpendingLimitsRequest(BaseModel):
    per_transaction: Decimal = Field(default=Decimal("100.00"))
    daily: Decimal = Field(default=Decimal("1000.00"))
    monthly: Decimal = Field(default=Decimal("10000.00"))
    total: Decimal = Field(default=Decimal("100000.00"))


class AgentPolicyRequest(BaseModel):
    allowed_merchants: Optional[List[str]] = None
    blocked_merchants: List[str] = Field(default_factory=list)
    allowed_categories: Optional[List[str]] = None
    blocked_categories: List[str] = Field(default_factory=list)
    require_approval_above: Optional[Decimal] = None
    auto_approve_below: Decimal = Field(default=Decimal("50.00"))


class CreateAgentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    spending_limits: Optional[SpendingLimitsRequest] = None
    policy: Optional[AgentPolicyRequest] = None
    metadata: Optional[dict] = None
    create_wallet: bool = Field(default=True, description="Automatically create a wallet for this agent")
    initial_balance: Decimal = Field(default=Decimal("0.00"))


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    spending_limits: Optional[SpendingLimitsRequest] = None
    policy: Optional[AgentPolicyRequest] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    description: Optional[str]
    owner_id: str
    wallet_id: Optional[str]
    spending_limits: dict
    policy: dict
    is_active: bool
    metadata: dict
    created_at: str
    updated_at: str

    @classmethod
    def from_agent(cls, agent: Agent) -> "AgentResponse":
        return cls(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            owner_id=agent.owner_id,
            wallet_id=agent.wallet_id,
            spending_limits=agent.spending_limits.model_dump(),
            policy=agent.policy.model_dump(),
            is_active=agent.is_active,
            metadata=agent.metadata,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat(),
        )


# Dependency
class AgentDependencies:
    def __init__(self, agent_repo: AgentRepository, wallet_repo: WalletRepository):
        self.agent_repo = agent_repo
        self.wallet_repo = wallet_repo


def get_deps() -> AgentDependencies:
    raise NotImplementedError("Dependency override required")


# Endpoints
@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: CreateAgentRequest,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Create a new AI agent."""
    owner_id = principal.organization_id
    spending_limits = None
    if request.spending_limits:
        spending_limits = SpendingLimits(
            per_transaction=request.spending_limits.per_transaction,
            daily=request.spending_limits.daily,
            monthly=request.spending_limits.monthly,
            total=request.spending_limits.total,
        )

    policy = None
    if request.policy:
        policy = AgentPolicy(
            allowed_merchants=request.policy.allowed_merchants,
            blocked_merchants=request.policy.blocked_merchants,
            allowed_categories=request.policy.allowed_categories,
            blocked_categories=request.policy.blocked_categories,
            require_approval_above=request.policy.require_approval_above,
            auto_approve_below=request.policy.auto_approve_below,
        )

    agent = await deps.agent_repo.create(
        name=request.name,
        owner_id=owner_id,
        description=request.description,
        spending_limits=spending_limits,
        policy=policy,
        metadata=request.metadata,
    )

    # Optionally create a wallet for the agent
    if request.create_wallet:
        wallet = await deps.wallet_repo.create(
            agent_id=agent.agent_id,
            mpc_provider="turnkey",
            currency="USDC",
            limit_per_tx=spending_limits.per_transaction if spending_limits else Decimal("100.00"),
            limit_total=spending_limits.total if spending_limits else Decimal("1000.00"),
        )
        await deps.agent_repo.bind_wallet(agent.agent_id, wallet.wallet_id)
        agent.wallet_id = wallet.wallet_id

    return AgentResponse.from_agent(agent)


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    owner_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """List all agents."""
    effective_owner = owner_id if (principal.is_admin and owner_id) else principal.organization_id
    agents = await deps.agent_repo.list(
        owner_id=effective_owner,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return [AgentResponse.from_agent(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Get agent details."""
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return AgentResponse.from_agent(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Update agent settings."""
    existing = await deps.agent_repo.get(agent_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and existing.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    spending_limits = None
    if request.spending_limits:
        spending_limits = SpendingLimits(
            per_transaction=request.spending_limits.per_transaction,
            daily=request.spending_limits.daily,
            monthly=request.spending_limits.monthly,
            total=request.spending_limits.total,
        )

    policy = None
    if request.policy:
        policy = AgentPolicy(
            allowed_merchants=request.policy.allowed_merchants,
            blocked_merchants=request.policy.blocked_merchants,
            allowed_categories=request.policy.allowed_categories,
            blocked_categories=request.policy.blocked_categories,
            require_approval_above=request.policy.require_approval_above,
            auto_approve_below=request.policy.auto_approve_below,
        )

    agent = await deps.agent_repo.update(
        agent_id,
        name=request.name,
        description=request.description,
        spending_limits=spending_limits,
        policy=policy,
        is_active=request.is_active,
        metadata=request.metadata,
    )
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentResponse.from_agent(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Delete an agent."""
    existing = await deps.agent_repo.get(agent_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and existing.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    deleted = await deps.agent_repo.delete(agent_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")


@router.post("/{agent_id}/wallet", response_model=AgentResponse)
async def bind_wallet_to_agent(
    agent_id: str,
    wallet_id: str = Query(...),
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Bind an existing wallet to an agent."""
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Verify wallet exists
    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    agent = await deps.agent_repo.bind_wallet(agent_id, wallet_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentResponse.from_agent(agent)


@router.get("/{agent_id}/limits", response_model=dict)
async def get_agent_limits(
    agent_id: str,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Get current spending limits and usage for an agent."""
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    wallet = None
    if agent.wallet_id:
        wallet = await deps.wallet_repo.get(agent.wallet_id)

    return {
        "agent_id": agent.agent_id,
        "spending_limits": agent.spending_limits.model_dump(),
        "wallet": {
            "wallet_id": wallet.wallet_id if wallet else None,
            "addresses": wallet.addresses if wallet else {},
            "mpc_provider": wallet.mpc_provider if wallet else None,
        } if wallet else None,
    }
