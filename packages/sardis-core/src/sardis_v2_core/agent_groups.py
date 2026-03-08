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
    parent_group_id: Optional[str] = None
    hierarchy_path: List[str] = Field(default_factory=list)
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
            "parent_group_id": group.parent_group_id,
            "hierarchy_path": group.hierarchy_path,
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
            parent_group_id=data.get("parent_group_id"),
            hierarchy_path=data.get("hierarchy_path", []),
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
        await self._store.set(group.group_id, self._serialize(group), ttl=0)
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
        await self._store.set(group_id, self._serialize(group), ttl=0)
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
            await self._store.set(group_id, self._serialize(group), ttl=0)
        return group

    async def remove_agent(self, group_id: str, agent_id: str) -> Optional[AgentGroup]:
        data = await self._store.get(group_id)
        if data is None:
            return None
        group = self._deserialize(data)
        if agent_id in group.agent_ids:
            group.agent_ids.remove(agent_id)
            group.updated_at = datetime.now(timezone.utc)
            await self._store.set(group_id, self._serialize(group), ttl=0)
        return group

    async def get_groups_for_agent(self, agent_id: str) -> List[AgentGroup]:
        all_keys = await self._store.keys("*")
        result = []
        for key in all_keys:
            data = await self._store.get(key)
            if data is not None and agent_id in data.get("agent_ids", []):
                result.append(self._deserialize(data))
        return result

    async def set_parent(
        self,
        group_id: str,
        parent_group_id: Optional[str],
    ) -> Optional[AgentGroup]:
        """Set parent group, validating no cycles. Updates hierarchy_path."""
        data = await self._store.get(group_id)
        if data is None:
            return None
        group = self._deserialize(data)

        if parent_group_id is not None:
            # Validate parent exists
            parent_data = await self._store.get(parent_group_id)
            if parent_data is None:
                raise ValueError(f"Parent group {parent_group_id} not found")

            # Cycle detection: walk up from parent to root
            visited = {group_id}
            current_id = parent_group_id
            while current_id is not None:
                if current_id in visited:
                    raise ValueError(
                        f"Cycle detected: setting {parent_group_id} as parent "
                        f"of {group_id} would create a loop"
                    )
                visited.add(current_id)
                cur_data = await self._store.get(current_id)
                if cur_data is None:
                    break
                current_id = cur_data.get("parent_group_id")

            # Build hierarchy_path from parent
            parent = self._deserialize(parent_data)
            group.hierarchy_path = parent.hierarchy_path + [parent_group_id]
        else:
            group.hierarchy_path = []

        group.parent_group_id = parent_group_id
        group.updated_at = datetime.now(timezone.utc)
        await self._store.set(group_id, self._serialize(group), ttl=0)
        return group


def merge_group_policies(
    child: AgentGroup,
    parent: AgentGroup,
) -> AgentGroup:
    """Merge parent policy into child — most restrictive wins.

    Rules:
    - per_transaction, daily, monthly, total: min(child, parent)
    - allowed_merchants: intersection if both set, parent if only parent set
    - blocked_merchants/categories: union
    - allowed_categories: intersection if both set, parent if only parent set
    """
    merged_budget = GroupSpendingLimits(
        per_transaction=min(child.budget.per_transaction, parent.budget.per_transaction),
        daily=min(child.budget.daily, parent.budget.daily),
        monthly=min(child.budget.monthly, parent.budget.monthly),
        total=min(child.budget.total, parent.budget.total),
    )

    child_mp = child.merchant_policy
    parent_mp = parent.merchant_policy

    # Allowed merchants: intersection
    if child_mp.allowed_merchants is not None and parent_mp.allowed_merchants is not None:
        allowed_set = set(m.lower() for m in child_mp.allowed_merchants) & set(
            m.lower() for m in parent_mp.allowed_merchants
        )
        merged_allowed_merchants = sorted(allowed_set)
    elif parent_mp.allowed_merchants is not None:
        merged_allowed_merchants = list(parent_mp.allowed_merchants)
    elif child_mp.allowed_merchants is not None:
        merged_allowed_merchants = list(child_mp.allowed_merchants)
    else:
        merged_allowed_merchants = None

    # Blocked merchants: union
    blocked_set = set(m.lower() for m in child_mp.blocked_merchants) | set(
        m.lower() for m in parent_mp.blocked_merchants
    )

    # Allowed categories: intersection
    if child_mp.allowed_categories is not None and parent_mp.allowed_categories is not None:
        allowed_cat_set = set(c.lower() for c in child_mp.allowed_categories) & set(
            c.lower() for c in parent_mp.allowed_categories
        )
        merged_allowed_categories = sorted(allowed_cat_set)
    elif parent_mp.allowed_categories is not None:
        merged_allowed_categories = list(parent_mp.allowed_categories)
    elif child_mp.allowed_categories is not None:
        merged_allowed_categories = list(child_mp.allowed_categories)
    else:
        merged_allowed_categories = None

    # Blocked categories: union
    blocked_cat_set = set(c.lower() for c in child_mp.blocked_categories) | set(
        c.lower() for c in parent_mp.blocked_categories
    )

    merged_mp = GroupMerchantPolicy(
        allowed_merchants=merged_allowed_merchants,
        blocked_merchants=sorted(blocked_set),
        allowed_categories=merged_allowed_categories,
        blocked_categories=sorted(blocked_cat_set),
    )

    return AgentGroup(
        group_id=child.group_id,
        name=child.name,
        owner_id=child.owner_id,
        budget=merged_budget,
        merchant_policy=merged_mp,
        agent_ids=child.agent_ids,
        metadata=child.metadata,
        parent_group_id=child.parent_group_id,
        hierarchy_path=child.hierarchy_path,
        created_at=child.created_at,
        updated_at=child.updated_at,
    )


class AgentGroupHierarchy:
    """Hierarchy resolution for group policy cascading."""

    def __init__(self, repo: "AgentGroupRepository"):
        self._repo = repo

    async def get_ancestors(self, group_id: str) -> List[AgentGroup]:
        """Return chain from group to root (exclusive of self)."""
        ancestors: List[AgentGroup] = []
        current = await self._repo.get(group_id)
        if current is None:
            return []

        visited = {group_id}
        parent_id = current.parent_group_id
        while parent_id is not None:
            if parent_id in visited:
                break  # safety: stop on cycle
            visited.add(parent_id)
            parent = await self._repo.get(parent_id)
            if parent is None:
                break
            ancestors.append(parent)
            parent_id = parent.parent_group_id

        return ancestors

    async def resolve_effective_policy(
        self,
        agent_id: str,
    ) -> Optional[AgentGroup]:
        """Walk hierarchy from agent's group up to root, merging policies.

        Returns a synthetic AgentGroup with the most restrictive effective
        policy, or None if the agent has no group.
        """
        groups = await self._repo.get_groups_for_agent(agent_id)
        if not groups:
            return None

        # For each group the agent belongs to, resolve up the hierarchy
        # and take the most restrictive across all groups
        effective: Optional[AgentGroup] = None
        for group in groups:
            # Walk up to root
            resolved = group
            ancestors = await self.get_ancestors(group.group_id)
            for ancestor in ancestors:
                resolved = merge_group_policies(resolved, ancestor)

            if effective is None:
                effective = resolved
            else:
                effective = merge_group_policies(effective, resolved)

        return effective
