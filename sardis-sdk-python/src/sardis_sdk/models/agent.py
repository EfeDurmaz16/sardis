"""Agent models for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import SardisModel


class Agent(SardisModel):
    """An AI agent registered with Sardis."""
    
    agent_id: str = Field(alias="id")
    name: str
    description: Optional[str] = None
    organization_id: Optional[str] = None
    wallet_id: Optional[str] = None
    public_key: Optional[str] = None
    key_algorithm: str = "ed25519"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class CreateAgentRequest(SardisModel):
    """Request to create a new agent."""
    
    name: str
    description: Optional[str] = None
    organization_id: Optional[str] = None
    public_key: Optional[str] = None
    key_algorithm: str = "ed25519"


class UpdateAgentRequest(SardisModel):
    """Request to update an agent."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
