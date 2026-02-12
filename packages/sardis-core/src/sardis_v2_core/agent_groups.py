"""Agent group management for Sardis multi-agent governance."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4

from pydantic import BaseModel, Field


class GroupSpendingLimits(BaseModel):
    """Aggregate spending limits for an agent group."""
    per_transaction: Decimal = Field(default=Decimal("500.00"))
    daily: Decimal = Field(default=Decimal("5000.00"))
    monthly: Decimal = Field(default=Decimal("50000.00"))
    total: Decimal = Field(default=Decimal("500000.00"))


class GroupMerchantPolicy(BaseModel):
    """Merchant-level policy for a group."""
    allowed_merchants: Optional[List[str]] = None  # None = all allowed
    blocked_merchants: List[str] = Field(default_factory=list)
    allowed_categories: Optional[List[str]] = None
    blocked_categories: List[str] = Field(default_factory=list)


class AgentGroup(BaseModel):
    """A group of agents with shared budget and merchant policies."""
    group_id: str
    name: str
    owner_id: str = "default"
    budget: GroupSpendingLimits = Field(default_factory=GroupSpendingLimits)
    merchant_policy: GroupMerchantPolicy = Field(default_factory=GroupMerchantPolicy)
    agent_ids: List[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }

    @staticmethod
    def new(name: str, owner_id: str = "default", **kwargs) -> "AgentGroup":
        return AgentGroup(
            group_id=f"grp_{uuid4().hex[:16]}",
            name=name,
            owner_id=owner_id,
            **kwargs,
        )


class AgentGroupRepository:
    """In-memory agent group repository (swap for PostgreSQL in production)."""

    def __init__(self, dsn: str = "memory://"):
        self._dsn = dsn
        self._groups: dict[str, AgentGroup] = {}

    async def create(
        self,
        name: str,
        owner_id: str = "default",
        budget: Optional[GroupSpendingLimits] = None,
        merchant_policy: Optional[GroupMerchantPolicy] = None,
        agent_ids: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> AgentGroup:
        group = AgentGroup.new(
            name=name,
            owner_id=owner_id,
            budget=budget or GroupSpendingLimits(),
            merchant_policy=merchant_policy or GroupMerchantPolicy(),
            agent_ids=agent_ids or [],
            metadata=metadata or {},
        )
        self._groups[group.group_id] = group
        return group

    async def get(self, group_id: str) -> Optional[AgentGroup]:
        return self._groups.get(group_id)

    async def list(
        self,
        owner_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AgentGroup]:
        groups = list(self._groups.values())
        if owner_id:
            groups = [g for g in groups if g.owner_id == owner_id]
        return groups[offset : offset + limit]

    async def update(
        self,
        group_id: str,
        name: Optional[str] = None,
        budget: Optional[GroupSpendingLimits] = None,
        merchant_policy: Optional[GroupMerchantPolicy] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[AgentGroup]:
        group = self._groups.get(group_id)
        if not group:
            return None
        if name is not None:
            group.name = name
        if budget is not None:
            group.budget = budget
        if merchant_policy is not None:
            group.merchant_policy = merchant_policy
        if metadata is not None:
            group.metadata = metadata
        group.updated_at = datetime.now(timezone.utc)
        return group

    async def delete(self, group_id: str) -> bool:
        if group_id in self._groups:
            del self._groups[group_id]
            return True
        return False

    async def add_agent(self, group_id: str, agent_id: str) -> Optional[AgentGroup]:
        group = self._groups.get(group_id)
        if not group:
            return None
        if agent_id not in group.agent_ids:
            group.agent_ids.append(agent_id)
            group.updated_at = datetime.now(timezone.utc)
        return group

    async def remove_agent(self, group_id: str, agent_id: str) -> Optional[AgentGroup]:
        group = self._groups.get(group_id)
        if not group:
            return None
        if agent_id in group.agent_ids:
            group.agent_ids.remove(agent_id)
            group.updated_at = datetime.now(timezone.utc)
        return group

    async def get_groups_for_agent(self, agent_id: str) -> List[AgentGroup]:
        return [g for g in self._groups.values() if agent_id in g.agent_ids]
