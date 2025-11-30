"""Transaction model for recording payments on the ledger."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class TransactionStatus(str, Enum):
    """Status of a transaction in the ledger."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Transaction(BaseModel):
    """
    Represents a payment transaction recorded on the Sardis ledger.
    
    Transactions are immutable once completed - this provides
    an audit trail of all payments made by agents.
    """
    
    tx_id: str = Field(default_factory=lambda: f"tx_{uuid.uuid4().hex[:20]}")
    
    # Parties involved
    from_wallet: str  # Source wallet ID
    to_wallet: str    # Destination wallet ID (merchant or service)
    
    # Transaction details
    amount: Decimal
    fee: Decimal = Field(default=Decimal("0.00"))
    currency: str = Field(default="USDC")
    
    # Purpose/memo for the transaction
    purpose: Optional[str] = None
    
    # Status tracking
    status: TransactionStatus = Field(default=TransactionStatus.PENDING)
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def total_cost(self) -> Decimal:
        """Get total amount including fee."""
        return self.amount + self.fee
    
    def mark_completed(self) -> None:
        """Mark transaction as successfully completed."""
        self.status = TransactionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
    
    def mark_failed(self, error: str) -> None:
        """Mark transaction as failed with error message."""
        self.status = TransactionStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.utcnow()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }

