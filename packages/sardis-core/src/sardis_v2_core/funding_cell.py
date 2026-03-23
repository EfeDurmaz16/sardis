"""FundingCell -- UTXO-style funding unit for agent payments.

A FundingCell is an indivisible (or splittable) unit of value carved from a
FundingCommitment.  Cells follow a strict lifecycle:

    AVAILABLE -> CLAIMED -> SPENT
                        \\-> RETURNED -> AVAILABLE (re-entry)
    AVAILABLE -> MERGED  (combined into a larger cell)
    *         -> EXPIRED (commitment expired)

The cell model is inspired by Bitcoin's UTXO set: each payment consumes one
or more cells, and change is returned as a new cell.  This gives us:

- **Double-spend protection** via ``SELECT ... FOR UPDATE SKIP LOCKED``
- **Deterministic audit trails** -- every cent is traceable to a cell
- **Concurrent safety** -- agents compete for cells without deadlocks
- **Natural budget enforcement** -- remaining cells == remaining budget

Usage::

    cell = FundingCell(
        commitment_id="fcom_abc123",
        value=Decimal("10.00"),
        currency="USDC",
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

logger = logging.getLogger("sardis.funding_cell")


class CellStatus(str, Enum):
    """Lifecycle states for a funding cell."""
    AVAILABLE = "available"    # Ready to be claimed
    CLAIMED = "claimed"        # Reserved for a mandate
    SPENT = "spent"            # Used in a payment object
    RETURNED = "returned"      # Released back to available
    MERGED = "merged"          # Combined into another cell
    EXPIRED = "expired"        # Commitment expired


# Valid state transitions: (from_status, to_status) -> transition_name
VALID_CELL_TRANSITIONS: dict[tuple[CellStatus, CellStatus], str] = {
    (CellStatus.AVAILABLE, CellStatus.CLAIMED): "claim",
    (CellStatus.CLAIMED, CellStatus.SPENT): "spend",
    (CellStatus.CLAIMED, CellStatus.RETURNED): "release",
    (CellStatus.RETURNED, CellStatus.AVAILABLE): "recycle",
    (CellStatus.AVAILABLE, CellStatus.MERGED): "merge",
    (CellStatus.AVAILABLE, CellStatus.EXPIRED): "expire",
    (CellStatus.CLAIMED, CellStatus.EXPIRED): "expire",
}


@dataclass
class FundingCell:
    """A single UTXO-style funding unit carved from a FundingCommitment.

    Each cell holds a fixed ``value`` in a given ``currency`` and progresses
    through a deterministic lifecycle tracked by ``status``.
    """
    # Identity
    commitment_id: str                                 # Parent funding commitment
    value: Decimal                                     # Cell value (never float)
    currency: str = "USDC"
    cell_id: str = field(default_factory=lambda: f"cell_{uuid4().hex[:12]}")

    # Lifecycle
    status: CellStatus = CellStatus.AVAILABLE

    # Claim state
    owner_mandate_id: str | None = None                # Mandate that claimed this cell
    claimed_at: datetime | None = None

    # Spend state
    spent_at: datetime | None = None
    payment_object_id: str | None = None               # Payment object that consumed it

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Extensible metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # ---- helpers ----

    @property
    def is_available(self) -> bool:
        """True when the cell can be claimed."""
        return self.status == CellStatus.AVAILABLE

    @property
    def is_claimed(self) -> bool:
        """True when the cell is reserved for a mandate."""
        return self.status == CellStatus.CLAIMED

    @property
    def is_terminal(self) -> bool:
        """True when the cell cannot transition further."""
        return self.status in (CellStatus.SPENT, CellStatus.MERGED, CellStatus.EXPIRED)

    def validate_transition(self, to_status: CellStatus) -> None:
        """Raise ``ValueError`` if the transition is not allowed."""
        key = (self.status, to_status)
        if key not in VALID_CELL_TRANSITIONS:
            valid_targets = [
                t[1].value for t in VALID_CELL_TRANSITIONS if t[0] == self.status
            ]
            raise ValueError(
                f"Invalid cell transition: {self.status.value} -> {to_status.value}. "
                f"Valid targets from {self.status.value}: {valid_targets}"
            )

    def claim(self, mandate_id: str) -> None:
        """Mark cell as claimed by a mandate (in-memory mutation)."""
        self.validate_transition(CellStatus.CLAIMED)
        self.status = CellStatus.CLAIMED
        self.owner_mandate_id = mandate_id
        self.claimed_at = datetime.now(UTC)
        logger.info(
            "Cell %s claimed by mandate %s (value=%s %s)",
            self.cell_id, mandate_id, self.value, self.currency,
        )

    def spend(self, payment_object_id: str) -> None:
        """Mark cell as spent by a payment object (in-memory mutation)."""
        self.validate_transition(CellStatus.SPENT)
        self.status = CellStatus.SPENT
        self.payment_object_id = payment_object_id
        self.spent_at = datetime.now(UTC)
        logger.info(
            "Cell %s spent in payment %s (value=%s %s)",
            self.cell_id, payment_object_id, self.value, self.currency,
        )

    def release(self) -> None:
        """Return the cell so it can be recycled (in-memory mutation)."""
        self.validate_transition(CellStatus.RETURNED)
        self.status = CellStatus.RETURNED
        self.owner_mandate_id = None
        self.claimed_at = None
        logger.info("Cell %s released (value=%s %s)", self.cell_id, self.value, self.currency)

    def __repr__(self) -> str:
        return (
            f"FundingCell(cell_id={self.cell_id!r}, value={self.value}, "
            f"currency={self.currency!r}, status={self.status.value!r})"
        )
