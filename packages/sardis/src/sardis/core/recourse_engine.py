"""RecourseEngine — the orchestrator's Programmable-Recourse collaborator.

Bundles the durable :class:`RecourseHoldStore` with a swappable
:class:`RecourseExecutorPort` so the orchestrator can, after a successful
payment that carries a policy-defined recourse window:

1. open a durable, signed :class:`RecourseHold` (status ``held``) and park the
   funds/claim via the executor;

and later (via a sweep job, a merchant confirmation, or a dispute flow):

2. **release** on window expiry — settle to the recipient (signed evidence);
3. **refund** within the window — reverse-transfer to the payer (``<= held``);
4. **dispute** within the window, then **resolve** down exactly one path.

Sardis owns every decision and its signed evidence (the moat).  The executor is
swappable execution and NEVER decides the outcome.  Fail-closed throughout: a
settling transition only persists once the executor reports success, and the
state machine forbids double-release / refund-over-amount / multi-path dispute
resolution — so even a buggy caller cannot move money twice.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from .recourse_executor import (
    NoopRecourseExecutor,
    RecourseExecutorPort,
)
from .recourse_hold import (
    RecourseHold,
    RecourseStatus,
    Resolution,
    build_recourse_hold,
)
from .recourse_hold_repository import RecourseHoldStore

logger = logging.getLogger("sardis.recourse_engine")


class RecourseEngine:
    """Engine-side recourse orchestration.  Owns the store + executor."""

    def __init__(
        self,
        *,
        store: RecourseHoldStore,
        executor: RecourseExecutorPort | None = None,
        signing_secret: str | None = None,
    ) -> None:
        self._store = store
        self._executor = executor or NoopRecourseExecutor()
        self._secret = signing_secret

    # ── open (the post-execution hook) ─────────────────────────────────

    async def open_hold(
        self,
        *,
        payment_ref: str,
        mandate_id: str | None,
        agent_id: str | None,
        amount: Decimal,
        amount_minor: int,
        currency: str,
        payer: str,
        recipient: str,
        window_seconds: int,
        policy_hash: str = "",
        mandate_hash: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> RecourseHold:
        """Create a durable ``held`` hold and park the funds/claim.

        The hold is persisted BEFORE the executor runs so a crash mid-open never
        loses the record; the executor's settlement refs are then saved back.  A
        failed open leaves the hold ``held`` with the failure recorded — the
        sweep can retry, and no money has been (irreversibly) released.
        """
        hold = build_recourse_hold(
            payment_ref=payment_ref,
            mandate_id=mandate_id,
            agent_id=agent_id,
            amount=amount,
            amount_minor=amount_minor,
            currency=currency,
            payer=payer,
            recipient=recipient,
            window_seconds=window_seconds,
            policy_hash=policy_hash,
            mandate_hash=mandate_hash,
            metadata=metadata,
        )
        await self._store.create(hold)

        ref = await self._executor.open_hold(hold)
        hold.escrow_contract = ref.escrow_contract
        hold.escrow_payment_id = ref.escrow_payment_id
        hold.open_tx_hash = ref.tx_hash
        if not ref.ok:
            hold.metadata["open_error"] = ref.error
            logger.warning("recourse open execution failed for %s: %s", hold.id, ref.error)
        await self._store.save(hold)
        logger.info(
            "recourse hold opened: %s payment_ref=%s amount_minor=%s %s window=%ss",
            hold.id, payment_ref, amount_minor, currency,
            int((hold.expires_at - hold.opened_at).total_seconds()),
        )
        return hold

    # ── release (window expired / delivery confirmed) ──────────────────

    async def release(
        self, hold_id: str, *, actor: str = "system"
    ) -> RecourseHold:
        """Settle a held hold to the recipient.  Fail-closed: no double-release.

        The domain ``release()`` guard rejects a second release (or releasing a
        refunded/resolved hold) before any execution runs, and the executor is
        only invoked on a legal transition.
        """
        hold = await self._require(hold_id)
        # 1) Validate legality WITHOUT mutating — fail-closed on a double-release
        #    or a terminal hold before any money is touched.
        hold.check_can_release()
        # 2) Move (or claim) the money.  A failed execution must NOT advance the
        #    hold, so the domain transition + save happen only on success.
        ref = await self._executor.settle_release(hold)
        if not ref.ok:
            raise RuntimeError(
                f"recourse release execution failed for {hold_id}: {ref.error}"
            )
        # 3) Apply the signed transition and persist.
        ev = hold.release(actor=actor, secret=self._secret)
        hold.settle_tx_hash = ref.tx_hash
        await self._store.save(hold)
        logger.info("recourse hold released: %s tx=%s evidence=%s",
                    hold_id, ref.tx_hash, ev.signature[:12])
        return hold

    # ── refund (within window) ─────────────────────────────────────────

    async def refund(
        self,
        hold_id: str,
        *,
        amount_minor: int | None = None,
        actor: str = "system",
    ) -> RecourseHold:
        """Return funds to the payer within the window (full or partial).

        Fail-closed: the domain ``refund()`` enforces ``refund <= held`` before
        any reverse-transfer is attempted."""
        hold = await self._require(hold_id)
        hold.check_can_refund(amount_minor)
        refunded = amount_minor if amount_minor is not None else hold.refundable_minor
        ref = await self._executor.settle_refund(hold, amount_minor=int(refunded))
        if not ref.ok:
            raise RuntimeError(
                f"recourse refund execution failed for {hold_id}: {ref.error}"
            )
        ev = hold.refund(amount_minor=amount_minor, actor=actor, secret=self._secret)
        hold.settle_tx_hash = ref.tx_hash
        await self._store.save(hold)
        logger.info("recourse hold refunded: %s tx=%s evidence=%s",
                    hold_id, ref.tx_hash, ev.signature[:12])
        return hold

    # ── dispute → resolve (single path) ────────────────────────────────

    async def dispute(
        self, hold_id: str, *, actor: str, reason: str | None = None
    ) -> RecourseHold:
        """Open a dispute on a held hold.  Pauses auto-release; no money moves."""
        hold = await self._require(hold_id)
        hold.dispute(actor=actor, reason=reason, secret=self._secret)
        await self._store.save(hold)
        logger.info("recourse hold disputed: %s by=%s", hold_id, actor)
        return hold

    async def resolve(
        self,
        hold_id: str,
        *,
        resolution: Resolution,
        actor: str,
        amount_minor: int | None = None,
    ) -> RecourseHold:
        """Resolve a disputed hold down exactly one path: refund or release."""
        hold = await self._require(hold_id)
        hold.check_can_resolve(resolution, amount_minor)
        if resolution == Resolution.REFUND:
            refunded = amount_minor if amount_minor is not None else hold.refundable_minor
            ref = await self._executor.settle_refund(hold, amount_minor=int(refunded))
        else:
            ref = await self._executor.settle_release(hold)
        if not ref.ok:
            raise RuntimeError(
                f"recourse resolve execution failed for {hold_id}: {ref.error}"
            )
        ev = hold.resolve(
            resolution=resolution, actor=actor,
            amount_minor=amount_minor, secret=self._secret,
        )
        hold.settle_tx_hash = ref.tx_hash
        await self._store.save(hold)
        logger.info("recourse hold resolved: %s resolution=%s tx=%s evidence=%s",
                    hold_id, resolution.value, ref.tx_hash, ev.signature[:12])
        return hold

    # ── expiry sweep ────────────────────────────────────────────────────

    async def sweep_expired(self, *, as_of=None) -> list[str]:
        """Release all held holds whose window has passed.  Returns released IDs.

        Disputed holds are intentionally excluded (a dispute pauses auto-release
        until explicitly resolved)."""
        expired = await self._store.list_expired_held(as_of=as_of)
        released: list[str] = []
        for hold in expired:
            try:
                await self.release(hold.id, actor="system")
                released.append(hold.id)
            except Exception as exc:  # noqa: BLE001 - one bad hold must not stall the sweep
                logger.error("recourse sweep failed to release %s: %s", hold.id, exc)
        if released:
            logger.info("recourse sweep released %d expired holds", len(released))
        return released

    # ── reads ───────────────────────────────────────────────────────────

    async def get(self, hold_id: str) -> RecourseHold | None:
        return await self._store.get(hold_id)

    async def get_by_payment_ref(self, payment_ref: str) -> RecourseHold | None:
        return await self._store.get_by_payment_ref(payment_ref)

    async def list_open(self, *, limit: int = 100) -> list[RecourseHold]:
        """All non-terminal holds (``held``/``disputed``), oldest first.

        The store applies the SQL filter; org-scoping is the caller's
        responsibility (the engine has no org concept — see the API surface)."""
        return await self._store.list_open(limit=limit)

    async def _require(self, hold_id: str) -> RecourseHold:
        hold = await self._store.get(hold_id)
        if hold is None:
            raise ValueError(f"recourse hold {hold_id} not found")
        return hold

    @staticmethod
    def is_open(hold: RecourseHold) -> bool:
        return hold.status in (RecourseStatus.HELD, RecourseStatus.DISPUTED)


__all__ = ["RecourseEngine"]
