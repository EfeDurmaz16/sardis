"""Agent models for Sardis SDK."""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from .base import SardisModel

if TYPE_CHECKING:
    from datetime import datetime


class Agent(SardisModel):
    """An AI agent registered with Sardis."""
    
    agent_id: str = Field(alias="id")
    name: str
    description: str | None = None
    organization_id: str | None = None
    wallet_id: str | None = None
    public_key: str | None = None
    key_algorithm: str = "ed25519"
    is_active: bool = True
    metadata: dict | None = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CreateAgentRequest(SardisModel):
    """Request to create a new agent."""
    
    name: str
    description: str | None = None
    organization_id: str | None = None
    public_key: str | None = None
    key_algorithm: str = "ed25519"


class UpdateAgentRequest(SardisModel):
    """Request to update an agent."""
    
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None

# Aliases for consistency
AgentCreate = CreateAgentRequest
AgentUpdate = UpdateAgentRequest
