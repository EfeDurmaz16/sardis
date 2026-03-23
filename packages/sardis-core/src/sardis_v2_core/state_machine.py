"""Payment State Machine — 22-state lifecycle for payment objects.

Every payment in Sardis transitions through a well-defined set of states,
from issuance through settlement, escrow, disputes, and terminal outcomes.
This module enforces those transitions and produces an immutable audit trail.

State categories:
─────────────────────────────────────────────────────────────────────
  Happy path:    issued → presented → verified → locked → settling → settled → fulfilled
  Escrow path:   verified → escrowed → confirming → released
  Dispute path:  escrowed/confirming → disputing → arbitrating → resolved_*
  Terminal:      revoked, expired, failed, refunded, cancelled
  Special:       partial_settled, unlocking
─────────────────────────────────────────────────────────────────────

Usage::

    from sardis_v2_core.state_machine import PaymentStateMachine, PaymentState

    machine = PaymentStateMachine(payment_object_id="po_abc123def456")
    record = machine.transition(
        to_state=PaymentState.PRESENTED,
        actor="merchant_sdk",
        reason="Merchant scanned QR code",
    )
    assert machine.current_state == PaymentState.PRESENTED
    assert len(machine.transition_log) == 1

    # Check what's available from the current state
    available = machine.available_transitions()
    # → [(PaymentState.VERIFIED, "verify"), (PaymentState.REVOKED, "revoke"), ...]

See also:
  - ``state_handlers.py`` — async entry/exit callbacks per state
  - ``settlement_lock.py`` — advisory lock to prevent double-settlement
  - ``settlement.py`` — settlement tracking and reconciliation
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.state_machine")


# =============================================================================
# Payment States
# =============================================================================

class PaymentState(str, Enum):
    """All 22 states in the payment object lifecycle."""

    # Happy path
    ISSUED = "issued"                    # Payment object minted
    PRESENTED = "presented"              # Shown to merchant for verification
    VERIFIED = "verified"                # Merchant verified signatures
    LOCKED = "locked"                    # Funds locked, ready for settlement
    SETTLING = "settling"                # On-chain settlement in progress
    SETTLED = "settled"                  # Settlement confirmed on-chain
    FULFILLED = "fulfilled"              # Delivery confirmed by both parties

    # Escrow path
    ESCROWED = "escrowed"               # Funds held in escrow contract
    CONFIRMING = "confirming"            # Awaiting delivery confirmation
    AUTO_RELEASING = "auto_releasing"    # Timelock expired, auto-releasing
    RELEASED = "released"               # Escrow released to merchant

    # Dispute path
    DISPUTING = "disputing"             # Dispute filed
    ARBITRATING = "arbitrating"          # Under arbitration
    RESOLVED_REFUND = "resolved_refund"  # Resolved: full refund to payer
    RESOLVED_RELEASE = "resolved_release"  # Resolved: released to merchant
    RESOLVED_SPLIT = "resolved_split"    # Resolved: split between parties

    # Terminal states
    REVOKED = "revoked"                 # Cancelled before settlement
    EXPIRED = "expired"                 # Past expiration without settlement
    FAILED = "failed"                   # Settlement failed on-chain
    REFUNDED = "refunded"              # Refund processed

    # Special states
    PARTIAL_SETTLED = "partial_settled"  # Partial amount settled
    UNLOCKING = "unlocking"             # Funds being unlocked
    CANCELLED = "cancelled"             # Cancelled by payer


# =============================================================================
# Valid State Transitions
# =============================================================================

# Maps (from_state, to_state) → transition_name.
# Any transition not in this dict is invalid and will be rejected.
VALID_TRANSITIONS: dict[tuple[PaymentState, PaymentState], str] = {
    # ── Happy path ────────────────────────────────────────────────
    (PaymentState.ISSUED, PaymentState.PRESENTED): "present",
    (PaymentState.PRESENTED, PaymentState.VERIFIED): "verify",
    (PaymentState.VERIFIED, PaymentState.LOCKED): "lock",
    (PaymentState.LOCKED, PaymentState.SETTLING): "settle",
    (PaymentState.SETTLING, PaymentState.SETTLED): "confirm_settlement",
    (PaymentState.SETTLED, PaymentState.FULFILLED): "fulfill",

    # ── Escrow path ───────────────────────────────────────────────
    (PaymentState.VERIFIED, PaymentState.ESCROWED): "escrow",
    (PaymentState.ESCROWED, PaymentState.CONFIRMING): "await_delivery",
    (PaymentState.CONFIRMING, PaymentState.RELEASED): "confirm_delivery",
    (PaymentState.ESCROWED, PaymentState.AUTO_RELEASING): "timelock_expire",
    (PaymentState.AUTO_RELEASING, PaymentState.RELEASED): "auto_release",

    # ── Dispute path ──────────────────────────────────────────────
    (PaymentState.ESCROWED, PaymentState.DISPUTING): "dispute",
    (PaymentState.CONFIRMING, PaymentState.DISPUTING): "dispute",
    (PaymentState.DISPUTING, PaymentState.ARBITRATING): "arbitrate",
    (PaymentState.ARBITRATING, PaymentState.RESOLVED_REFUND): "resolve_refund",
    (PaymentState.ARBITRATING, PaymentState.RESOLVED_RELEASE): "resolve_release",
    (PaymentState.ARBITRATING, PaymentState.RESOLVED_SPLIT): "resolve_split",

    # ── Terminal transitions ──────────────────────────────────────
    (PaymentState.ISSUED, PaymentState.REVOKED): "revoke",
    (PaymentState.PRESENTED, PaymentState.REVOKED): "revoke",
    (PaymentState.ISSUED, PaymentState.EXPIRED): "expire",
    (PaymentState.PRESENTED, PaymentState.EXPIRED): "expire",
    (PaymentState.VERIFIED, PaymentState.EXPIRED): "expire",
    (PaymentState.LOCKED, PaymentState.EXPIRED): "expire",
    (PaymentState.SETTLING, PaymentState.FAILED): "fail",
    (PaymentState.SETTLED, PaymentState.REFUNDED): "refund",
    (PaymentState.FULFILLED, PaymentState.REFUNDED): "refund",

    # ── Special transitions ───────────────────────────────────────
    (PaymentState.SETTLING, PaymentState.PARTIAL_SETTLED): "partial_settle",
    (PaymentState.LOCKED, PaymentState.UNLOCKING): "unlock",
    (PaymentState.UNLOCKING, PaymentState.CANCELLED): "cancel",
    (PaymentState.ISSUED, PaymentState.CANCELLED): "cancel",
}

# States from which no further transitions are possible.
# Computed from VALID_TRANSITIONS: a state is terminal if it never
# appears as a ``from_state`` in any transition.
TERMINAL_STATES: frozenset[PaymentState] = frozenset(
    state for state in PaymentState
    if not any(from_s == state for (from_s, _) in VALID_TRANSITIONS)
)


# =============================================================================
# State Transition Record
# =============================================================================

@dataclass
class StateTransitionRecord:
    """Immutable audit record for a single state transition.

    Every call to ``PaymentStateMachine.transition()`` produces one of these.
    They form an append-only log that can be persisted to the ledger for
    compliance and dispute resolution.
    """

    payment_object_id: str
    from_state: PaymentState
    to_state: PaymentState
    transition_name: str
    actor: str
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: str = field(default_factory=lambda: f"str_{uuid4().hex[:16]}")


# =============================================================================
# Payment State Machine
# =============================================================================

@dataclass
class PaymentStateMachine:
    """Manages the lifecycle of a payment object through 22 states.

    The state machine enforces valid transitions, rejects illegal moves,
    and maintains an append-only log of every state change.

    Thread-safety note: this is an in-memory data structure.  For
    concurrent access (e.g. multiple API workers), use ``SettlementLock``
    to acquire an advisory lock before mutating state.

    Usage::

        machine = PaymentStateMachine(payment_object_id="po_abc123")
        machine.transition(PaymentState.PRESENTED, actor="merchant_sdk")
        machine.transition(PaymentState.VERIFIED, actor="merchant_verifier")
        machine.transition(PaymentState.LOCKED, actor="sardis_core")

        assert machine.current_state == PaymentState.LOCKED
        assert len(machine.transition_log) == 3
        assert machine.is_terminal() is False
    """

    payment_object_id: str
    current_state: PaymentState = PaymentState.ISSUED
    transition_log: list[StateTransitionRecord] = field(default_factory=list)

    def can_transition(self, to_state: PaymentState) -> bool:
        """Check whether a transition to ``to_state`` is valid.

        Returns True if the transition is defined in ``VALID_TRANSITIONS``
        and the machine is not already in a terminal state.
        """
        if self.current_state in TERMINAL_STATES:
            return False
        return (self.current_state, to_state) in VALID_TRANSITIONS

    def transition(
        self,
        to_state: PaymentState,
        actor: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StateTransitionRecord:
        """Validate and perform a state transition.

        Args:
            to_state: The target state.
            actor: Who or what triggered this transition (e.g. "merchant_sdk",
                   "sardis_core", "arbitrator_usr_abc").
            reason: Optional human-readable reason for the transition.
            metadata: Optional key-value context (tx_hash, dispute_id, etc.).

        Returns:
            A ``StateTransitionRecord`` capturing the full audit trail.

        Raises:
            ValueError: If the transition is not valid from the current state.
        """
        key = (self.current_state, to_state)
        if key not in VALID_TRANSITIONS:
            valid_targets = [
                f"{t[1].value} ({name})"
                for t, name in VALID_TRANSITIONS.items()
                if t[0] == self.current_state
            ]
            raise ValueError(
                f"Invalid payment state transition: "
                f"{self.current_state.value} -> {to_state.value}. "
                f"Valid transitions from {self.current_state.value}: "
                f"{valid_targets or ['none (terminal state)']}"
            )

        transition_name = VALID_TRANSITIONS[key]
        from_state = self.current_state

        record = StateTransitionRecord(
            payment_object_id=self.payment_object_id,
            from_state=from_state,
            to_state=to_state,
            transition_name=transition_name,
            actor=actor,
            reason=reason,
            metadata=metadata or {},
        )

        # Commit the state change
        self.current_state = to_state
        self.transition_log.append(record)

        logger.info(
            "Payment %s transitioned: %s -> %s (%s) by %s%s",
            self.payment_object_id,
            from_state.value,
            to_state.value,
            transition_name,
            actor,
            f" reason={reason}" if reason else "",
        )

        return record

    def is_terminal(self) -> bool:
        """Return True if the machine is in a terminal state."""
        return self.current_state in TERMINAL_STATES

    def available_transitions(self) -> list[tuple[PaymentState, str]]:
        """Return all valid transitions from the current state.

        Returns:
            List of ``(target_state, transition_name)`` tuples.
            Empty list if in a terminal state.
        """
        if self.current_state in TERMINAL_STATES:
            return []
        return [
            (to_state, name)
            for (from_state, to_state), name in VALID_TRANSITIONS.items()
            if from_state == self.current_state
        ]

    def get_transition_history(self) -> list[dict[str, Any]]:
        """Return the full transition log as a list of dicts for serialization."""
        return [
            {
                "id": record.id,
                "payment_object_id": record.payment_object_id,
                "from_state": record.from_state.value,
                "to_state": record.to_state.value,
                "transition_name": record.transition_name,
                "actor": record.actor,
                "reason": record.reason,
                "metadata": record.metadata,
                "created_at": record.created_at.isoformat(),
            }
            for record in self.transition_log
        ]
