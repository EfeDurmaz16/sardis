"""FundingCommitment -- pre-funded value pool that backs FundingCells.

A FundingCommitment represents a pool of value (e.g. USDC in a vault or
wallet) that has been earmarked for agent spending.  The commitment is
subdivided into FundingCells on demand using one of two strategies:

- **FIXED** -- cells are minted at a fixed denomination (e.g. $10 each).
  Best for high-volume micro-payments where uniform sizing simplifies
  the claim algorithm.
- **PROPORTIONAL** -- cells are carved on demand in the exact amount
  requested.  Best for variable-amount payments where fixed sizes would
  produce excessive change cells.

Lifecycle::

    ACTIVE -> EXHAUSTED  (remaining_value == 0)
    ACTIVE -> EXPIRED    (expires_at passed)
    ACTIVE -> CANCELLED  (manually withdrawn)

Usage::

    commitment = FundingCommitment(
        org_id="org_acme",
        vault_ref="vault_0x1234",
        total_value=Decimal("10000"),
        remaining_value=Decimal("10000"),
        cell_strategy=CellStrategy.FIXED,
        cell_denomination=Decimal("10"),
    )
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.funding_commitment")


class CellStrategy(str, Enum):
    """How cells are carved from a commitment."""
    FIXED = "fixed"                # Fixed denomination cells (e.g. $10 each)
    PROPORTIONAL = "proportional"  # Split proportionally on demand


class CommitmentStatus(str, Enum):
    """Lifecycle states for a funding commitment."""
    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# Valid state transitions: (from_status, to_status) -> transition_name
VALID_COMMITMENT_TRANSITIONS: dict[tuple[CommitmentStatus, CommitmentStatus], str] = {
    (CommitmentStatus.ACTIVE, CommitmentStatus.EXHAUSTED): "exhaust",
    (CommitmentStatus.ACTIVE, CommitmentStatus.EXPIRED): "expire",
    (CommitmentStatus.ACTIVE, CommitmentStatus.CANCELLED): "cancel",
}


@dataclass
class FundingCommitment:
    """A pre-funded value pool that backs FundingCells.

    The commitment tracks ``total_value`` and ``remaining_value`` as cells
    are carved.  When ``remaining_value`` reaches zero the status moves to
    EXHAUSTED automatically.
    """
    # Identity
    org_id: str                                        # Owning organisation
    vault_ref: str                                     # On-chain vault or wallet reference
    total_value: Decimal                               # Original committed amount
    remaining_value: Decimal                           # Unallocated value
    commitment_id: str = field(default_factory=lambda: f"fcom_{uuid4().hex[:12]}")

    # Currency
    currency: str = "USDC"

    # Cell strategy
    cell_strategy: CellStrategy = CellStrategy.FIXED
    cell_denomination: Decimal | None = None           # For FIXED strategy

    # Settlement
    settlement_preferences: dict[str, Any] = field(default_factory=dict)

    # Lifecycle
    status: CommitmentStatus = CommitmentStatus.ACTIVE
    expires_at: datetime | None = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Extensible metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # ---- helpers ----

    @property
    def is_active(self) -> bool:
        """True when the commitment can issue new cells."""
        if self.status != CommitmentStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return False
        return True

    @property
    def utilisation_ratio(self) -> Decimal:
        """Fraction of the total value that has been allocated to cells."""
        if self.total_value == 0:
            return Decimal("0")
        return (self.total_value - self.remaining_value) / self.total_value

    def can_allocate(self, amount: Decimal) -> bool:
        """Check whether ``amount`` can be carved from remaining value."""
        return self.is_active and amount <= self.remaining_value

    def allocate(self, amount: Decimal) -> None:
        """Deduct ``amount`` from remaining value (in-memory mutation).

        Raises ``ValueError`` if the commitment cannot cover the amount.
        Automatically transitions to EXHAUSTED when remaining hits zero.
        """
        if not self.is_active:
            raise ValueError(
                f"Commitment {self.commitment_id} is {self.status.value}, cannot allocate"
            )
        if amount > self.remaining_value:
            raise ValueError(
                f"Commitment {self.commitment_id} has {self.remaining_value} remaining, "
                f"cannot allocate {amount}"
            )
        self.remaining_value -= amount
        logger.info(
            "Commitment %s allocated %s %s (remaining=%s)",
            self.commitment_id, amount, self.currency, self.remaining_value,
        )
        if self.remaining_value == Decimal("0"):
            self.status = CommitmentStatus.EXHAUSTED
            logger.info("Commitment %s exhausted", self.commitment_id)

    def return_value(self, amount: Decimal) -> None:
        """Return ``amount`` to remaining value (e.g. after cell release).

        Re-activates an EXHAUSTED commitment if value is returned.
        """
        self.remaining_value += amount
        if self.remaining_value > self.total_value:
            self.remaining_value = self.total_value
        if self.status == CommitmentStatus.EXHAUSTED and self.remaining_value > Decimal("0"):
            self.status = CommitmentStatus.ACTIVE
            logger.info("Commitment %s re-activated after value return", self.commitment_id)
        logger.info(
            "Commitment %s returned %s %s (remaining=%s)",
            self.commitment_id, amount, self.currency, self.remaining_value,
        )

    def validate_transition(self, to_status: CommitmentStatus) -> None:
        """Raise ``ValueError`` if the transition is not allowed."""
        key = (self.status, to_status)
        if key not in VALID_COMMITMENT_TRANSITIONS:
            valid_targets = [
                t[1].value for t in VALID_COMMITMENT_TRANSITIONS if t[0] == self.status
            ]
            raise ValueError(
                f"Invalid commitment transition: {self.status.value} -> {to_status.value}. "
                f"Valid targets from {self.status.value}: {valid_targets}"
            )

    def transition(self, to_status: CommitmentStatus, reason: str | None = None) -> None:
        """Move commitment to a new lifecycle state (in-memory mutation)."""
        self.validate_transition(to_status)
        old_status = self.status
        self.status = to_status
        logger.info(
            "Commitment %s transitioned: %s -> %s (reason: %s)",
            self.commitment_id, old_status.value, to_status.value, reason,
        )

    def __repr__(self) -> str:
        return (
            f"FundingCommitment(commitment_id={self.commitment_id!r}, "
            f"total={self.total_value}, remaining={self.remaining_value}, "
            f"currency={self.currency!r}, status={self.status.value!r})"
        )
