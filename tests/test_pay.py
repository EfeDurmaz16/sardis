"""Tests for the sardis.pay() endpoint and SDK."""
from __future__ import annotations

import warnings
from decimal import Decimal

import pytest


class TestSimpleSDKPay:
    """Test sardis.pay() on the simple SDK in simulation mode."""

    def _make_client(self):
        from sardis import SardisClient
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return SardisClient()

    def test_pay_simulation_success(self):
        client = self._make_client()
        result = client.pay(to="openai.com", amount=25)
        assert result.success is True
        assert result.tx_id is not None
        assert float(result.amount) == 25.0

    def test_pay_simulation_creates_wallet_if_none(self):
        client = self._make_client()
        assert len(client._wallets) == 0
        client.pay(to="openai.com", amount=10)
        assert len(client._wallets) == 1

    def test_pay_simulation_reuses_existing_wallet(self):
        client = self._make_client()
        client.wallets.create(name="test", chain="base")
        client.pay(to="openai.com", amount=10)
        assert len(client._wallets) == 1

    def test_pay_currency_and_chain(self):
        client = self._make_client()
        result = client.pay(to="openai.com", amount=50, currency="USDC", chain="base")
        assert result.success is True

    def test_pay_over_limit_rejected(self):
        client = self._make_client()
        # Default per-tx limit is 100
        wallet = client.wallets.create(name="limited", limit_per_tx=20)
        result = client.payments.send(wallet_id=wallet.wallet_id, to="openai.com", amount=50)
        assert result.success is False


class TestStubManagers:
    """Test that stub managers raise NotImplementedError."""

    def _make_client(self):
        from sardis import SardisClient
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return SardisClient()

    def test_payment_objects_stub(self):
        client = self._make_client()
        with pytest.raises(NotImplementedError, match="production SDK"):
            client.payment_objects.mint("wal_123", mandate_id="m1", amount=10)

    def test_fx_stub(self):
        client = self._make_client()
        with pytest.raises(NotImplementedError, match="production SDK"):
            client.fx.get_quote("wal_123", from_token="USDC", to_token="EURC", amount=100)

    def test_holds_stub(self):
        client = self._make_client()
        with pytest.raises(NotImplementedError, match="production SDK"):
            client.holds.create("wal_123", merchant="x", amount=10)

    def test_policies_stub(self):
        client = self._make_client()
        with pytest.raises(NotImplementedError, match="production SDK"):
            client.policies.update("wal_123", policy_text="max $100/day")

    def test_subscriptions_stub(self):
        client = self._make_client()
        with pytest.raises(NotImplementedError, match="production SDK"):
            client.subscriptions.create(wallet_id="w", mandate_id="m", recipient="r", amount=10)

    def test_escrow_stub(self):
        client = self._make_client()
        with pytest.raises(NotImplementedError, match="production SDK"):
            client.escrow.create(wallet_id="w", recipient="r", amount=10)

    def test_mandates_stub(self):
        client = self._make_client()
        with pytest.raises(NotImplementedError, match="production SDK"):
            client.mandates.get("mnd_123")


class TestPolicyExplainer:
    """Test the PolicyExplainer module."""

    def test_denial_explanation(self):
        from sardis_v2_core.policy_explainer import explain_denial
        result = explain_denial("per_transaction_limit")
        assert result.allowed is False
        assert "per-transaction" in result.summary.lower() or "per_tx" in result.reason_code
        assert "per_tx_limit" in result.checks_failed
        assert result.suggested_action is not None
        assert len(result.checks_passed) > 0  # earlier checks passed

    def test_approval_explanation(self):
        from sardis_v2_core.policy_explainer import explain_approval
        result = explain_approval()
        assert result.allowed is True
        assert len(result.checks_passed) == 12

    def test_requires_approval_explanation(self):
        from sardis_v2_core.policy_explainer import explain_approval
        result = explain_approval("requires_approval")
        assert result.allowed is True
        assert result.suggested_action is not None

    def test_json_serialization(self):
        import json

        from sardis_v2_core.policy_explainer import explain_denial
        result = explain_denial("merchant_denied")
        parsed = json.loads(result.to_json())
        assert parsed["allowed"] is False
        assert "merchant_rules" in parsed["checks_failed"]

    def test_text_serialization(self):
        from sardis_v2_core.policy_explainer import explain_denial
        result = explain_denial("insufficient_balance")
        text = result.to_text()
        assert "DENIED" in text
        assert "Suggested action" in text

    def test_to_dict_roundtrip(self):
        from sardis_v2_core.policy_explainer import explain_denial
        result = explain_denial("goal_drift_exceeded")
        d = result.to_dict()
        assert d["reason_code"] == "goal_drift_exceeded"
        assert "goal_drift" in d["checks_failed"]


class TestWalletBalanceRemaining:
    """Test WalletBalance.remaining property."""

    def test_remaining_equals_balance(self):
        from datetime import datetime, timezone

        from sardis_sdk.models.wallet import WalletBalance
        balance = WalletBalance(
            wallet_id="wal_1",
            chain="base",
            token="USDC",
            balance=Decimal("100.00"),
            address="0xabc",
        )
        assert balance.remaining == Decimal("100.00")
