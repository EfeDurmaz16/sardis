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
    """Redis-backed agent group repository with in-memory fallback."""

    def __init__(self, dsn: str = "memory://"):
        self._dsn = dsn
        from sardis_v2_core.redis_state import RedisStateStore
        self._store = RedisStateStore(namespace="agent_groups")

    def _serialize(self, group: AgentGroup) -> dict:
        """Serialize AgentGroup to a JSON-safe dict."""
        return {
            "group_id": group.group_id,
            "name": group.name,
            "owner_id": group.owner_id,
            "budget": {
                "per_transaction": str(group.budget.per_transaction),
                "daily": str(group.budget.daily),
                "monthly": str(group.budget.monthly),
                "total": str(group.budget.total),
            },
            "merchant_policy": {
                "allowed_merchants": group.merchant_policy.allowed_merchants,
                "blocked_merchants": group.merchant_policy.blocked_merchants,
                "allowed_categories": group.merchant_policy.allowed_categories,
                "blocked_categories": group.merchant_policy.blocked_categories,
            },
            "agent_ids": group.agent_ids,
            "metadata": group.metadata,
            "created_at": group.created_at.isoformat(),
            "updated_at": group.updated_at.isoformat(),
        }

    def _deserialize(self, data: dict) -> AgentGroup:
        """Deserialize a dict back to AgentGroup."""
        budget_data = data.get("budget", {})
        mp_data = data.get("merchant_policy", {})
        return AgentGroup(
            group_id=data["group_id"],
            name=data["name"],
            owner_id=data.get("owner_id", "default"),
            budget=GroupSpendingLimits(
                per_transaction=Decimal(str(budget_data.get("per_transaction", "500.00"))),
                daily=Decimal(str(budget_data.get("daily", "5000.00"))),
                monthly=Decimal(str(budget_data.get("monthly", "50000.00"))),
                total=Decimal(str(budget_data.get("total", "500000.00"))),
            ),
            merchant_policy=GroupMerchantPolicy(
                allowed_merchants=mp_data.get("allowed_merchants"),
                blocked_merchants=mp_data.get("blocked_merchants", []),
                allowed_categories=mp_data.get("allowed_categories"),
                blocked_categories=mp_data.get("blocked_categories", []),
            ),
            agent_ids=data.get("agent_ids", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else datetime.now(timezone.utc),
        )

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
        await self._store.set(group.group_id, self._serialize(group), ttl=300)
        return group

    async def get(self, group_id: str) -> Optional[AgentGroup]:
        data = await self._store.get(group_id)
        if data is None:
            return None
        return self._deserialize(data)

    async def list(
        self,
        owner_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AgentGroup]:
        all_keys = await self._store.keys("*")
        groups = []
        for key in all_keys:
            data = await self._store.get(key)
            if data is not None:
                groups.append(self._deserialize(data))
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
        data = await self._store.get(group_id)
        if data is None:
            return None
        group = self._deserialize(data)
        if name is not None:
            group.name = name
        if budget is not None:
            group.budget = budget
        if merchant_policy is not None:
            group.merchant_policy = merchant_policy
        if metadata is not None:
            group.metadata = metadata
        group.updated_at = datetime.now(timezone.utc)
        await self._store.set(group_id, self._serialize(group), ttl=300)
        return group

    async def delete(self, group_id: str) -> bool:
        exists = await self._store.exists(group_id)
        if exists:
            await self._store.delete(group_id)
            return True
        return False

    async def add_agent(self, group_id: str, agent_id: str) -> Optional[AgentGroup]:
        data = await self._store.get(group_id)
        if data is None:
            return None
        group = self._deserialize(data)
        if agent_id not in group.agent_ids:
            group.agent_ids.append(agent_id)
            group.updated_at = datetime.now(timezone.utc)
            await self._store.set(group_id, self._serialize(group), ttl=300)
        return group

    async def remove_agent(self, group_id: str, agent_id: str) -> Optional[AgentGroup]:
        data = await self._store.get(group_id)
        if data is None:
            return None
        group = self._deserialize(data)
        if agent_id in group.agent_ids:
            group.agent_ids.remove(agent_id)
            group.updated_at = datetime.now(timezone.utc)
            await self._store.set(group_id, self._serialize(group), ttl=300)
        return group

    async def get_groups_for_agent(self, agent_id: str) -> List[AgentGroup]:
        all_keys = await self._store.keys("*")
        result = []
        for key in all_keys:
            data = await self._store.get(key)
            if data is not None and agent_id in data.get("agent_ids", []):
                result.append(self._deserialize(data))
        return result
