"""RecourseHold — the Programmable Recourse primitive (LIGHT).

A payment can carry a *policy-defined, time-boxed recourse window*.  When it
does, the orchestrator opens a :class:`RecourseHold` after a successful
execution instead of treating the payment as immediately final.  Funds (or a
claim on them) sit in the hold for the window; the hold then resolves down a
single fail-closed path::

    held ──expire(window passed)──▶ released   (settle to recipient)
      │
      ├──refund(within window)────▶ refunded   (return to payer, <= held)
      │
      └──dispute──────────────────▶ disputed ──┬─resolve_refund─▶ resolved (refund)
                                                └─resolve_release▶ resolved (release)

Sardis owns the **decision / policy / evidence** — that is the moat.  The
escrow contract (vendored Circle ``RefundProtocol``) and the reverse-transfer
are *swappable execution*, behind :class:`sardis.core.recourse_executor` —
this module never imports a chain client or vendor SDK.

Invariants (fail-closed):

* a hold cannot be released twice (no double-release);
* a refund can never exceed the held amount (``refunded <= held``);
* a dispute resolves through exactly one path (refund **or** release);
* every transition out of a state records a **signed**
  :class:`~sardis.core.approval_request.DecisionEvidence`, whose
  ``decision_hash`` binds the transition to the immutable hold identity and the
  policy/mandate snapshot captured when the hold opened.

Money is :class:`~decimal.Decimal` plus exact integer minor-units throughout.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

from .approval_request import DecisionEvidence, _as_decimal, _to_base36

# ── Identifiers ────────────────────────────────────────────────────────


def new_recourse_id() -> str:
    """``rch_<base36 ts>_<rand>`` — the durable RecourseHold identifier."""
    ts = _to_base36(int(time.time()))
    return f"rch_{ts}_{secrets.token_hex(4)}"


# ── State machine ──────────────────────────────────────────────────────


class RecourseStatus(str, Enum):
    """Lifecycle of a recourse hold.  ``HELD`` and ``DISPUTED`` are the only
    non-terminal states."""

    HELD = "held"  # window open — funds/claim parked
    RELEASED = "released"  # window expired → settled to recipient (terminal)
    REFUNDED = "refunded"  # within window → returned to payer (terminal)
    DISPUTED = "disputed"  # dispute filed — awaiting resolution
    RESOLVED = "resolved"  # dispute resolved (terminal; resolution=refund|release)


_TERMINAL = {RecourseStatus.RELEASED, RecourseStatus.REFUNDED, RecourseStatus.RESOLVED}

# Allowed transitions.  Anything not listed is rejected (fail-closed).
_ALLOWED: dict[RecourseStatus, frozenset[RecourseStatus]] = {
    RecourseStatus.HELD: frozenset(
        {RecourseStatus.RELEASED, RecourseStatus.REFUNDED, RecourseStatus.DISPUTED}
    ),
    RecourseStatus.DISPUTED: frozenset({RecourseStatus.RESOLVED}),
    RecourseStatus.RELEASED: frozenset(),
    RecourseStatus.REFUNDED: frozenset(),
    RecourseStatus.RESOLVED: frozenset(),
}


class Resolution(str, Enum):
    """How a transition settled the money.  Recorded as the hold's resolution."""

    RELEASE = "release"  # settled to recipient
    REFUND = "refund"  # returned to payer


class RecourseStateError(RuntimeError):
    """Raised on an illegal state transition (e.g. releasing a refunded hold)."""


class RecourseAmountError(RuntimeError):
    """Raised when a refund would exceed the held amount (fail-closed)."""


# ── Signing key (mirrors ExecutionReceipt / ApprovalRequest) ───────────


def _resolve_recourse_key(secret: str | None) -> bytes:
    """Resolve the HMAC signing key for recourse evidence.

    Explicit secret wins; otherwise ``SARDIS_RECOURSE_HMAC_KEY``; otherwise a
    ``dev-`` fallback — but ONLY outside production/staging, where a missing key
    fails closed (refuses to sign).
    """
    resolved = secret or os.getenv("SARDIS_RECOURSE_HMAC_KEY", "")
    if not resolved:
        env = os.getenv("SARDIS_ENVIRONMENT", os.getenv("SARDIS_ENV", "dev")).strip().lower()
        if env in ("prod", "production", "staging"):
            raise RuntimeError(
                "SARDIS_RECOURSE_HMAC_KEY must be set in production/staging. "
                "Refusing to sign recourse evidence with a default key."
            )
        resolved = "dev-recourse-key"
    return resolved


# ── The durable RecourseHold object ────────────────────────────────────


@dataclass
class RecourseHold:
    """A durable, signed, time-boxed recourse hold on a settled payment.

    Carries the money (Decimal + exact minor-units), the parties, the window,
    the bound policy/mandate snapshot hashes (so a transition's evidence is
    pinned to the state in effect when the hold opened), and the signed
    :class:`DecisionEvidence` for the latest transition.
    """

    # Identity / linkage
    id: str
    payment_ref: str  # payment_object_id / mandate_id the hold backs
    mandate_id: str | None
    agent_id: str | None

    # Money — Decimal + exact integer minor-units (never float).
    amount: Decimal
    amount_minor: int
    currency: str

    # Parties
    payer: str  # refundTo — gets the money back on refund
    recipient: str  # to — gets the money on release

    # Window
    opened_at: datetime
    expires_at: datetime

    # State
    status: RecourseStatus = RecourseStatus.HELD
    resolution: Resolution | None = None
    refunded_minor: int = 0  # cumulative minor-units returned to payer
    resolved_at: datetime | None = None
    resolved_by: str | None = None

    # Bound snapshot hashes (captured when the hold opened; pin the evidence).
    policy_hash: str = ""
    mandate_hash: str = ""

    # Swappable-execution references (set by the executor; opaque here).
    escrow_contract: str | None = None
    escrow_payment_id: str | None = None  # RefundProtocol paymentID (uint)
    open_tx_hash: str | None = None
    settle_tx_hash: str | None = None

    # Signed evidence for the LATEST transition out of HELD/DISPUTED.
    evidence: DecisionEvidence | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.amount = _as_decimal(self.amount)
        self.amount_minor = int(self.amount_minor)
        self.refunded_minor = int(self.refunded_minor)

    # ----- predicates -----

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL

    def is_expired(self, *, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        return self.status == RecourseStatus.HELD and now >= self.expires_at

    @property
    def refundable_minor(self) -> int:
        """Minor-units still available to refund (held minus already refunded)."""
        return self.amount_minor - self.refunded_minor

    # ----- canonical hold payload (immutable identity fields only) -----

    def _canonical(self) -> str:
        payload = {
            "id": self.id,
            "payment_ref": self.payment_ref,
            "mandate_id": self.mandate_id,
            "agent_id": self.agent_id,
            "amount": str(self.amount),
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "payer": self.payer,
            "recipient": self.recipient,
            "opened_at": self.opened_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "policy_hash": self.policy_hash,
            "mandate_hash": self.mandate_hash,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    def hold_hash(self) -> str:
        return hashlib.sha256(self._canonical().encode("utf-8")).hexdigest()

    # ----- evidence -----

    def _record_evidence(
        self,
        *,
        decision: str,
        actor: str,
        secret: str | None,
    ) -> DecisionEvidence:
        """Build + sign a DecisionEvidence binding this transition to the hold.

        Reuses the ApprovalRequest signing pattern: the ``decision_hash`` covers
        the hold identity (via ``request_hash``) + the bound policy/mandate
        snapshot, and the signature covers the decision hash so any field
        tamper invalidates both.
        """
        decided_at = datetime.now(UTC)
        ev = DecisionEvidence(
            approval_id=self.id,
            decision=decision,
            approver=actor,
            channel="system",
            decided_at=decided_at,
            request_hash=self.hold_hash(),
            policy_hash=self.policy_hash,
            mandate_hash=self.mandate_hash,
            decision_hash="",
            signature="",
        ).sign(_resolve_recourse_key(secret))
        self.evidence = ev
        return ev

    def _guard(self, target: RecourseStatus) -> None:
        allowed = _ALLOWED.get(self.status, frozenset())
        if target not in allowed:
            raise RecourseStateError(
                f"illegal recourse transition {self.status.value} -> {target.value} "
                f"for {self.id}"
            )

    def check_can_release(self) -> None:
        """Non-mutating legality check for a release (raises on illegal)."""
        self._guard(RecourseStatus.RELEASED)

    def check_can_refund(self, amount_minor: int | None = None) -> None:
        """Non-mutating legality + amount check for a refund (raises on illegal).

        Lets the engine validate fail-closed BEFORE invoking the executor, so a
        failed money-movement never leaves a half-mutated hold."""
        self._guard(RecourseStatus.REFUNDED)
        amt = self.refundable_minor if amount_minor is None else int(amount_minor)
        if amt <= 0 or amt > self.refundable_minor:
            raise RecourseAmountError(
                f"refund {amt} outside (0, {self.refundable_minor}] for {self.id} "
                f"(held={self.amount_minor})"
            )

    def check_can_resolve(
        self, resolution: Resolution, amount_minor: int | None = None
    ) -> None:
        """Non-mutating legality + amount check for a dispute resolution."""
        self._guard(RecourseStatus.RESOLVED)
        if resolution == Resolution.REFUND:
            amt = self.refundable_minor if amount_minor is None else int(amount_minor)
            if amt <= 0 or amt > self.refundable_minor:
                raise RecourseAmountError(
                    f"resolve-refund {amt} outside (0, {self.refundable_minor}] "
                    f"for {self.id}"
                )

    # ----- state transitions (each produces signed evidence) -----

    def release(
        self, *, actor: str = "system", secret: str | None = None
    ) -> DecisionEvidence:
        """Window expired (or delivery confirmed): settle to the recipient.

        Fail-closed: a hold can only be released from ``HELD`` — a second
        release (or releasing a refunded hold) raises.
        """
        self._guard(RecourseStatus.RELEASED)
        ev = self._record_evidence(decision="released", actor=actor, secret=secret)
        self.status = RecourseStatus.RELEASED
        self.resolution = Resolution.RELEASE
        self.resolved_at = ev.decided_at
        self.resolved_by = actor
        return ev

    def refund(
        self,
        *,
        amount_minor: int | None = None,
        actor: str = "system",
        secret: str | None = None,
    ) -> DecisionEvidence:
        """Within window: return funds to the payer (full or partial).

        Fail-closed: ``amount_minor`` defaults to the full refundable balance
        and may never exceed it (``refunded <= held``).  A partial refund still
        terminates the hold as ``REFUNDED`` — the unrefunded remainder is the
        recipient's; the remainder is settled out-of-band on release of the
        residual claim.  The light primitive treats refund as terminal.
        """
        self._guard(RecourseStatus.REFUNDED)
        amt = self.refundable_minor if amount_minor is None else int(amount_minor)
        if amt <= 0:
            raise RecourseAmountError(
                f"refund amount must be positive for {self.id} (got {amt})"
            )
        if amt > self.refundable_minor:
            raise RecourseAmountError(
                f"refund {amt} exceeds refundable balance {self.refundable_minor} "
                f"for {self.id} (held={self.amount_minor})"
            )
        ev = self._record_evidence(decision="refunded", actor=actor, secret=secret)
        self.refunded_minor += amt
        self.status = RecourseStatus.REFUNDED
        self.resolution = Resolution.REFUND
        self.resolved_at = ev.decided_at
        self.resolved_by = actor
        return ev

    def dispute(
        self,
        *,
        actor: str,
        reason: str | None = None,
        secret: str | None = None,
    ) -> DecisionEvidence:
        """Open a dispute within the window.  Pauses auto-release; the hold can
        now only move to ``RESOLVED``."""
        self._guard(RecourseStatus.DISPUTED)
        if reason:
            self.metadata["dispute_reason"] = reason
        self.metadata["disputed_by"] = actor
        ev = self._record_evidence(decision="disputed", actor=actor, secret=secret)
        self.status = RecourseStatus.DISPUTED
        return ev

    def resolve(
        self,
        *,
        resolution: Resolution,
        actor: str,
        amount_minor: int | None = None,
        secret: str | None = None,
    ) -> DecisionEvidence:
        """Resolve a disputed hold down exactly one path: refund or release.

        Fail-closed: only valid from ``DISPUTED``; a refund resolution may not
        exceed the held amount.
        """
        self._guard(RecourseStatus.RESOLVED)
        if resolution == Resolution.REFUND:
            amt = self.refundable_minor if amount_minor is None else int(amount_minor)
            if amt <= 0 or amt > self.refundable_minor:
                raise RecourseAmountError(
                    f"resolve-refund {amt} outside (0, {self.refundable_minor}] "
                    f"for {self.id}"
                )
            self.refunded_minor += amt
        ev = self._record_evidence(
            decision=f"resolved_{resolution.value}", actor=actor, secret=secret
        )
        self.status = RecourseStatus.RESOLVED
        self.resolution = resolution
        self.resolved_at = ev.decided_at
        self.resolved_by = actor
        return ev

    # ----- serialization -----

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "payment_ref": self.payment_ref,
            "mandate_id": self.mandate_id,
            "agent_id": self.agent_id,
            "amount": str(self.amount),
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "payer": self.payer,
            "recipient": self.recipient,
            "opened_at": self.opened_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "resolution": self.resolution.value if self.resolution else None,
            "refunded_minor": self.refunded_minor,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "policy_hash": self.policy_hash,
            "mandate_hash": self.mandate_hash,
            "escrow_contract": self.escrow_contract,
            "escrow_payment_id": self.escrow_payment_id,
            "open_tx_hash": self.open_tx_hash,
            "settle_tx_hash": self.settle_tx_hash,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "metadata": self.metadata,
        }


def build_recourse_hold(
    *,
    payment_ref: str,
    mandate_id: str | None,
    agent_id: str | None,
    amount: Decimal | str | int,
    amount_minor: int,
    currency: str,
    payer: str,
    recipient: str,
    window_seconds: int,
    policy_hash: str = "",
    mandate_hash: str = "",
    metadata: dict[str, Any] | None = None,
) -> RecourseHold:
    """Factory for a fresh ``held`` recourse hold with a time-boxed window."""
    if window_seconds <= 0:
        raise ValueError("recourse window_seconds must be positive")
    now = datetime.now(UTC)
    return RecourseHold(
        id=new_recourse_id(),
        payment_ref=payment_ref,
        mandate_id=mandate_id,
        agent_id=agent_id,
        amount=_as_decimal(amount),
        amount_minor=int(amount_minor),
        currency=currency,
        payer=payer,
        recipient=recipient,
        opened_at=now,
        expires_at=now + timedelta(seconds=window_seconds),
        status=RecourseStatus.HELD,
        policy_hash=policy_hash,
        mandate_hash=mandate_hash,
        metadata=metadata or {},
    )


__all__ = [
    "RecourseAmountError",
    "RecourseHold",
    "RecourseStateError",
    "RecourseStatus",
    "Resolution",
    "build_recourse_hold",
    "new_recourse_id",
]
