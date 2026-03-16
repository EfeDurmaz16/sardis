"""Spending Mandate — the core authorization primitive for agent payments.

A spending mandate is a machine-readable payment permission that defines:
- WHO can spend (agent identity + principal authority)
- WHAT they can buy (merchant scope, purpose, category)
- HOW MUCH they can spend (per-tx, daily, weekly, monthly, total)
- ON WHICH RAILS (card, USDC, bank transfer)
- FOR HOW LONG (time bounds, expiration)
- WITH WHAT APPROVAL (auto, threshold, always-human)
- WITH WHAT REVOCATION (instant, with reason, audited)

The mandate is the bridge between the current product (off-chain policy
enforcement) and the payment token future (on-chain mandate semantics).

Industry alignment:
- Stripe Shared Payment Tokens: seller-scoped, amount-bounded, expirable
- Visa Trusted Agent Protocol: agent identity + trusted authorization
- Mastercard Agent Pay: tokenized agent transactions with trust framework
- Google AP2: cross-rail payment protocol for AI agents
- OpenAI Commerce: delegated payment through compliant PSPs

Usage::

    mandate = SpendingMandate(
        principal_id="usr_abc",
        issuer_id="usr_abc",
        agent_id="agent_procurement_01",
        purpose_scope="Cloud infrastructure and API subscriptions",
        amount_per_tx=Decimal("500"),
        amount_daily=Decimal("2000"),
        amount_monthly=Decimal("10000"),
        merchant_scope={"allowed": ["aws.amazon.com", "openai.com", "anthropic.com"]},
        approval_threshold=Decimal("1000"),
        expires_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.spending_mandate")


class MandateStatus(str, Enum):
    """Lifecycle states for a spending mandate."""
    DRAFT = "draft"              # Created but not yet active
    ACTIVE = "active"            # Active and enforcing
    SUSPENDED = "suspended"      # Temporarily paused (resumable)
    REVOKED = "revoked"          # Permanently invalidated
    EXPIRED = "expired"          # Past expiration time
    CONSUMED = "consumed"        # Total budget exhausted


class ApprovalMode(str, Enum):
    """How approval is handled for payments under this mandate."""
    AUTO = "auto"                # All payments auto-approved within limits
    THRESHOLD = "threshold"      # Auto below threshold, human above
    ALWAYS_HUMAN = "always_human"  # Every payment requires human approval


# Valid state transitions: (from_status, to_status) → transition_name
VALID_TRANSITIONS: dict[tuple[str, str], str] = {
    (MandateStatus.DRAFT, MandateStatus.ACTIVE): "activate",
    (MandateStatus.ACTIVE, MandateStatus.SUSPENDED): "suspend",
    (MandateStatus.SUSPENDED, MandateStatus.ACTIVE): "resume",
    (MandateStatus.ACTIVE, MandateStatus.REVOKED): "revoke",
    (MandateStatus.SUSPENDED, MandateStatus.REVOKED): "revoke",
    (MandateStatus.ACTIVE, MandateStatus.EXPIRED): "expire",
    (MandateStatus.ACTIVE, MandateStatus.CONSUMED): "consume",
}


@dataclass
class MandateStateTransition:
    """Audit record for a mandate lifecycle change."""
    mandate_id: str
    from_status: str
    to_status: str
    changed_by: str
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: str = field(default_factory=lambda: f"mst_{uuid4().hex[:16]}")


@dataclass
class SpendingMandate:
    """A machine-readable spending mandate for AI agent payments.

    This is the core authorization primitive — it defines what an agent
    is allowed to spend, on what, and under what conditions.
    """
    # Identity
    principal_id: str                          # Who authorized this
    issuer_id: str                             # Who created it
    org_id: str = ""
    agent_id: str | None = None
    wallet_id: str | None = None
    id: str = field(default_factory=lambda: f"mandate_{uuid4().hex[:12]}")

    # Scope
    merchant_scope: dict[str, Any] = field(default_factory=dict)
    purpose_scope: str | None = None

    # Limits
    amount_per_tx: Decimal | None = None
    amount_daily: Decimal | None = None
    amount_weekly: Decimal | None = None
    amount_monthly: Decimal | None = None
    amount_total: Decimal | None = None
    currency: str = "USDC"

    # Spent tracking
    spent_total: Decimal = field(default_factory=lambda: Decimal("0"))

    # Rails
    allowed_rails: list[str] = field(default_factory=lambda: ["card", "usdc", "bank"])
    allowed_chains: list[str] | None = None
    allowed_tokens: list[str] | None = None

    # Time
    valid_from: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None

    # Approval
    approval_threshold: Decimal | None = None
    approval_mode: ApprovalMode = ApprovalMode.AUTO

    # Lifecycle
    status: MandateStatus = MandateStatus.ACTIVE
    revoked_at: datetime | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None

    # Audit
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def policy_hash(self) -> str:
        """SHA-256 hash of the mandate's rules for integrity verification."""
        rules = {
            "merchant_scope": self.merchant_scope,
            "purpose_scope": self.purpose_scope,
            "amount_per_tx": str(self.amount_per_tx) if self.amount_per_tx else None,
            "amount_daily": str(self.amount_daily) if self.amount_daily else None,
            "amount_weekly": str(self.amount_weekly) if self.amount_weekly else None,
            "amount_monthly": str(self.amount_monthly) if self.amount_monthly else None,
            "amount_total": str(self.amount_total) if self.amount_total else None,
            "allowed_rails": sorted(self.allowed_rails),
            "allowed_chains": sorted(self.allowed_chains) if self.allowed_chains else None,
            "allowed_tokens": sorted(self.allowed_tokens) if self.allowed_tokens else None,
            "approval_threshold": str(self.approval_threshold) if self.approval_threshold else None,
            "approval_mode": self.approval_mode.value,
        }
        return hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()

    @property
    def is_active(self) -> bool:
        """Check if mandate is currently active and within time bounds."""
        if self.status != MandateStatus.ACTIVE:
            return False
        now = datetime.now(UTC)
        if self.valid_from and now < self.valid_from:
            return False
        if self.expires_at and now > self.expires_at:
            return False
        return True

    @property
    def remaining_total(self) -> Decimal | None:
        """Remaining total budget, or None if no total limit."""
        if self.amount_total is None:
            return None
        return self.amount_total - self.spent_total

    def check_payment(
        self,
        amount: Decimal,
        merchant: str | None = None,
        rail: str | None = None,
        chain: str | None = None,
        token: str | None = None,
        purpose: str | None = None,
    ) -> MandateCheckResult:
        """Check if a payment is authorized by this mandate.

        Returns a MandateCheckResult with approved/rejected status,
        reason, and whether human approval is required.
        """
        # Check lifecycle
        if not self.is_active:
            return MandateCheckResult(
                approved=False,
                reason=f"Mandate is {self.status.value}",
                error_code="MANDATE_NOT_ACTIVE",
            )

        # Check per-transaction limit
        if self.amount_per_tx is not None and amount > self.amount_per_tx:
            return MandateCheckResult(
                approved=False,
                reason=f"Amount {amount} exceeds per-transaction limit {self.amount_per_tx}",
                error_code="MANDATE_AMOUNT_EXCEEDED",
            )

        # Check total remaining budget
        if self.amount_total is not None and amount > self.remaining_total:
            return MandateCheckResult(
                approved=False,
                reason=f"Amount {amount} exceeds remaining mandate budget {self.remaining_total}",
                error_code="MANDATE_BUDGET_EXHAUSTED",
            )

        # Check merchant scope
        if merchant and self.merchant_scope:
            allowed = self.merchant_scope.get("allowed")
            blocked = self.merchant_scope.get("blocked", [])

            if merchant in blocked:
                return MandateCheckResult(
                    approved=False,
                    reason=f"Merchant {merchant} is blocked by mandate",
                    error_code="MANDATE_MERCHANT_BLOCKED",
                )

            if allowed and merchant not in allowed:
                # Check wildcard patterns
                matched = any(
                    merchant.endswith(a.lstrip("*")) if a.startswith("*") else merchant == a
                    for a in allowed
                )
                if not matched:
                    return MandateCheckResult(
                        approved=False,
                        reason=f"Merchant {merchant} not in mandate allowed list",
                        error_code="MANDATE_MERCHANT_NOT_ALLOWED",
                    )

        # Check rail permission
        if rail and rail not in self.allowed_rails:
            return MandateCheckResult(
                approved=False,
                reason=f"Rail {rail} not permitted by mandate (allowed: {self.allowed_rails})",
                error_code="MANDATE_RAIL_NOT_ALLOWED",
            )

        # Check chain permission
        if chain and self.allowed_chains and chain not in self.allowed_chains:
            return MandateCheckResult(
                approved=False,
                reason=f"Chain {chain} not permitted by mandate",
                error_code="MANDATE_CHAIN_NOT_ALLOWED",
            )

        # Check token permission
        if token and self.allowed_tokens and token not in self.allowed_tokens:
            return MandateCheckResult(
                approved=False,
                reason=f"Token {token} not permitted by mandate",
                error_code="MANDATE_TOKEN_NOT_ALLOWED",
            )

        # Check approval threshold
        requires_approval = False
        if self.approval_mode == ApprovalMode.ALWAYS_HUMAN:
            requires_approval = True
        elif self.approval_mode == ApprovalMode.THRESHOLD and self.approval_threshold:
            if amount > self.approval_threshold:
                requires_approval = True

        return MandateCheckResult(
            approved=True,
            reason="Mandate check passed",
            requires_approval=requires_approval,
            mandate_id=self.id,
            mandate_version=self.version,
        )

    def transition(self, to_status: MandateStatus, changed_by: str, reason: str | None = None) -> MandateStateTransition:
        """Transition the mandate to a new state.

        Validates the transition is allowed and returns an audit record.
        Raises ValueError if the transition is invalid.
        """
        key = (self.status, to_status)
        if key not in VALID_TRANSITIONS:
            raise ValueError(
                f"Invalid mandate transition: {self.status.value} → {to_status.value}. "
                f"Valid transitions from {self.status.value}: "
                f"{[t[1].value for t in VALID_TRANSITIONS if t[0] == self.status]}"
            )

        transition = MandateStateTransition(
            mandate_id=self.id,
            from_status=self.status.value,
            to_status=to_status.value,
            changed_by=changed_by,
            reason=reason,
        )

        old_status = self.status
        self.status = to_status
        self.updated_at = datetime.now(UTC)

        if to_status == MandateStatus.REVOKED:
            self.revoked_at = datetime.now(UTC)
            self.revoked_by = changed_by
            self.revocation_reason = reason

        logger.info(
            "Mandate %s transitioned: %s → %s (by %s, reason: %s)",
            self.id, old_status.value, to_status.value, changed_by, reason,
        )

        return transition


@dataclass
class MandateCheckResult:
    """Result of checking a payment against a spending mandate."""
    approved: bool
    reason: str
    error_code: str | None = None
    requires_approval: bool = False
    mandate_id: str | None = None
    mandate_version: int | None = None

    def __repr__(self) -> str:
        status = "approved" if self.approved else "rejected"
        suffix = " (needs approval)" if self.requires_approval else ""
        return f"MandateCheckResult({status}{suffix})"
