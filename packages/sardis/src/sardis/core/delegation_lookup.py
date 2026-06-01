"""Delegation-aware spending-mandate lookup — wires the Attenuated Delegation
Graph into the orchestrator's Phase 0.5 (MANDATE_VALIDATION).

The :class:`~sardis.core.orchestrator.PaymentOrchestrator` authorizes a payment
in Phase 0.5 by asking a :class:`SpendingMandateLookupPort` for the *active*
SpendingMandate governing the acting agent/wallet.  For the root mandate holder
that is a direct lookup.  But when the acting agent is a **delegatee** — a
sub-agent (or tool) exercising a scoped, bounded, revocable slice of authority
delegated down a capability chain — the payment must be re-checked against the
WHOLE chain at EXECUTION time, fail-closed:

    every link non-revoked + within its cap/scope + non-expired, else DENY.

This adapter is that bridge.  It composes:

* ``base`` — the underlying :class:`SpendingMandateLookupPort` (e.g. the
  Postgres :class:`~sardis.core.spending_mandate_lookup.SpendingMandateLookup`)
  that resolves + records spend against the root SpendingMandate row;
* ``engine`` — the :class:`~sardis.core.delegation_engine.DelegationEngine`
  that resolves + re-checks + decrements the attenuated delegation chain.

Decision flow in :meth:`get_active_mandate`:

1. Resolve the acting agent's delegation chain (``engine.resolve_chain``).
2. **No chain** -> the agent is NOT a delegatee; fall through to the base lookup
   (it is the root mandate holder, or has no authority at all).
3. **A chain exists** -> the agent IS a delegatee.  Re-check the whole chain
   with the in-flight payment's amount + scope (``engine.check_chain``).  Any
   broken link -> return ``None`` (the orchestrator denies fail-closed before
   any money moves).  Authorized -> stash the resolved chain (keyed by the
   per-execution ``payment.mandate_id``) so the orchestrator can bind it into
   the portable Proof-of-Authority, and return the root SpendingMandate
   (``chain[0]``) so the orchestrator enforces its scope/limits/approvals
   normally on top of the delegation check.

Sardis owns the authority DECISION (the moat): the chain re-check here is the
authoritative, fail-closed gate; the root mandate's own ``check_payment`` then
applies as a second, redundant ceiling.

Money is :class:`~decimal.Decimal` in token (major) units throughout.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger("sardis.delegation_lookup")


class DelegationAwareMandateLookup:
    """A :class:`SpendingMandateLookupPort` that enforces the delegation chain.

    Wraps a base mandate lookup and a :class:`DelegationEngine`.  Direct
    (non-delegated) payments behave exactly like the base lookup; delegated
    payments are gated fail-closed on the whole attenuated chain at execution
    time and have their leaf + ancestor caps decremented on settlement.
    """

    def __init__(self, *, base: Any, engine: Any) -> None:
        self._base = base
        self._engine = engine
        # Resolved chains keyed by the per-execution ``payment.mandate_id`` (the
        # orchestrator's dedup key, unique per execution).  Bridges the
        # ``get_active_mandate`` decision to the orchestrator's later
        # ``get_resolved_chain`` read; cleared when read.
        self._chains: dict[str, list[Any]] = {}

    # ── Phase 0.5: resolve + execution-time chain re-check (FAIL-CLOSED) ─

    async def get_active_mandate(
        self,
        agent_id: str | None = None,
        wallet_id: str | None = None,
        payment: Any | None = None,
    ) -> Any | None:
        """Return the governing root SpendingMandate, or ``None`` to DENY.

        For a delegatee, the whole attenuated chain is re-checked against the
        in-flight payment; any broken link yields ``None`` (deny fail-closed).
        For a non-delegatee, this defers to the base lookup unchanged.
        """
        chain: list[Any] = []
        if agent_id:
            chain = await self._engine.resolve_chain(agent_id)

        if not chain:
            # Not acting under delegated authority — direct root-mandate path.
            return await self._base.get_active_mandate(
                agent_id=agent_id, wallet_id=wallet_id
            )

        # The acting agent is a DELEGATEE: re-check the whole chain NOW with the
        # real payment's amount + scope.  This is the authoritative gate.
        amount, counterparty, category, mcc, rail = self._payment_facts(payment)
        result = await self._engine.check_chain(
            chain,
            amount=amount,
            counterparty=counterparty,
            category=category,
            mcc=mcc,
            rail=rail,
        )
        if not result.authorized:
            # Fail-closed: a broken link (revoked / expired / over-cap /
            # out-of-scope anywhere up the chain) removes authority entirely.
            logger.warning(
                "Delegation chain DENIED for delegatee=%s: %s (broken_link=%s)",
                agent_id, result.reason, result.broken_link,
            )
            return None

        root = chain[0]
        # Stash the resolved chain so the orchestrator can record it on the
        # PaymentResult / Proof-of-Authority.  Keyed by the per-execution id.
        exec_key = getattr(payment, "mandate_id", None)
        if exec_key:
            self._chains[exec_key] = chain
        logger.info(
            "Delegation chain AUTHORIZED for delegatee=%s: leaf=%s root_mandate=%s depth=%d",
            agent_id, result.leaf_delegation_id, getattr(root, "id", None),
            len(chain) - 1,
        )
        return root

    @staticmethod
    def _payment_facts(
        payment: Any | None,
    ) -> tuple[Decimal, str | None, str | None, str | None, str | None]:
        """Extract (amount, counterparty, category, mcc, rail) from a payment.

        Money is normalized to token (major) units to match the delegation caps
        (which, like SpendingMandate limits, are expressed in major units) — a
        50-USDC payment is checked as ``50``, never ``50_000_000``.
        """
        if payment is None:
            return Decimal("0"), None, None, None, None
        # Lazy import: avoids any module-load import-order coupling with the
        # orchestrator (which owns the canonical minor->major normalization).
        from .orchestrator import _resolve_token_amount

        amount = _resolve_token_amount(payment)
        counterparty = (
            getattr(payment, "merchant_id", None)
            or getattr(payment, "destination", None)
        )
        category = getattr(payment, "merchant_category", None)
        mcc = getattr(payment, "mcc", None)
        rail = getattr(payment, "rail", None)
        return amount, counterparty, category, mcc, rail

    # ── chain read-back for Proof-of-Authority ──────────────────────────

    def get_resolved_chain(self, execution_id: str) -> list[Any]:
        """Pop the resolved delegation chain for a per-execution id.

        Returns the root-first chain (``[]`` for a direct payment) and clears the
        stash so it does not leak across executions.
        """
        return self._chains.pop(execution_id, [])

    # ── Phase 3.5: spend recording (root + every ancestor) ──────────────

    async def record_spend(self, mandate_id: str, amount: Any) -> None:
        """Record the spend against the ROOT SpendingMandate row (delegated to
        the base lookup).

        The root's ``spent_total`` is consumed by a delegatee's spend just as it
        would be by a direct payment, so this is always called.  The per-hop
        delegation caps are decremented separately via :meth:`record_chain_spend`
        (driven by the orchestrator with the resolved chain) so the root is NOT
        double-counted here.
        """
        await self._base.record_spend(mandate_id=mandate_id, amount=amount)

    async def record_chain_spend(self, chain: list[Any], amount: Any) -> None:
        """Decrement the leaf delegation AND every ancestor delegation hop.

        A delegate's spend draws down its own remaining AND every ancestor
        delegation's remaining (the cardinal attenuation rule, enforced at spend
        time so the next chain re-check sees the reduced caps).  Each hop is
        decremented atomically per-row by the store; the root SpendingMandate is
        NOT touched here (it is recorded by :meth:`record_spend`), so there is no
        double-count.  No-op for an empty / non-delegated chain.
        """
        if not chain:
            return
        await self._engine.record_chain_spend(chain, Decimal(str(amount)))


__all__ = ["DelegationAwareMandateLookup"]
