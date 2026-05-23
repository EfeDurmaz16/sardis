"""Payment Object — the one-time-use payment token minted from spending mandates.

A PaymentObject is an atomic, signed, single-use authorization token that
bridges an off-chain spending mandate to an on-chain settlement.  It is the
unit that merchants receive and verify before accepting payment.

Lifecycle:
──────────

    SpendingMandate (ongoing authority)
        │
        ▼
    PaymentObjectMinter.mint()
        │
        ▼
    ┌─────────────────────────────────────────────────────┐
    │  MINTED                                             │
    │  → Created, signed by [principal, issuer, agent]    │
    │  → Funding cells claimed from mandate budget        │
    ├─────────────────────────────────────────────────────┤
    │  PRESENTED                                          │
    │  → Shown to merchant for verification               │
    ├─────────────────────────────────────────────────────┤
    │  VERIFIED                                           │
    │  → Merchant confirmed signature chain               │
    ├─────────────────────────────────────────────────────┤
    │  LOCKED                                             │
    │  → Funds locked in escrow for settlement            │
    ├─────────────────────────────────────────────────────┤
    │  SETTLING                                           │
    │  → On-chain settlement transaction submitted        │
    ├─────────────────────────────────────────────────────┤
    │  SETTLED                                            │
    │  → On-chain settlement confirmed                    │
    ├─────────────────────────────────────────────────────┤
    │  FULFILLED                                          │
    │  → Delivery confirmed, payment complete             │
    └─────────────────────────────────────────────────────┘

    Terminal states: SETTLED, FULFILLED, REVOKED, EXPIRED, FAILED, REFUNDED

    Side paths:
      MINTED/PRESENTED/VERIFIED → REVOKED   (cancelled before settlement)
      MINTED/PRESENTED/VERIFIED → EXPIRED   (past expiration)
      LOCKED/SETTLING → FAILED              (settlement failed)
      SETTLED → FULFILLED                   (delivery confirmed)
      LOCKED → ESCROWED                     (dispute hold)
      ESCROWED → DISPUTING                  (under dispute)
      SETTLED/FULFILLED → REFUNDED          (refund processed)

Key invariants:
  - PaymentObjects are ALWAYS one-time-use (one_time_use=True).
  - The signature_chain must contain signatures from principal, issuer, and agent.
  - The session_hash provides replay protection — no two payment objects
    can share the same session hash.
  - The compute_hash() method produces a deterministic SHA-256 digest of the
    core fields for integrity verification.

Usage::

    po = PaymentObject(
        mandate_id="mandate_abc123",
        cell_ids=["cell_001", "cell_002"],
        merchant_id="merchant_openai",
        exact_amount=Decimal("49.99"),
        signature_chain=["sig_principal", "sig_issuer", "sig_agent"],
        session_hash="a1b2c3...",
    )
    assert po.status == PaymentObjectStatus.MINTED
    assert po.is_terminal() is False
    integrity = po.compute_hash()

See also:
  - ``spending_mandate.py`` — the mandate that authorizes minting.
  - ``minter.py`` — the service that creates PaymentObjects.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.payment_object")


class PaymentObjectStatus(str, Enum):
    """Lifecycle states for a payment object."""
    MINTED = "minted"            # Created and signed
    PRESENTED = "presented"      # Shown to merchant
    VERIFIED = "verified"        # Merchant verified signatures
    LOCKED = "locked"            # Funds locked for settlement
    SETTLING = "settling"        # On-chain settlement in progress
    SETTLED = "settled"          # Settlement confirmed
    FULFILLED = "fulfilled"      # Delivery confirmed
    ESCROWED = "escrowed"        # In escrow hold
    DISPUTING = "disputing"      # Under dispute
    REVOKED = "revoked"          # Cancelled before settlement
    EXPIRED = "expired"          # Past expiration
    FAILED = "failed"            # Settlement failed
    REFUNDED = "refunded"        # Refund processed


class PrivacyTier(str, Enum):
    """Privacy level for payment object data exposure."""
    TRANSPARENT = "transparent"  # Full payment details visible on-chain
    HYBRID = "hybrid"            # Amount visible, parties hashed
    FULL_ZK = "full_zk"          # Zero-knowledge proof, no details exposed


# Terminal states — once a payment object reaches one of these, no further
# transitions are possible (except SETTLED → FULFILLED / REFUNDED).
_TERMINAL_STATES: frozenset[PaymentObjectStatus] = frozenset({
    PaymentObjectStatus.FULFILLED,
    PaymentObjectStatus.REVOKED,
    PaymentObjectStatus.EXPIRED,
    PaymentObjectStatus.FAILED,
    PaymentObjectStatus.REFUNDED,
})

# Valid state transitions: from_status → set of allowed to_statuses
VALID_TRANSITIONS: dict[PaymentObjectStatus, set[PaymentObjectStatus]] = {
    PaymentObjectStatus.MINTED: {
        PaymentObjectStatus.PRESENTED,
        PaymentObjectStatus.REVOKED,
        PaymentObjectStatus.EXPIRED,
    },
    PaymentObjectStatus.PRESENTED: {
        PaymentObjectStatus.VERIFIED,
        PaymentObjectStatus.REVOKED,
        PaymentObjectStatus.EXPIRED,
    },
    PaymentObjectStatus.VERIFIED: {
        PaymentObjectStatus.LOCKED,
        PaymentObjectStatus.REVOKED,
        PaymentObjectStatus.EXPIRED,
    },
    PaymentObjectStatus.LOCKED: {
        PaymentObjectStatus.SETTLING,
        PaymentObjectStatus.ESCROWED,
        PaymentObjectStatus.FAILED,
    },
    PaymentObjectStatus.SETTLING: {
        PaymentObjectStatus.SETTLED,
        PaymentObjectStatus.FAILED,
    },
    PaymentObjectStatus.SETTLED: {
        PaymentObjectStatus.FULFILLED,
        PaymentObjectStatus.REFUNDED,
    },
    PaymentObjectStatus.FULFILLED: set(),       # Terminal
    PaymentObjectStatus.ESCROWED: {
        PaymentObjectStatus.DISPUTING,
        PaymentObjectStatus.SETTLED,            # Dispute resolved in favor of merchant
    },
    PaymentObjectStatus.DISPUTING: {
        PaymentObjectStatus.SETTLED,            # Resolved in favor of merchant
        PaymentObjectStatus.REFUNDED,           # Resolved in favor of payer
    },
    PaymentObjectStatus.REVOKED: set(),         # Terminal
    PaymentObjectStatus.EXPIRED: set(),         # Terminal
    PaymentObjectStatus.FAILED: set(),          # Terminal
    PaymentObjectStatus.REFUNDED: set(),        # Terminal
}


@dataclass
class PaymentObject:
    """A one-time-use payment token minted from a spending mandate.

    PaymentObjects are the atomic unit of payment in Sardis.  Each object
    represents an exact amount payable to a specific merchant, backed by
    claimed funding cells from a spending mandate.

    The signature chain (principal → issuer → agent) provides a
    cryptographic proof of authorization, and the session hash prevents
    replay attacks.
    """
    # Identity
    mandate_id: str                                       # Source spending mandate
    merchant_id: str                                      # Payable to this merchant
    object_id: str = field(default_factory=lambda: f"po_{uuid4().hex[:16]}")

    # Funding
    cell_ids: list[str] = field(default_factory=list)     # Funding cells claimed
    exact_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"

    # Security
    one_time_use: bool = True                             # Always true
    signature_chain: list[str] = field(default_factory=list)  # [principal, issuer, agent]
    session_hash: str = ""                                # Replay protection hash

    # Expiration
    expires_at: datetime | None = None

    # Lifecycle
    status: PaymentObjectStatus = PaymentObjectStatus.MINTED

    # Privacy
    privacy_tier: PrivacyTier = PrivacyTier.TRANSPARENT

    # Audit
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of core fields for integrity verification.

        The hash covers the immutable identity and financial fields so that
        any tampering with the payment object can be detected.  Mutable
        fields (status, metadata) are intentionally excluded.

        Returns:
            Hex-encoded SHA-256 digest of the canonical JSON representation.
        """
        canonical = {
            "object_id": self.object_id,
            "mandate_id": self.mandate_id,
            "merchant_id": self.merchant_id,
            "cell_ids": sorted(self.cell_ids),
            "exact_amount": str(self.exact_amount),
            "currency": self.currency,
            "one_time_use": self.one_time_use,
            "session_hash": self.session_hash,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "privacy_tier": self.privacy_tier.value,
            "created_at": self.created_at.isoformat(),
        }
        return hashlib.sha256(
            json.dumps(canonical, sort_keys=True).encode()
        ).hexdigest()

    def is_terminal(self) -> bool:
        """Return True if the payment object is in a terminal state.

        Terminal states are final — no further transitions are valid.
        """
        return self.status in _TERMINAL_STATES

    def is_expired(self) -> bool:
        """Return True if the payment object has passed its expiration time."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def can_transition_to(self, target: PaymentObjectStatus) -> bool:
        """Check whether a transition to the target status is valid."""
        allowed = VALID_TRANSITIONS.get(self.status, set())
        return target in allowed

    def transition(
        self,
        to_status: PaymentObjectStatus,
        *,
        reason: str | None = None,
    ) -> None:
        """Transition the payment object to a new status.

        Validates the transition is allowed according to VALID_TRANSITIONS.
        Raises ValueError if the transition is invalid.

        Args:
            to_status: Target status.
            reason: Optional human-readable reason for the transition.
        """
        if not self.can_transition_to(to_status):
            allowed = VALID_TRANSITIONS.get(self.status, set())
            raise ValueError(
                f"Invalid payment object transition: {self.status.value} -> "
                f"{to_status.value}. Valid transitions from {self.status.value}: "
                f"{sorted(s.value for s in allowed)}"
            )

        old_status = self.status
        self.status = to_status

        logger.info(
            "PaymentObject %s transitioned: %s -> %s (reason: %s)",
            self.object_id,
            old_status.value,
            to_status.value,
            reason,
        )

    def __repr__(self) -> str:
        return (
            f"PaymentObject(id={self.object_id!r}, mandate={self.mandate_id!r}, "
            f"amount={self.exact_amount}, merchant={self.merchant_id!r}, "
            f"status={self.status.value!r})"
        )
