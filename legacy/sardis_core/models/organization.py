"""Organization model for enterprise management of agents."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class Organization(BaseModel):
    """
    Represents an organization (Company/Enterprise) that owns multiple agents.
    
    Organizations allow for centralized management of:
    - Spending limits across all agents
    - Permission policies
    - Billing and settlement
    """
    
    org_id: str = Field(default_factory=lambda: f"org_{uuid.uuid4().hex[:16]}")
    name: str
    
    # Administrative users who can manage this org
    admin_ids: List[str] = Field(default_factory=list)
    
    # Global settings for the organization
    settings: Dict[str, Any] = Field(default_factory=dict)
    
    # Status
    is_active: bool = True
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
