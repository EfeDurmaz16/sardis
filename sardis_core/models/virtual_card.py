"""Virtual card model for wallet payment abstraction."""

from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import secrets


def generate_masked_number() -> str:
    """Generate a masked virtual card number (last 4 digits visible)."""
    last_four = secrets.randbelow(10000)
    return f"**** **** **** {last_four:04d}"


class VirtualCard(BaseModel):
    """
    Virtual card abstraction for a wallet.
    
    This represents a virtual payment identity that can be used
    for transactions. In the future, this could map to a real
    card network integration.
    """
    
    card_id: str = Field(default_factory=lambda: f"vc_{uuid.uuid4().hex[:16]}")
    wallet_id: str
    masked_number: str = Field(default_factory=generate_masked_number)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

