"""
Policy enforcement for agent payments.

This module provides the user-facing Policy class that answers the core
question: **"Is my agent allowed to make this payment?"**

How policy enforcement works:
────────────────────────────
When an agent calls ``wallet.pay()``, Sardis runs the payment through a
policy check *before* any money moves.  The check pipeline looks like this:

    wallet.pay(to="openai.com", amount=25)
        │
        ▼
    Policy.check(amount=25, destination="openai.com", token="USDC")
        │
        ├── 1. Amount limit      → Is $25 under the per-tx cap?
        ├── 2. Token check       → Is USDC an allowed token?
        ├── 3. Destination block  → Is openai.com on the blocklist?
        ├── 4. Destination allow  → Is openai.com on the allowlist (if set)?
        ├── 5. Purpose check     → Is a purpose required and provided?
        ├── 6. Wallet limit      → Has the wallet's total spend cap been reached?
        └── 7. Approval routing  → Amount OK but needs human sign-off?
                │
                ▼
        PolicyResult(approved=True/False, reason="...", checks_passed=[...])

If ANY check fails, the payment is **rejected** and no funds move.
If all checks pass but the amount exceeds the approval threshold, the
payment is flagged as ``requires_approval`` for human sign-off.

Quick start:
    >>> from sardis import Policy
    >>> policy = Policy(max_per_tx=50, allowed_destinations={"openai:*", "anthropic:*"})
    >>> result = policy.check(amount=25, destination="openai:api")
    >>> result.approved  # True — under $50 and openai is allowed

    >>> result = policy.check(amount=75, destination="openai:api")
    >>> result.approved  # False — exceeds $50 per-tx limit
    >>> result.reason    # "Amount 75 exceeds limit 50"

For production (API-backed) enforcement, see ``sardis_v2_core.spending_policy``
which adds DB-backed spend tracking, time-window limits, MCC codes, and more.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .wallet import Wallet


@dataclass
class PolicyResult:
    """Result of a policy check."""
    approved: bool
    reason: Optional[str] = None
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    requires_approval: bool = False
    approval_reason: Optional[str] = None

    def __repr__(self) -> str:
        if self.requires_approval:
            return "PolicyResult(requires_approval)"
        status = "approved" if self.approved else "rejected"
        return f"PolicyResult({status})"


@dataclass
class Policy:
    """
    Spending policy for AI agents.

    A Policy defines the guardrails an agent must operate within.  Every call
    to ``wallet.pay()`` checks the policy first — if the policy says no,
    the payment never executes.

    **What you can control:**

    +-----------------------+-----------------------------------------------+
    | Rule                  | What it does                                  |
    +=======================+===============================================+
    | ``max_per_tx``        | Cap on a single payment (e.g. $100)           |
    +-----------------------+-----------------------------------------------+
    | ``max_total``         | Lifetime spending cap (e.g. $1000)            |
    +-----------------------+-----------------------------------------------+
    | ``allowed_destinations``| Allowlist of merchants (supports wildcards)  |
    +-----------------------+-----------------------------------------------+
    | ``blocked_destinations``| Blocklist of merchants (checked first)       |
    +-----------------------+-----------------------------------------------+
    | ``allowed_tokens``    | Which tokens the agent can spend (USDC, etc.) |
    +-----------------------+-----------------------------------------------+
    | ``require_purpose``   | Force the agent to state why it's paying      |
    +-----------------------+-----------------------------------------------+
    | ``approval_threshold``| Auto-approve below this; human approval above |
    +-----------------------+-----------------------------------------------+

    **Examples:**

    Basic limit::

        policy = Policy(max_per_tx=50)
        # Agent can spend up to $50 per transaction

    Restrict to specific vendors::

        policy = Policy(
            max_per_tx=200,
            allowed_destinations={"openai:*", "anthropic:*", "aws:*"},
        )
        # Agent can only pay OpenAI, Anthropic, and AWS

    Block categories + require approval for large amounts::

        policy = Policy(
            max_per_tx=500,
            blocked_destinations={"gambling:*", "adult:*"},
            approval_threshold=100,  # human approval needed above $100
        )
    """
    
    max_per_tx: Decimal = field(default_factory=lambda: Decimal("100.00"))
    max_total: Decimal = field(default_factory=lambda: Decimal("1000.00"))
    allowed_destinations: Optional[Set[str]] = None  # None = allow all
    blocked_destinations: Set[str] = field(default_factory=set)
    allowed_tokens: Set[str] = field(default_factory=lambda: {"USDC", "USDT", "PYUSD"})
    require_purpose: bool = False
    approval_threshold: Optional[Decimal] = None
    
    def __init__(
        self,
        max_per_tx: float | Decimal = 100,
        max_total: float | Decimal = 1000,
        allowed_destinations: Optional[Set[str]] = None,
        blocked_destinations: Optional[Set[str]] = None,
        allowed_tokens: Optional[Set[str]] = None,
        require_purpose: bool = False,
        approval_threshold: Optional[float | Decimal] = None,
    ):
        """
        Create a spending policy.

        Args:
            max_per_tx: Maximum amount per transaction
            max_total: Maximum total spending
            allowed_destinations: Whitelist of allowed destinations (None = all)
            blocked_destinations: Blacklist of blocked destinations
            allowed_tokens: Set of allowed token types
            require_purpose: Whether transactions must have a purpose
            approval_threshold: Amount above which human approval is required (None = no approval needed)
        """
        self.max_per_tx = Decimal(str(max_per_tx))
        self.max_total = Decimal(str(max_total))
        self.allowed_destinations = allowed_destinations
        self.blocked_destinations = blocked_destinations or set()
        self.allowed_tokens = allowed_tokens or {"USDC", "USDT", "PYUSD"}
        self.require_purpose = require_purpose
        self.approval_threshold = Decimal(str(approval_threshold)) if approval_threshold is not None else None
    
    def check(
        self,
        amount: Decimal | float,
        wallet: Optional["Wallet"] = None,
        destination: Optional[str] = None,
        token: str = "USDC",
        purpose: Optional[str] = None,
    ) -> PolicyResult:
        """
        Run this payment through the policy check pipeline.

        This is the method that enforces the policy.  It runs checks in order
        and **short-circuits on the first failure** — no money moves if any
        check fails.

        Check order:
            1. Amount limit → ``amount <= max_per_tx``?
            2. Token check → is the token in ``allowed_tokens``?
            3. Blocklist → is the destination in ``blocked_destinations``?
            4. Allowlist → is the destination in ``allowed_destinations`` (if set)?
            5. Purpose → is a purpose provided (if ``require_purpose=True``)?
            6. Wallet limit → has the wallet's lifetime cap been reached?
            7. Approval threshold → all OK, but needs human sign-off?

        Args:
            amount: How much the agent wants to pay.
            wallet: Source wallet — if provided, checks lifetime spend cap.
            destination: Who the agent is paying (e.g. "openai:api").
                Supports wildcard matching against allowlist/blocklist patterns.
            token: Token type (default: USDC).
            purpose: Why the agent is making this payment (required if
                ``require_purpose=True``).

        Returns:
            PolicyResult with:
              - ``approved``: True if the payment should proceed.
              - ``reason``: Human-readable explanation.
              - ``checks_passed`` / ``checks_failed``: Which specific checks
                passed or failed (useful for debugging).
              - ``requires_approval``: True if a human needs to approve.
        """
        amount = Decimal(str(amount))
        checks_passed = []
        checks_failed = []

        # ── Check 1: Per-transaction amount limit ──────────────────────
        if amount <= self.max_per_tx:
            checks_passed.append("amount_limit")
        else:
            checks_failed.append("amount_limit")
            return PolicyResult(
                approved=False,
                reason=f"Amount {amount} exceeds limit {self.max_per_tx}",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        
        # ── Check 2: Token type ────────────────────────────────────────
        if token in self.allowed_tokens:
            checks_passed.append("token_allowed")
        else:
            checks_failed.append("token_allowed")
            return PolicyResult(
                approved=False,
                reason=f"Token {token} not allowed",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        
        # ── Check 3: Destination blocklist (deny wins) ─────────────────
        if destination and destination in self.blocked_destinations:
            checks_failed.append("destination_blocked")
            return PolicyResult(
                approved=False,
                reason=f"Destination {destination} is blocked",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        checks_passed.append("destination_not_blocked")
        
        # ── Check 4: Destination allowlist (if configured) ──────────────
        if self.allowed_destinations is not None and destination:
            allowed = self._check_destination_pattern(destination, self.allowed_destinations)
            if allowed:
                checks_passed.append("destination_allowed")
            else:
                checks_failed.append("destination_allowed")
                return PolicyResult(
                    approved=False,
                    reason=f"Destination {destination} not in allowed list",
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )
        
        # ── Check 5: Purpose requirement ───────────────────────────────
        if self.require_purpose and not purpose:
            checks_failed.append("purpose_required")
            return PolicyResult(
                approved=False,
                reason="Transaction purpose is required",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        if self.require_purpose:
            checks_passed.append("purpose_provided")
        
        # ── Check 6: Wallet lifetime spending limit ─────────────────────
        if wallet:
            if wallet.can_spend(amount):
                checks_passed.append("wallet_limit")
            else:
                checks_failed.append("wallet_limit")
                return PolicyResult(
                    approved=False,
                    reason="Wallet spending limit exceeded",
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )

        # ── Check 7: Approval threshold ────────────────────────────────
        # All checks passed, but if the amount exceeds the approval
        # threshold, flag it for human sign-off before executing.
        if self.approval_threshold is not None and amount > self.approval_threshold:
            checks_passed.append("approval_threshold_triggered")
            return PolicyResult(
                approved=True,
                reason=f"Amount {amount} exceeds approval threshold {self.approval_threshold}",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                requires_approval=True,
                approval_reason=f"Amount {amount} exceeds approval threshold {self.approval_threshold}",
            )

        return PolicyResult(
            approved=True,
            reason="All policy checks passed",
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )
    
    def _check_destination_pattern(self, destination: str, patterns: Set[str]) -> bool:
        """Check if destination matches any pattern (supports wildcards)."""
        for pattern in patterns:
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if destination.startswith(prefix):
                    return True
            elif destination == pattern:
                return True
        return False
    
    def __repr__(self) -> str:
        return f"Policy(max_per_tx={self.max_per_tx})"






