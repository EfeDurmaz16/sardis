"""
Spending Policy Engine — the core of Sardis policy enforcement.

Every payment an AI agent makes must pass through a SpendingPolicy before
execution.  This module defines the rules, limits, and checks that determine
whether a transaction is allowed, denied, or requires human approval.

How policy enforcement works (high-level):
─────────────────────────────────────────
1. A policy is attached to each agent (via the policy store or created with
   defaults based on trust level).
2. When a payment request arrives, the orchestrator calls
   ``policy.evaluate(...)`` (async, production) or ``policy.validate_payment(...)``
   (sync, dev/test).
3. The policy runs checks **in order** — the first failure short-circuits
   with a denial reason:

   ┌─────────────────────────────────────────────────────┐
   │  evaluate() check pipeline (in order)               │
   ├─────────────────────────────────────────────────────┤
   │  1. Amount validation   — amount > 0, fee >= 0      │
   │  2. Scope check         — is the spending category   │
   │                           (retail, compute, etc.)    │
   │                           allowed?                   │
   │  3. MCC check           — is the merchant category   │
   │                           code blocked?              │
   │  4. Per-tx limit        — does amount + fee exceed   │
   │                           the single-transaction cap?│
   │  5. Total limit         — does cumulative spending   │
   │                           exceed the lifetime cap?   │
   │  6. Time-window limits  — daily / weekly / monthly   │
   │                           caps                       │
   │  7. On-chain balance    — does the wallet have       │
   │                           enough funds?              │
   │  8. Merchant rules      — allowlist / blocklist /    │
   │                           per-merchant caps          │
   │  9. Goal drift          — has the agent drifted too  │
   │                           far from its stated goal?  │
   │ 10. Approval threshold  — amount OK but needs human  │
   │                           sign-off?                  │
   └─────────────────────────────────────────────────────┘

4. If all checks pass → (True, "OK").
   If any check fails  → (False, "<reason_code>") — e.g. "per_transaction_limit".
   If approval needed  → (True, "requires_approval").

5. After a successful on-chain payment, ``record_spend()`` updates the
   cumulative totals so future checks reflect the new spending state.

Key concepts:
  - **TrustLevel**: LOW / MEDIUM / HIGH / UNLIMITED — preset limit tiers.
  - **TimeWindowLimit**: Rolling daily/weekly/monthly spend caps.
  - **MerchantRule**: Per-merchant or per-category allow/deny with optional caps.
  - **SpendingScope**: Restricts spending to certain categories (compute, retail, etc.).
  - **Fail-closed**: Any error during evaluation defaults to denial.

See also:
  - ``orchestrator.py`` — calls evaluate() as Phase 1 of payment execution.
  - ``policy_store.py`` — persists policies per agent (in-memory or Postgres).
  - ``spending_policy_store.py`` — atomic DB-backed spend tracking.
  - ``nl_policy_parser.py`` — converts natural language → SpendingPolicy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Any, TYPE_CHECKING
import uuid

from .mcc_service import get_mcc_info, is_blocked_category

if TYPE_CHECKING:
    from .wallets import Wallet
    from .tokens import TokenType


class TrustLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNLIMITED = "unlimited"


class SpendingScope(str, Enum):
    ALL = "all"
    RETAIL = "retail"
    DIGITAL = "digital"
    SERVICES = "services"
    COMPUTE = "compute"
    DATA = "data"
    AGENT_TO_AGENT = "agent_to_agent"


@dataclass(slots=True)
class TimeWindowLimit:
    """
    A rolling time-based spending cap (daily, weekly, or monthly).

    Tracks how much has been spent in the current window and automatically
    resets when the window expires.  Used by SpendingPolicy to enforce
    "max $500/day" or "max $10,000/month" style rules.
    """

    window_type: str
    limit_amount: Decimal
    currency: str = "USDC"
    current_spent: Decimal = field(default_factory=lambda: Decimal("0"))
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def reset_if_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.window_type == "daily":
            duration = timedelta(days=1)
        elif self.window_type == "weekly":
            duration = timedelta(weeks=1)
        elif self.window_type == "monthly":
            duration = timedelta(days=30)
        else:
            return False
        if now >= self.window_start + duration:
            self.current_spent = Decimal("0")
            self.window_start = now
            return True
        return False

    def remaining(self) -> Decimal:
        self.reset_if_expired()
        return max(Decimal("0"), self.limit_amount - self.current_spent)

    def can_spend(self, amount: Decimal) -> tuple[bool, str]:
        self.reset_if_expired()
        if self.current_spent + amount > self.limit_amount:
            return False, "time_window_limit"
        return True, "OK"

    def record_spend(self, amount: Decimal) -> None:
        self.reset_if_expired()
        self.current_spent += amount


@dataclass(slots=True)
class MerchantRule:
    """
    A single merchant-level allow or deny rule.

    Merchant rules let you control exactly who the agent can pay:
      - **allow**: Only permit payments to specific merchants or categories.
      - **deny**: Block specific merchants or categories (checked first — deny wins).

    Rules can optionally include per-merchant caps (``max_per_tx``, ``daily_limit``)
    and expiration dates for temporary access.
    """

    rule_id: str = field(default_factory=lambda: f"rule_{uuid.uuid4().hex[:12]}")
    rule_type: str = "allow"
    merchant_id: Optional[str] = None
    category: Optional[str] = None
    max_per_tx: Optional[Decimal] = None
    daily_limit: Optional[Decimal] = None
    reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    def is_active(self) -> bool:
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def matches_merchant(self, merchant_id: str, merchant_category: Optional[str] = None) -> bool:
        if not self.is_active():
            return False
        # SECURITY: Case-insensitive matching prevents bypass via casing tricks
        if self.merchant_id and self.merchant_id.lower() == merchant_id.lower():
            return True
        if self.category and merchant_category and self.category.lower() == merchant_category.lower():
            return True
        return False


@dataclass(slots=True)
class SpendingPolicy:
    """
    Defines and enforces spending rules for a single AI agent.

    A SpendingPolicy is the central object that answers the question:
    "Is this agent allowed to make this payment?"

    It combines multiple layers of control:
      - **Amount limits**: per-transaction cap, lifetime total, daily/weekly/monthly windows
      - **Merchant controls**: allowlist, blocklist, per-merchant caps, MCC category blocking
      - **Scope restrictions**: limit spending to certain categories (e.g. only "compute")
      - **Goal drift detection**: block payments if the agent is off-task
      - **Approval routing**: auto-approve small payments, require human sign-off for large ones

    Usage:
        # Create a policy with default LOW trust limits ($50/tx, $100/day)
        policy = create_default_policy("agent_123", TrustLevel.LOW)

        # Or build a custom policy
        policy = SpendingPolicy(
            agent_id="agent_123",
            limit_per_tx=Decimal("200"),
            limit_total=Decimal("5000"),
            blocked_merchant_categories=["gambling", "adult"],
            approval_threshold=Decimal("500"),  # human approval above $500
        )

        # Enforce it (async, production — reads spend state from DB)
        approved, reason = await policy.evaluate(wallet, amount, fee, chain=..., token=...)

        # Enforce it (sync, dev/test — in-memory state only)
        approved, reason = policy.validate_payment(amount, fee)
    """

    policy_id: str = field(default_factory=lambda: f"policy_{uuid.uuid4().hex[:16]}")
    agent_id: str = ""
    trust_level: TrustLevel = TrustLevel.LOW
    limit_per_tx: Decimal = field(default_factory=lambda: Decimal("100.00"))
    limit_total: Decimal = field(default_factory=lambda: Decimal("1000.00"))
    spent_total: Decimal = field(default_factory=lambda: Decimal("0"))
    daily_limit: Optional[TimeWindowLimit] = None
    weekly_limit: Optional[TimeWindowLimit] = None
    monthly_limit: Optional[TimeWindowLimit] = None
    merchant_rules: list[MerchantRule] = field(default_factory=list)
    allowed_scopes: list[SpendingScope] = field(default_factory=lambda: [SpendingScope.ALL])
    blocked_merchant_categories: list[str] = field(default_factory=list)
    allowed_chains: list[str] = field(default_factory=list)
    allowed_tokens: list[str] = field(default_factory=list)
    allowed_destination_addresses: list[str] = field(default_factory=list)
    blocked_destination_addresses: list[str] = field(default_factory=list)
    require_preauth: bool = False
    approval_threshold: Optional[Decimal] = None
    max_drift_score: Optional[Decimal] = field(default_factory=lambda: Decimal("0.5"))
    max_hold_hours: int = 168
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __setattr__(self, name: str, value: Any) -> None:
        """Handle setting _spent_total as an alias for spent_total (for backward compatibility)."""
        if name == "_spent_total":
            name = "spent_total"
        object.__setattr__(self, name, value)

    async def evaluate(
        self,
        wallet: "Wallet",  # Forward reference to avoid circular import
        amount: Decimal,
        fee: Decimal,
        *,
        chain: str,
        token: "TokenType",  # Forward reference
        merchant_id: Optional[str] = None,
        merchant_category: Optional[str] = None,
        mcc_code: Optional[str] = None,
        scope: SpendingScope = SpendingScope.ALL,
        rpc_client: Optional[Any] = None,  # ChainRPCClient for balance queries
        drift_score: Optional[Decimal] = None,
        policy_store: Optional[Any] = None,  # SpendingPolicyStore for DB-backed enforcement
    ) -> tuple[bool, str]:
        """
        Evaluate a payment request against this policy.

        This is the **primary enforcement method** — called by the orchestrator
        before every payment.  It runs 10 checks in sequence; the first failure
        short-circuits with a denial reason code.

        Check order:
            1. Amount validation (positive amount, non-negative fee)
            2. Scope check (is the spending category allowed?)
            3. MCC check (is the merchant category code blocked?)
            4. Per-transaction limit (amount + fee vs. cap)
            5. Total lifetime limit (cumulative spend)
            6. Time-window limits (daily / weekly / monthly)
            7. On-chain balance (wallet has enough funds?)
            8. Merchant rules (allowlist / blocklist / per-merchant caps)
            9. Goal drift (agent staying on task?)
           10. Approval threshold (OK but needs human sign-off)

        Args:
            wallet: The agent's non-custodial wallet.
            amount: Payment amount in token units.
            fee: Estimated gas/transaction fee (included in limit checks).
            chain: Target blockchain (e.g. "base", "polygon").
            token: Token type (e.g. USDC, USDT).
            merchant_id: Who the agent is paying (optional).
            merchant_category: Category name like "cloud" or "gambling" (optional).
            mcc_code: 4-digit Merchant Category Code (optional).
            scope: Spending scope (retail, compute, agent_to_agent, etc.).
            rpc_client: RPC client for on-chain balance lookup (optional).
            drift_score: How far the agent has drifted from its goal (0.0–1.0, optional).
            policy_store: DB-backed spend tracker for production use (optional).
                When provided, cumulative totals come from the database (race-safe).
                When omitted, uses in-memory state (suitable for dev/test only).

        Returns:
            ``(True, "OK")`` — approved, execute the payment.
            ``(True, "requires_approval")`` — approved, but needs human sign-off.
            ``(False, "<reason_code>")`` — denied.  Common reason codes:
                - ``"per_transaction_limit"`` — single payment too large
                - ``"total_limit_exceeded"`` — lifetime cap reached
                - ``"daily_limit_exceeded"`` — daily window exhausted
                - ``"merchant_denied"`` — merchant on blocklist
                - ``"scope_not_allowed"`` — wrong spending category
                - ``"insufficient_balance"`` — wallet can't cover it
                - ``"goal_drift_exceeded"`` — agent off-task
        """
        # ── Check 1: Amount validation ──────────────────────────────────
        if amount <= 0:
            return False, "amount_must_be_positive"
        if fee < 0:
            return False, "fee_must_be_non_negative"

        total_cost = amount + fee  # All limit checks use amount + fee

        # ── Check 2: Scope ──────────────────────────────────────────────
        # Verify the spending category (retail, compute, etc.) is allowed.
        # SpendingScope.ALL acts as a wildcard — permits any category.
        if SpendingScope.ALL not in self.allowed_scopes and scope not in self.allowed_scopes:
            return False, "scope_not_allowed"

        # ── Check 3: Merchant Category Code (MCC) ──────────────────────
        # Block entire merchant categories (e.g. gambling, adult content).
        if mcc_code:
            mcc_ok, mcc_reason = self._check_mcc_policy(mcc_code)
            if not mcc_ok:
                return False, mcc_reason

        # ── Check 4: Per-transaction limit ──────────────────────────────
        # Cap on a single payment.  Category-specific overrides (e.g.
        # "groceries max $200/tx") take precedence over the global limit.
        effective_per_tx = self._get_effective_per_tx_limit(mcc_code, merchant_category)
        if total_cost > effective_per_tx:
            return False, "per_transaction_limit"

        # ── Checks 5–6: Cumulative & time-window limits ────────────────
        # In production, spend totals come from the database (via
        # policy_store) to prevent race conditions between concurrent
        # transactions.  In dev/test, in-memory state is used instead.
        if policy_store is not None:
            # Velocity check (rapid-fire prevention)
            vel_ok, vel_reason = await policy_store.check_velocity(self.agent_id)
            if not vel_ok:
                return False, vel_reason

            # Load authoritative state from database
            db_state = await policy_store.load_state(self.agent_id)
            if db_state is not None:
                # Total limit check from DB
                if db_state["spent_total"] + total_cost > self.limit_total:
                    return False, "total_limit_exceeded"
                # Time-window checks from DB
                for wtype, wdata in db_state["windows"].items():
                    if wdata["current_spent"] + total_cost > wdata["limit_amount"]:
                        return False, f"{wtype}_limit_exceeded"
            else:
                # No DB state yet — fall back to in-memory for first-time evaluation
                if self.spent_total + total_cost > self.limit_total:
                    return False, "total_limit_exceeded"
                for window_limit in filter(None, [self.daily_limit, self.weekly_limit, self.monthly_limit]):
                    ok, reason = window_limit.can_spend(total_cost)
                    if not ok:
                        return ok, reason
        else:
            # In-memory fallback (dev/test)
            if self.spent_total + total_cost > self.limit_total:
                return False, "total_limit_exceeded"
            for window_limit in filter(None, [self.daily_limit, self.weekly_limit, self.monthly_limit]):
                ok, reason = window_limit.can_spend(total_cost)
                if not ok:
                    return ok, reason

        # ── Check 7: On-chain balance ──────────────────────────────────
        # Query the actual wallet balance on-chain.  Sardis is non-custodial,
        # so the wallet's blockchain balance is the source of truth.
        if rpc_client:
            balance = await wallet.get_balance(chain, token, rpc_client)
            if balance < total_cost:
                return False, "insufficient_balance"

        # ── Check 8: Merchant rules (allowlist / blocklist) ────────────
        # Per-merchant controls: deny specific merchants, restrict to an
        # allowlist, or cap spending at individual merchants.
        if merchant_id:
            merchant_ok, merchant_reason = self._check_merchant_rules(merchant_id, merchant_category, amount)
            if not merchant_ok:
                return False, merchant_reason

        # ── Check 9: Goal drift ────────────────────────────────────────
        # If the agent has drifted too far from its stated goal (measured
        # by an external scoring system), block the payment.
        if drift_score is not None and self.max_drift_score is not None:
            if drift_score > self.max_drift_score:
                return False, "goal_drift_exceeded"

        # ── Check 10: Approval threshold ───────────────────────────────
        # All checks passed, but the amount exceeds the auto-approval cap.
        # Return approved=True with "requires_approval" so the caller can
        # route this to a human for sign-off before executing on-chain.
        if self.approval_threshold is not None and amount > self.approval_threshold:
            return True, "requires_approval"

        return True, "OK"

    @staticmethod
    def _normalize_chain(value: Optional[str]) -> str:
        return (value or "").strip().lower()

    @staticmethod
    def _normalize_token(value: Optional[str]) -> str:
        return (value or "").strip().upper()

    @staticmethod
    def _normalize_destination(value: Optional[str]) -> str:
        return (value or "").strip().lower()

    def validate_execution_context(
        self,
        *,
        destination: Optional[str],
        chain: Optional[str],
        token: Optional[str],
    ) -> tuple[bool, str]:
        """
        Deterministic execution guard rails for on-chain payments.

        This layer is intentionally model-agnostic and does not depend on
        AI interpretation. It should be used as a final gate before execution.
        """
        chain_norm = self._normalize_chain(chain)
        token_norm = self._normalize_token(token)
        destination_norm = self._normalize_destination(destination)

        allowed_chains = {self._normalize_chain(c) for c in self.allowed_chains if self._normalize_chain(c)}
        allowed_tokens = {self._normalize_token(t) for t in self.allowed_tokens if self._normalize_token(t)}
        allowed_destinations = {
            self._normalize_destination(a) for a in self.allowed_destination_addresses if self._normalize_destination(a)
        }
        blocked_destinations = {
            self._normalize_destination(a) for a in self.blocked_destination_addresses if self._normalize_destination(a)
        }

        if allowed_chains and chain_norm not in allowed_chains:
            return False, "chain_not_allowlisted"

        if allowed_tokens and token_norm not in allowed_tokens:
            return False, "token_not_allowlisted"

        if destination_norm:
            if destination_norm in blocked_destinations:
                return False, "destination_blocked"
            if allowed_destinations and destination_norm not in allowed_destinations:
                return False, "destination_not_allowlisted"
        elif allowed_destinations:
            return False, "destination_required_for_allowlist"

        return True, "OK"
    
    def validate_payment(
        self,
        amount: Decimal,
        fee: Decimal,
        *,
        merchant_id: Optional[str] = None,
        merchant_category: Optional[str] = None,
        mcc_code: Optional[str] = None,
        scope: SpendingScope = SpendingScope.ALL,
        drift_score: Optional[Decimal] = None,
    ) -> tuple[bool, str]:
        """
        Synchronous policy check — runs the same checks as evaluate() but
        without on-chain balance lookup or DB-backed spend tracking.

        Use this for:
          - Quick local validation in tests or dev mode
          - Pre-flight checks before calling the full async pipeline
          - The ``/policies/check`` API endpoint (hypothetical "what-if" queries)

        For production payment execution, use ``evaluate()`` instead — it reads
        cumulative spend from the database and checks on-chain balance.

        Returns:
            ``(True, "OK")`` | ``(True, "requires_approval")`` | ``(False, "<reason>")``
        """
        if amount <= 0:
            return False, "amount_must_be_positive"
        if fee < 0:
            return False, "fee_must_be_non_negative"

        total_cost = amount + fee
        if SpendingScope.ALL not in self.allowed_scopes and scope not in self.allowed_scopes:
            return False, "scope_not_allowed"

        # Check MCC code policy
        if mcc_code:
            mcc_ok, mcc_reason = self._check_mcc_policy(mcc_code)
            if not mcc_ok:
                return False, mcc_reason

        # Per-tx limit includes fee (audit-F08)
        # Category-specific overrides take precedence over global limit
        effective_per_tx = self._get_effective_per_tx_limit(mcc_code, merchant_category)
        if total_cost > effective_per_tx:
            return False, "per_transaction_limit"
        if self.spent_total + total_cost > self.limit_total:
            return False, "total_limit_exceeded"
        for window_limit in filter(None, [self.daily_limit, self.weekly_limit, self.monthly_limit]):
            ok, reason = window_limit.can_spend(total_cost)
            if not ok:
                return ok, reason
        if merchant_id:
            merchant_ok, merchant_reason = self._check_merchant_rules(merchant_id, merchant_category, amount)
            if not merchant_ok:
                return False, merchant_reason

        # Check drift score
        if drift_score is not None and self.max_drift_score is not None:
            if drift_score > self.max_drift_score:
                return False, "goal_drift_exceeded"

        # Check approval threshold
        if self.approval_threshold is not None and amount > self.approval_threshold:
            return True, "requires_approval"

        return True, "OK"

    @staticmethod
    def _categories_match(rule_cat: str, resolved_cat: str) -> bool:
        """Compare categories with singular/plural normalization."""
        a = rule_cat.lower().strip()
        b = resolved_cat.lower().strip()
        if a == b:
            return True
        # Build plural/singular variants of `a` and check if `b` matches any
        variants = {a}
        if a.endswith("ies"):
            variants.add(a[:-3] + "y")       # groceries -> grocery
        elif a.endswith("s"):
            variants.add(a[:-1])              # alcohols -> alcohol
        else:
            variants.add(a + "s")             # alcohol -> alcohols
            if a.endswith("y"):
                variants.add(a[:-1] + "ies")  # grocery -> groceries
        return b in variants

    def _get_effective_per_tx_limit(
        self,
        mcc_code: Optional[str] = None,
        merchant_category: Optional[str] = None,
    ) -> Decimal:
        """Return effective per-tx limit, considering category-specific overrides."""
        if not self.merchant_rules:
            return self.limit_per_tx

        # Resolve MCC to category if not already provided
        resolved_category = merchant_category
        if not resolved_category and mcc_code:
            info = get_mcc_info(mcc_code)
            if info:
                resolved_category = info.category

        if resolved_category:
            for rule in self.merchant_rules:
                if not rule.is_active() or not rule.max_per_tx:
                    continue
                # Check both category and merchant_id fields — LLM parser
                # may store category names in either field
                match_field = rule.category or rule.merchant_id
                if match_field and self._categories_match(match_field, resolved_category):
                    return rule.max_per_tx

        return self.limit_per_tx

    def _check_merchant_rules(
        self,
        merchant_id: str,
        merchant_category: Optional[str],
        amount: Decimal,
    ) -> tuple[bool, str]:
        for rule in self.merchant_rules:
            if rule.rule_type == "deny" and rule.matches_merchant(merchant_id, merchant_category):
                return False, "merchant_denied"
        allow_rules = [rule for rule in self.merchant_rules if rule.rule_type == "allow"]
        if allow_rules:
            match = next((rule for rule in allow_rules if rule.matches_merchant(merchant_id, merchant_category)), None)
            if not match:
                return False, "merchant_not_allowlisted"
            if match.max_per_tx and amount > match.max_per_tx:
                return False, "merchant_cap_exceeded"
        return True, "OK"

    def _check_mcc_policy(self, mcc_code: str) -> tuple[bool, str]:
        """
        Check if MCC code is allowed by policy.

        Args:
            mcc_code: 4-digit Merchant Category Code

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        # Check if MCC belongs to blocked category
        if self.blocked_merchant_categories and is_blocked_category(mcc_code, self.blocked_merchant_categories):
            mcc_info = get_mcc_info(mcc_code)
            category_name = mcc_info.category if mcc_info else "unknown"
            return False, f"merchant_category_blocked:{category_name}"

        # Check default high-risk blocks
        mcc_info = get_mcc_info(mcc_code)
        if mcc_info and mcc_info.default_blocked:
            return False, f"high_risk_merchant:{mcc_info.description}"

        return True, "OK"

    def record_spend(self, amount: Decimal) -> None:
        self.spent_total += amount
        for window_limit in filter(None, [self.daily_limit, self.weekly_limit, self.monthly_limit]):
            window_limit.record_spend(amount)
        self.updated_at = datetime.now(timezone.utc)

    def remaining_total(self) -> Decimal:
        return max(Decimal("0"), self.limit_total - self.spent_total)

    def add_merchant_allow(
        self,
        *,
        merchant_id: Optional[str] = None,
        category: Optional[str] = None,
        max_per_tx: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> MerchantRule:
        rule = MerchantRule(rule_type="allow", merchant_id=merchant_id, category=category, max_per_tx=max_per_tx, reason=reason)
        self.merchant_rules.append(rule)
        self.updated_at = datetime.now(timezone.utc)
        return rule

    def add_merchant_deny(
        self,
        *,
        merchant_id: Optional[str] = None,
        category: Optional[str] = None,
        reason: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> MerchantRule:
        rule = MerchantRule(rule_type="deny", merchant_id=merchant_id, category=category, reason=reason, expires_at=expires_at)
        self.merchant_rules.insert(0, rule)
        self.updated_at = datetime.now(timezone.utc)
        return rule

    def block_merchant_category(self, category: str) -> None:
        """
        Block a merchant category by name (e.g., 'gambling', 'alcohol').

        Args:
            category: Category name to block
        """
        if category not in self.blocked_merchant_categories:
            self.blocked_merchant_categories.append(category)
            self.updated_at = datetime.now(timezone.utc)

    def unblock_merchant_category(self, category: str) -> None:
        """
        Unblock a merchant category.

        Args:
            category: Category name to unblock
        """
        if category in self.blocked_merchant_categories:
            self.blocked_merchant_categories.remove(category)
            self.updated_at = datetime.now(timezone.utc)


# Preset spending limits per trust level.
#
# When no custom policy is attached to an agent, Sardis creates a default
# policy using these limits.  New agents start at LOW — you can upgrade to
# MEDIUM/HIGH as the agent proves trustworthy.
#
#   Trust Level  │ Per-Tx   │ Daily    │ Weekly    │ Monthly    │ Total
#   ─────────────┼──────────┼──────────┼───────────┼────────────┼──────────
#   LOW          │ $50      │ $100     │ $500      │ $1,000     │ $5,000
#   MEDIUM       │ $500     │ $1,000   │ $5,000    │ $10,000    │ $50,000
#   HIGH         │ $5,000   │ $10,000  │ $50,000   │ $100,000   │ $500,000
#   UNLIMITED    │ no cap   │ no cap   │ no cap    │ no cap     │ no cap
#
DEFAULT_LIMITS = {
    TrustLevel.LOW: {"per_tx": Decimal("50.00"), "daily": Decimal("100.00"), "weekly": Decimal("500.00"), "monthly": Decimal("1000.00"), "total": Decimal("5000.00")},
    TrustLevel.MEDIUM: {"per_tx": Decimal("500.00"), "daily": Decimal("1000.00"), "weekly": Decimal("5000.00"), "monthly": Decimal("10000.00"), "total": Decimal("50000.00")},
    TrustLevel.HIGH: {"per_tx": Decimal("5000.00"), "daily": Decimal("10000.00"), "weekly": Decimal("50000.00"), "monthly": Decimal("100000.00"), "total": Decimal("500000.00")},
    TrustLevel.UNLIMITED: {"per_tx": Decimal("999999999.00"), "daily": None, "weekly": None, "monthly": None, "total": Decimal("999999999.00")},
}


def create_default_policy(
    agent_id: str,
    trust_level: TrustLevel = TrustLevel.LOW,
    *,
    kya_level: str | None = None,
) -> SpendingPolicy:
    """
    Create a SpendingPolicy with preset limits for the given trust level.

    This is the fallback when no custom policy is stored for an agent.
    The orchestrator and wallet manager call this automatically — you
    don't need to call it yourself unless you're building a custom flow.

    If ``kya_level`` is provided, the trust level is derived from the
    KYA level instead (see ``trust_level_for_kya``).
    """
    if kya_level is not None:
        trust_level = trust_level_for_kya(kya_level)
    tier = DEFAULT_LIMITS[trust_level]
    policy = SpendingPolicy(agent_id=agent_id, trust_level=trust_level, limit_per_tx=tier["per_tx"], limit_total=tier["total"])
    if tier["daily"]:
        policy.daily_limit = TimeWindowLimit(window_type="daily", limit_amount=tier["daily"])
    if tier["weekly"]:
        policy.weekly_limit = TimeWindowLimit(window_type="weekly", limit_amount=tier["weekly"])
    if tier["monthly"]:
        policy.monthly_limit = TimeWindowLimit(window_type="monthly", limit_amount=tier["monthly"])
    return policy


# ============ KYA ↔ TrustLevel Mapping ============
#
# KYA levels map to spending policy trust levels so that agent verification
# automatically determines spending capabilities.
#
#   KYA Level   │ Trust Level │ Per-Tx  │ Daily
#   ────────────┼─────────────┼─────────┼────────
#   none        │ LOW         │ $50     │ $100
#   basic       │ LOW         │ $50     │ $100
#   verified    │ MEDIUM      │ $500    │ $1,000
#   attested    │ HIGH        │ $5,000  │ $10,000
#

KYA_TO_TRUST: dict[str, TrustLevel] = {
    "none": TrustLevel.LOW,
    "basic": TrustLevel.LOW,
    "verified": TrustLevel.MEDIUM,
    "attested": TrustLevel.HIGH,
}

TRUST_TO_KYA: dict[TrustLevel, str] = {
    TrustLevel.LOW: "basic",
    TrustLevel.MEDIUM: "verified",
    TrustLevel.HIGH: "attested",
    TrustLevel.UNLIMITED: "attested",
}


def trust_level_for_kya(kya_level: str) -> TrustLevel:
    """Map a KYA level string to the corresponding TrustLevel."""
    return KYA_TO_TRUST.get(kya_level.lower(), TrustLevel.LOW)


def kya_level_for_trust(trust_level: TrustLevel) -> str:
    """Map a TrustLevel to the corresponding KYA level string."""
    return TRUST_TO_KYA.get(trust_level, "basic")
