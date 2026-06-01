"""Revocation — the Propagating-Revocation primitive (the lead wedge).

Revoking a :class:`~sardis.core.spending_mandate.SpendingMandate` already makes
the orchestrator deny *future* payments for that mandate (the lookup returns
only ``status = 'active'`` rows).  That is necessary but not sufficient.  The
differentiating promise is bigger:

    ONE revoke atomically propagates across EVERY rail — freeze the agent's
    cards, revoke its outstanding spend objects / one-time passes, deny its
    pending approvals + in-flight payments, mark the mandate revoked — and
    returns a SIGNED, INDEPENDENTLY-VERIFIABLE proof listing exactly what was
    killed and when.

No single rail-owner can build this: it requires neutrality *across* all rails.
That is the moat.  Sardis owns the **revocation decision and its signed proof**;
the per-rail "kill" is swappable execution behind
:mod:`sardis.core.revocation_ports`.

This module is the domain core.  It defines:

* :class:`PropagationTarget` — one derived authority that was (or could not be)
  killed, with its ``kill_status`` (``killed`` | ``blocked_pending`` |
  ``failed``), its ``kind`` (mandate / spend_object / card / approval /
  in_flight), its ``ref`` and a free-text ``detail``;
* :class:`Revocation` — the durable decision: id (``rev_…``), target (the agent
  / mandate / principal whose authority is being killed), scope, who requested
  it, when, status, and the full list of :class:`PropagationTarget`;
* :class:`RevocationProof` — the signed, independently-verifiable proof.  Its
  ``decision_hash`` binds the revocation identity + the *complete* target list +
  the overall outcome + the timestamp; the signature is an HMAC-SHA256 over the
  decision hash, mirroring
  :class:`~sardis.core.approval_request.DecisionEvidence` /
  :class:`~sardis.core.execution_receipt.ExecutionReceipt`.  Key resolution
  uses ``SARDIS_REVOCATION_HMAC_KEY`` and is **fail-closed in production**, with
  a ``dev-`` fallback only outside prod/staging.

Fail-closed contract (the hard rule): a partial propagation must NEVER be
reported as fully propagated.  If a downstream kill fails (e.g. a card-freeze
provider errors), the target is recorded ``blocked_pending`` — the orchestrator
*still* denies the revoked mandate at execution time (so no authority stays
silently alive), and the overall revocation outcome reflects that some rails are
``blocked_pending_downstream``.  The proof tells the truth about partial state.

Money is :class:`~decimal.Decimal` where it appears.  No vendor SDK is imported.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ── Identifiers ────────────────────────────────────────────────────────


def _to_base36(num: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if num == 0:
        return "0"
    out: list[str] = []
    while num:
        num, rem = divmod(num, 36)
        out.append(chars[rem])
    return "".join(reversed(out))


def new_revocation_id() -> str:
    """``rev_<base36 ts>_<rand>`` — the durable Revocation identifier."""
    ts = _to_base36(int(time.time()))
    return f"rev_{ts}_{secrets.token_hex(4)}"


# ── Enums ──────────────────────────────────────────────────────────────


class RevocationTargetKind(str, Enum):
    """What kind of authority the *whole* revocation is aimed at.

    A revocation is requested against ONE of these; the engine then enumerates
    every derived authority (mandates, spend objects, cards, …) reachable from
    it and kills each as a :class:`PropagationTarget`.
    """

    AGENT = "agent"  # kill all authority of an agent (the common case)
    MANDATE = "mandate"  # kill one specific spending mandate + its derivations
    PRINCIPAL = "principal"  # kill all authority granted by a principal


class RevocationStatus(str, Enum):
    """Lifecycle / outcome of a revocation.

    The decision itself is instantaneous and terminal — there is no "undo".
    What varies is whether *every* rail confirmed the kill:

    * ``propagated`` — every target killed (or already dead); fully done.
    * ``blocked_pending_downstream`` — the decision is in force (the
      orchestrator denies at execution time) but ≥1 downstream kill could not be
      confirmed and is ``blocked_pending``.  NEVER reported as ``propagated``.
    """

    PROPAGATED = "propagated"
    BLOCKED_PENDING_DOWNSTREAM = "blocked_pending_downstream"


class PropagationKind(str, Enum):
    """Which rail / object class a single propagation target belongs to."""

    MANDATE = "mandate"  # the SpendingMandate(s) themselves
    SPEND_OBJECT = "spend_object"  # one-time PaymentObjects / passes
    CARD = "card"  # virtual cards (frozen via CardPort)
    APPROVAL = "approval"  # pending ApprovalRequests
    IN_FLIGHT = "in_flight"  # in-flight / pending payments


class KillStatus(str, Enum):
    """Outcome of killing ONE derived authority.

    ``blocked_pending`` is the fail-closed status: the kill could not be
    confirmed downstream, so authority is *blocked at execution time* by the
    orchestrator (which denies the revoked mandate) while the downstream
    confirmation is still pending.  It is explicitly NOT "killed" — the proof
    must never claim a thing is dead when it might still be alive on its rail.
    """

    KILLED = "killed"  # confirmed dead on its rail
    BLOCKED_PENDING = "blocked_pending"  # blocked at execution, downstream unconfirmed
    FAILED = "failed"  # hard failure (also blocked at execution); detail records why
    ALREADY_DEAD = "already_dead"  # was already terminal/revoked — no-op, counts as killed


# Statuses that mean "authority is confirmed gone on its own rail".
_CONFIRMED_DEAD = {KillStatus.KILLED, KillStatus.ALREADY_DEAD}


# ── Propagation target ─────────────────────────────────────────────────


@dataclass(slots=True)
class PropagationTarget:
    """One derived authority enumerated by the revocation, and its kill outcome.

    Every authority the engine touches is recorded here — even ones already dead
    (``already_dead``) and ones it could not confirm killing (``blocked_pending``
    / ``failed``).  The full list is bound into the proof, so an auditor sees
    exactly what was — and was not — killed.
    """

    kind: PropagationKind
    ref: str  # the object id (mandate id, po_ id, card ref, apreq_ id, …)
    kill_status: KillStatus
    detail: str = ""  # human-readable: provider, error, "already terminal", …
    killed_at: datetime | None = None

    def is_confirmed_dead(self) -> bool:
        return self.kill_status in _CONFIRMED_DEAD

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "ref": self.ref,
            "kill_status": self.kill_status.value,
            "detail": self.detail,
            "killed_at": self.killed_at.isoformat() if self.killed_at else None,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PropagationTarget:
        killed_at = d.get("killed_at")
        return cls(
            kind=PropagationKind(d["kind"]),
            ref=d["ref"],
            kill_status=KillStatus(d["kill_status"]),
            detail=d.get("detail", ""),
            killed_at=datetime.fromisoformat(killed_at) if killed_at else None,
        )


# ── Signing key (mirrors ExecutionReceipt / ApprovalRequest / Recourse) ─


def _resolve_revocation_key(secret: str | None) -> bytes:
    """Resolve the HMAC signing key for revocation proofs.

    Explicit secret wins; otherwise ``SARDIS_REVOCATION_HMAC_KEY``; otherwise a
    ``dev-`` fallback — but ONLY outside production/staging, where a missing key
    fails closed (refuses to sign a proof of revocation).
    """
    resolved = secret or os.getenv("SARDIS_REVOCATION_HMAC_KEY", "")
    if not resolved:
        env = os.getenv("SARDIS_ENVIRONMENT", os.getenv("SARDIS_ENV", "dev")).strip().lower()
        if env in ("prod", "production", "staging"):
            raise RuntimeError(
                "SARDIS_REVOCATION_HMAC_KEY must be set in production/staging. "
                "Refusing to sign a proof-of-revocation with a default key."
            )
        resolved = "dev-revocation-key"
    return resolved.encode()


# ── Signed, independently-verifiable proof ─────────────────────────────


@dataclass(slots=True)
class RevocationProof:
    """Signed proof that a revocation happened and what it killed.

    The proof is **self-contained and independently verifiable**: every field
    needed to recompute the ``decision_hash`` and the ``signature`` is carried
    on the proof itself.  An auditor with the HMAC key can call :meth:`verify`
    on the deserialized proof — no access to the live system required.

    The ``decision_hash`` binds:

    * the revocation identity (id, target kind+ref, scope, requested_by);
    * the **full, ordered target list** (each kind/ref/kill_status/detail) — so
      a tampered or truncated list invalidates the hash;
    * the overall ``outcome`` (propagated | blocked_pending_downstream);
    * the ``revoked_at`` timestamp.

    The ``signature`` is HMAC-SHA256 over the ``decision_hash`` plus the
    identity fields, so tampering with any bound field invalidates both.
    """

    revocation_id: str
    target_kind: str  # RevocationTargetKind value
    target_ref: str
    scope: str
    requested_by: str
    revoked_at: datetime
    outcome: str  # RevocationStatus value
    targets: list[dict[str, Any]]  # PropagationTarget.to_dict() in stable order
    decision_hash: str  # SHA-256 over the canonical decision payload
    signature: str  # HMAC-SHA256 over decision_hash + identity fields

    # ----- canonicalization & signing -----

    def _canonical_decision(self) -> str:
        # Targets are sorted deterministically so the hash is order-independent
        # of insertion order but still binds the exact set + each outcome.
        sorted_targets = sorted(
            self.targets, key=lambda t: (t["kind"], t["ref"], t["kill_status"])
        )
        payload = {
            "revocation_id": self.revocation_id,
            "target_kind": self.target_kind,
            "target_ref": self.target_ref,
            "scope": self.scope,
            "requested_by": self.requested_by,
            "revoked_at": self.revoked_at.isoformat(),
            "outcome": self.outcome,
            "targets": [
                {
                    "kind": t["kind"],
                    "ref": t["ref"],
                    "kill_status": t["kill_status"],
                    "detail": t.get("detail", ""),
                }
                for t in sorted_targets
            ],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    def compute_decision_hash(self) -> str:
        return hashlib.sha256(self._canonical_decision().encode("utf-8")).hexdigest()

    def compute_signature(self, secret: str | None = None) -> str:
        key = _resolve_revocation_key(secret)
        msg = "|".join(
            [
                self.revocation_id,
                self.target_kind,
                self.target_ref,
                self.outcome,
                self.decision_hash,
            ]
        )
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).hexdigest()

    def sign(self, secret: str | None = None) -> RevocationProof:
        self.decision_hash = self.compute_decision_hash()
        self.signature = self.compute_signature(secret)
        return self

    def verify(self, secret: str | None = None) -> bool:
        """Independently verify the proof: recompute the hash from the bound
        fields and check the HMAC.  Returns ``False`` on any mismatch."""
        if self.decision_hash != self.compute_decision_hash():
            return False
        return hmac.compare_digest(self.signature, self.compute_signature(secret))

    def to_dict(self) -> dict[str, Any]:
        return {
            "revocation_id": self.revocation_id,
            "target_kind": self.target_kind,
            "target_ref": self.target_ref,
            "scope": self.scope,
            "requested_by": self.requested_by,
            "revoked_at": self.revoked_at.isoformat(),
            "outcome": self.outcome,
            "targets": self.targets,
            "decision_hash": self.decision_hash,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RevocationProof:
        return cls(
            revocation_id=d["revocation_id"],
            target_kind=d["target_kind"],
            target_ref=d["target_ref"],
            scope=d["scope"],
            requested_by=d["requested_by"],
            revoked_at=datetime.fromisoformat(d["revoked_at"]),
            outcome=d["outcome"],
            targets=list(d["targets"]),
            decision_hash=d["decision_hash"],
            signature=d["signature"],
        )


# ── The durable Revocation object ──────────────────────────────────────


@dataclass
class Revocation:
    """A durable revocation decision and the full record of its propagation.

    Created the moment a kill is requested.  The engine fills in
    :attr:`targets` as it enumerates and kills each derived authority, sets the
    terminal :attr:`status`, and attaches the signed :class:`RevocationProof`.
    """

    # Identity
    id: str
    target_kind: RevocationTargetKind
    target_ref: str  # agent_id | mandate_id | principal_id
    scope: str  # free-text/structured scope ("all" | "rails:card,usdc" | …)
    requested_by: str  # principal id / "system"
    requested_at: datetime

    # Outcome
    status: RevocationStatus = RevocationStatus.PROPAGATED
    revoked_at: datetime | None = None

    # The full propagation record — every authority touched.
    targets: list[PropagationTarget] = field(default_factory=list)

    # Signed proof (None until the engine finalizes).
    proof: RevocationProof | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    # ----- mutation -----

    def add_target(self, target: PropagationTarget) -> None:
        self.targets.append(target)

    def has_unconfirmed(self) -> bool:
        """True if ANY target is not confirmed dead — i.e. some authority is
        only blocked-at-execution pending downstream confirmation."""
        return any(not t.is_confirmed_dead() for t in self.targets)

    def compute_outcome(self) -> RevocationStatus:
        """Derive the honest overall outcome from the per-target kill statuses.

        Fail-closed: if even one target is not confirmed dead, the outcome is
        ``blocked_pending_downstream`` — never ``propagated``.
        """
        return (
            RevocationStatus.BLOCKED_PENDING_DOWNSTREAM
            if self.has_unconfirmed()
            else RevocationStatus.PROPAGATED
        )

    def build_proof(self, secret: str | None = None) -> RevocationProof:
        """Build + sign the :class:`RevocationProof` from the current state."""
        revoked_at = self.revoked_at or datetime.now(UTC)
        self.revoked_at = revoked_at
        proof = RevocationProof(
            revocation_id=self.id,
            target_kind=self.target_kind.value,
            target_ref=self.target_ref,
            scope=self.scope,
            requested_by=self.requested_by,
            revoked_at=revoked_at,
            outcome=self.status.value,
            targets=[t.to_dict() for t in self.targets],
            decision_hash="",
            signature="",
        ).sign(secret)
        self.proof = proof
        return proof

    # ----- serialization -----

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_kind": self.target_kind.value,
            "target_ref": self.target_ref,
            "scope": self.scope,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at.isoformat(),
            "status": self.status.value,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "targets": [t.to_dict() for t in self.targets],
            "proof": self.proof.to_dict() if self.proof else None,
            "metadata": self.metadata,
        }


def build_revocation(
    *,
    target_kind: RevocationTargetKind,
    target_ref: str,
    requested_by: str,
    scope: str = "all",
    metadata: dict[str, Any] | None = None,
) -> Revocation:
    """Factory for a fresh revocation request (no targets killed yet)."""
    return Revocation(
        id=new_revocation_id(),
        target_kind=target_kind,
        target_ref=target_ref,
        scope=scope,
        requested_by=requested_by,
        requested_at=datetime.now(UTC),
        metadata=metadata or {},
    )


__all__ = [
    "KillStatus",
    "PropagationKind",
    "PropagationTarget",
    "Revocation",
    "RevocationProof",
    "RevocationStatus",
    "RevocationTargetKind",
    "build_revocation",
    "new_revocation_id",
]
