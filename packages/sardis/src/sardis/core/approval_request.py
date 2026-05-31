"""ApprovalRequest — the durable, signed human-in-the-loop primitive.

The audit found the loop missing: an approvals UI exists, but
``requires_approval`` -> deliver -> approve -> *re-execute through the single
fail-closed path* was never wired.  This module is the ENGINE half of that
loop.  It owns the **decision, the policy/mandate evidence, and the signed
record** (the moat).  Delivery (Twilio / Photon) is swappable and lives behind
:class:`sardis.core.notification_port.NotificationPort` — delivery NEVER decides
the outcome, it only relays the human's decision back to the engine.

An :class:`ApprovalRequest` is a durable object with a strict state machine::

    pending ──approve──▶ approved   (terminal — unlocks ONE re-execution)
       │
       ├────deny──────▶ denied      (terminal — fail-closed, money blocked)
       │
       └────expire────▶ expired     (terminal — fail-closed, money blocked)

Every transition out of ``pending`` is recorded with a **signed decision
evidence bundle**: HMAC-SHA256 over a canonical JSON of the immutable request
fields (mandate/spend identity, agent, amount, counterparty), the bound
``policy_hash`` and ``mandate_hash`` captured at request time, the approver, the
decision, and the timestamp.  The signature key resolution mirrors
:class:`sardis.core.execution_receipt.ExecutionReceipt` — env
``SARDIS_APPROVAL_HMAC_KEY``, fail-closed in production, ``dev-`` fallback only
outside production.

Money is :class:`~decimal.Decimal` throughout.  No vendor SDK is imported here.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any


# ── Identifiers ────────────────────────────────────────────────────────


def new_approval_id() -> str:
    """``apreq_<base36 ts>_<rand>`` — distinct prefix from the legacy
    ``appr_`` UI approvals so the two surfaces never collide."""
    ts = _to_base36(int(time.time()))
    return f"apreq_{ts}_{secrets.token_hex(4)}"


def _to_base36(num: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if num == 0:
        return "0"
    out: list[str] = []
    while num:
        num, rem = divmod(num, 36)
        out.append(chars[rem])
    return "".join(reversed(out))


# ── State machine ──────────────────────────────────────────────────────


class ApprovalState(str, Enum):
    """Lifecycle of an approval request.  Only ``PENDING`` is non-terminal."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


_TERMINAL = {ApprovalState.APPROVED, ApprovalState.DENIED, ApprovalState.EXPIRED}

# Allowed transitions.  Anything not listed is rejected (fail-closed).
_ALLOWED: dict[ApprovalState, frozenset[ApprovalState]] = {
    ApprovalState.PENDING: frozenset(
        {ApprovalState.APPROVED, ApprovalState.DENIED, ApprovalState.EXPIRED}
    ),
    ApprovalState.APPROVED: frozenset(),
    ApprovalState.DENIED: frozenset(),
    ApprovalState.EXPIRED: frozenset(),
}


class ApprovalStateError(RuntimeError):
    """Raised on an illegal state transition (e.g. approving a denied request)."""


class ApprovalSignatureError(RuntimeError):
    """Raised when a decision's signed evidence fails verification."""


# ── Decision channels (who relayed the human's decision) ───────────────


class DecisionChannel(str, Enum):
    """Where the human decision came in from.  Recorded for audit; it never
    affects the outcome — the engine re-checks policy/mandate regardless."""

    DASHBOARD = "dashboard"  # authenticated principal in the product UI
    SMS = "sms"  # Twilio inbound / Verify
    WHATSAPP = "whatsapp"  # Photon/Spectrum relay or Twilio WhatsApp
    IMESSAGE = "imessage"  # Photon/Spectrum relay
    API = "api"  # programmatic (tests / service principals)
    SYSTEM = "system"  # expiry sweep, never a human


# ── Money helpers ──────────────────────────────────────────────────────


def _as_decimal(value: Any) -> Decimal:
    """Coerce to ``Decimal`` without ever going through ``float``."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):  # pragma: no cover - defensive
        raise TypeError("float amounts are forbidden on approval money paths")
    return Decimal(str(value))


# ── Signed decision evidence ───────────────────────────────────────────


def _resolve_hmac_key(secret: str | None) -> bytes:
    """Resolve the HMAC signing key.

    Mirrors :meth:`ExecutionReceipt.compute_signature`: an explicit secret wins;
    otherwise ``SARDIS_APPROVAL_HMAC_KEY``; otherwise a ``dev-`` key — but ONLY
    outside production/staging, where a missing key fails closed.
    """
    resolved = secret or os.getenv("SARDIS_APPROVAL_HMAC_KEY", "")
    if not resolved:
        env = os.getenv("SARDIS_ENVIRONMENT", os.getenv("SARDIS_ENV", "dev")).strip().lower()
        if env in ("prod", "production", "staging"):
            raise RuntimeError(
                "SARDIS_APPROVAL_HMAC_KEY must be set in production/staging. "
                "Refusing to sign approval evidence with a default key."
            )
        resolved = "dev-approval-key"
    return resolved.encode()


@dataclass(slots=True)
class DecisionEvidence:
    """Signed proof of a single human decision on an approval request.

    The hash binds the decision to the *exact* request and the policy/mandate
    snapshot that was in effect when approval was demanded, so a stored decision
    cannot be replayed against a mutated request.  The signature is verifiable
    with the same key by any auditor.
    """

    approval_id: str
    decision: str  # "approved" | "denied" | "expired"
    approver: str  # principal id / email / "system"
    channel: str
    decided_at: datetime
    request_hash: str  # SHA-256 of the immutable request payload
    policy_hash: str  # bound at request time
    mandate_hash: str  # bound at request time
    decision_hash: str  # SHA-256 over the canonical decision payload
    signature: str  # HMAC-SHA256 over decision_hash + identity fields
    step_up_verified: bool = False  # OTP/step-up confirmed for high-value

    # ----- canonicalization & signing -----

    def _canonical_decision(self) -> str:
        payload = {
            "approval_id": self.approval_id,
            "decision": self.decision,
            "approver": self.approver,
            "channel": self.channel,
            "decided_at": self.decided_at.isoformat(),
            "request_hash": self.request_hash,
            "policy_hash": self.policy_hash,
            "mandate_hash": self.mandate_hash,
            "step_up_verified": self.step_up_verified,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    def compute_decision_hash(self) -> str:
        return hashlib.sha256(self._canonical_decision().encode("utf-8")).hexdigest()

    def compute_signature(self, secret: str | None = None) -> str:
        key = _resolve_hmac_key(secret)
        # Sign over the decision hash so a tampered field invalidates both.
        msg = "|".join([self.approval_id, self.decision, self.approver, self.decision_hash])
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).hexdigest()

    def sign(self, secret: str | None = None) -> DecisionEvidence:
        self.decision_hash = self.compute_decision_hash()
        self.signature = self.compute_signature(secret)
        return self

    def verify(self, secret: str | None = None) -> bool:
        if self.decision_hash != self.compute_decision_hash():
            return False
        return hmac.compare_digest(self.signature, self.compute_signature(secret))

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "decision": self.decision,
            "approver": self.approver,
            "channel": self.channel,
            "decided_at": self.decided_at.isoformat(),
            "request_hash": self.request_hash,
            "policy_hash": self.policy_hash,
            "mandate_hash": self.mandate_hash,
            "decision_hash": self.decision_hash,
            "signature": self.signature,
            "step_up_verified": self.step_up_verified,
        }


# ── The durable ApprovalRequest object ─────────────────────────────────


@dataclass
class ApprovalRequest:
    """A durable, signed human-in-the-loop approval request.

    Created when the orchestrator's ``requires_approval`` gate fires.  Carries
    the full context a human needs to decide, the policy/mandate hashes bound at
    request time (so re-execution can detect drift), and — once decided — the
    signed :class:`DecisionEvidence`.
    """

    # Identity / context
    id: str
    agent_id: str | None
    mandate_id: str | None  # the payment mandate_id this gates
    spending_mandate_id: str | None  # the governing SpendingMandate, if any
    amount: Decimal
    currency: str
    counterparty: str | None  # merchant id / destination address
    reason: str

    # State
    status: ApprovalState = ApprovalState.PENDING
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(UTC) + timedelta(hours=24)
    )
    decided_by: str | None = None
    decided_at: datetime | None = None

    # Bound snapshot hashes (captured at request time, fail-closed on drift)
    policy_hash: str = ""
    mandate_hash: str = ""

    # Step-up: high-value approvals require OTP confirmation of the approver.
    requires_step_up: bool = False

    # Signed decision evidence (None until decided)
    evidence: DecisionEvidence | None = None

    # Re-execution accounting — guarantees idempotent settlement.
    reexecuted: bool = False

    # The verified mandate-chain snapshot needed to re-run execute_chain.
    # Opaque to this module; the orchestrator owns its shape.
    chain_snapshot: Any | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.amount = _as_decimal(self.amount)

    # ----- predicates -----

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL

    def is_expired(self, *, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        return self.status == ApprovalState.PENDING and now >= self.expires_at

    # ----- canonical request payload (immutable fields only) -----

    def _canonical_request(self) -> str:
        payload = {
            "id": self.id,
            "agent_id": self.agent_id,
            "mandate_id": self.mandate_id,
            "spending_mandate_id": self.spending_mandate_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "counterparty": self.counterparty,
            "reason": self.reason,
            "requested_at": self.requested_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "policy_hash": self.policy_hash,
            "mandate_hash": self.mandate_hash,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    def request_hash(self) -> str:
        return hashlib.sha256(self._canonical_request().encode("utf-8")).hexdigest()

    # ----- state transitions (each produces signed evidence) -----

    def _guard(self, target: ApprovalState) -> None:
        allowed = _ALLOWED.get(self.status, frozenset())
        if target not in allowed:
            raise ApprovalStateError(
                f"illegal approval transition {self.status.value} -> {target.value} "
                f"for {self.id}"
            )

    def _record_decision(
        self,
        *,
        target: ApprovalState,
        approver: str,
        channel: DecisionChannel,
        step_up_verified: bool,
        secret: str | None,
    ) -> DecisionEvidence:
        self._guard(target)
        decided_at = datetime.now(UTC)
        ev = DecisionEvidence(
            approval_id=self.id,
            decision=target.value,
            approver=approver,
            channel=channel.value,
            decided_at=decided_at,
            request_hash=self.request_hash(),
            policy_hash=self.policy_hash,
            mandate_hash=self.mandate_hash,
            decision_hash="",
            signature="",
            step_up_verified=step_up_verified,
        ).sign(secret)
        self.status = target
        self.decided_by = approver
        self.decided_at = decided_at
        self.evidence = ev
        return ev

    def approve(
        self,
        *,
        approver: str,
        channel: DecisionChannel = DecisionChannel.DASHBOARD,
        step_up_verified: bool = False,
        secret: str | None = None,
    ) -> DecisionEvidence:
        """Approve the request.  Fail-closed step-up: if step-up is required and
        OTP was not verified, refuse to record an approval."""
        if self.requires_step_up and not step_up_verified:
            raise ApprovalStateError(
                f"approval {self.id} requires step-up (OTP) verification of the approver"
            )
        return self._record_decision(
            target=ApprovalState.APPROVED,
            approver=approver,
            channel=channel,
            step_up_verified=step_up_verified,
            secret=secret,
        )

    def deny(
        self,
        *,
        approver: str,
        reason: str | None = None,
        channel: DecisionChannel = DecisionChannel.DASHBOARD,
        secret: str | None = None,
    ) -> DecisionEvidence:
        if reason:
            self.metadata["deny_reason"] = reason
        return self._record_decision(
            target=ApprovalState.DENIED,
            approver=approver,
            channel=channel,
            step_up_verified=False,
            secret=secret,
        )

    def expire(self, *, secret: str | None = None) -> DecisionEvidence:
        """System-driven expiry.  Terminal, fail-closed (money stays blocked)."""
        return self._record_decision(
            target=ApprovalState.EXPIRED,
            approver="system",
            channel=DecisionChannel.SYSTEM,
            step_up_verified=False,
            secret=secret,
        )

    # ----- serialization -----

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "mandate_id": self.mandate_id,
            "spending_mandate_id": self.spending_mandate_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "counterparty": self.counterparty,
            "reason": self.reason,
            "status": self.status.value,
            "requested_at": self.requested_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "policy_hash": self.policy_hash,
            "mandate_hash": self.mandate_hash,
            "requires_step_up": self.requires_step_up,
            "reexecuted": self.reexecuted,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "metadata": self.metadata,
        }


def build_approval_request(
    *,
    agent_id: str | None,
    mandate_id: str | None,
    amount: Decimal | str | int,
    currency: str,
    counterparty: str | None,
    reason: str,
    spending_mandate_id: str | None = None,
    policy_hash: str = "",
    mandate_hash: str = "",
    expires_in_hours: int = 24,
    requires_step_up: bool = False,
    chain_snapshot: Any | None = None,
    metadata: dict[str, Any] | None = None,
) -> ApprovalRequest:
    """Factory for a fresh ``pending`` request with sensible defaults."""
    now = datetime.now(UTC)
    return ApprovalRequest(
        id=new_approval_id(),
        agent_id=agent_id,
        mandate_id=mandate_id,
        spending_mandate_id=spending_mandate_id,
        amount=_as_decimal(amount),
        currency=currency,
        counterparty=counterparty,
        reason=reason,
        status=ApprovalState.PENDING,
        requested_at=now,
        expires_at=now + timedelta(hours=expires_in_hours),
        policy_hash=policy_hash,
        mandate_hash=mandate_hash,
        requires_step_up=requires_step_up,
        chain_snapshot=chain_snapshot,
        metadata=metadata or {},
    )


def _uuid_hex() -> str:  # small helper kept for parity with other modules
    return uuid.uuid4().hex
