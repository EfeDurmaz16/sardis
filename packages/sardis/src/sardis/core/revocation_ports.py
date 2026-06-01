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


class DelegationRevokerPort(Protocol):
    kind = PropagationKind.DELEGATION

    async def revoke_subtree(
        self,
        *,
        mandate_ids: list[str],
        agent_id: str | None,
        delegation_ids: list[str],
        requested_by: str,
        reason: str,
    ) -> list[KillOutcome]:
        """Revoke the ENTIRE delegation subtree reachable from the target.

        Revoking a parent must kill all descendant delegations: delegations
        rooted at any killed mandate (``root_mandate_id in mandate_ids``),
        delegations a revoked agent holds (``delegatee == agent_id``) plus their
        descendants, and any directly-targeted ``delegation_ids`` plus their
        descendants.  Returns one :class:`KillOutcome` per delegation touched.
        """
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


class DelegationSubtreeRevoker:
    """Revoke an entire delegation subtree over a :class:`DelegationStore`.

    Works against BOTH the in-memory and Postgres stores (it only uses the
    store's ``get`` / ``children_of`` / ``save`` surface), so one adapter serves
    dev/tests and production.  The walk is breadth-first from every seed
    (mandate roots, the revoked agent's held delegations, directly-targeted
    delegations), marking each reachable delegation revoked and recording a
    :class:`KillOutcome`.

    Cycle-safe (a ``seen`` set) and idempotent (already-revoked hops are
    reported ``already_dead``).  Fail-closed: a hop that cannot be persisted is
    reported ``blocked_pending`` — the execution-time chain re-check still denies
    any payment whose chain contains a non-active link, so authority is gone even
    if a row's status write is unconfirmed.
    """

    kind = PropagationKind.DELEGATION

    def __init__(self, store: Any) -> None:
        # ``store`` is a DelegationStore (get / children_of / save). Injected so
        # this never imports a live pool and is unit-testable with the in-memory
        # store.
        self._store = store

    async def revoke_subtree(
        self,
        *,
        mandate_ids: list[str],
        agent_id: str | None,
        delegation_ids: list[str],
        requested_by: str,
        reason: str,
    ) -> list[KillOutcome]:
        from .delegation import DelegationStatus

        # 1) Collect the seed delegations: roots of killed mandates, the agent's
        #    held delegations, and any directly-targeted delegations.
        seeds: dict[str, Any] = {}
        for mid in mandate_ids:
            for d in await self._store.children_of(parent_kind="mandate", parent_ref=mid):
                seeds[d.id] = d
        for did in delegation_ids:
            d = await self._store.get(did)
            if d is not None:
                seeds[d.id] = d
        if agent_id is not None and hasattr(self._store, "get_for_delegatee"):
            # The agent may hold a delegation as a delegatee — kill it + subtree.
            held = await self._store.get_for_delegatee(agent_id)
            if held is not None:
                seeds[held.id] = held

        # 2) BFS the subtree from every seed, killing each reachable delegation.
        outcomes: list[KillOutcome] = []
        seen: set[str] = set()
        queue: list[Any] = list(seeds.values())
        while queue:
            d = queue.pop(0)
            if d.id in seen:
                continue
            seen.add(d.id)

            if d.status == DelegationStatus.REVOKED:
                outcomes.append(KillOutcome.already_dead(d.id, "delegation already revoked"))
            else:
                d.revoke(revoked_by=requested_by, reason=reason or "authority revoked")
                try:
                    await self._store.save(d)
                    outcomes.append(KillOutcome.killed(d.id, "delegation revoked"))
                except Exception as exc:  # noqa: BLE001 - surfaced, not swallowed
                    outcomes.append(
                        KillOutcome.blocked_pending(
                            d.id,
                            f"delegation revoke not persisted ({exc}); blocked at execution",
                        )
                    )

            # Enqueue this delegation's direct children (descend the subtree).
            for child in await self._store.children_of(
                parent_kind="delegation", parent_ref=d.id
            ):
                if child.id not in seen:
                    queue.append(child)

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


# ── Real (Postgres / provider-backed) adapters ─────────────────────────
#
# These are the production legs.  Each wraps the SAME surface the rest of the
# product already uses (the spending_mandates table + mandate_state_transitions,
# the payment_objects table, the ApprovalGate cascade, the CardPort) so the
# revocation kill goes through the canonical write path — never a back door.
# All of them report failures honestly (blocked_pending / failed) so the engine
# can fail closed; none of them decide *whether* to revoke.


# Terminal mandate states (already-dead — killing them is a no-op).
_MANDATE_TERMINAL = {"revoked", "expired", "consumed"}


class PostgresMandateRevoker:
    """Real mandate revoker over the ``spending_mandates`` table (migration 071).

    Mirrors the route-level revoke (``UPDATE … status='revoked'`` +
    ``mandate_state_transitions`` audit row) but for the *whole target set*: a
    revoke aimed at an agent / principal kills every mandate reachable from it in
    one statement, returning one :class:`KillOutcome` per mandate.

    Fail-closed: this is the authority root.  If the UPDATE itself raises, the
    engine records a synthetic ``failed`` target (via ``_safe_call``) and the
    overall outcome is ``blocked_pending_downstream`` — but because the row was
    never confirmed flipped, no authority is *claimed* dead that is still alive.
    The orchestrator's lookup (``status = 'active'``) is the execution backstop.
    """

    kind = PropagationKind.MANDATE

    def __init__(self, db: Any) -> None:
        # ``db`` is the Database facade (execute/fetch/fetchrow). Injected so the
        # adapter is unit-testable with a fake and never imports a live pool.
        self._db = db

    def _where(self, target_kind: str, target_ref: str) -> tuple[str, list[Any]]:
        if target_kind == "mandate":
            return "id = $1", [target_ref]
        if target_kind == "agent":
            return "agent_id = $1", [target_ref]
        if target_kind == "principal":
            return "principal_id = $1", [target_ref]
        raise ValueError(f"unknown revocation target_kind: {target_kind!r}")

    async def revoke_for_target(
        self, *, target_kind: str, target_ref: str, requested_by: str, reason: str
    ) -> list[KillOutcome]:
        # A delegation-targeted revoke has no SpendingMandate row to flip here —
        # the delegation subtree revoker handles it. Return no mandate targets.
        if target_kind == "delegation":
            return []
        where, params = self._where(target_kind, target_ref)
        rows = await self._db.fetch(
            f"SELECT id, status FROM spending_mandates WHERE {where}", *params
        )
        outcomes: list[KillOutcome] = []
        for row in rows:
            mid = row["id"]
            status = (row["status"] or "").lower()
            if status in _MANDATE_TERMINAL:
                outcomes.append(
                    KillOutcome.already_dead(mid, f"mandate already {status}")
                )
                continue
            # Conditional UPDATE: only flip rows still alive, so two concurrent
            # revokes cannot both claim the kill.  rowcount == 0 ⇒ lost the race
            # (someone else revoked) ⇒ already_dead, still confirmed dead.
            tag = await self._db.execute(
                """
                UPDATE spending_mandates
                SET status = 'revoked', revoked_at = NOW(), revoked_by = $2,
                    revocation_reason = $3, updated_at = NOW()
                WHERE id = $1 AND status IN ('active', 'suspended', 'draft')
                """,
                mid, requested_by, reason or None,
            )
            if _rowcount(tag) == 0:
                outcomes.append(
                    KillOutcome.already_dead(mid, "mandate concurrently revoked")
                )
                continue
            # Best-effort audit row (failure here must NOT un-confirm the kill —
            # the mandate IS revoked; the orchestrator already denies on it).
            try:
                await self._db.execute(
                    """
                    INSERT INTO mandate_state_transitions
                        (id, mandate_id, from_status, to_status, changed_by,
                         reason, created_at)
                    VALUES ($1, $2, $3, 'revoked', $4, $5, NOW())
                    """,
                    f"mst_{mid[-12:]}_{_short_rand()}", mid, status or "active",
                    requested_by, reason or None,
                )
            except Exception as exc:  # noqa: BLE001 - audit is best-effort
                logger.warning(
                    "revocation: mandate %s revoked but transition audit failed: %s",
                    mid, exc,
                )
            outcomes.append(KillOutcome.killed(mid, "mandate marked revoked"))
        return outcomes


class PostgresSpendObjectRevoker:
    """Real spend-object revoker over the ``payment_objects`` table (mig. 078).

    Revokes every non-terminal one-time spend object (po_…) minted from the
    killed mandates.  Terminal objects (settled / fulfilled / revoked / …) are
    reported ``already_dead`` — money already moved or already cancelled cannot
    be un-moved by a freeze; honesty over optimism.
    """

    kind = PropagationKind.SPEND_OBJECT
    _TERMINAL = ("settled", "fulfilled", "revoked", "expired", "failed", "refunded")

    def __init__(self, db: Any) -> None:
        self._db = db

    async def revoke_for_mandates(
        self, *, mandate_ids: list[str], requested_by: str
    ) -> list[KillOutcome]:
        if not mandate_ids:
            return []
        rows = await self._db.fetch(
            """
            SELECT object_id, status FROM payment_objects
            WHERE mandate_id = ANY($1::text[])
            """,
            list(mandate_ids),
        )
        outcomes: list[KillOutcome] = []
        for row in rows:
            oid = row["object_id"]
            status = (row["status"] or "").lower()
            if status in self._TERMINAL:
                outcomes.append(
                    KillOutcome.already_dead(oid, f"spend object already {status}")
                )
                continue
            tag = await self._db.execute(
                """
                UPDATE payment_objects
                SET status = 'revoked'
                WHERE object_id = $1 AND status NOT IN (
                    'settled','fulfilled','revoked','expired','failed','refunded'
                )
                """,
                oid,
            )
            if _rowcount(tag) == 0:
                outcomes.append(
                    KillOutcome.already_dead(oid, "spend object concurrently terminal")
                )
            else:
                outcomes.append(KillOutcome.killed(oid, "spend object revoked"))
        return outcomes


class ApprovalGateRevoker:
    """Real pending-approval killer over the :class:`ApprovalGate` cascade.

    This is the cascade the dashboard ``RevokeDialog`` promised: revoking an
    agent must also kill its *pending* approvals so a human cannot later click
    "approve" on a request whose authority is already gone.  It enumerates
    pending requests via the store, filters to the target agent / governing
    SpendingMandate, and denies each through the gate's signed
    ``record_decision`` path (so the kill is itself signed evidence).

    Already-decided requests (approved / denied / expired) are ``already_dead``.
    A request that cannot be denied (e.g. it expired between read and write) is
    reported ``blocked_pending`` — never silently skipped.
    """

    kind = PropagationKind.APPROVAL

    def __init__(self, gate: Any) -> None:
        # ``gate`` is an ApprovalGate (has a ._store with list_pending +
        # record_decision).  Injected to avoid a hard import cycle.
        self._gate = gate

    async def deny_pending_for_target(
        self, *, agent_id: str | None, mandate_ids: list[str], requested_by: str
    ) -> list[KillOutcome]:
        wanted_mandates = set(mandate_ids)
        pending = await self._gate._store.list_pending(limit=1000)
        outcomes: list[KillOutcome] = []
        for req in pending:
            match = (agent_id is not None and req.agent_id == agent_id) or (
                req.spending_mandate_id in wanted_mandates
                or req.mandate_id in wanted_mandates
            )
            if not match:
                continue
            try:
                decided = await self._gate.record_decision(
                    approval_id=req.id,
                    decision="deny",
                    approver=requested_by,
                    reason="authority revoked",
                )
            except Exception as exc:  # noqa: BLE001 - surfaced, not swallowed
                outcomes.append(
                    KillOutcome.blocked_pending(
                        req.id, f"approval deny raised: {exc}; blocked at execution"
                    )
                )
                continue
            status = getattr(decided.status, "value", str(decided.status))
            if status == "denied":
                outcomes.append(KillOutcome.killed(req.id, "pending approval denied"))
            elif status == "expired":
                outcomes.append(
                    KillOutcome.already_dead(req.id, "approval expired before deny")
                )
            else:
                # Should not happen for a deny verb, but never claim a kill we
                # did not get.
                outcomes.append(
                    KillOutcome.blocked_pending(
                        req.id, f"approval not denied (now {status}); blocked at execution"
                    )
                )
        return outcomes


class CallbackInFlightBlocker:
    """Real in-flight blocker over an injected enumerator + status updater.

    The in-flight payment ledger lives in different tables per rail (the legacy
    ``transactions`` table, the MPP session store, the execution queue), and its
    schema is not uniform — so rather than couple this leg to one table, it takes
    two injected coroutines (mirroring :class:`ProviderCardFreezer`):

    * ``enumerate`` ``(agent_id, mandate_ids) -> list[(ref, status)]`` — the
      in-flight payments for the target;
    * ``block`` ``(ref) -> bool`` — attempt to block one; ``True`` ⇒ confirmed
      blocked, ``False`` ⇒ could not confirm.

    Fail-closed: a payment already broadcast (``block`` returns ``False`` or
    raises) is ``blocked_pending`` — the authority is denied at execution, but
    the in-flight tx's fate is not yet confirmed, and the proof says so.
    """

    kind = PropagationKind.IN_FLIGHT
    _IN_FLIGHT = {"pending", "authorized", "queued", "submitting", "in_flight"}

    def __init__(self, enumerate_in_flight: Any, block_one: Any) -> None:
        self._enumerate = enumerate_in_flight
        self._block = block_one

    async def block_for_target(
        self, *, agent_id: str | None, mandate_ids: list[str], requested_by: str
    ) -> list[KillOutcome]:
        rows: list[tuple[str, str]] = await self._enumerate(
            agent_id=agent_id, mandate_ids=list(mandate_ids)
        )
        outcomes: list[KillOutcome] = []
        for ref, status in rows:
            if (status or "").lower() not in self._IN_FLIGHT:
                outcomes.append(
                    KillOutcome.already_dead(ref, f"payment already {status}")
                )
                continue
            try:
                ok = await self._block(ref)
            except Exception as exc:  # noqa: BLE001 - surfaced, not swallowed
                outcomes.append(
                    KillOutcome.blocked_pending(
                        ref, f"in-flight block raised: {exc}; blocked at execution"
                    )
                )
                continue
            if ok:
                outcomes.append(KillOutcome.killed(ref, "in-flight payment blocked"))
            else:
                outcomes.append(
                    KillOutcome.blocked_pending(
                        ref,
                        "in-flight payment broadcast unconfirmed; blocked at execution",
                    )
                )
        return outcomes


# ── small helpers ──────────────────────────────────────────────────────


def _rowcount(tag: Any) -> int:
    """Parse an asyncpg command tag (``"UPDATE 3"``) into an affected-row count."""
    try:
        return int(str(tag).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


def _short_rand() -> str:
    import secrets as _secrets

    return _secrets.token_hex(4)


__all__ = [
    "ApprovalGateRevoker",
    "ApprovalRevokerPort",
    "CallbackInFlightBlocker",
    "CardFreezerPort",
    "DelegationRevokerPort",
    "DelegationSubtreeRevoker",
    "InFlightBlockerPort",
    "InMemoryApprovalRevoker",
    "InMemoryCardFreezer",
    "InMemoryInFlightBlocker",
    "InMemoryMandateRevoker",
    "InMemorySpendObjectRevoker",
    "KillOutcome",
    "MandateRevokerPort",
    "PostgresMandateRevoker",
    "PostgresSpendObjectRevoker",
    "ProviderCardFreezer",
    "SpendObjectRevokerPort",
]
