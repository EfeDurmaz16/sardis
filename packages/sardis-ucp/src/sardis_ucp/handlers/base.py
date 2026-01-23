"""Base payment handler protocol and types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Protocol

from ..models.mandates import UCPPaymentMandate


class PaymentStatus(str, Enum):
    """Status of a payment execution."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class PaymentReceipt:
    """Receipt from a successful payment execution."""

    mandate_id: str
    chain: str
    token: str
    amount_minor: int
    destination: str
    status: PaymentStatus = PaymentStatus.SUBMITTED

    # Transaction details
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None

    # Audit
    audit_anchor: Optional[str] = None
    ledger_tx_id: Optional[str] = None

    # Timing
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None

    # Error (if failed)
    error: Optional[str] = None
    error_code: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mandate_id": self.mandate_id,
            "chain": self.chain,
            "token": self.token,
            "amount_minor": self.amount_minor,
            "destination": self.destination,
            "status": self.status.value,
            "tx_hash": self.tx_hash,
            "block_number": self.block_number,
            "gas_used": self.gas_used,
            "audit_anchor": self.audit_anchor,
            "ledger_tx_id": self.ledger_tx_id,
            "submitted_at": self.submitted_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "error": self.error,
            "error_code": self.error_code,
            "metadata": self.metadata,
        }


class PaymentHandler(Protocol):
    """Protocol for UCP payment handlers.

    Payment handlers are responsible for executing payments on specific
    payment rails (stablecoins, fiat, etc.).
    """

    @property
    def handler_name(self) -> str:
        """Unique identifier for this handler."""
        ...

    @property
    def supported_tokens(self) -> list[str]:
        """List of supported token symbols."""
        ...

    @property
    def supported_chains(self) -> list[str]:
        """List of supported blockchain networks."""
        ...

    def can_handle(self, mandate: UCPPaymentMandate) -> bool:
        """Check if this handler can process the given mandate."""
        ...

    async def execute(self, mandate: UCPPaymentMandate) -> PaymentReceipt:
        """Execute a payment mandate.

        Args:
            mandate: The payment mandate to execute

        Returns:
            PaymentReceipt with execution result

        Raises:
            PaymentExecutionError: If payment fails
        """
        ...

    async def get_status(self, tx_hash: str) -> PaymentStatus:
        """Get the current status of a transaction.

        Args:
            tx_hash: Transaction hash to check

        Returns:
            Current payment status
        """
        ...


class PaymentExecutionError(Exception):
    """Raised when payment execution fails."""

    def __init__(
        self,
        message: str,
        code: str,
        mandate_id: str | None = None,
        tx_hash: str | None = None,
        details: Dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.mandate_id = mandate_id
        self.tx_hash = tx_hash
        self.details = details or {}


__all__ = [
    "PaymentStatus",
    "PaymentReceipt",
    "PaymentHandler",
    "PaymentExecutionError",
]
