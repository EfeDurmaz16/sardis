"""Merchant model for payment recipients."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class Merchant(BaseModel):
    """
    Represents a merchant or service that can receive payments.
    
    Merchants have their own wallet to receive funds from agent payments.
    """
    
    merchant_id: str = Field(default_factory=lambda: f"merchant_{uuid.uuid4().hex[:12]}")
    name: str
    
    # The wallet ID for receiving payments
    wallet_id: Optional[str] = None
    
    # Optional details
    description: Optional[str] = None
    category: Optional[str] = None  # e.g., "retail", "api_service", "compute"
    
    # Status
    is_active: bool = True
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

