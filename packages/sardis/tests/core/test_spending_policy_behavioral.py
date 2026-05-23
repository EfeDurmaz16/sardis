"""Behavioral tests for SpendingPolicy.validate_payment() and evaluate().

Covers the core policy enforcement checks:
  a) Per-transaction amount limit (under/at/over)
  b) Daily cumulative limit
  c) Monthly cumulative limit
  d) Merchant allowlist
  e) Merchant blocklist
  f) Time window restriction
  g) Multiple rules combined
"""
from __future__ import annotations

from decimal import Decimal

from sardis.core.spending_policy import (
    SpendingPolicy,
    SpendingScope,
    TimeWindowLimit,
    TrustLevel,
    create_default_policy,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _policy(**overrides) -> SpendingPolicy:
    """Create a policy with sensible test defaults."""
    defaults = {
        "agent_id": "agent_test",
        "trust_level": TrustLevel.MEDIUM,
        "limit_per_tx": Decimal("500"),
        "limit_total": Decimal("5000"),
    }
    defaults.update(overrides)
    return SpendingPolicy(**defaults)


# ── Per-transaction limit ────────────────────────────────────────────


class TestPerTransactionLimit:
    def test_under_limit_passes(self):
        policy = _policy(limit_per_tx=Decimal("100"))
        ok, reason = policy.validate_payment(Decimal("50"), Decimal("0"))
        assert ok is True
        assert reason == "OK"

    def test_at_limit_passes(self):
        policy = _policy(limit_per_tx=Decimal("100"))
        ok, reason = policy.validate_payment(Decimal("100"), Decimal("0"))
        assert ok is True

    def test_over_limit_denied(self):
        policy = _policy(limit_per_tx=Decimal("100"))
        ok, reason = policy.validate_payment(Decimal("101"), Decimal("0"))
        assert ok is False
        assert reason == "per_transaction_limit"

    def test_fee_included_in_limit_check(self):
        """amount + fee must fit within per-tx limit."""
        policy = _policy(limit_per_tx=Decimal("100"))
        ok, reason = policy.validate_payment(Decimal("90"), Decimal("15"))
        assert ok is False
        assert reason == "per_transaction_limit"

    def test_zero_amount_rejected(self):
        policy = _policy()
        ok, reason = policy.validate_payment(Decimal("0"), Decimal("0"))
        assert ok is False
        assert reason == "amount_must_be_positive"

    def test_negative_fee_rejected(self):
        policy = _policy()
        ok, reason = policy.validate_payment(Decimal("10"), Decimal("-1"))
        assert ok is False
        assert reason == "fee_must_be_non_negative"


# ── Daily cumulative limit ───────────────────────────────────────────


class TestDailyLimit:
    def test_within_daily_limit(self):
        policy = _policy(
            daily_limit=TimeWindowLimit(window_type="daily", limit_amount=Decimal("200"))
        )
        ok, reason = policy.validate_payment(Decimal("100"), Decimal("0"))
        assert ok is True

    def test_exceeds_daily_limit(self):
        policy = _policy(
            limit_per_tx=Decimal("500"),
            daily_limit=TimeWindowLimit(window_type="daily", limit_amount=Decimal("200")),
        )
        # Record prior spend
        policy.daily_limit.current_spent = Decimal("150")
        ok, reason = policy.validate_payment(Decimal("60"), Decimal("0"))
        assert ok is False
        assert reason == "time_window_limit"

    def test_record_spend_updates_daily(self):
        policy = _policy(
            daily_limit=TimeWindowLimit(window_type="daily", limit_amount=Decimal("200"))
        )
        policy.record_spend(Decimal("50"))
        assert policy.daily_limit.current_spent == Decimal("50")


# ── Monthly cumulative limit ────────────────────────────────────────


class TestMonthlyLimit:
    def test_within_monthly_limit(self):
        policy = _policy(
            monthly_limit=TimeWindowLimit(window_type="monthly", limit_amount=Decimal("1000"))
        )
        ok, reason = policy.validate_payment(Decimal("500"), Decimal("0"))
        assert ok is True

    def test_exceeds_monthly_limit(self):
        policy = _policy(
            limit_per_tx=Decimal("1000"),
            monthly_limit=TimeWindowLimit(window_type="monthly", limit_amount=Decimal("1000")),
        )
        policy.monthly_limit.current_spent = Decimal("600")
        ok, reason = policy.validate_payment(Decimal("500"), Decimal("0"))
        assert ok is False
        assert reason == "time_window_limit"


# ── Merchant allowlist ───────────────────────────────────────────────


class TestMerchantAllowlist:
    def test_allowed_merchant_passes(self):
        policy = _policy()
        policy.add_merchant_allow(merchant_id="openai.com")
        ok, reason = policy.validate_payment(
            Decimal("10"), Decimal("0"), merchant_id="openai.com"
        )
        assert ok is True

    def test_unknown_merchant_blocked_when_allowlist_exists(self):
        policy = _policy()
        policy.add_merchant_allow(merchant_id="openai.com")
        ok, reason = policy.validate_payment(
            Decimal("10"), Decimal("0"), merchant_id="stripe.com"
        )
        assert ok is False
        assert reason == "merchant_not_allowlisted"

    def test_no_allowlist_allows_any_merchant(self):
        policy = _policy()
        ok, reason = policy.validate_payment(
            Decimal("10"), Decimal("0"), merchant_id="anyone.com"
        )
        assert ok is True


# ── Merchant blocklist ───────────────────────────────────────────────


class TestMerchantBlocklist:
    def test_blocked_merchant_denied(self):
        policy = _policy()
        policy.add_merchant_deny(merchant_id="casino.com")
        ok, reason = policy.validate_payment(
            Decimal("10"), Decimal("0"), merchant_id="casino.com"
        )
        assert ok is False
        assert reason == "merchant_denied"

    def test_unblocked_merchant_passes(self):
        policy = _policy()
        policy.add_merchant_deny(merchant_id="casino.com")
        ok, reason = policy.validate_payment(
            Decimal("10"), Decimal("0"), merchant_id="openai.com"
        )
        assert ok is True

    def test_deny_wins_over_allow(self):
        """Deny rules are checked first — deny wins."""
        policy = _policy()
        policy.add_merchant_allow(merchant_id="casino.com")
        policy.add_merchant_deny(merchant_id="casino.com")
        ok, reason = policy.validate_payment(
            Decimal("10"), Decimal("0"), merchant_id="casino.com"
        )
        assert ok is False
        assert reason == "merchant_denied"


# ── Time window restriction ──────────────────────────────────────────


class TestTimeWindowRestriction:
    def test_weekly_limit_enforced(self):
        policy = _policy(
            limit_per_tx=Decimal("1000"),
            weekly_limit=TimeWindowLimit(window_type="weekly", limit_amount=Decimal("500")),
        )
        policy.weekly_limit.current_spent = Decimal("450")
        ok, reason = policy.validate_payment(Decimal("60"), Decimal("0"))
        assert ok is False
        assert reason == "time_window_limit"

    def test_window_remaining_calculation(self):
        window = TimeWindowLimit(window_type="daily", limit_amount=Decimal("100"))
        window.current_spent = Decimal("40")
        assert window.remaining() == Decimal("60")


# ── Multiple rules combined ──────────────────────────────────────────


class TestMultipleRulesCombined:
    def test_all_checks_pass(self):
        policy = _policy(
            limit_per_tx=Decimal("200"),
            limit_total=Decimal("1000"),
            daily_limit=TimeWindowLimit(window_type="daily", limit_amount=Decimal("500")),
            approval_threshold=Decimal("150"),
        )
        policy.add_merchant_allow(merchant_id="openai.com")
        ok, reason = policy.validate_payment(
            Decimal("100"), Decimal("0"), merchant_id="openai.com"
        )
        assert ok is True
        assert reason == "OK"

    def test_requires_approval_above_threshold(self):
        policy = _policy(approval_threshold=Decimal("50"))
        ok, reason = policy.validate_payment(Decimal("100"), Decimal("0"))
        assert ok is True
        assert reason == "requires_approval"

    def test_total_limit_exceeded(self):
        policy = _policy(limit_per_tx=Decimal("500"), limit_total=Decimal("100"))
        policy.spent_total = Decimal("80")
        ok, reason = policy.validate_payment(Decimal("30"), Decimal("0"))
        assert ok is False
        assert reason == "total_limit_exceeded"

    def test_scope_not_allowed(self):
        policy = _policy(allowed_scopes=[SpendingScope.COMPUTE])
        ok, reason = policy.validate_payment(
            Decimal("10"), Decimal("0"), scope=SpendingScope.RETAIL
        )
        assert ok is False
        assert reason == "scope_not_allowed"

    def test_drift_score_blocks_off_task_agent(self):
        policy = _policy(max_drift_score=Decimal("0.5"))
        ok, reason = policy.validate_payment(
            Decimal("10"), Decimal("0"), drift_score=Decimal("0.8")
        )
        assert ok is False
        assert reason == "goal_drift_exceeded"


# ── Default policy presets ───────────────────────────────────────────


class TestDefaultPolicyPresets:
    def test_low_trust_limits(self):
        policy = create_default_policy("agent_1", TrustLevel.LOW)
        assert policy.limit_per_tx == Decimal("50.00")
        assert policy.daily_limit is not None
        assert policy.daily_limit.limit_amount == Decimal("100.00")

    def test_high_trust_limits(self):
        policy = create_default_policy("agent_1", TrustLevel.HIGH)
        assert policy.limit_per_tx == Decimal("5000.00")
