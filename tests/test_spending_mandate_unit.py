"""Unit tests for SpendingMandate model.

Tests:
  a) Status lifecycle: DRAFT -> ACTIVE -> SUSPENDED -> REVOKED
  b) is_within_limits() / check_payment() for various amounts
  c) record_transaction() / spent_total tracking
  d) Merchant scope matching
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sardis_v2_core.spending_mandate import (
    VALID_TRANSITIONS,
    ApprovalMode,
    MandateCheckResult,
    MandateStatus,
    SpendingMandate,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _mandate(**overrides) -> SpendingMandate:
    defaults = {
        "principal_id": "usr_abc",
        "issuer_id": "usr_abc",
        "agent_id": "agent_001",
        "amount_per_tx": Decimal("500"),
        "amount_total": Decimal("5000"),
        "status": MandateStatus.ACTIVE,
    }
    defaults.update(overrides)
    return SpendingMandate(**defaults)


# ── Status lifecycle ─────────────────────────────────────────────────


class TestStatusLifecycle:
    def test_draft_to_active(self):
        m = _mandate(status=MandateStatus.DRAFT)
        t = m.transition(MandateStatus.ACTIVE, changed_by="admin")
        assert m.status == MandateStatus.ACTIVE
        assert t.from_status == "draft"
        assert t.to_status == "active"

    def test_active_to_suspended(self):
        m = _mandate(status=MandateStatus.ACTIVE)
        t = m.transition(MandateStatus.SUSPENDED, changed_by="admin", reason="review")
        assert m.status == MandateStatus.SUSPENDED
        assert t.reason == "review"

    def test_suspended_to_active(self):
        m = _mandate(status=MandateStatus.SUSPENDED)
        m.transition(MandateStatus.ACTIVE, changed_by="admin")
        assert m.status == MandateStatus.ACTIVE

    def test_active_to_revoked(self):
        m = _mandate(status=MandateStatus.ACTIVE)
        m.transition(MandateStatus.REVOKED, changed_by="admin", reason="policy violation")
        assert m.status == MandateStatus.REVOKED
        assert m.revoked_by == "admin"
        assert m.revocation_reason == "policy violation"
        assert m.revoked_at is not None

    def test_suspended_to_revoked(self):
        m = _mandate(status=MandateStatus.SUSPENDED)
        m.transition(MandateStatus.REVOKED, changed_by="admin")
        assert m.status == MandateStatus.REVOKED

    def test_invalid_transition_raises(self):
        m = _mandate(status=MandateStatus.DRAFT)
        with pytest.raises(ValueError, match="Invalid mandate transition"):
            m.transition(MandateStatus.REVOKED, changed_by="admin")

    def test_revoked_cannot_transition(self):
        m = _mandate(status=MandateStatus.REVOKED)
        with pytest.raises(ValueError):
            m.transition(MandateStatus.ACTIVE, changed_by="admin")

    def test_full_lifecycle(self):
        m = _mandate(status=MandateStatus.DRAFT)
        m.transition(MandateStatus.ACTIVE, changed_by="admin")
        m.transition(MandateStatus.SUSPENDED, changed_by="admin")
        m.transition(MandateStatus.ACTIVE, changed_by="admin")
        m.transition(MandateStatus.REVOKED, changed_by="admin")
        assert m.status == MandateStatus.REVOKED


# ── check_payment (amount limits) ────────────────────────────────────


class TestCheckPayment:
    def test_under_per_tx_limit(self):
        m = _mandate(amount_per_tx=Decimal("100"))
        result = m.check_payment(Decimal("50"))
        assert result.approved is True

    def test_over_per_tx_limit(self):
        m = _mandate(amount_per_tx=Decimal("100"))
        result = m.check_payment(Decimal("150"))
        assert result.approved is False
        assert result.error_code == "MANDATE_AMOUNT_EXCEEDED"

    def test_exactly_at_per_tx_limit(self):
        m = _mandate(amount_per_tx=Decimal("100"))
        result = m.check_payment(Decimal("100"))
        assert result.approved is True

    def test_total_budget_exhausted(self):
        m = _mandate(amount_total=Decimal("100"))
        m.spent_total = Decimal("80")
        result = m.check_payment(Decimal("30"))
        assert result.approved is False
        assert result.error_code == "MANDATE_BUDGET_EXHAUSTED"

    def test_remaining_total_calculation(self):
        m = _mandate(amount_total=Decimal("1000"))
        m.spent_total = Decimal("300")
        assert m.remaining_total == Decimal("700")

    def test_no_total_limit_returns_none(self):
        m = _mandate(amount_total=None)
        assert m.remaining_total is None

    def test_inactive_mandate_rejected(self):
        m = _mandate(status=MandateStatus.SUSPENDED)
        result = m.check_payment(Decimal("10"))
        assert result.approved is False
        assert result.error_code == "MANDATE_NOT_ACTIVE"

    def test_expired_mandate_rejected(self):
        m = _mandate(expires_at=datetime.now(UTC) - timedelta(hours=1))
        result = m.check_payment(Decimal("10"))
        assert result.approved is False
        assert result.error_code == "MANDATE_NOT_ACTIVE"


# ── Merchant scope matching ──────────────────────────────────────────


class TestMerchantScope:
    def test_allowed_merchant_passes(self):
        m = _mandate(merchant_scope={"allowed": ["openai.com", "anthropic.com"]})
        result = m.check_payment(Decimal("10"), merchant="openai.com")
        assert result.approved is True

    def test_disallowed_merchant_rejected(self):
        m = _mandate(merchant_scope={"allowed": ["openai.com"]})
        result = m.check_payment(Decimal("10"), merchant="casino.com")
        assert result.approved is False
        assert result.error_code == "MANDATE_MERCHANT_NOT_ALLOWED"

    def test_blocked_merchant_rejected(self):
        m = _mandate(merchant_scope={"blocked": ["casino.com"]})
        result = m.check_payment(Decimal("10"), merchant="casino.com")
        assert result.approved is False
        assert result.error_code == "MANDATE_MERCHANT_BLOCKED"

    def test_wildcard_merchant_matching(self):
        m = _mandate(merchant_scope={"allowed": ["*.amazon.com"]})
        result = m.check_payment(Decimal("10"), merchant="aws.amazon.com")
        assert result.approved is True

    def test_no_scope_allows_any_merchant(self):
        m = _mandate(merchant_scope={})
        result = m.check_payment(Decimal("10"), merchant="anything.com")
        assert result.approved is True

    def test_no_merchant_passes_when_scope_set(self):
        m = _mandate(merchant_scope={"allowed": ["openai.com"]})
        result = m.check_payment(Decimal("10"))
        assert result.approved is True


# ── Rail and chain permissions ───────────────────────────────────────


class TestRailPermissions:
    def test_allowed_rail_passes(self):
        m = _mandate(allowed_rails=["card", "usdc"])
        result = m.check_payment(Decimal("10"), rail="usdc")
        assert result.approved is True

    def test_disallowed_rail_rejected(self):
        m = _mandate(allowed_rails=["card"])
        result = m.check_payment(Decimal("10"), rail="usdc")
        assert result.approved is False
        assert result.error_code == "MANDATE_RAIL_NOT_ALLOWED"

    def test_chain_permission(self):
        m = _mandate(allowed_chains=["base", "polygon"])
        result = m.check_payment(Decimal("10"), chain="ethereum")
        assert result.approved is False
        assert result.error_code == "MANDATE_CHAIN_NOT_ALLOWED"


# ── Approval threshold ───────────────────────────────────────────────


class TestApprovalThreshold:
    def test_below_threshold_auto_approved(self):
        m = _mandate(
            approval_mode=ApprovalMode.THRESHOLD,
            approval_threshold=Decimal("100"),
        )
        result = m.check_payment(Decimal("50"))
        assert result.approved is True
        assert result.requires_approval is False

    def test_above_threshold_requires_approval(self):
        m = _mandate(
            approval_mode=ApprovalMode.THRESHOLD,
            approval_threshold=Decimal("100"),
        )
        result = m.check_payment(Decimal("200"))
        assert result.approved is True
        assert result.requires_approval is True

    def test_always_human_mode(self):
        m = _mandate(approval_mode=ApprovalMode.ALWAYS_HUMAN)
        result = m.check_payment(Decimal("1"))
        assert result.approved is True
        assert result.requires_approval is True


# ── Policy hash ──────────────────────────────────────────────────────


class TestPolicyHash:
    def test_hash_is_deterministic(self):
        m1 = _mandate(id="mandate_fixed")
        m2 = _mandate(id="mandate_fixed")
        assert m1.policy_hash == m2.policy_hash

    def test_different_rules_different_hash(self):
        m1 = _mandate(amount_per_tx=Decimal("100"))
        m2 = _mandate(amount_per_tx=Decimal("500"))
        assert m1.policy_hash != m2.policy_hash
