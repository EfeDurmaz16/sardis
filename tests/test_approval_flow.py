"""Tests for Human-in-the-Loop approval queue and goal drift detection."""
from decimal import Decimal

import pytest

# ── Simple SDK: Policy approval threshold ──────────────────────────────

from sardis.policy import Policy, PolicyResult
from sardis.transaction import Transaction, TransactionResult, TransactionStatus
from sardis.wallet import Wallet


class TestPolicyApprovalThreshold:
    """Tests for Policy.approval_threshold in the simple SDK."""

    def test_policy_without_threshold_approves_normally(self):
        policy = Policy(max_per_tx=100)
        result = policy.check(amount=50)
        assert result.approved is True
        assert result.requires_approval is False
        assert result.approval_reason is None

    def test_policy_with_threshold_below_approves_normally(self):
        policy = Policy(max_per_tx=1000, approval_threshold=500)
        result = policy.check(amount=200)
        assert result.approved is True
        assert result.requires_approval is False

    def test_policy_with_threshold_above_requires_approval(self):
        policy = Policy(max_per_tx=5000, approval_threshold=500)
        result = policy.check(amount=1000)
        assert result.approved is True
        assert result.requires_approval is True
        assert result.approval_reason is not None
        assert "500" in result.approval_reason

    def test_policy_with_threshold_equal_approves_normally(self):
        policy = Policy(max_per_tx=1000, approval_threshold=500)
        result = policy.check(amount=500)
        assert result.approved is True
        assert result.requires_approval is False

    def test_policy_rejects_before_approval_check(self):
        """Amount exceeding max_per_tx is rejected, not sent for approval."""
        policy = Policy(max_per_tx=100, approval_threshold=50)
        result = policy.check(amount=200)
        assert result.approved is False
        assert result.requires_approval is False

    def test_policy_result_repr_shows_requires_approval(self):
        result = PolicyResult(approved=True, requires_approval=True)
        assert "requires_approval" in repr(result)


class TestTransactionPendingApproval:
    """Tests for PENDING_APPROVAL in Transaction.execute()."""

    def test_transaction_below_threshold_executes(self):
        wallet = Wallet(initial_balance=1000)
        policy = Policy(max_per_tx=5000, approval_threshold=500)
        tx = Transaction(from_wallet=wallet, to="merchant:api", amount=100, policy=policy)
        result = tx.execute()
        assert result.status == TransactionStatus.EXECUTED
        assert result.approval_id is None

    def test_transaction_above_threshold_pending_approval(self):
        wallet = Wallet(initial_balance=5000, limit_per_tx=5000, limit_total=10000)
        policy = Policy(max_per_tx=5000, approval_threshold=500)
        tx = Transaction(from_wallet=wallet, to="merchant:api", amount=1000, policy=policy)
        result = tx.execute()
        assert result.status == TransactionStatus.PENDING_APPROVAL
        assert result.approval_id is not None
        assert result.approval_id.startswith("appr_")
        # Wallet should NOT be debited
        assert wallet.balance == Decimal("5000")

    def test_transaction_rejected_not_pending(self):
        """Transaction exceeding max_per_tx should be rejected, not pending."""
        wallet = Wallet(initial_balance=5000)
        policy = Policy(max_per_tx=100, approval_threshold=50)
        tx = Transaction(from_wallet=wallet, to="merchant:api", amount=200, policy=policy)
        result = tx.execute()
        assert result.status == TransactionStatus.REJECTED
        assert result.approval_id is None

    def test_pending_approval_status_is_not_success(self):
        wallet = Wallet(initial_balance=5000, limit_per_tx=5000, limit_total=10000)
        policy = Policy(max_per_tx=5000, approval_threshold=500)
        tx = Transaction(from_wallet=wallet, to="merchant:api", amount=1000, policy=policy)
        result = tx.execute()
        assert result.success is False  # PENDING_APPROVAL is not success

    def test_transaction_status_enum_has_pending_approval(self):
        assert TransactionStatus.PENDING_APPROVAL == "pending_approval"
        assert TransactionStatus.PENDING_APPROVAL.value == "pending_approval"


# ── Core SpendingPolicy: approval_threshold + drift ────────────────────

from sardis_v2_core.spending_policy import SpendingPolicy, TrustLevel


class TestSpendingPolicyApprovalThreshold:
    """Tests for SpendingPolicy.approval_threshold in core package."""

    def test_spending_policy_no_threshold(self):
        policy = SpendingPolicy(agent_id="agent_1")
        ok, reason = policy.validate_payment(Decimal("50"), Decimal("0"))
        assert ok is True
        assert reason == "OK"

    def test_spending_policy_below_threshold(self):
        policy = SpendingPolicy(
            agent_id="agent_1",
            approval_threshold=Decimal("500"),
            limit_per_tx=Decimal("5000"),
        )
        ok, reason = policy.validate_payment(Decimal("200"), Decimal("0"))
        assert ok is True
        assert reason == "OK"

    def test_spending_policy_above_threshold_requires_approval(self):
        policy = SpendingPolicy(
            agent_id="agent_1",
            approval_threshold=Decimal("500"),
            limit_per_tx=Decimal("5000"),
        )
        ok, reason = policy.validate_payment(Decimal("1000"), Decimal("0"))
        assert ok is True
        assert reason == "requires_approval"

    def test_spending_policy_rejected_before_approval(self):
        """Per-tx limit rejection takes precedence over approval threshold."""
        policy = SpendingPolicy(
            agent_id="agent_1",
            approval_threshold=Decimal("500"),
            limit_per_tx=Decimal("100"),
        )
        ok, reason = policy.validate_payment(Decimal("200"), Decimal("0"))
        assert ok is False
        assert reason == "per_transaction_limit"


class TestSpendingPolicyDriftScore:
    """Tests for SpendingPolicy.max_drift_score."""

    def test_drift_below_threshold_passes(self):
        policy = SpendingPolicy(
            agent_id="agent_1",
            max_drift_score=Decimal("0.5"),
            limit_per_tx=Decimal("5000"),
        )
        ok, reason = policy.validate_payment(
            Decimal("100"), Decimal("0"), drift_score=Decimal("0.3"),
        )
        assert ok is True

    def test_drift_above_threshold_rejected(self):
        policy = SpendingPolicy(
            agent_id="agent_1",
            max_drift_score=Decimal("0.5"),
            limit_per_tx=Decimal("5000"),
        )
        ok, reason = policy.validate_payment(
            Decimal("100"), Decimal("0"), drift_score=Decimal("0.8"),
        )
        assert ok is False
        assert reason == "goal_drift_exceeded"

    def test_drift_none_passes(self):
        """No drift score provided means no drift check."""
        policy = SpendingPolicy(
            agent_id="agent_1",
            max_drift_score=Decimal("0.5"),
            limit_per_tx=Decimal("5000"),
        )
        ok, reason = policy.validate_payment(Decimal("100"), Decimal("0"))
        assert ok is True
        assert reason == "OK"


# ── Verifier: Goal Drift Detection ─────────────────────────────────────

from sardis_protocol.verifier import MandateVerifier


class TestGoalDriftComputation:
    """Tests for MandateVerifier._compute_drift static method."""

    def _make_intent(self, scope=None, requested_amount=None):
        """Create a minimal mock IntentMandate."""
        from unittest.mock import MagicMock
        intent = MagicMock()
        intent.scope = scope
        intent.requested_amount = requested_amount
        return intent

    def _make_payment(self, merchant_domain="example.com", amount_minor=1000):
        """Create a minimal mock PaymentMandate."""
        from unittest.mock import MagicMock
        payment = MagicMock()
        payment.merchant_domain = merchant_domain
        payment.amount_minor = amount_minor
        return payment

    def test_no_drift_when_no_scope(self):
        intent = self._make_intent(scope=None)
        payment = self._make_payment()
        score, reasons = MandateVerifier._compute_drift(intent, payment)
        assert score == 0.0
        assert len(reasons) == 0

    def test_scope_match_no_drift(self):
        intent = self._make_intent(scope=["cloud"], requested_amount=1000)
        payment = self._make_payment(merchant_domain="aws.amazon.com", amount_minor=1000)
        score, reasons = MandateVerifier._compute_drift(intent, payment)
        assert score < 0.5

    def test_scope_mismatch_high_drift(self):
        intent = self._make_intent(scope=["cloud"])
        payment = self._make_payment(merchant_domain="gambling-site.com")
        score, reasons = MandateVerifier._compute_drift(intent, payment)
        assert score >= 0.8
        assert any("scope_mismatch" in r for r in reasons)

    def test_high_risk_domain_max_drift(self):
        intent = self._make_intent(scope=["cloud"])
        payment = self._make_payment(merchant_domain="bet365.com")
        score, reasons = MandateVerifier._compute_drift(intent, payment)
        assert score == 1.0
        assert any("high_risk_domain" in r for r in reasons)

    def test_amount_deviation_drift(self):
        intent = self._make_intent(scope=None, requested_amount=1000)
        payment = self._make_payment(amount_minor=2000)
        score, reasons = MandateVerifier._compute_drift(intent, payment)
        assert score > 0
        assert any("amount_deviation" in r for r in reasons)

    def test_fuzzy_scope_match(self):
        """Scope keyword appearing in domain should match."""
        intent = self._make_intent(scope=["cloud"])
        payment = self._make_payment(merchant_domain="mycloud-provider.com")
        score, reasons = MandateVerifier._compute_drift(intent, payment)
        # "cloud" appears in domain, so it should match
        assert not any("scope_mismatch" in r for r in reasons)
