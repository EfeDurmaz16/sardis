"""
Spending Mandate for the simple Sardis SDK.

A spending mandate defines the scoped authority an AI agent has to spend
money. It sits above the Policy (which defines rules) and below the
Wallet (which holds funds).

Usage::

    from sardis import SardisClient

    client = SardisClient()
    mandate = client.mandates.create(
        agent_id="agent_001",
        purpose="Cloud infrastructure and API calls",
        amount_per_tx=500,
        amount_daily=2000,
        merchant_scope={"allowed": ["aws.amazon.com", "openai.com"]},
        approval_threshold=1000,
    )

    # Wallet.pay() automatically checks the mandate
    wallet = client.wallets.create(name="my-agent", mandate=mandate)
    result = wallet.pay(to="openai.com", amount=25)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4


class MandateStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"
    CONSUMED = "consumed"


@dataclass
class SpendingMandate:
    """A spending mandate defining an agent's payment authority.

    Attributes:
        purpose: Natural language description of what this mandate allows
        amount_per_tx: Max per single transaction
        amount_daily: Max daily aggregate
        amount_monthly: Max monthly aggregate
        amount_total: Lifetime budget
        merchant_scope: Dict with 'allowed' and/or 'blocked' merchant lists
        allowed_rails: List of permitted rails ('card', 'usdc', 'bank')
        approval_threshold: Amount above which human approval is required
        expires_at: When the mandate expires
    """
    purpose: str = ""
    amount_per_tx: Decimal = field(default_factory=lambda: Decimal("1000"))
    amount_daily: Decimal | None = None
    amount_monthly: Decimal | None = None
    amount_total: Decimal | None = None
    merchant_scope: dict[str, Any] = field(default_factory=dict)
    allowed_rails: list[str] = field(default_factory=lambda: ["card", "usdc", "bank"])
    approval_threshold: Decimal | None = None
    expires_at: datetime | None = None

    # Internal state
    id: str = field(default_factory=lambda: f"mandate_{uuid4().hex[:12]}")
    agent_id: str | None = None
    status: MandateStatus = MandateStatus.ACTIVE
    spent_total: Decimal = field(default_factory=lambda: Decimal("0"))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def check(self, amount: Decimal | float, merchant: str | None = None, rail: str | None = None) -> MandateCheckResult:
        """Check if a payment is authorized by this mandate."""
        amount = Decimal(str(amount))

        if self.status != MandateStatus.ACTIVE:
            return MandateCheckResult(False, f"Mandate is {self.status.value}", "MANDATE_NOT_ACTIVE")

        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return MandateCheckResult(False, "Mandate has expired", "MANDATE_EXPIRED")

        if amount > self.amount_per_tx:
            return MandateCheckResult(False, f"Amount {amount} exceeds per-tx limit {self.amount_per_tx}", "MANDATE_AMOUNT_EXCEEDED")

        if self.amount_total is not None:
            remaining = self.amount_total - self.spent_total
            if amount > remaining:
                return MandateCheckResult(False, f"Amount {amount} exceeds remaining budget {remaining}", "MANDATE_BUDGET_EXHAUSTED")

        if merchant and self.merchant_scope:
            blocked = self.merchant_scope.get("blocked", [])
            if merchant in blocked:
                return MandateCheckResult(False, f"Merchant {merchant} is blocked", "MANDATE_MERCHANT_BLOCKED")

            allowed = self.merchant_scope.get("allowed")
            if allowed and merchant not in allowed:
                if not any(merchant.endswith(a.lstrip("*")) for a in allowed if a.startswith("*")):
                    return MandateCheckResult(False, f"Merchant {merchant} not in allowed list", "MANDATE_MERCHANT_NOT_ALLOWED")

        if rail and rail not in self.allowed_rails:
            return MandateCheckResult(False, f"Rail {rail} not permitted", "MANDATE_RAIL_NOT_ALLOWED")

        requires_approval = False
        if self.approval_threshold and amount > self.approval_threshold:
            requires_approval = True

        return MandateCheckResult(True, "Mandate check passed", requires_approval=requires_approval)

    def record_spend(self, amount: Decimal | float) -> None:
        """Record a successful spend against this mandate's budget."""
        self.spent_total += Decimal(str(amount))
        if self.amount_total and self.spent_total >= self.amount_total:
            self.status = MandateStatus.CONSUMED

    def revoke(self, reason: str = "") -> None:
        """Permanently revoke this mandate."""
        self.status = MandateStatus.REVOKED

    def suspend(self) -> None:
        """Temporarily suspend this mandate."""
        self.status = MandateStatus.SUSPENDED

    def resume(self) -> None:
        """Resume a suspended mandate."""
        if self.status == MandateStatus.SUSPENDED:
            self.status = MandateStatus.ACTIVE


@dataclass
class MandateCheckResult:
    """Result of checking a payment against a mandate."""
    approved: bool
    reason: str
    error_code: str | None = None
    requires_approval: bool = False
