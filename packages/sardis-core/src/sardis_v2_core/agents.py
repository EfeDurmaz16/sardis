"""Agent management for Sardis."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4

from pydantic import BaseModel, Field


class SpendingLimits(BaseModel):
    """Spending limits configuration for an agent."""
    per_transaction: Decimal = Field(default=Decimal("100.00"))
    daily: Decimal = Field(default=Decimal("1000.00"))
    monthly: Decimal = Field(default=Decimal("10000.00"))
    total: Decimal = Field(default=Decimal("100000.00"))


class AgentPolicy(BaseModel):
    """Policy rules for an agent."""
    allowed_merchants: Optional[List[str]] = None  # None = all allowed
    blocked_merchants: List[str] = Field(default_factory=list)
    allowed_categories: Optional[List[str]] = None
    blocked_categories: List[str] = Field(default_factory=list)
    require_approval_above: Optional[Decimal] = None
    auto_approve_below: Decimal = Field(default=Decimal("50.00"))


class Agent(BaseModel):
    """An AI agent with spending capabilities."""
    agent_id: str
    name: str
    description: Optional[str] = None
    owner_id: str = "default"  # Organization/user who owns this agent
    wallet_id: Optional[str] = None
    spending_limits: SpendingLimits = Field(default_factory=SpendingLimits)
    policy: AgentPolicy = Field(default_factory=AgentPolicy)
    api_key_hash: Optional[str] = None  # For agent-specific API keys
    is_active: bool = True
    # KYA (Know Your Agent) fields
    kya_level: str = "none"      # none | basic | verified | attested
    kya_status: str = "pending"  # pending | in_progress | active | suspended | revoked | expired
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }

    @staticmethod
    def new(name: str, owner_id: str = "default", **kwargs) -> "Agent":
        return Agent(
            agent_id=f"agent_{uuid4().hex[:16]}",
            name=name,
            owner_id=owner_id,
            **kwargs,
        )


class AgentRepository:
    """In-memory agent repository (swap for PostgreSQL in production)."""

    def __init__(self, dsn: str = "memory://"):
        self._dsn = dsn
        self._agents: dict[str, Agent] = {}

    async def create(
        self,
        name: str,
        owner_id: str = "default",
        description: Optional[str] = None,
        spending_limits: Optional[SpendingLimits] = None,
        policy: Optional[AgentPolicy] = None,
        metadata: Optional[dict] = None,
        kya_level: str = "none",
        kya_status: str = "pending",
    ) -> Agent:
        agent = Agent.new(
            name=name,
            owner_id=owner_id,
            description=description,
            spending_limits=spending_limits or SpendingLimits(),
            policy=policy or AgentPolicy(),
            metadata=metadata or {},
            kya_level=kya_level,
            kya_status=kya_status,
        )
        self._agents[agent.agent_id] = agent
        return agent

    async def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    async def list(
        self,
        owner_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Agent]:
        agents = list(self._agents.values())
        if owner_id:
            agents = [a for a in agents if a.owner_id == owner_id]
        if is_active is not None:
            agents = [a for a in agents if a.is_active == is_active]
        return agents[offset : offset + limit]

    async def update(
        self,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        spending_limits: Optional[SpendingLimits] = None,
        policy: Optional[AgentPolicy] = None,
        is_active: Optional[bool] = None,
        metadata: Optional[dict] = None,
        kya_level: Optional[str] = None,
        kya_status: Optional[str] = None,
    ) -> Optional[Agent]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        if name is not None:
            agent.name = name
        if description is not None:
            agent.description = description
        if spending_limits is not None:
            agent.spending_limits = spending_limits
        if policy is not None:
            agent.policy = policy
        if is_active is not None:
            agent.is_active = is_active
        if metadata is not None:
            agent.metadata = metadata
        if kya_level is not None:
            agent.kya_level = kya_level
        if kya_status is not None:
            agent.kya_status = kya_status
        agent.updated_at = datetime.now(timezone.utc)
        return agent

    async def delete(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    async def bind_wallet(self, agent_id: str, wallet_id: str) -> Optional[Agent]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        agent.wallet_id = wallet_id
        agent.updated_at = datetime.now(timezone.utc)
        return agent
