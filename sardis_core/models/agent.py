"""Agent model representing an AI agent registered with Sardis."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class Agent(BaseModel):
    """
    Represents an AI agent registered with the Sardis payment system.
    
    Agents are owned by developers/companies and have associated
    wallets for making payments.
    """
    
    agent_id: str = Field(default_factory=lambda: f"agent_{uuid.uuid4().hex[:16]}")
    name: str
    owner_id: str  # Developer or company that owns this agent
    
    # Optional description of what this agent does
    description: Optional[str] = None
    
    # The wallet ID associated with this agent (set when wallet is created)
    wallet_id: Optional[str] = None
    
    # Agent status
    is_active: bool = True
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

