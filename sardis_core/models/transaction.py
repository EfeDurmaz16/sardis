"""Transaction model for recording payments on the ledger."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class TransactionStatus(str, Enum):
    """Status of a transaction in the ledger."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class OnChainRecord(BaseModel):
    """
    On-chain transaction record for verification.
    
    This links an internal Sardis transaction to its blockchain
    representation for auditing and verification.
    """
    chain: str  # e.g., "base_sepolia", "ethereum"
    tx_hash: str  # Blockchain transaction hash
    block_number: Optional[int] = None
    block_hash: Optional[str] = None
    from_address: str  # On-chain sender address
    to_address: str  # On-chain recipient address
    gas_used: Optional[int] = None
    explorer_url: Optional[str] = None
    status: str = "pending"  # pending, confirmed, failed
    confirmed_at: Optional[datetime] = None


class Transaction(BaseModel):
    """
    Represents a payment transaction recorded on the Sardis ledger.
    
    Transactions are immutable once completed - this provides
    an audit trail of all payments made by agents.
    
    On-chain verification:
    - If settlement_mode is "chain_write_per_tx", each transaction gets an
      on-chain record with a verifiable transaction hash.
    - The on_chain_records list contains all blockchain transactions associated
      with this internal transaction.
    - Use explorer_url to verify transactions on block explorers.
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
    
    # On-chain verification data
    on_chain_records: List[OnChainRecord] = Field(default_factory=list)
    is_settled_on_chain: bool = False
    settlement_batch_id: Optional[str] = None  # For batched settlements
    
    # Idempotency
    idempotency_key: Optional[str] = None
    
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
    
    def add_on_chain_record(self, record: OnChainRecord) -> None:
        """Add an on-chain transaction record."""
        self.on_chain_records.append(record)
        if record.status == "confirmed":
            self.is_settled_on_chain = True
    
    def get_explorer_urls(self) -> List[str]:
        """Get all block explorer URLs for this transaction."""
        return [r.explorer_url for r in self.on_chain_records if r.explorer_url]
    
    def get_primary_tx_hash(self) -> Optional[str]:
        """Get the primary (first confirmed) transaction hash."""
        for record in self.on_chain_records:
            if record.status == "confirmed":
                return record.tx_hash
        # Return first pending if no confirmed
        if self.on_chain_records:
            return self.on_chain_records[0].tx_hash
        return None
    
    def to_verification_dict(self) -> dict:
        """
        Export transaction for verification purposes.
        
        Returns a dict suitable for third-party auditing with
        all necessary information to verify the transaction on-chain.
        """
        return {
            "sardis_tx_id": self.tx_id,
            "amount": str(self.amount),
            "fee": str(self.fee),
            "currency": self.currency,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "is_on_chain": self.is_settled_on_chain,
            "chain_records": [
                {
                    "chain": r.chain,
                    "tx_hash": r.tx_hash,
                    "block_number": r.block_number,
                    "explorer_url": r.explorer_url,
                    "status": r.status,
                }
                for r in self.on_chain_records
            ],
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }

