"""Wallet model with balance and spending limits."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
import uuid

from .virtual_card import VirtualCard


class Wallet(BaseModel):
    """
    Agent wallet with balance tracking and spending limits.
    
    Each agent has exactly one wallet that holds their stablecoin
    balance and enforces spending constraints.
    """
    
    wallet_id: str = Field(default_factory=lambda: f"wallet_{uuid.uuid4().hex[:16]}")
    agent_id: str
    
    # Balance tracking
    balance: Decimal = Field(default=Decimal("0.00"))
    currency: str = Field(default="USDC")
    
    # Spending limits
    limit_per_tx: Decimal = Field(default=Decimal("100.00"))
    limit_total: Decimal = Field(default=Decimal("1000.00"))
    spent_total: Decimal = Field(default=Decimal("0.00"))
    
    # Virtual card for payment identity
    virtual_card: Optional[VirtualCard] = None
    
    # Metadata
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def remaining_balance(self) -> Decimal:
        """Get the current available balance."""
        return self.balance
    
    def remaining_limit(self) -> Decimal:
        """Get remaining spend limit before hitting total cap."""
        return max(Decimal("0.00"), self.limit_total - self.spent_total)
    
    def can_spend(self, amount: Decimal, fee: Decimal = Decimal("0.00")) -> tuple[bool, str]:
        """
        Check if a transaction of given amount (plus fee) is allowed.
        
        Returns:
            Tuple of (allowed, reason)
        """
        total_cost = amount + fee
        
        if not self.is_active:
            return False, "Wallet is inactive"
        
        if total_cost > self.balance:
            return False, f"Insufficient balance: have {self.balance}, need {total_cost}"
        
        if amount > self.limit_per_tx:
            return False, f"Amount {amount} exceeds per-transaction limit of {self.limit_per_tx}"
        
        if amount > self.remaining_limit():
            return False, f"Amount {amount} exceeds remaining spending limit of {self.remaining_limit()}"
        
        return True, "OK"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }

