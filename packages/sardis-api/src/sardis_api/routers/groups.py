"""Agent group API endpoints for multi-agent governance."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from sardis_v2_core.agent_groups import (
    AgentGroup,
    AgentGroupRepository,
    GroupSpendingLimits,
    GroupMerchantPolicy,
)
from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])


# Request/Response Models

class GroupBudgetRequest(BaseModel):
    per_transaction: Decimal = Field(default=Decimal("500.00"))
    daily: Decimal = Field(default=Decimal("5000.00"))
    monthly: Decimal = Field(default=Decimal("50000.00"))
    total: Decimal = Field(default=Decimal("500000.00"))


class GroupMerchantPolicyRequest(BaseModel):
    allowed_merchants: Optional[List[str]] = None
    blocked_merchants: List[str] = Field(default_factory=list)
    allowed_categories: Optional[List[str]] = None
    blocked_categories: List[str] = Field(default_factory=list)


class CreateGroupRequest(BaseModel):
    name: str
    budget: Optional[GroupBudgetRequest] = None
    merchant_policy: Optional[GroupMerchantPolicyRequest] = None
    metadata: Optional[dict] = None


class UpdateGroupRequest(BaseModel):
    name: Optional[str] = None
    budget: Optional[GroupBudgetRequest] = None
    merchant_policy: Optional[GroupMerchantPolicyRequest] = None
    metadata: Optional[dict] = None


class AgentGroupResponse(BaseModel):
    group_id: str
    name: str
    owner_id: str
    budget: dict
    merchant_policy: dict
    agent_ids: List[str]
    metadata: dict
    created_at: str
    updated_at: str

    @classmethod
    def from_group(cls, group: AgentGroup) -> "AgentGroupResponse":
        return cls(
            group_id=group.group_id,
            name=group.name,
            owner_id=group.owner_id,
            budget=group.budget.model_dump(),
            merchant_policy=group.merchant_policy.model_dump(),
            agent_ids=group.agent_ids,
            metadata=group.metadata,
            created_at=group.created_at.isoformat(),
            updated_at=group.updated_at.isoformat(),
        )


class AddAgentRequest(BaseModel):
    agent_id: str


class GroupSpendingResponse(BaseModel):
    group_id: str
    name: str
    budget: dict
    agent_count: int
    agent_ids: List[str]


# Dependency

class GroupDependencies:
    def __init__(self, group_repo: AgentGroupRepository):
        self.group_repo = group_repo


def get_deps() -> GroupDependencies:
    raise NotImplementedError("Dependency override required")


# Endpoints

@router.post("", response_model=AgentGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    request: CreateGroupRequest,
    deps: GroupDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Create a new agent group."""
    owner_id = principal.organization_id

    budget = None
    if request.budget:
        budget = GroupSpendingLimits(
            per_transaction=request.budget.per_transaction,
            daily=request.budget.daily,
            monthly=request.budget.monthly,
            total=request.budget.total,
        )

    merchant_policy = None
    if request.merchant_policy:
        merchant_policy = GroupMerchantPolicy(
            allowed_merchants=request.merchant_policy.allowed_merchants,
            blocked_merchants=request.merchant_policy.blocked_merchants,
            allowed_categories=request.merchant_policy.allowed_categories,
            blocked_categories=request.merchant_policy.blocked_categories,
        )

    group = await deps.group_repo.create(
        name=request.name,
        owner_id=owner_id,
        budget=budget,
        merchant_policy=merchant_policy,
        metadata=request.metadata,
    )
    return AgentGroupResponse.from_group(group)


@router.get("", response_model=List[AgentGroupResponse])
async def list_groups(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    deps: GroupDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """List all agent groups."""
    owner_id = principal.organization_id
    groups = await deps.group_repo.list(
        owner_id=owner_id,
        limit=limit,
        offset=offset,
    )
    return [AgentGroupResponse.from_group(g) for g in groups]


@router.get("/{group_id}", response_model=AgentGroupResponse)
async def get_group(
    group_id: str,
    deps: GroupDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Get group details."""
    group = await deps.group_repo.get(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not principal.is_admin and group.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return AgentGroupResponse.from_group(group)


@router.patch("/{group_id}", response_model=AgentGroupResponse)
async def update_group(
    group_id: str,
    request: UpdateGroupRequest,
    deps: GroupDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Update group settings."""
    existing = await deps.group_repo.get(group_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not principal.is_admin and existing.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    budget = None
    if request.budget:
        budget = GroupSpendingLimits(
            per_transaction=request.budget.per_transaction,
            daily=request.budget.daily,
            monthly=request.budget.monthly,
            total=request.budget.total,
        )

    merchant_policy = None
    if request.merchant_policy:
        merchant_policy = GroupMerchantPolicy(
            allowed_merchants=request.merchant_policy.allowed_merchants,
            blocked_merchants=request.merchant_policy.blocked_merchants,
            allowed_categories=request.merchant_policy.allowed_categories,
            blocked_categories=request.merchant_policy.blocked_categories,
        )

    group = await deps.group_repo.update(
        group_id,
        name=request.name,
        budget=budget,
        merchant_policy=merchant_policy,
        metadata=request.metadata,
    )
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return AgentGroupResponse.from_group(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: str,
    deps: GroupDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Delete an agent group."""
    existing = await deps.group_repo.get(group_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not principal.is_admin and existing.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    deleted = await deps.group_repo.delete(group_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")


@router.post("/{group_id}/agents", response_model=AgentGroupResponse)
async def add_agent_to_group(
    group_id: str,
    request: AddAgentRequest,
    deps: GroupDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Add an agent to a group."""
    existing = await deps.group_repo.get(group_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not principal.is_admin and existing.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    group = await deps.group_repo.add_agent(group_id, request.agent_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return AgentGroupResponse.from_group(group)


@router.delete("/{group_id}/agents/{agent_id}", response_model=AgentGroupResponse)
async def remove_agent_from_group(
    group_id: str,
    agent_id: str,
    deps: GroupDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Remove an agent from a group."""
    existing = await deps.group_repo.get(group_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not principal.is_admin and existing.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    group = await deps.group_repo.remove_agent(group_id, agent_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return AgentGroupResponse.from_group(group)


@router.get("/{group_id}/spending", response_model=GroupSpendingResponse)
async def get_group_spending(
    group_id: str,
    deps: GroupDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Get current spending for a group."""
    group = await deps.group_repo.get(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not principal.is_admin and group.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return GroupSpendingResponse(
        group_id=group.group_id,
        name=group.name,
        budget=group.budget.model_dump(),
        agent_count=len(group.agent_ids),
        agent_ids=group.agent_ids,
    )
