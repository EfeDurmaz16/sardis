"""Revocation rail-killer ports — swappable execution for propagation.

Sardis owns the revocation DECISION and its signed proof (the moat, in
:mod:`sardis.core.revocation`).  *Propagating* the kill across each rail is
swappable execution and lives here behind narrow ports — one per class of
derived authority:

* :class:`MandateRevokerPort`  — mark the SpendingMandate(s) revoked.
* :class:`SpendObjectRevokerPort` — revoke/expire outstanding one-time spend
  objects (PaymentObjects / passes).
* :class:`CardFreezerPort` — freeze the agent's virtual cards.  The *real* leg
  goes through the provider-layer :class:`CardPort` (``set_state(state="frozen")``);
  here it is wrapped so this package never imports the apps/api provider layer.
* :class:`ApprovalRevokerPort` — deny/expire the agent's pending
  ApprovalRequests.
* :class:`InFlightBlockerPort` — block in-flight / pending payments.

Each port returns a list of :class:`KillOutcome` — one per object it found —
recording whether the kill was confirmed (``killed`` / ``already_dead``) or
could not be confirmed (``blocked_pending`` / ``failed``).  A port NEVER decides
*whether* to revoke; it only carries out the kill the engine already decided on,
and it must report failures honestly so the engine can fail closed.

Every port ships an in-memory / mock implementation so the engine runs in dev
and tests with no live keys.  The real adapters (CardPort freeze, the Postgres
mandate/approval/spend-object/payment stores) are wired at the API layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from .revocation import KillStatus, PropagationKind

logger = logging.getLogger("sardis.revocation_ports")


@dataclass(slots=True)
class KillOutcome:
    """The result of attempting to kill ONE derived authority on a rail."""

    ref: str
    kill_status: KillStatus
    detail: str = ""

    @classmethod
    def killed(cls, ref: str, detail: str = "") -> KillOutcome:
        return cls(ref=ref, kill_status=KillStatus.KILLED, detail=detail)

    @classmethod
    def already_dead(cls, ref: str, detail: str = "") -> KillOutcome:
        return cls(ref=ref, kill_status=KillStatus.ALREADY_DEAD, detail=detail)

    @classmethod
    def blocked_pending(cls, ref: str, detail: str) -> KillOutcome:
        return cls(ref=ref, kill_status=KillStatus.BLOCKED_PENDING, detail=detail)

    @classmethod
    def failed(cls, ref: str, detail: str) -> KillOutcome:
        return cls(ref=ref, kill_status=KillStatus.FAILED, detail=detail)


# ── Port protocols (one per rail) ──────────────────────────────────────


class MandateRevokerPort(Protocol):
    kind = PropagationKind.MANDATE

    async def revoke_for_target(
        self, *, target_kind: str, target_ref: str, requested_by: str, reason: str
    ) -> list[KillOutcome]:
        """Revoke every spending mandate reachable from the target."""
        ...


class SpendObjectRevokerPort(Protocol):
    kind = PropagationKind.SPEND_OBJECT

    async def revoke_for_mandates(
        self, *, mandate_ids: list[str], requested_by: str
    ) -> list[KillOutcome]:
        """Revoke/expire all outstanding one-time spend objects for the mandates."""
        ...


class CardFreezerPort(Protocol):
    kind = PropagationKind.CARD

    async def freeze_for_target(
        self, *, target_kind: str, target_ref: str, requested_by: str
    ) -> list[KillOutcome]:
        """Freeze every virtual card belonging to the target agent/principal."""
        ...


class ApprovalRevokerPort(Protocol):
    kind = PropagationKind.APPROVAL

    async def deny_pending_for_target(
        self, *, agent_id: str | None, mandate_ids: list[str], requested_by: str
    ) -> list[KillOutcome]:
        """Deny/expire the target's pending ApprovalRequests."""
        ...


class InFlightBlockerPort(Protocol):
    kind = PropagationKind.IN_FLIGHT

    async def block_for_target(
        self, *, agent_id: str | None, mandate_ids: list[str], requested_by: str
    ) -> list[KillOutcome]:
        """Block in-flight / pending payments for the target."""
        ...


# ── In-memory / mock implementations (dev + tests, no live keys) ───────


class InMemoryMandateRevoker:
    """Mock mandate store: marks in-memory mandates revoked and reports the set.

    ``mandates`` maps ``mandate_id -> {"status", "agent_id", "principal_id"}``.
    Enumerates by the target, flips active/suspended → revoked, and reports each
    (already-revoked rows are ``already_dead``).
    """

    kind = PropagationKind.MANDATE

    def __init__(self, mandates: dict[str, dict[str, Any]]) -> None:
        self._mandates = mandates

    def _matches(self, m: dict[str, Any], target_kind: str, target_ref: str) -> bool:
        if target_kind == "mandate":
            return False  # matched by id below
        if target_kind == "agent":
            return m.get("agent_id") == target_ref
        if target_kind == "principal":
            return m.get("principal_id") == target_ref
        return False

    async def revoke_for_target(
        self, *, target_kind: str, target_ref: str, requested_by: str, reason: str
    ) -> list[KillOutcome]:
        outcomes: list[KillOutcome] = []
        for mid, m in self._mandates.items():
            hit = (target_kind == "mandate" and mid == target_ref) or self._matches(
                m, target_kind, target_ref
            )
            if not hit:
                continue
            if m.get("status") == "revoked":
                outcomes.append(KillOutcome.already_dead(mid, "mandate already revoked"))
                continue
            m["status"] = "revoked"
            m["revoked_by"] = requested_by
            m["revocation_reason"] = reason
            outcomes.append(KillOutcome.killed(mid, "mandate marked revoked"))
        return outcomes

    def revoked_mandate_ids(self) -> list[str]:
        return [mid for mid, m in self._mandates.items() if m.get("status") == "revoked"]


class InMemorySpendObjectRevoker:
    """Mock spend-object store keyed by mandate_id.

    ``objects`` maps ``object_id -> {"mandate_id", "status"}``.  Non-terminal
    objects for the killed mandates are flipped to ``revoked``.
    """

    kind = PropagationKind.SPEND_OBJECT
    _TERMINAL = {"settled", "fulfilled", "revoked", "expired", "failed", "refunded"}

    def __init__(self, objects: dict[str, dict[str, Any]]) -> None:
        self._objects = objects

    async def revoke_for_mandates(
        self, *, mandate_ids: list[str], requested_by: str
    ) -> list[KillOutcome]:
        wanted = set(mandate_ids)
        outcomes: list[KillOutcome] = []
        for oid, o in self._objects.items():
            if o.get("mandate_id") not in wanted:
                continue
            if o.get("status") in self._TERMINAL:
                outcomes.append(
                    KillOutcome.already_dead(oid, f"spend object already {o.get('status')}")
                )
                continue
            o["status"] = "revoked"
            outcomes.append(KillOutcome.killed(oid, "spend object revoked"))
        return outcomes


class InMemoryCardFreezer:
    """Mock card freezer.  ``cards`` maps ``card_ref -> {"agent_id",
    "principal_id", "state"}``.  Sets matching non-closed cards to ``frozen``.

    ``fail_refs`` simulates a downstream provider error for specific cards: the
    card is reported ``blocked_pending`` (NOT killed), so the engine fails
    closed — exactly the partial-propagation case.
    """

    kind = PropagationKind.CARD

    def __init__(
        self,
        cards: dict[str, dict[str, Any]],
        *,
        fail_refs: set[str] | None = None,
    ) -> None:
        self._cards = cards
        self._fail = fail_refs or set()

    def _matches(self, c: dict[str, Any], target_kind: str, target_ref: str) -> bool:
        if target_kind == "agent":
            return c.get("agent_id") == target_ref
        if target_kind == "principal":
            return c.get("principal_id") == target_ref
        return False

    async def freeze_for_target(
        self, *, target_kind: str, target_ref: str, requested_by: str
    ) -> list[KillOutcome]:
        outcomes: list[KillOutcome] = []
        for ref, c in self._cards.items():
            # A mandate target reaches cards via its agent; the engine passes
            # the agent_id through as target_kind="agent" for the card sweep.
            if not self._matches(c, target_kind, target_ref):
                continue
            if c.get("state") in ("frozen", "closed"):
                outcomes.append(KillOutcome.already_dead(ref, f"card already {c.get('state')}"))
                continue
            if ref in self._fail:
                # Downstream freeze could not be confirmed → blocked_pending.
                outcomes.append(
                    KillOutcome.blocked_pending(
                        ref, "card freeze not confirmed by provider; blocked at execution"
                    )
                )
                continue
            c["state"] = "frozen"
            outcomes.append(KillOutcome.killed(ref, "card frozen"))
        return outcomes


class ProviderCardFreezer:
    """Real card freezer: wraps a provider-layer :class:`CardPort`.

    ``card_port`` is a duck-typed object exposing
    ``set_state(card_ref, state="frozen")`` (the apps/api ``CardPort``).
    ``enumerate_cards`` is an injected coroutine returning the card refs for a
    target — the engine has no card index of its own.  Importing this module
    never requires the provider layer; the port is injected.

    Fail-closed: if ``set_state`` raises or returns ``ok=False``, the card is
    reported ``blocked_pending`` (the orchestrator still denies the revoked
    mandate), never silently ``killed``.
    """

    kind = PropagationKind.CARD

    def __init__(self, card_port: Any, enumerate_cards: Any) -> None:
        self._card_port = card_port
        self._enumerate = enumerate_cards

    async def freeze_for_target(
        self, *, target_kind: str, target_ref: str, requested_by: str
    ) -> list[KillOutcome]:
        refs: list[str] = await self._enumerate(
            target_kind=target_kind, target_ref=target_ref
        )
        outcomes: list[KillOutcome] = []
        for ref in refs:
            try:
                res = await self._card_port.set_state(ref, state="frozen")
            except Exception as exc:  # noqa: BLE001 - surfaced, not swallowed
                logger.error("revocation: card freeze raised for %s: %s", ref, exc)
                outcomes.append(
                    KillOutcome.blocked_pending(
                        ref, f"card freeze raised: {exc}; blocked at execution"
                    )
                )
                continue
            if getattr(res, "ok", True):
                outcomes.append(KillOutcome.killed(ref, f"card frozen via {getattr(res, 'provider', 'card_port')}"))
            else:
                outcomes.append(
                    KillOutcome.blocked_pending(
                        ref,
                        f"card freeze returned not-ok ({getattr(res, 'error', 'unknown')}); "
                        "blocked at execution",
                    )
                )
        return outcomes


class InMemoryApprovalRevoker:
    """Mock approval store.  ``approvals`` maps ``apreq_id -> {"agent_id",
    "mandate_id", "status"}``.  Denies/expires matching pending requests."""

    kind = PropagationKind.APPROVAL

    def __init__(self, approvals: dict[str, dict[str, Any]]) -> None:
        self._approvals = approvals

    async def deny_pending_for_target(
        self, *, agent_id: str | None, mandate_ids: list[str], requested_by: str
    ) -> list[KillOutcome]:
        wanted_mandates = set(mandate_ids)
        outcomes: list[KillOutcome] = []
        for aid, a in self._approvals.items():
            match = (agent_id is not None and a.get("agent_id") == agent_id) or (
                a.get("mandate_id") in wanted_mandates
            )
            if not match:
                continue
            if a.get("status") != "pending":
                outcomes.append(
                    KillOutcome.already_dead(aid, f"approval already {a.get('status')}")
                )
                continue
            a["status"] = "denied"
            a["decided_by"] = requested_by
            outcomes.append(KillOutcome.killed(aid, "pending approval denied"))
        return outcomes


class InMemoryInFlightBlocker:
    """Mock in-flight payment ledger.  ``payments`` maps ``pay_id -> {"agent_id",
    "mandate_id", "status"}``.  Blocks payments still in a pre-settlement state.

    ``fail_refs`` simulates an unconfirmable block (e.g. a broadcast already in
    the mempool): reported ``blocked_pending`` — the authority is denied at
    execution but the in-flight tx's fate is not yet confirmed.
    """

    kind = PropagationKind.IN_FLIGHT
    _IN_FLIGHT = {"pending", "authorized", "queued", "submitting", "in_flight"}

    def __init__(
        self,
        payments: dict[str, dict[str, Any]],
        *,
        fail_refs: set[str] | None = None,
    ) -> None:
        self._payments = payments
        self._fail = fail_refs or set()

    async def block_for_target(
        self, *, agent_id: str | None, mandate_ids: list[str], requested_by: str
    ) -> list[KillOutcome]:
        wanted_mandates = set(mandate_ids)
        outcomes: list[KillOutcome] = []
        for pid, p in self._payments.items():
            match = (agent_id is not None and p.get("agent_id") == agent_id) or (
                p.get("mandate_id") in wanted_mandates
            )
            if not match:
                continue
            if p.get("status") not in self._IN_FLIGHT:
                outcomes.append(
                    KillOutcome.already_dead(pid, f"payment already {p.get('status')}")
                )
                continue
            if pid in self._fail:
                outcomes.append(
                    KillOutcome.blocked_pending(
                        pid, "in-flight payment broadcast unconfirmed; blocked at execution"
                    )
                )
                continue
            p["status"] = "blocked"
            outcomes.append(KillOutcome.killed(pid, "in-flight payment blocked"))
        return outcomes


__all__ = [
    "ApprovalRevokerPort",
    "CardFreezerPort",
    "InFlightBlockerPort",
    "InMemoryApprovalRevoker",
    "InMemoryCardFreezer",
    "InMemoryInFlightBlocker",
    "InMemoryMandateRevoker",
    "InMemorySpendObjectRevoker",
    "KillOutcome",
    "MandateRevokerPort",
    "ProviderCardFreezer",
    "SpendObjectRevokerPort",
]
