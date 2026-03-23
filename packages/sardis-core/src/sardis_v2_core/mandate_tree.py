"""Mandate Trees — hierarchical delegation of spending authority.

Parent mandates delegate to children with inherited, narrowing bounds.
Children can never exceed parent limits — they can only narrow them.

The delegation tree enables multi-level agent hierarchies:
  CEO → Department Head → Team Lead → Individual Agent

Each level narrows the spending authority: smaller amounts, fewer merchants,
shorter time windows, stricter approval requirements.

Usage::

    validator = MandateTreeValidator()
    result = validator.validate_delegation(
        parent=parent_mandate,
        child=SpendingMandate(
            parent_mandate_id=parent.id,
            amount_per_tx=Decimal("50"),   # Must be ≤ parent's amount_per_tx
            ...
        ),
    )
    if not result.valid:
        raise ValueError(result.reason)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from .spending_mandate import MandateStatus, SpendingMandate

logger = logging.getLogger("sardis.mandate_tree")


MAX_DELEGATION_DEPTH = 10


@dataclass
class DelegationResult:
    """Result of a mandate delegation validation."""

    valid: bool
    reason: str | None = None
    error_code: str | None = None
    violations: list[str] = field(default_factory=list)


@dataclass
class MandateTreeNode:
    """A node in the mandate delegation tree."""

    mandate: SpendingMandate
    children: list[MandateTreeNode] = field(default_factory=list)
    depth: int = 0

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def total_delegated(self) -> Decimal:
        """Sum of amount_total across all direct children."""
        return sum(
            (c.mandate.amount_total or Decimal("0")) for c in self.children
        )


class MandateTreeValidator:
    """Validates mandate delegation constraints.

    Ensures children can never exceed parent bounds — they can only narrow:
    - Amount limits must be ≤ parent limits
    - Merchant scope must be a subset of parent scope
    - Time window must be within parent time window
    - Approval mode can be stricter, never laxer
    """

    def validate_delegation(
        self,
        parent: SpendingMandate,
        child: SpendingMandate,
    ) -> DelegationResult:
        """Validate that a child mandate is a valid delegation of the parent."""
        violations: list[str] = []

        # Parent must be active
        if parent.status != MandateStatus.ACTIVE:
            return DelegationResult(
                valid=False,
                reason=f"Parent mandate is {parent.status.value}, cannot delegate",
                error_code="PARENT_NOT_ACTIVE",
            )

        # Check delegation depth
        depth = getattr(parent, "delegation_depth", 0) + 1
        if depth > MAX_DELEGATION_DEPTH:
            return DelegationResult(
                valid=False,
                reason=f"Delegation depth {depth} exceeds maximum {MAX_DELEGATION_DEPTH}",
                error_code="MAX_DEPTH_EXCEEDED",
            )

        # Amount limits: child ≤ parent
        self._check_amount_bound(
            "amount_per_tx", parent.amount_per_tx, child.amount_per_tx, violations
        )
        self._check_amount_bound(
            "amount_daily", parent.amount_daily, child.amount_daily, violations
        )
        self._check_amount_bound(
            "amount_weekly", parent.amount_weekly, child.amount_weekly, violations
        )
        self._check_amount_bound(
            "amount_monthly", parent.amount_monthly, child.amount_monthly, violations
        )
        self._check_amount_bound(
            "amount_total", parent.amount_total, child.amount_total, violations
        )

        # Currency must match
        if child.currency != parent.currency:
            violations.append(
                f"Currency mismatch: child={child.currency}, parent={parent.currency}"
            )

        # Merchant scope: child must be subset of parent
        self._check_merchant_scope(parent.merchant_scope, child.merchant_scope, violations)

        # Time bounds: child must be within parent
        self._check_time_bounds(parent, child, violations)

        # Rail restrictions: child must be subset of parent
        if child.allowed_rails:
            parent_rails = set(parent.allowed_rails or [])
            child_rails = set(child.allowed_rails)
            extra = child_rails - parent_rails
            if parent_rails and extra:
                violations.append(
                    f"Child allows rails not in parent: {extra}"
                )

        # Chain restrictions: child must be subset of parent
        if child.allowed_chains and parent.allowed_chains:
            parent_chains = set(parent.allowed_chains)
            child_chains = set(child.allowed_chains)
            extra = child_chains - parent_chains
            if extra:
                violations.append(
                    f"Child allows chains not in parent: {extra}"
                )

        # Token restrictions: child must be subset of parent
        if child.allowed_tokens and parent.allowed_tokens:
            parent_tokens = set(parent.allowed_tokens)
            child_tokens = set(child.allowed_tokens)
            extra = child_tokens - parent_tokens
            if extra:
                violations.append(
                    f"Child allows tokens not in parent: {extra}"
                )

        # Approval mode: child can be stricter, never laxer
        self._check_approval_mode(parent, child, violations)

        if violations:
            return DelegationResult(
                valid=False,
                reason=f"Delegation violates {len(violations)} constraint(s)",
                error_code="DELEGATION_CONSTRAINT_VIOLATION",
                violations=violations,
            )

        return DelegationResult(valid=True)

    def _check_amount_bound(
        self,
        field_name: str,
        parent_val: Decimal | None,
        child_val: Decimal | None,
        violations: list[str],
    ) -> None:
        """Child amount must be ≤ parent amount. If parent is None (unlimited), any child value is ok."""
        if parent_val is not None and child_val is not None:
            if child_val > parent_val:
                violations.append(
                    f"{field_name}: child ({child_val}) exceeds parent ({parent_val})"
                )
        elif parent_val is not None and child_val is None:
            # Parent has a limit but child doesn't — child is more permissive
            violations.append(
                f"{field_name}: parent has limit ({parent_val}) but child has no limit"
            )

    def _check_merchant_scope(
        self,
        parent_scope: dict[str, Any],
        child_scope: dict[str, Any],
        violations: list[str],
    ) -> None:
        """Child merchant scope must be a subset of parent scope."""
        parent_allowed = set(parent_scope.get("allowed", []))
        child_allowed = set(child_scope.get("allowed", []))

        # If parent has an allowlist, child's allowlist must be a subset
        if parent_allowed and child_allowed:
            extra = child_allowed - parent_allowed
            if extra:
                violations.append(
                    f"Child allows merchants not in parent allowlist: {extra}"
                )
        elif parent_allowed and not child_allowed:
            # Parent restricts merchants but child doesn't — child is more permissive
            violations.append(
                "Parent has merchant allowlist but child has none (more permissive)"
            )

        # Child should inherit parent's blocklist
        parent_blocked = set(parent_scope.get("blocked", []))
        child_blocked = set(child_scope.get("blocked", []))
        missing_blocks = parent_blocked - child_blocked
        if missing_blocks:
            violations.append(
                f"Child missing parent's blocked merchants: {missing_blocks}"
            )

    def _check_time_bounds(
        self,
        parent: SpendingMandate,
        child: SpendingMandate,
        violations: list[str],
    ) -> None:
        """Child time window must be within parent time window."""
        if parent.valid_from and child.valid_from:
            if child.valid_from < parent.valid_from:
                violations.append(
                    f"Child valid_from ({child.valid_from}) is before parent ({parent.valid_from})"
                )

        if parent.expires_at:
            if child.expires_at is None:
                violations.append(
                    "Parent has expiry but child has none (more permissive)"
                )
            elif child.expires_at > parent.expires_at:
                violations.append(
                    f"Child expires_at ({child.expires_at}) is after parent ({parent.expires_at})"
                )

    def _check_approval_mode(
        self,
        parent: SpendingMandate,
        child: SpendingMandate,
        violations: list[str],
    ) -> None:
        """Child approval mode can be stricter, never laxer."""
        # Strictness order: auto < threshold < always_human
        strictness = {"auto": 0, "threshold": 1, "always_human": 2}
        parent_level = strictness.get(parent.approval_mode.value, 0)
        child_level = strictness.get(child.approval_mode.value, 0)

        if child_level < parent_level:
            violations.append(
                f"Child approval mode ({child.approval_mode.value}) "
                f"is less strict than parent ({parent.approval_mode.value})"
            )

        # If both use threshold, child threshold must be ≤ parent
        if (
            parent.approval_threshold is not None
            and child.approval_threshold is not None
            and child.approval_threshold > parent.approval_threshold
        ):
            violations.append(
                f"Child approval threshold ({child.approval_threshold}) "
                f"exceeds parent ({parent.approval_threshold})"
            )


def build_mandate_tree(
    mandates: list[SpendingMandate],
    root_id: str | None = None,
) -> MandateTreeNode | None:
    """Build a tree structure from a flat list of mandates.

    If root_id is provided, builds the subtree rooted at that mandate.
    Otherwise, finds the root (mandate with no parent).
    """
    by_id: dict[str, SpendingMandate] = {m.id: m for m in mandates}
    children_of: dict[str, list[str]] = {}

    for m in mandates:
        parent_id = getattr(m, "parent_mandate_id", None)
        if parent_id:
            children_of.setdefault(parent_id, []).append(m.id)

    # Find root
    if root_id:
        root_mandate = by_id.get(root_id)
    else:
        roots = [m for m in mandates if not getattr(m, "parent_mandate_id", None)]
        root_mandate = roots[0] if roots else None

    if root_mandate is None:
        return None

    def _build(mandate_id: str, depth: int) -> MandateTreeNode:
        mandate = by_id[mandate_id]
        child_ids = children_of.get(mandate_id, [])
        child_nodes = [_build(cid, depth + 1) for cid in child_ids]
        return MandateTreeNode(mandate=mandate, children=child_nodes, depth=depth)

    return _build(root_mandate.id, 0)
