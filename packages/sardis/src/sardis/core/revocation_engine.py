"""RevocationEngine — the propagating kill switch.

``revoke(target)`` is the lead-wedge primitive: ONE call atomically propagates a
revocation across EVERY rail and returns a signed, independently-verifiable
:class:`~sardis.core.revocation.RevocationProof`.

The propagation algorithm (single, ordered, fail-closed):

1. **Idempotency check** — if a revocation already exists for this target,
   return the *same* revocation + proof.  Re-revoke is a no-op.

2. **Create the durable record first** — persist the ``Revocation`` (no targets
   yet) BEFORE touching any rail, so a crash mid-propagation never loses the
   decision.  The decision is already in force at this point: the orchestrator's
   mandate lookup returns only ``active`` rows, so once step 3 flips the
   mandate, every future payment for it is denied regardless of what the other
   rails do.

3. **Mandate first** — mark the SpendingMandate(s) revoked.  This is the
   authority root: with it gone, the orchestrator denies at execution time even
   if every other rail-kill below fails.  Record each as a PropagationTarget.

4. **Enumerate + kill derived authority across all rails**, recording every
   object touched as a PropagationTarget with its ``kill_status``:
   spend objects (revoke/expire), agent cards (freeze via CardPort), pending
   approvals (deny), in-flight payments (block).

5. **Compute the honest outcome** — if ANY target is not confirmed dead, the
   outcome is ``blocked_pending_downstream`` (NEVER ``propagated``).  The
   authority is still blocked at execution time (step 3), but the proof tells
   the truth: this rail is "blocked-at-execution pending downstream
   confirmation".

6. **Sign + persist the proof.**

A rail-killer that *raises* is caught and turned into a synthetic ``failed``
PropagationTarget — one buggy rail must never abort the whole kill or, worse,
leave the proof claiming success.  Fail-closed is the invariant everywhere:
partial propagation is reported as partial, and authority is denied at
execution regardless.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from .revocation import (
    KillStatus,
    PropagationKind,
    PropagationTarget,
    Revocation,
    RevocationTargetKind,
    build_revocation,
)
from .revocation_ports import (
    ApprovalRevokerPort,
    CardFreezerPort,
    InFlightBlockerPort,
    KillOutcome,
    MandateRevokerPort,
    SpendObjectRevokerPort,
)
from .revocation_repository import RevocationStore

logger = logging.getLogger("sardis.revocation_engine")


class RevocationEngine:
    """Engine-side propagating revocation.  Owns the store + the rail killers.

    The mandate revoker is required — it is the authority root that makes the
    orchestrator deny at execution time.  The other killers are optional: a
    deployment without cards simply omits the card freezer, and that rail
    contributes no targets.  Every killer is swappable (real adapter or mock).
    """

    def __init__(
        self,
        *,
        store: RevocationStore,
        mandate_revoker: MandateRevokerPort,
        spend_object_revoker: SpendObjectRevokerPort | None = None,
        card_freezer: CardFreezerPort | None = None,
        approval_revoker: ApprovalRevokerPort | None = None,
        in_flight_blocker: InFlightBlockerPort | None = None,
        signing_secret: str | None = None,
    ) -> None:
        self._store = store
        self._mandate_revoker = mandate_revoker
        self._spend_object_revoker = spend_object_revoker
        self._card_freezer = card_freezer
        self._approval_revoker = approval_revoker
        self._in_flight_blocker = in_flight_blocker
        self._secret = signing_secret

    # ── public entry point ──────────────────────────────────────────────

    async def revoke(
        self,
        *,
        target_kind: RevocationTargetKind,
        target_ref: str,
        requested_by: str,
        reason: str = "",
        scope: str = "all",
        agent_id: str | None = None,
    ) -> Revocation:
        """Atomically propagate a revocation across every rail.

        ``agent_id`` is an optional hint used to reach agent-scoped rails (cards,
        approvals, in-flight payments) when the target is a *mandate* (a mandate
        carries an agent).  For ``target_kind=agent`` it defaults to
        ``target_ref``.  Returns the durable :class:`Revocation` with its signed
        :class:`~sardis.core.revocation.RevocationProof`.

        Idempotent: a re-revoke of an already-revoked target returns the same
        revocation + proof without re-propagating.
        """
        # 1) Idempotency — same target → same proof, no double-propagation.
        existing = await self._store.get_active_for_target(
            target_kind=target_kind.value, target_ref=target_ref
        )
        if existing is not None and existing.proof is not None:
            logger.info(
                "revocation idempotent hit: target=%s/%s -> %s",
                target_kind.value,
                target_ref,
                existing.id,
            )
            return existing

        rev = build_revocation(
            target_kind=target_kind,
            target_ref=target_ref,
            requested_by=requested_by,
            scope=scope,
            metadata={"reason": reason} if reason else {},
        )
        # 2) Persist the decision BEFORE propagating (crash-safe).
        await self._store.create(rev)

        # 3) Mandate first — the authority root.  With it revoked, the
        #    orchestrator denies at execution time even if everything below
        #    fails.  This is what makes a partial propagation still fail-closed.
        revoked_mandate_ids = await self._kill_mandates(
            rev, target_kind=target_kind, target_ref=target_ref,
            requested_by=requested_by, reason=reason,
        )

        # The agent whose card/approval/in-flight rails we must also sweep.
        effective_agent = agent_id or (
            target_ref if target_kind == RevocationTargetKind.AGENT else None
        )

        # 4) Enumerate + kill derived authority across the remaining rails.
        await self._kill_spend_objects(rev, mandate_ids=revoked_mandate_ids,
                                       requested_by=requested_by)
        await self._kill_cards(rev, target_kind=target_kind, target_ref=target_ref,
                               effective_agent=effective_agent, requested_by=requested_by)
        await self._kill_approvals(rev, agent_id=effective_agent,
                                   mandate_ids=revoked_mandate_ids,
                                   requested_by=requested_by)
        await self._kill_in_flight(rev, agent_id=effective_agent,
                                   mandate_ids=revoked_mandate_ids,
                                   requested_by=requested_by)

        # 5) Honest outcome — partial propagation is reported as partial.
        rev.status = rev.compute_outcome()
        rev.revoked_at = datetime.now(UTC)

        # 6) Sign + persist the proof.
        rev.build_proof(self._secret)
        await self._store.save(rev)

        confirmed = sum(1 for t in rev.targets if t.is_confirmed_dead())
        logger.info(
            "revocation %s propagated: target=%s/%s outcome=%s targets=%d confirmed_dead=%d",
            rev.id, target_kind.value, target_ref, rev.status.value,
            len(rev.targets), confirmed,
        )
        return rev

    # ── per-rail propagation (each records targets, never raises out) ───

    async def _kill_mandates(
        self,
        rev: Revocation,
        *,
        target_kind: RevocationTargetKind,
        target_ref: str,
        requested_by: str,
        reason: str,
    ) -> list[str]:
        """Revoke the mandate(s) and return the ids that are now dead.

        The returned ids drive the other rails (spend objects / approvals /
        in-flight are keyed by mandate).  ``already_dead`` ids are still returned
        — their derived authority must also be swept on a re-revoke path that
        bypassed idempotency (defensive).
        """
        outcomes = await self._safe_call(
            rev,
            PropagationKind.MANDATE,
            self._mandate_revoker.revoke_for_target(
                target_kind=target_kind.value,
                target_ref=target_ref,
                requested_by=requested_by,
                reason=reason,
            ),
            fallback_ref=target_ref,
        )
        return [o.ref for o in outcomes if o.kill_status in (
            KillStatus.KILLED, KillStatus.ALREADY_DEAD
        )]

    async def _kill_spend_objects(
        self, rev: Revocation, *, mandate_ids: list[str], requested_by: str
    ) -> None:
        if self._spend_object_revoker is None or not mandate_ids:
            return
        await self._safe_call(
            rev,
            PropagationKind.SPEND_OBJECT,
            self._spend_object_revoker.revoke_for_mandates(
                mandate_ids=mandate_ids, requested_by=requested_by
            ),
            fallback_ref=",".join(mandate_ids),
        )

    async def _kill_cards(
        self,
        rev: Revocation,
        *,
        target_kind: RevocationTargetKind,
        target_ref: str,
        effective_agent: str | None,
        requested_by: str,
    ) -> None:
        if self._card_freezer is None:
            return
        # Cards are agent/principal-scoped. For a mandate target, reach cards via
        # the mandate's agent (target_kind="agent"); otherwise pass the target
        # through directly.
        if target_kind == RevocationTargetKind.MANDATE:
            if effective_agent is None:
                return  # no agent to reach the cards by — nothing to sweep
            sweep_kind, sweep_ref = "agent", effective_agent
        else:
            sweep_kind, sweep_ref = target_kind.value, target_ref
        await self._safe_call(
            rev,
            PropagationKind.CARD,
            self._card_freezer.freeze_for_target(
                target_kind=sweep_kind, target_ref=sweep_ref, requested_by=requested_by
            ),
            fallback_ref=sweep_ref,
        )

    async def _kill_approvals(
        self,
        rev: Revocation,
        *,
        agent_id: str | None,
        mandate_ids: list[str],
        requested_by: str,
    ) -> None:
        if self._approval_revoker is None or (agent_id is None and not mandate_ids):
            return
        await self._safe_call(
            rev,
            PropagationKind.APPROVAL,
            self._approval_revoker.deny_pending_for_target(
                agent_id=agent_id, mandate_ids=mandate_ids, requested_by=requested_by
            ),
            fallback_ref=agent_id or ",".join(mandate_ids),
        )

    async def _kill_in_flight(
        self,
        rev: Revocation,
        *,
        agent_id: str | None,
        mandate_ids: list[str],
        requested_by: str,
    ) -> None:
        if self._in_flight_blocker is None or (agent_id is None and not mandate_ids):
            return
        await self._safe_call(
            rev,
            PropagationKind.IN_FLIGHT,
            self._in_flight_blocker.block_for_target(
                agent_id=agent_id, mandate_ids=mandate_ids, requested_by=requested_by
            ),
            fallback_ref=agent_id or ",".join(mandate_ids),
        )

    # ── safety wrapper ──────────────────────────────────────────────────

    async def _safe_call(
        self,
        rev: Revocation,
        kind: PropagationKind,
        coro: Any,
        *,
        fallback_ref: str,
    ) -> list[KillOutcome]:
        """Await a rail-killer, record its outcomes as targets, never raise out.

        Fail-closed: if the killer RAISES, we record a synthetic ``failed``
        target (which counts as "not confirmed dead" → the overall outcome
        becomes ``blocked_pending_downstream``).  The authority is still denied
        at execution time because the mandate is already revoked.  A buggy rail
        can therefore never abort the whole kill nor inflate the proof.
        """
        now = datetime.now(UTC)
        try:
            outcomes = await coro
        except Exception as exc:  # noqa: BLE001 - one bad rail must not abort the kill
            logger.error(
                "revocation %s: rail %s raised during propagation: %s",
                rev.id, kind.value, exc,
            )
            rev.add_target(
                PropagationTarget(
                    kind=kind,
                    ref=fallback_ref,
                    kill_status=KillStatus.FAILED,
                    detail=f"rail killer raised: {exc}; blocked at execution",
                    killed_at=now,
                )
            )
            return []
        for o in outcomes:
            rev.add_target(
                PropagationTarget(
                    kind=kind,
                    ref=o.ref,
                    kill_status=o.kill_status,
                    detail=o.detail,
                    killed_at=now if o.kill_status in (
                        KillStatus.KILLED, KillStatus.ALREADY_DEAD
                    ) else None,
                )
            )
        return outcomes

    # ── reads ───────────────────────────────────────────────────────────

    async def get(self, revocation_id: str) -> Revocation | None:
        return await self._store.get(revocation_id)

    async def list_recent(self, *, limit: int = 100) -> list[Revocation]:
        return await self._store.list_recent(limit=limit)


__all__ = ["RevocationEngine"]
