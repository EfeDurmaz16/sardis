"""Delegation — the Attenuated Delegation Graph primitive (object-capability for money).

An agent (or principal) delegates a SCOPED, BOUNDED, REVOCABLE slice of its own
authority to a sub-agent.  The sub-agent may delegate a still-smaller slice of
*that* to a tool, and so on — forming an **attenuating capability chain**:

    human ── $500 mandate ──▶ Agent A
                                 │  delegate $50 (subset of scope)
                                 ▼
                              Agent B (sub-agent)
                                 │  delegate $20 (subset of B's scope)
                                 ▼
                              Tool C

The cardinal rule (object-capability attenuation): **a delegate can NEVER exceed
its delegator.**  Every hop must narrow — cap ``<=`` parent remaining, expiry
``<=`` parent, scope ``⊆`` parent scope.  Authority only ever shrinks downward.

A :class:`Delegation` is a *derived* authority — a scoped, signed child of its
parent (a SpendingMandate at the root, or another Delegation deeper down).  It is
NOT a free-standing grant: at execution time the WHOLE chain from the acting
delegate up to the root mandate is re-checked, and any broken link (revoked /
expired / over-cap / out-of-scope) denies the payment fail-closed.

Sardis owns the delegation DECISION and its signed proof (the moat).  This module
is the domain core:

* :class:`Delegation` — the durable derived-authority record: id (``dlg_…``),
  delegator (agent/principal + the parent mandate/delegation it draws from),
  delegatee (sub-agent), attenuated scope, amount cap, expiry, depth, status,
  spent tracking, and signed :class:`DelegationEvidence`.
* :class:`DelegationEvidence` — signed, independently-verifiable proof that this
  delegation was created with these exact attenuated bounds.  Mirrors the HMAC
  pattern of :class:`~sardis.core.approval_request.DecisionEvidence` /
  :class:`~sardis.core.revocation.RevocationProof` /
  :class:`~sardis.core.execution_receipt.ExecutionReceipt`.  Key resolution uses
  ``SARDIS_DELEGATION_HMAC_KEY`` and is **fail-closed in production**.

Money is :class:`~decimal.Decimal` in token (major) units throughout — never
float.  No vendor SDK is imported.
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
from decimal import Decimal
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


def new_delegation_id() -> str:
    """``dlg_<base36 ts>_<rand>`` — the durable Delegation identifier."""
    ts = _to_base36(int(time.time()))
    return f"dlg_{ts}_{secrets.token_hex(4)}"


# Object-capability depth guard: how deep an attenuating chain may go before the
# engine refuses to mint another hop.  The root SpendingMandate is depth 0; the
# first delegation is depth 1.  A hard ceiling caps blast radius and keeps chain
# resolution / re-check bounded at execution time.
MAX_DELEGATION_DEPTH = 8


# ── Enums ──────────────────────────────────────────────────────────────


class DelegatorKind(str, Enum):
    """What the delegated authority is drawn FROM (the parent in the chain)."""

    MANDATE = "mandate"  # the root: a SpendingMandate (depth 0 parent)
    DELEGATION = "delegation"  # a deeper hop: another Delegation


class DelegationStatus(str, Enum):
    """Lifecycle of a single delegation hop.

    ``revoked`` is terminal and is what the Revocation engine flips when a parent
    (mandate / agent / delegation) is killed — propagation marks the whole
    subtree revoked.  ``exhausted`` means the cap is fully spent; ``expired``
    means past its own (already-attenuated) expiry.
    """

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"


# Statuses that mean this hop can no longer authorize anything.
_TERMINAL = {DelegationStatus.REVOKED, DelegationStatus.EXPIRED, DelegationStatus.EXHAUSTED}


# ── Signing key (mirrors RevocationProof / DecisionEvidence / ExecutionReceipt) ─


def _resolve_delegation_key(secret: str | None) -> bytes:
    """Resolve the HMAC signing key for delegation evidence.

    Explicit secret wins; otherwise ``SARDIS_DELEGATION_HMAC_KEY``; otherwise a
    ``dev-`` fallback — but ONLY outside production/staging, where a missing key
    fails closed (refuses to sign a proof of delegated authority).
    """
    resolved = secret or os.getenv("SARDIS_DELEGATION_HMAC_KEY", "")
    if not resolved:
        env = os.getenv("SARDIS_ENVIRONMENT", os.getenv("SARDIS_ENV", "dev")).strip().lower()
        if env in ("prod", "production", "staging"):
            raise RuntimeError(
                "SARDIS_DELEGATION_HMAC_KEY must be set in production/staging. "
                "Refusing to sign a delegation of authority with a default key."
            )
        resolved = "dev-delegation-key"
    return resolved.encode()


def _dec_str(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


# ── Signed, independently-verifiable evidence ──────────────────────────


@dataclass(slots=True)
class DelegationEvidence:
    """Signed proof that a delegation was minted with these attenuated bounds.

    The ``decision_hash`` binds the delegation identity (id, delegator chain,
    delegatee) + the *exact* attenuated grant (cap, scope hash, expiry, depth) so
    a tampered or widened delegation invalidates the hash.  The ``signature`` is
    HMAC-SHA256 over the decision hash plus identity fields, mirroring
    :class:`~sardis.core.revocation.RevocationProof`.
    """

    delegation_id: str
    delegator_kind: str  # DelegatorKind value
    delegator_ref: str  # parent mandate id | parent delegation id
    delegator_principal: str  # the agent/principal doing the delegating
    delegatee: str  # the sub-agent receiving the authority
    root_mandate_id: str  # the SpendingMandate at the root of the chain
    depth: int
    amount_cap: str | None  # token units as str (Decimal-safe)
    currency: str
    expires_at: str | None  # ISO
    scope_hash: str  # SHA-256 of the attenuated scope
    created_at: datetime
    decision_hash: str
    signature: str

    # ----- canonicalization & signing -----

    def _canonical_decision(self) -> str:
        payload = {
            "delegation_id": self.delegation_id,
            "delegator_kind": self.delegator_kind,
            "delegator_ref": self.delegator_ref,
            "delegator_principal": self.delegator_principal,
            "delegatee": self.delegatee,
            "root_mandate_id": self.root_mandate_id,
            "depth": self.depth,
            "amount_cap": self.amount_cap,
            "currency": self.currency,
            "expires_at": self.expires_at,
            "scope_hash": self.scope_hash,
            "created_at": self.created_at.isoformat(),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    def compute_decision_hash(self) -> str:
        return hashlib.sha256(self._canonical_decision().encode("utf-8")).hexdigest()

    def compute_signature(self, secret: str | None = None) -> str:
        key = _resolve_delegation_key(secret)
        msg = "|".join(
            [
                self.delegation_id,
                self.delegator_ref,
                self.delegatee,
                self.root_mandate_id,
                self.decision_hash,
            ]
        )
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).hexdigest()

    def sign(self, secret: str | None = None) -> DelegationEvidence:
        self.decision_hash = self.compute_decision_hash()
        self.signature = self.compute_signature(secret)
        return self

    def verify(self, secret: str | None = None) -> bool:
        """Independently verify: recompute the hash from bound fields + check HMAC."""
        if self.decision_hash != self.compute_decision_hash():
            return False
        return hmac.compare_digest(self.signature, self.compute_signature(secret))

    def to_dict(self) -> dict[str, Any]:
        return {
            "delegation_id": self.delegation_id,
            "delegator_kind": self.delegator_kind,
            "delegator_ref": self.delegator_ref,
            "delegator_principal": self.delegator_principal,
            "delegatee": self.delegatee,
            "root_mandate_id": self.root_mandate_id,
            "depth": self.depth,
            "amount_cap": self.amount_cap,
            "currency": self.currency,
            "expires_at": self.expires_at,
            "scope_hash": self.scope_hash,
            "created_at": self.created_at.isoformat(),
            "decision_hash": self.decision_hash,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DelegationEvidence:
        return cls(
            delegation_id=d["delegation_id"],
            delegator_kind=d["delegator_kind"],
            delegator_ref=d["delegator_ref"],
            delegator_principal=d["delegator_principal"],
            delegatee=d["delegatee"],
            root_mandate_id=d["root_mandate_id"],
            depth=int(d["depth"]),
            amount_cap=d.get("amount_cap"),
            currency=d.get("currency", "USDC"),
            expires_at=d.get("expires_at"),
            scope_hash=d["scope_hash"],
            created_at=datetime.fromisoformat(d["created_at"]),
            decision_hash=d["decision_hash"],
            signature=d["signature"],
        )


# ── Attenuated scope ───────────────────────────────────────────────────


@dataclass
class DelegationScope:
    """The attenuated authority surface a delegation grants over money.

    Each dimension is a *subset constraint*: a delegation may only narrow each
    field of its delegator's scope, never widen it.  Empty / ``None`` means "no
    further restriction at this hop" — but the parent's restriction still applies
    because the whole chain is re-checked at execution.

    * ``counterparties`` — allowed payees / merchant ids / destination addresses.
    * ``categories`` — allowed purpose categories.
    * ``mcc`` — allowed merchant-category codes (cards rail).
    * ``rails`` — allowed payment rails (card / usdc / bank).
    """

    counterparties: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    mcc: list[str] = field(default_factory=list)
    rails: list[str] = field(default_factory=list)

    def scope_hash(self) -> str:
        """Stable SHA-256 over the (sorted) scope — bound into the signed proof."""
        payload = {
            "counterparties": sorted(self.counterparties),
            "categories": sorted(self.categories),
            "mcc": sorted(self.mcc),
            "rails": sorted(self.rails),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "counterparties": list(self.counterparties),
            "categories": list(self.categories),
            "mcc": list(self.mcc),
            "rails": list(self.rails),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> DelegationScope:
        d = d or {}
        return cls(
            counterparties=list(d.get("counterparties") or []),
            categories=list(d.get("categories") or []),
            mcc=list(d.get("mcc") or []),
            rails=list(d.get("rails") or []),
        )


# ── The durable Delegation object ──────────────────────────────────────


@dataclass
class Delegation:
    """A derived, attenuated, revocable slice of spending authority.

    Created by the :class:`~sardis.core.delegation_engine.DelegationEngine`, which
    enforces attenuation against the delegator at mint time.  At execution time
    the WHOLE chain up to ``root_mandate_id`` is re-checked link-by-link; this row
    only authorizes a payment when it AND every ancestor is active, in-scope,
    under-cap and non-expired.
    """

    # Identity
    delegator_kind: DelegatorKind  # MANDATE (root parent) | DELEGATION (deeper)
    delegator_ref: str  # the parent's id (mandate id or delegation id)
    delegator_principal: str  # who is delegating (agent / principal id)
    delegatee: str  # the sub-agent receiving the authority
    root_mandate_id: str  # the SpendingMandate at the root of this chain

    id: str = field(default_factory=new_delegation_id)
    org_id: str = ""

    # Attenuated grant — each MUST be a narrowing of the delegator.
    amount_cap: Decimal | None = None  # token units; <= parent remaining
    currency: str = "USDC"
    scope: DelegationScope = field(default_factory=DelegationScope)
    expires_at: datetime | None = None  # <= parent expiry
    valid_from: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Position in the chain.  Root mandate is depth 0; first delegation depth 1.
    depth: int = 1

    # Spend tracking.  A delegate spend decrements this AND every ancestor.
    spent_total: Decimal = field(default_factory=lambda: Decimal("0"))

    # Lifecycle
    status: DelegationStatus = DelegationStatus.ACTIVE
    revoked_at: datetime | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None

    # Signed evidence (None until the engine finalizes the mint).
    evidence: DelegationEvidence | None = None

    # Audit
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # ----- derived -----

    @property
    def remaining(self) -> Decimal | None:
        """Remaining cap at this hop, or ``None`` if uncapped."""
        if self.amount_cap is None:
            return None
        return self.amount_cap - self.spent_total

    @property
    def is_active(self) -> bool:
        """Active, within its own time bounds, and not exhausted."""
        if self.status != DelegationStatus.ACTIVE:
            return False
        now = datetime.now(UTC)
        if self.valid_from and now < self.valid_from:
            return False
        if self.expires_at and now > self.expires_at:
            return False
        if self.amount_cap is not None and self.spent_total >= self.amount_cap:
            return False
        return True

    def build_evidence(self, secret: str | None = None) -> DelegationEvidence:
        """Build + sign the :class:`DelegationEvidence` from the current state."""
        ev = DelegationEvidence(
            delegation_id=self.id,
            delegator_kind=self.delegator_kind.value,
            delegator_ref=self.delegator_ref,
            delegator_principal=self.delegator_principal,
            delegatee=self.delegatee,
            root_mandate_id=self.root_mandate_id,
            depth=self.depth,
            amount_cap=_dec_str(self.amount_cap),
            currency=self.currency,
            expires_at=self.expires_at.isoformat() if self.expires_at else None,
            scope_hash=self.scope.scope_hash(),
            created_at=self.created_at,
            decision_hash="",
            signature="",
        ).sign(secret)
        self.evidence = ev
        return ev

    def revoke(self, *, revoked_by: str, reason: str | None = None) -> None:
        """Mark this hop revoked (idempotent).  Terminal — no resurrection."""
        if self.status == DelegationStatus.REVOKED:
            return
        self.status = DelegationStatus.REVOKED
        self.revoked_at = datetime.now(UTC)
        self.revoked_by = revoked_by
        self.revocation_reason = reason
        self.updated_at = datetime.now(UTC)

    # ----- serialization -----

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "delegator_kind": self.delegator_kind.value,
            "delegator_ref": self.delegator_ref,
            "delegator_principal": self.delegator_principal,
            "delegatee": self.delegatee,
            "root_mandate_id": self.root_mandate_id,
            "amount_cap": _dec_str(self.amount_cap),
            "currency": self.currency,
            "scope": self.scope.to_dict(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "depth": self.depth,
            "spent_total": str(self.spent_total),
            "status": self.status.value,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_by": self.revoked_by,
            "revocation_reason": self.revocation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


__all__ = [
    "MAX_DELEGATION_DEPTH",
    "Delegation",
    "DelegationEvidence",
    "DelegationScope",
    "DelegationStatus",
    "DelegatorKind",
    "new_delegation_id",
]
