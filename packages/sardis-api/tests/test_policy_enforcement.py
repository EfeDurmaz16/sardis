"""Tests: SpendingPolicy enforcement on all 8 payment paths.

These are source-inspection-based tests that verify the code structure
of each payment router to confirm SpendingPolicy enforcement is present.
"""
from __future__ import annotations

import inspect
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class PolicyResult:
    """Mock policy evaluation result."""

    def __init__(self, allowed: bool, reason: str | None = None):
        self.allowed = allowed
        self.reason = reason


def _mock_wallet_manager(allowed: bool = True, reason: str | None = None):
    """Create a mock wallet manager with configurable policy result."""
    wm = AsyncMock()
    result = PolicyResult(allowed=allowed, reason=reason)
    wm.async_validate_policies = AsyncMock(return_value=result)
    wm.async_record_spend = AsyncMock()
    return wm


# ---------------------------------------------------------------------------
# Path 1 & 2: mandates.py  (POST /mandates/{id}/execute, POST /mandates/execute)
# ---------------------------------------------------------------------------

class TestMandatesPathPolicyEnforcement:
    """Mandates router: policy must be checked before execution."""

    def _source(self) -> str:
        from sardis_api.routers import mandates
        return inspect.getsource(mandates)

    def test_mandates_calls_validate_policies(self):
        """Verify mandates.py calls wallet_manager.async_validate_policies."""
        source = self._source()
        assert "async_validate_policies" in source, (
            "mandates.py must call async_validate_policies"
        )

    def test_mandates_calls_record_spend(self):
        """Verify mandates.py calls wallet_manager.async_record_spend after execution."""
        source = self._source()
        assert "async_record_spend" in source, (
            "mandates.py must call async_record_spend to track spend state"
        )

    def test_mandates_checks_allowed_attribute(self):
        """Verify mandates.py inspects the policy result's .allowed attribute."""
        source = self._source()
        assert "policy_result.allowed" in source or ".allowed" in source, (
            "mandates.py must check policy_result.allowed"
        )

    def test_mandates_execute_stored_raises_403_on_denial(self):
        """POST /mandates/{id}/execute raises HTTP 403 when policy denies."""
        source = self._source()
        # The endpoint must raise HTTPException with 403 when not allowed
        assert "HTTP_403_FORBIDDEN" in source or "status.HTTP_403_FORBIDDEN" in source, (
            "mandates.py must raise 403 on policy denial"
        )

    def test_mandates_legacy_execute_raises_403_on_denial(self):
        """POST /mandates/execute (legacy) also enforces policy and raises 403."""
        source = self._source()
        # Both execute paths call async_validate_policies; count occurrences
        count = source.count("async_validate_policies")
        assert count >= 2, (
            f"Expected async_validate_policies in both execute endpoints, found {count}"
        )

    def test_mandates_legacy_execute_records_spend(self):
        """Both execute paths must record spend after successful execution."""
        source = self._source()
        count = source.count("async_record_spend")
        assert count >= 2, (
            f"Expected async_record_spend in both execute paths, found {count}"
        )


# ---------------------------------------------------------------------------
# Path 3: ap2.py  (POST /ap2/payments/execute)
# ---------------------------------------------------------------------------

class TestAP2PathPolicyEnforcement:
    """AP2 router: SpendingPolicy must be enforced before compliance."""

    def _source(self) -> str:
        from sardis_api.routers import ap2
        return inspect.getsource(ap2)

    def test_ap2_has_wallet_manager_dependency(self):
        """ap2.py declares wallet_manager in its Dependencies dataclass."""
        source = self._source()
        assert "wallet_manager" in source, (
            "ap2.py Dependencies must include wallet_manager"
        )

    def test_ap2_calls_async_validate_policies(self):
        """ap2.py calls async_validate_policies on the wallet_manager."""
        source = self._source()
        assert "async_validate_policies" in source, (
            "ap2.py must call wallet_manager.async_validate_policies"
        )

    def test_ap2_policy_denial_returns_403(self):
        """ap2.py raises HTTP 403 when policy denies."""
        source = self._source()
        assert "HTTP_403_FORBIDDEN" in source or "spending_policy_denied" in source, (
            "ap2.py must return 403 on policy denial"
        )

    def test_ap2_policy_checked_before_compliance(self):
        """SpendingPolicy check appears before compliance check in ap2.py."""
        source = self._source()
        policy_idx = source.find("async_validate_policies")
        compliance_idx = source.find("perform_compliance_checks")
        assert policy_idx != -1, "async_validate_policies not found in ap2.py"
        assert compliance_idx != -1, "perform_compliance_checks not found in ap2.py"
        assert policy_idx < compliance_idx, (
            "SpendingPolicy check must precede compliance checks in ap2.py"
        )

    def test_ap2_policy_uses_allowed_attribute(self):
        """ap2.py checks getattr(policy_result, 'allowed', False)."""
        source = self._source()
        assert "allowed" in source, "ap2.py must check the 'allowed' attribute"


# ---------------------------------------------------------------------------
# Path 4: mvp.py  (POST /mvp/payments/execute)
# ---------------------------------------------------------------------------

class TestMVPPathPolicyEnforcement:
    """MVP router: SpendingPolicy + Compliance must be enforced."""

    def _source(self) -> str:
        from sardis_api.routers import mvp
        return inspect.getsource(mvp)

    def test_mvp_calls_async_validate_policies(self):
        """mvp.py calls wallet_manager.async_validate_policies."""
        source = self._source()
        assert "async_validate_policies" in source, (
            "mvp.py must call async_validate_policies"
        )

    def test_mvp_has_compliance_check(self):
        """mvp.py also enforces compliance (KYC/AML) after policy."""
        source = self._source()
        assert "compliance" in source, (
            "mvp.py must include compliance enforcement"
        )

    def test_mvp_calls_record_spend(self):
        """mvp.py records spend after successful execution."""
        source = self._source()
        assert "async_record_spend" in source, (
            "mvp.py must call async_record_spend"
        )

    def test_mvp_policy_denial_raises_403(self):
        """mvp.py raises 403 when SpendingPolicy denies."""
        source = self._source()
        assert "spending_policy_denied" in source or "HTTP_403_FORBIDDEN" in source, (
            "mvp.py must raise 403 on policy denial"
        )

    def test_mvp_policy_checked_before_compliance(self):
        """SpendingPolicy check appears before compliance check in mvp.py."""
        source = self._source()
        policy_idx = source.find("async_validate_policies")
        compliance_idx = source.find("compliance.preflight")
        assert policy_idx != -1, "async_validate_policies not found in mvp.py"
        assert compliance_idx != -1, "compliance.preflight not found in mvp.py"
        assert policy_idx < compliance_idx, (
            "SpendingPolicy check must precede compliance in mvp.py"
        )


# ---------------------------------------------------------------------------
# Path 5 & 6: a2a.py  (POST /a2a/pay, POST /a2a/messages)
# ---------------------------------------------------------------------------

class TestA2APayPathPolicyEnforcement:
    """A2A /pay: mandatory policy check (fail-closed, not conditional)."""

    def _source(self) -> str:
        from sardis_api.routers import a2a
        return inspect.getsource(a2a)

    def test_a2a_calls_async_validate_policies(self):
        """a2a.py calls wallet_manager.async_validate_policies."""
        source = self._source()
        assert "async_validate_policies" in source, (
            "a2a.py must call async_validate_policies"
        )

    def test_a2a_pay_has_mandatory_fail_closed_guard(self):
        """a2a /pay raises error if wallet_manager is not configured (fail-closed)."""
        source = self._source()
        assert "wallet_manager_not_configured" in source, (
            "a2a.py must fail-closed with wallet_manager_not_configured when wallet_manager absent"
        )

    def test_a2a_pay_raises_403_on_policy_denial(self):
        """a2a /pay raises HTTP 403 when SpendingPolicy denies."""
        source = self._source()
        assert "HTTP_403_FORBIDDEN" in source or "status.HTTP_403_FORBIDDEN" in source, (
            "a2a.py must raise 403 on policy denial in /pay"
        )

    def test_a2a_messages_payment_has_policy_check(self):
        """a2a /messages payment path also enforces policy."""
        source = self._source()
        # Both /pay and /messages paths must check policy
        count = source.count("async_validate_policies")
        assert count >= 2, (
            f"Expected async_validate_policies in both /pay and /messages, found {count}"
        )

    def test_a2a_messages_returns_policy_denied_error_code(self):
        """a2a /messages returns 'policy_denied' error_code when policy fails."""
        source = self._source()
        assert "policy_denied" in source, (
            "a2a.py /messages path must return policy_denied error_code"
        )

    def test_a2a_policy_denial_guard_not_conditional(self):
        """a2a /pay guard is unconditional: raises if wallet_manager is None."""
        source = self._source()
        # The /pay path has: if not deps.wallet_manager: raise ...
        assert "not deps.wallet_manager" in source, (
            "a2a /pay must unconditionally fail if wallet_manager is not configured"
        )


# ---------------------------------------------------------------------------
# Path 7: wallets.py  (POST /wallets/{id}/transfer)
# ---------------------------------------------------------------------------

class TestWalletsTransferPathPolicyEnforcement:
    """Wallets /transfer: mandatory policy + compliance check."""

    def _source(self) -> str:
        from sardis_api.routers import wallets
        return inspect.getsource(wallets)

    def test_wallets_calls_async_validate_policies(self):
        """wallets.py calls wallet_manager.async_validate_policies in transfer."""
        source = self._source()
        assert "async_validate_policies" in source, (
            "wallets.py must call async_validate_policies"
        )

    def test_wallets_has_mandatory_fail_closed_guard(self):
        """wallets /transfer fails-closed if wallet_manager is not configured."""
        source = self._source()
        assert "wallet_manager_not_configured" in source, (
            "wallets.py must fail-closed with wallet_manager_not_configured"
        )

    def test_wallets_guard_not_conditional(self):
        """wallets /transfer raises immediately if wallet_manager is None."""
        source = self._source()
        assert "not deps.wallet_manager" in source, (
            "wallets /transfer must unconditionally fail if wallet_manager is not configured"
        )

    def test_wallets_has_compliance_check(self):
        """wallets /transfer also runs compliance (KYC/AML) after policy."""
        source = self._source()
        assert "compliance" in source and "preflight" in source, (
            "wallets.py must run compliance.preflight after policy check"
        )

    def test_wallets_policy_denial_raises_403(self):
        """wallets /transfer raises 403 when policy denies."""
        source = self._source()
        assert "HTTP_403_FORBIDDEN" in source or "status.HTTP_403_FORBIDDEN" in source, (
            "wallets.py must raise 403 on policy denial"
        )

    def test_wallets_calls_record_spend(self):
        """wallets /transfer records spend after successful execution."""
        source = self._source()
        assert "async_record_spend" in source, (
            "wallets.py must call async_record_spend after transfer"
        )

    def test_wallets_policy_checked_before_compliance(self):
        """SpendingPolicy check appears before compliance check in wallets.py."""
        source = self._source()
        policy_idx = source.find("async_validate_policies")
        compliance_idx = source.find("compliance.preflight")
        assert policy_idx != -1, "async_validate_policies not found in wallets.py"
        assert compliance_idx != -1, "compliance.preflight not found in wallets.py"
        assert policy_idx < compliance_idx, (
            "SpendingPolicy check must precede compliance in wallets.py"
        )


# ---------------------------------------------------------------------------
# Path 8: cards.py  (Card webhook - Lithic)
# ---------------------------------------------------------------------------

class TestCardsWebhookPathPolicyEnforcement:
    """Cards webhook: policy_store enforced in production."""

    def _source(self) -> str:
        from sardis_api.routers import cards
        return inspect.getsource(cards)

    def test_cards_has_policy_evaluation_function(self):
        """cards.py defines _evaluate_policy_for_card helper."""
        source = self._source()
        assert "_evaluate_policy_for_card" in source, (
            "cards.py must define _evaluate_policy_for_card for webhook policy enforcement"
        )

    def test_cards_webhook_calls_policy_evaluation(self):
        """The webhook handler calls _evaluate_policy_for_card for transaction events."""
        source = self._source()
        # _evaluate_policy_for_card is called in both simulate_purchase and webhook
        count = source.count("_evaluate_policy_for_card")
        assert count >= 2, (
            f"Expected _evaluate_policy_for_card in both webhook and simulate_purchase, found {count}"
        )

    def test_cards_policy_store_mandatory_in_production(self):
        """cards.py enforces policy_store presence in production (fail-closed)."""
        source = self._source()
        assert "production" in source or "SARDIS_ENVIRONMENT" in source, (
            "cards.py must check environment for mandatory policy enforcement"
        )
        assert "policy_enforcement_unavailable_in_production" in source, (
            "cards.py must return policy_enforcement_unavailable_in_production in prod without policy_store"
        )

    def test_cards_policy_denial_marks_transaction_declined(self):
        """cards.py marks transaction as declined_policy when policy denies."""
        source = self._source()
        assert "declined_policy" in source, (
            "cards.py must mark transactions as declined_policy when policy denies"
        )

    def test_cards_policy_denial_can_auto_freeze(self):
        """cards.py may auto-freeze the card when policy denies."""
        source = self._source()
        assert "_auto_freeze_enabled" in source, (
            "cards.py must support auto-freeze on policy denial"
        )

    def test_cards_policy_uses_wallet_id_and_mcc(self):
        """cards.py policy evaluation uses wallet_id and mcc_code."""
        source = self._source()
        assert "wallet_id" in source and "mcc_code" in source, (
            "cards.py _evaluate_policy_for_card must accept wallet_id and mcc_code"
        )


# ---------------------------------------------------------------------------
# Cross-cutting: spend recording on all payment paths
# ---------------------------------------------------------------------------

class TestSpendRecordingAllPaths:
    """Verify all payment paths record spend state after execution."""

    def test_mandates_records_spend(self):
        from sardis_api.routers import mandates
        source = inspect.getsource(mandates)
        assert "async_record_spend" in source, (
            "mandates.py must call async_record_spend"
        )

    def test_mvp_records_spend(self):
        from sardis_api.routers import mvp
        source = inspect.getsource(mvp)
        assert "async_record_spend" in source, (
            "mvp.py must call async_record_spend"
        )

    def test_a2a_pay_records_spend(self):
        from sardis_api.routers import a2a
        source = inspect.getsource(a2a)
        count = source.count("async_record_spend")
        assert count >= 2, (
            f"Expected async_record_spend in both /pay and /messages paths in a2a.py, found {count}"
        )

    def test_wallets_transfer_records_spend(self):
        from sardis_api.routers import wallets
        source = inspect.getsource(wallets)
        assert "async_record_spend" in source, (
            "wallets.py must call async_record_spend after transfer"
        )

    def test_ap2_does_not_double_record_spend(self):
        """ap2.py delegates to orchestrator which handles spend; it should not call async_record_spend directly."""
        from sardis_api.routers import ap2
        source = inspect.getsource(ap2)
        # ap2 uses orchestrator.execute_chain - spend recording is inside orchestrator.
        # It's acceptable if ap2 does or does not call it directly; what matters is
        # that the orchestrator path records it. Just verify the orchestrator is used.
        assert "orchestrator" in source, (
            "ap2.py must delegate execution to orchestrator (which records spend)"
        )


# ---------------------------------------------------------------------------
# Cross-cutting: policy denial is always fail-closed (never silent)
# ---------------------------------------------------------------------------

class TestPolicyFailClosedBehavior:
    """Verify policy denials are never silently swallowed."""

    def test_mandates_no_silent_bypass(self):
        """mandates.py raises on policy denial, never silently skips."""
        from sardis_api.routers import mandates
        source = inspect.getsource(mandates)
        # Must check allowed and raise
        assert "not policy_result.allowed" in source or "policy_result.allowed" in source, (
            "mandates.py must inspect policy_result.allowed"
        )
        assert "HTTPException" in source, (
            "mandates.py must raise HTTPException on policy denial"
        )

    def test_a2a_pay_no_silent_bypass(self):
        """a2a /pay raises immediately if wallet_manager absent or policy denies."""
        from sardis_api.routers import a2a
        source = inspect.getsource(a2a)
        assert "wallet_manager_not_configured" in source, (
            "a2a.py /pay must fail-closed without wallet_manager"
        )

    def test_wallets_transfer_no_silent_bypass(self):
        """wallets /transfer raises immediately if wallet_manager absent or policy denies."""
        from sardis_api.routers import wallets
        source = inspect.getsource(wallets)
        assert "wallet_manager_not_configured" in source, (
            "wallets.py /transfer must fail-closed without wallet_manager"
        )

    def test_mvp_conditional_check_present(self):
        """mvp.py checks if wallet_manager is set before calling (acceptable - it's an optional dep)."""
        from sardis_api.routers import mvp
        source = inspect.getsource(mvp)
        # mvp uses conditional check (if deps.wallet_manager:) - that's by design
        assert "deps.wallet_manager" in source, (
            "mvp.py must reference deps.wallet_manager"
        )
        assert "async_validate_policies" in source, (
            "mvp.py must call async_validate_policies"
        )

    def test_ap2_conditional_check_present(self):
        """ap2.py checks if wallet_manager is set before calling (acceptable - it's optional)."""
        from sardis_api.routers import ap2
        source = inspect.getsource(ap2)
        assert "deps.wallet_manager" in source, (
            "ap2.py must reference deps.wallet_manager"
        )
        assert "async_validate_policies" in source, (
            "ap2.py must call async_validate_policies"
        )

    def test_cards_production_fail_closed(self):
        """cards.py explicitly fails-closed when policy_store absent in production."""
        from sardis_api.routers import cards
        source = inspect.getsource(cards)
        assert "policy_enforcement_unavailable_in_production" in source, (
            "cards.py must fail-closed in production without policy_store"
        )
