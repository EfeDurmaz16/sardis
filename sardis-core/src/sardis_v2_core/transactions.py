"""Ledger transaction models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional
import uuid


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass(slots=True)
class OnChainRecord:
    chain: str
    tx_hash: str
    from_address: str
    to_address: str
    block_number: Optional[int] = None
    block_hash: Optional[str] = None
    gas_used: Optional[int] = None
    explorer_url: Optional[str] = None
    status: str = "pending"
    confirmed_at: Optional[datetime] = None


@dataclass(slots=True)
class Transaction:
    tx_id: str = field(default_factory=lambda: f"tx_{uuid.uuid4().hex[:20]}")
    from_wallet: str = ""
    to_wallet: str = ""
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    fee: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"
    purpose: Optional[str] = None
    status: TransactionStatus = TransactionStatus.PENDING
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    on_chain_records: List[OnChainRecord] = field(default_factory=list)
    is_settled_on_chain: bool = False
    settlement_batch_id: Optional[str] = None
    audit_anchor: Optional[str] = None
    idempotency_key: Optional[str] = None

    def total_cost(self) -> Decimal:
        return self.amount + self.fee

    def mark_completed(self) -> None:
        self.status = TransactionStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        self.status = TransactionStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.now(timezone.utc)

    def add_on_chain_record(self, record: OnChainRecord) -> None:
        self.on_chain_records.append(record)
        if record.status == "confirmed":
            self.is_settled_on_chain = True

    def get_primary_tx_hash(self) -> Optional[str]:
        for record in self.on_chain_records:
            if record.status == "confirmed":
                return record.tx_hash
        if self.on_chain_records:
            return self.on_chain_records[0].tx_hash
        return None

    def to_verification_dict(self) -> dict:
        return {
            "sardis_tx_id": self.tx_id,
            "amount": str(self.amount),
            "fee": str(self.fee),
            "currency": self.currency,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "audit_anchor": self.audit_anchor,
            "is_on_chain": self.is_settled_on_chain,
            "chain_records": [
                {
                    "chain": record.chain,
                    "tx_hash": record.tx_hash,
                    "block_number": record.block_number,
                    "explorer_url": record.explorer_url,
                    "status": record.status,
                }
                for record in self.on_chain_records
            ],
        }
