"""DelegationEngine — enforce attenuation at every hop AND at execution time.

This is the object-capability authority engine for money.  It does three things,
all fail-closed:

1. :meth:`delegate` — mint a new :class:`Delegation`.  It REJECTS the mint unless
   the requested grant is a strict narrowing of the delegator's *current*
   authority:

   * ``amount_cap <= delegator remaining`` (cap can never exceed what the parent
     still has to give);
   * ``expires_at <= delegator expiry`` (a child can never outlive its parent);
   * requested scope ``⊆`` delegator scope for every dimension
     (counterparties / categories / mcc / rails);
   * the delegator is itself active (non-revoked, non-expired, non-exhausted);
   * ``depth + 1 <= MAX_DELEGATION_DEPTH``.

   The delegator may be the root :class:`SpendingMandate` (depth 0) or another
   :class:`Delegation` deeper in the chain.  Authority only ever shrinks downward
   — a delegate can NEVER exceed its delegator.

2. :meth:`resolve_chain` — given a delegatee (the acting sub-agent), walk UP the
   ``delegator_ref`` pointers to the root SpendingMandate, returning the ordered
   chain ``[root_mandate, dlg_1, dlg_2, …, leaf]``.

3. :meth:`check_chain` — at execution time, re-check the WHOLE chain link by
   link.  A payment is authorized only if EVERY link is active, non-revoked,
   non-expired, within its cap and in scope.  Any break anywhere up the chain →
   DENY (fail-closed).  This is what makes revoking a parent kill the subtree:
   even if a downstream delegation row was missed, the parent link is dead and
   the chain check denies.

4. :meth:`record_chain_spend` — after a settled delegated payment, decrement the
   leaf delegation's remaining AND every ancestor delegation's remaining (the
   root mandate's spend is recorded by the orchestrator's existing mandate-spend
   path).  A delegate spend draws down the whole chain.

Sardis owns the delegation DECISION + its signed proof (the moat).  The
attenuation checks here reuse the subset/narrowing logic that
:class:`~sardis.core.mandate_tree.MandateTreeValidator` already applies to
SpendingMandate hierarchies, extended to the per-hop Delegation surface.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from .delegation import (
    MAX_DELEGATION_DEPTH,
    Delegation,
    DelegationScope,
    DelegationStatus,
    DelegatorKind,
)
from .delegation_repository import DelegationStore
from .spending_mandate import MandateStatus, SpendingMandate

logger = logging.getLogger("sardis.delegation_engine")


# ── Results ────────────────────────────────────────────────────────────


@dataclass(slots=True)
class AttenuationResult:
    """Outcome of an attenuation check at mint time."""

    valid: bool
    reason: str | None = None
    error_code: str | None = None
    violations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ChainCheckResult:
    """Outcome of re-checking a whole delegation chain at execution time."""

    authorized: bool
    reason: str
    error_code: str | None = None
    # The id of the link that broke (mandate id or delegation id), if denied.
    broken_link: str | None = None
    # The leaf delegation id whose authority was being exercised.
    leaf_delegation_id: str | None = None


class DelegationError(Exception):
    """Raised when a delegation cannot be minted (attenuation violated)."""

    def __init__(self, message: str, *, error_code: str | None = None,
                 violations: list[str] | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.violations = violations or []


# ── Engine ─────────────────────────────────────────────────────────────


class DelegationEngine:
    """Mint + resolve + re-check attenuating delegation chains.

    ``store`` is the durable :class:`DelegationStore`.  ``mandate_resolver`` is an
    async callable ``(mandate_id) -> SpendingMandate | None`` used to fetch the
    root SpendingMandate when resolving / checking a chain (the engine has no
    mandate index of its own — it reuses the product's mandate store).
    ``signing_secret`` overrides ``SARDIS_DELEGATION_HMAC_KEY`` (tests).
    """

    def __init__(
        self,
        *,
        store: DelegationStore,
        mandate_resolver: Any,
        signing_secret: str | None = None,
    ) -> None:
        self._store = store
        self._resolve_mandate = mandate_resolver
        self._secret = signing_secret

    # ── 1) mint with attenuation enforcement ────────────────────────────

    async def delegate(
        self,
        *,
        delegator_ref: str,
        delegator_kind: DelegatorKind,
        delegatee: str,
        delegator_principal: str,
        amount_cap: Decimal | None = None,
        scope: DelegationScope | None = None,
        expires_at: datetime | None = None,
        currency: str | None = None,
        org_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Delegation:
        """Mint a new attenuated delegation, or raise :class:`DelegationError`.

        Fail-closed: every dimension of the requested grant must be a narrowing
        of the delegator's *current* authority.  If any check fails the mint is
        rejected and NO row is created.
        """
        scope = scope or DelegationScope()
        delegator = await self._load_delegator(delegator_kind, delegator_ref)
        if delegator is None:
            raise DelegationError(
                f"delegator {delegator_kind.value}:{delegator_ref} not found",
                error_code="DELEGATOR_NOT_FOUND",
            )

        att = self._attenuate(
            delegator=delegator,
            delegator_kind=delegator_kind,
            amount_cap=amount_cap,
            scope=scope,
            expires_at=expires_at,
            currency=currency,
        )
        if not att.valid:
            raise DelegationError(
                att.reason or "attenuation violated",
                error_code=att.error_code,
                violations=att.violations,
            )

        depth, root_mandate_id, eff_currency = self._chain_facts(
            delegator, delegator_kind, currency
        )

        dlg = Delegation(
            delegator_kind=delegator_kind,
            delegator_ref=delegator_ref,
            delegator_principal=delegator_principal,
            delegatee=delegatee,
            root_mandate_id=root_mandate_id,
            org_id=org_id,
            amount_cap=amount_cap,
            currency=eff_currency,
            scope=scope,
            expires_at=expires_at,
            depth=depth,
            metadata=metadata or {},
        )
        dlg.build_evidence(self._secret)
        await self._store.create(dlg)
        logger.info(
            "delegation minted: %s delegatee=%s depth=%d cap=%s parent=%s:%s",
            dlg.id, delegatee, depth, amount_cap, delegator_kind.value, delegator_ref,
        )
        return dlg

    def _attenuate(
        self,
        *,
        delegator: Any,
        delegator_kind: DelegatorKind,
        amount_cap: Decimal | None,
        scope: DelegationScope,
        expires_at: datetime | None,
        currency: str | None,
    ) -> AttenuationResult:
        """The cardinal rule: a delegate can NEVER exceed its delegator."""
        violations: list[str] = []

        # Delegator must itself be active — you cannot delegate dead authority.
        if not self._delegator_active(delegator, delegator_kind):
            return AttenuationResult(
                valid=False,
                reason="delegator authority is not active (revoked/expired/exhausted)",
                error_code="DELEGATOR_NOT_ACTIVE",
            )

        # Depth ceiling — refuse to mint a hop beyond the max chain depth.
        parent_depth = self._delegator_depth(delegator, delegator_kind)
        if parent_depth + 1 > MAX_DELEGATION_DEPTH:
            return AttenuationResult(
                valid=False,
                reason=f"delegation depth {parent_depth + 1} exceeds max {MAX_DELEGATION_DEPTH}",
                error_code="MAX_DEPTH_EXCEEDED",
            )

        # Amount: child cap <= parent REMAINING (not parent's original cap).
        parent_remaining = self._delegator_remaining(delegator, delegator_kind)
        if parent_remaining is not None:
            if amount_cap is None:
                violations.append(
                    "delegator is capped but delegation requests an uncapped amount"
                )
            elif amount_cap > parent_remaining:
                violations.append(
                    f"amount_cap {amount_cap} exceeds delegator remaining {parent_remaining}"
                )
        if amount_cap is not None and amount_cap <= 0:
            violations.append(f"amount_cap must be positive, got {amount_cap}")

        # Currency must match the delegator's.
        parent_currency = self._delegator_currency(delegator, delegator_kind)
        if currency is not None and currency != parent_currency:
            violations.append(
                f"currency mismatch: requested {currency}, delegator {parent_currency}"
            )

        # Expiry: child expiry <= parent expiry.  If the parent expires, the
        # child MUST expire no later (an uncapped child outlives its parent).
        parent_expiry = self._delegator_expiry(delegator, delegator_kind)
        if parent_expiry is not None:
            if expires_at is None:
                violations.append(
                    "delegator has an expiry but delegation requests none (would outlive parent)"
                )
            elif expires_at > parent_expiry:
                violations.append(
                    f"expires_at {expires_at.isoformat()} is after delegator expiry "
                    f"{parent_expiry.isoformat()}"
                )

        # Scope: every dimension must be a SUBSET of the delegator's.
        parent_scope = self._delegator_scope(delegator, delegator_kind)
        self._check_scope_subset(parent_scope, scope, violations)

        if violations:
            return AttenuationResult(
                valid=False,
                reason=f"delegation violates {len(violations)} attenuation constraint(s)",
                error_code="ATTENUATION_VIOLATION",
                violations=violations,
            )
        return AttenuationResult(valid=True)

    @staticmethod
    def _check_scope_subset(
        parent: DelegationScope, child: DelegationScope, violations: list[str]
    ) -> None:
        """Child scope must be a subset of parent scope on every dimension.

        Empty parent dimension == unrestricted at that hop, so any child set is a
        valid narrowing.  A non-empty parent dimension constrains: the child must
        either narrow within it (subset) or inherit it (empty child).  A child set
        with an element absent from a non-empty parent set is a WIDENING → reject.
        """
        for dim in ("counterparties", "categories", "mcc", "rails"):
            p = set(getattr(parent, dim))
            c = set(getattr(child, dim))
            if p and c:
                extra = c - p
                if extra:
                    violations.append(
                        f"scope.{dim}: delegation adds values not in delegator scope: {sorted(extra)}"
                    )

    # ── 2) resolve the chain ────────────────────────────────────────────

    async def resolve_chain(self, delegatee: str) -> list[Any]:
        """Resolve the ordered chain for an acting sub-agent.

        Returns ``[root_mandate, dlg_1, …, leaf_delegation]`` — the root
        SpendingMandate first, then every delegation hop down to the one the
        ``delegatee`` holds.  Returns ``[]`` if the sub-agent holds no active
        delegation (it is not acting under delegated authority).
        """
        leaf = await self._store.get_for_delegatee(delegatee)
        if leaf is None:
            return []
        return await self.resolve_chain_for(leaf)

    async def resolve_chain_for(self, leaf: Delegation) -> list[Any]:
        """Resolve the chain from a known leaf delegation up to the root mandate."""
        # Walk UP the delegator pointers, collecting delegations leaf-first.
        delegations: list[Delegation] = [leaf]
        cursor = leaf
        seen: set[str] = {leaf.id}
        while cursor.delegator_kind == DelegatorKind.DELEGATION:
            parent = await self._store.get(cursor.delegator_ref)
            if parent is None:
                # Broken pointer — return what we have; check_chain fails closed.
                logger.warning(
                    "delegation chain broken: %s points to missing parent %s",
                    cursor.id, cursor.delegator_ref,
                )
                break
            if parent.id in seen:  # defensive: cycle guard
                logger.error("delegation chain cycle detected at %s", parent.id)
                break
            seen.add(parent.id)
            delegations.append(parent)
            cursor = parent

        # The deepest delegation's delegator is the root mandate.
        root_mandate = await self._resolve_mandate(cursor.root_mandate_id or cursor.delegator_ref)
        chain: list[Any] = []
        if root_mandate is not None:
            chain.append(root_mandate)
        # delegations were collected leaf-first; reverse to root-first.
        chain.extend(reversed(delegations))
        return chain

    # ── 3) re-check the whole chain at execution time (FAIL-CLOSED) ──────

    async def check_chain(
        self,
        chain: list[Any],
        *,
        amount: Decimal,
        counterparty: str | None = None,
        category: str | None = None,
        mcc: str | None = None,
        rail: str | None = None,
    ) -> ChainCheckResult:
        """Authorize a delegated payment only if EVERY link holds.

        Each link is checked: active + non-revoked + non-expired + within its
        remaining cap + the payment within its scope.  The first broken link
        denies (fail-closed).  An empty chain is NOT authorized — there is no
        delegated authority to exercise.
        """
        if not chain:
            return ChainCheckResult(
                authorized=False,
                reason="empty delegation chain — no delegated authority",
                error_code="NO_DELEGATION_CHAIN",
            )

        leaf = chain[-1]
        leaf_id = getattr(leaf, "id", None) if isinstance(leaf, Delegation) else None

        # 3a) Root mandate (chain[0]) must authorize the payment.
        root = chain[0]
        if isinstance(root, SpendingMandate):
            if not root.is_active:
                return ChainCheckResult(
                    authorized=False,
                    reason=f"root mandate {root.id} is {root.status.value}",
                    error_code="ROOT_MANDATE_NOT_ACTIVE",
                    broken_link=root.id,
                    leaf_delegation_id=leaf_id,
                )
            check = root.check_payment(
                amount=amount, merchant=counterparty, rail=rail
            )
            if not check.approved:
                return ChainCheckResult(
                    authorized=False,
                    reason=f"root mandate denies: {check.reason}",
                    error_code=check.error_code or "ROOT_MANDATE_DENIED",
                    broken_link=root.id,
                    leaf_delegation_id=leaf_id,
                )

        # 3b) Every delegation hop must hold.
        for link in chain:
            if not isinstance(link, Delegation):
                continue
            broken = self._check_delegation_link(
                link,
                amount=amount,
                counterparty=counterparty,
                category=category,
                mcc=mcc,
                rail=rail,
            )
            if broken is not None:
                return ChainCheckResult(
                    authorized=False,
                    reason=broken[1],
                    error_code=broken[0],
                    broken_link=link.id,
                    leaf_delegation_id=leaf_id,
                )

        return ChainCheckResult(
            authorized=True,
            reason="delegation chain authorizes the payment",
            leaf_delegation_id=leaf_id,
        )

    @staticmethod
    def _check_delegation_link(
        link: Delegation,
        *,
        amount: Decimal,
        counterparty: str | None,
        category: str | None,
        mcc: str | None,
        rail: str | None,
    ) -> tuple[str, str] | None:
        """Return ``(error_code, reason)`` if the link breaks, else ``None``."""
        # Lifecycle / time / exhaustion.
        if link.status == DelegationStatus.REVOKED:
            return ("DELEGATION_REVOKED", f"delegation {link.id} is revoked")
        if link.status != DelegationStatus.ACTIVE or not link.is_active:
            return ("DELEGATION_NOT_ACTIVE", f"delegation {link.id} is {link.status.value} or out of time bounds")
        # Amount: payment must fit within this hop's remaining cap.
        remaining = link.remaining
        if remaining is not None and amount > remaining:
            return (
                "DELEGATION_CAP_EXCEEDED",
                f"amount {amount} exceeds delegation {link.id} remaining {remaining}",
            )
        # Scope: payment must be within every constrained dimension.
        s = link.scope
        if s.counterparties and counterparty is not None and counterparty not in s.counterparties:
            return (
                "DELEGATION_COUNTERPARTY_OUT_OF_SCOPE",
                f"counterparty {counterparty} not in delegation {link.id} scope",
            )
        if s.categories and category is not None and category not in s.categories:
            return (
                "DELEGATION_CATEGORY_OUT_OF_SCOPE",
                f"category {category} not in delegation {link.id} scope",
            )
        if s.mcc and mcc is not None and mcc not in s.mcc:
            return (
                "DELEGATION_MCC_OUT_OF_SCOPE",
                f"mcc {mcc} not in delegation {link.id} scope",
            )
        if s.rails and rail is not None and rail not in s.rails:
            return (
                "DELEGATION_RAIL_OUT_OF_SCOPE",
                f"rail {rail} not in delegation {link.id} scope",
            )
        return None

    # ── 4) spend recording walks the chain ──────────────────────────────

    async def record_chain_spend(self, chain: list[Any], amount: Decimal) -> None:
        """Decrement every delegation hop's remaining by ``amount``.

        A delegate's spend draws down its own remaining AND every ancestor
        delegation's remaining (the root SpendingMandate's spent_total is
        recorded by the orchestrator's existing mandate-spend path, so it is NOT
        double-counted here).
        """
        for link in chain:
            if isinstance(link, Delegation):
                await self._store.record_spend(link.id, amount)

    # ── delegator-shape adapters (SpendingMandate root vs Delegation hop) ─

    async def _load_delegator(
        self, kind: DelegatorKind, ref: str
    ) -> Any | None:
        if kind == DelegatorKind.MANDATE:
            return await self._resolve_mandate(ref)
        return await self._store.get(ref)

    @staticmethod
    def _delegator_active(delegator: Any, kind: DelegatorKind) -> bool:
        if kind == DelegatorKind.MANDATE:
            return getattr(delegator, "status", None) == MandateStatus.ACTIVE and delegator.is_active
        return delegator.status == DelegationStatus.ACTIVE and delegator.is_active

    @staticmethod
    def _delegator_remaining(delegator: Any, kind: DelegatorKind) -> Decimal | None:
        if kind == DelegatorKind.MANDATE:
            return delegator.remaining_total  # None if uncapped
        return delegator.remaining

    @staticmethod
    def _delegator_currency(delegator: Any, kind: DelegatorKind) -> str:
        return getattr(delegator, "currency", "USDC")

    @staticmethod
    def _delegator_expiry(delegator: Any, kind: DelegatorKind) -> datetime | None:
        return getattr(delegator, "expires_at", None)

    @staticmethod
    def _delegator_scope(delegator: Any, kind: DelegatorKind) -> DelegationScope:
        if kind == DelegatorKind.DELEGATION:
            return delegator.scope
        # Map a SpendingMandate's surface onto the DelegationScope dimensions:
        # merchant_scope.allowed -> counterparties; allowed_rails -> rails.
        merchant = getattr(delegator, "merchant_scope", {}) or {}
        return DelegationScope(
            counterparties=list(merchant.get("allowed") or []),
            categories=[],
            mcc=[],
            rails=list(getattr(delegator, "allowed_rails", []) or []),
        )

    @staticmethod
    def _delegator_depth(delegator: Any, kind: DelegatorKind) -> int:
        if kind == DelegatorKind.MANDATE:
            return 0  # the root mandate is depth 0
        return delegator.depth

    def _chain_facts(
        self, delegator: Any, kind: DelegatorKind, currency: str | None
    ) -> tuple[int, str, str]:
        """Return ``(depth, root_mandate_id, currency)`` for the new hop."""
        eff_currency = currency or self._delegator_currency(delegator, kind)
        if kind == DelegatorKind.MANDATE:
            return 1, delegator.id, eff_currency
        return delegator.depth + 1, delegator.root_mandate_id, eff_currency


__all__ = [
    "AttenuationResult",
    "ChainCheckResult",
    "DelegationEngine",
    "DelegationError",
]
