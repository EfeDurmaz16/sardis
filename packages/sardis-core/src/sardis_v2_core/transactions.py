"""Ledger transaction models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .wallets import Wallet


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
    block_number: int | None = None
    block_hash: str | None = None
    gas_used: int | None = None
    explorer_url: str | None = None
    status: str = "pending"
    confirmed_at: datetime | None = None


@dataclass(slots=True)
class Transaction:
    tx_id: str = field(default_factory=lambda: f"tx_{uuid.uuid4().hex[:20]}")
    from_wallet: str = ""
    to_wallet: str = ""
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    fee: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"
    purpose: str | None = None
    status: TransactionStatus = TransactionStatus.PENDING
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    on_chain_records: list[OnChainRecord] = field(default_factory=list)
    is_settled_on_chain: bool = False
    settlement_batch_id: str | None = None
    audit_anchor: str | None = None
    idempotency_key: str | None = None

    def total_cost(self) -> Decimal:
        return self.amount + self.fee

    def mark_completed(self) -> None:
        self.status = TransactionStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

    def mark_failed(self, error: str) -> None:
        self.status = TransactionStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.now(UTC)

    def add_on_chain_record(self, record: OnChainRecord) -> None:
        self.on_chain_records.append(record)
        if record.status == "confirmed":
            self.is_settled_on_chain = True

    def get_primary_tx_hash(self) -> str | None:
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


def validate_wallet_not_frozen(wallet: Wallet) -> tuple[bool, str]:
    """
    Check if wallet is frozen and reject transaction if so.

    Args:
        wallet: Wallet to check

    Returns:
        Tuple of (allowed: bool, reason: str)
    """
    if wallet.is_frozen:
        freeze_info = f"Frozen by {wallet.frozen_by}" if wallet.frozen_by else "Wallet frozen"
        if wallet.freeze_reason:
            freeze_info += f": {wallet.freeze_reason}"
        return False, f"wallet_frozen:{freeze_info}"
    return True, "OK"
