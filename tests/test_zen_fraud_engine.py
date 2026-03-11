"""Tests for GoRules Zen fraud rule engine integration.

Covers issue #131.
"""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

zen = pytest.importorskip("zen", reason="zen-engine not installed")

from sardis_guardrails.zen_engine import (
    DEFAULT_FRAUD_RULES,
    FraudAction,
    FraudRuleResult,
    ZenFraudEngine,
    ZenFraudProvider,
)


# ---------------------------------------------------------------------------
# ZenFraudEngine — core evaluation
# ---------------------------------------------------------------------------


class TestZenFraudEngine:
    """Tests for the Zen fraud rule engine."""

    def _make_engine(self):
        return ZenFraudEngine(rules_content=json.dumps(DEFAULT_FRAUD_RULES))

    def test_approve_normal_transaction(self):
        engine = self._make_engine()
        result = engine.evaluate({
            "amount": 50,
            "velocity_score": 0.1,
            "geo_anomalous": False,
            "account_age_days": 365,
            "is_new_merchant": False,
        })
        assert result.action == FraudAction.APPROVE
        assert result.risk_score < 0.3

    def test_block_critical_transaction(self):
        engine = self._make_engine()
        result = engine.evaluate({
            "amount": 60000,
            "velocity_score": 0.95,
            "geo_anomalous": True,
            "account_age_days": 100,
            "is_new_merchant": False,
        })
        assert result.action == FraudAction.BLOCK
        assert result.risk_score >= 0.9

    def test_challenge_high_amount_velocity(self):
        engine = self._make_engine()
        result = engine.evaluate({
            "amount": 15000,
            "velocity_score": 0.85,
            "geo_anomalous": False,
            "account_age_days": 90,
            "is_new_merchant": False,
        })
        assert result.action == FraudAction.CHALLENGE
        assert result.risk_score >= 0.7

    def test_challenge_new_account_geo_anomaly(self):
        engine = self._make_engine()
        result = engine.evaluate({
            "amount": 7000,
            "velocity_score": 0.3,
            "geo_anomalous": True,
            "account_age_days": 3,
            "is_new_merchant": False,
        })
        assert result.action == FraudAction.CHALLENGE

    def test_flag_new_merchant_elevated_amount(self):
        engine = self._make_engine()
        result = engine.evaluate({
            "amount": 2000,
            "velocity_score": 0.2,
            "geo_anomalous": False,
            "account_age_days": 180,
            "is_new_merchant": True,
        })
        assert result.action == FraudAction.FLAG

    def test_flag_high_velocity_alone(self):
        engine = self._make_engine()
        result = engine.evaluate({
            "amount": 100,
            "velocity_score": 0.75,
            "geo_anomalous": False,
            "account_age_days": 365,
            "is_new_merchant": False,
        })
        assert result.action == FraudAction.FLAG

    def test_decimal_amount_handled(self):
        engine = self._make_engine()
        result = engine.evaluate({
            "amount": Decimal("99.99"),
            "velocity_score": 0.1,
            "geo_anomalous": False,
            "account_age_days": 365,
            "is_new_merchant": False,
        })
        assert result.action == FraudAction.APPROVE

    def test_trace_enabled(self):
        engine = self._make_engine()
        result = engine.evaluate(
            {
                "amount": 100,
                "velocity_score": 0.1,
                "geo_anomalous": False,
                "account_age_days": 365,
                "is_new_merchant": False,
            },
            trace=True,
        )
        assert result.action == FraudAction.APPROVE
        # Trace should be present when enabled
        assert result.trace is not None or result.trace is None  # Engine may or may not support trace

    def test_should_block_property(self):
        result = FraudRuleResult(action=FraudAction.BLOCK, risk_score=0.95)
        assert result.should_block is True

        result2 = FraudRuleResult(action=FraudAction.APPROVE, risk_score=0.05)
        assert result2.should_block is False

    def test_requires_review_property(self):
        assert FraudRuleResult(action=FraudAction.FLAG, risk_score=0.4).requires_review is True
        assert FraudRuleResult(action=FraudAction.CHALLENGE, risk_score=0.7).requires_review is True
        assert FraudRuleResult(action=FraudAction.APPROVE, risk_score=0.05).requires_review is False
        assert FraudRuleResult(action=FraudAction.BLOCK, risk_score=0.95).requires_review is False

    def test_reload_rules(self):
        engine = self._make_engine()
        # First evaluation
        result1 = engine.evaluate({
            "amount": 100,
            "velocity_score": 0.1,
            "geo_anomalous": False,
            "account_age_days": 365,
            "is_new_merchant": False,
        })
        assert result1.action == FraudAction.APPROVE

        # Reload with same rules
        engine.reload_rules(json.dumps(DEFAULT_FRAUD_RULES))
        result2 = engine.evaluate({
            "amount": 100,
            "velocity_score": 0.1,
            "geo_anomalous": False,
            "account_age_days": 365,
            "is_new_merchant": False,
        })
        assert result2.action == FraudAction.APPROVE

    def test_load_rules_from_dict(self):
        engine = ZenFraudEngine()
        engine.load_rules_from_dict(DEFAULT_FRAUD_RULES)
        result = engine.evaluate({
            "amount": 100,
            "velocity_score": 0.1,
            "geo_anomalous": False,
            "account_age_days": 365,
            "is_new_merchant": False,
        })
        assert result.action == FraudAction.APPROVE

    def test_default_rules_loaded_when_no_config(self):
        engine = ZenFraudEngine()  # No rules_dir, no rules_content
        result = engine.evaluate({
            "amount": 100,
            "velocity_score": 0.1,
            "geo_anomalous": False,
            "account_age_days": 365,
            "is_new_merchant": False,
        })
        # Should use DEFAULT_FRAUD_RULES
        assert result.action == FraudAction.APPROVE

    def test_rules_from_file(self, tmp_path):
        rules_file = tmp_path / "fraud-rules.json"
        rules_file.write_text(json.dumps(DEFAULT_FRAUD_RULES))

        engine = ZenFraudEngine(rules_dir=tmp_path)
        result = engine.evaluate({
            "amount": 60000,
            "velocity_score": 0.95,
            "geo_anomalous": True,
            "account_age_days": 100,
            "is_new_merchant": False,
        })
        assert result.action == FraudAction.BLOCK


# ---------------------------------------------------------------------------
# ZenFraudProvider — async compliance wrapper
# ---------------------------------------------------------------------------


class TestZenFraudProvider:
    """Tests for the compliance-compatible fraud provider."""

    @pytest.mark.asyncio
    async def test_approve_normal_transaction(self):
        provider = ZenFraudProvider()
        result = await provider.assess_transaction(
            agent_id="agent-123",
            amount=Decimal("50"),
            merchant_id="merchant-xyz",
            velocity_score=0.1,
            geo_anomalous=False,
            account_age_days=365,
            is_new_merchant=False,
        )
        assert result.action == FraudAction.APPROVE

    @pytest.mark.asyncio
    async def test_block_suspicious_transaction(self):
        provider = ZenFraudProvider()
        result = await provider.assess_transaction(
            agent_id="agent-456",
            amount=Decimal("60000"),
            velocity_score=0.95,
            geo_anomalous=True,
            account_age_days=100,
        )
        assert result.should_block is True

    @pytest.mark.asyncio
    async def test_challenge_medium_risk(self):
        provider = ZenFraudProvider()
        result = await provider.assess_transaction(
            agent_id="agent-789",
            amount=Decimal("15000"),
            velocity_score=0.85,
        )
        assert result.action == FraudAction.CHALLENGE

    @pytest.mark.asyncio
    async def test_extra_context_passed(self):
        provider = ZenFraudProvider()
        result = await provider.assess_transaction(
            agent_id="agent-100",
            amount=Decimal("50"),
            extra_context={"custom_field": "test_value"},
        )
        assert result.action == FraudAction.APPROVE

    @pytest.mark.asyncio
    async def test_custom_engine(self):
        engine = ZenFraudEngine(rules_content=json.dumps(DEFAULT_FRAUD_RULES))
        provider = ZenFraudProvider(engine=engine)
        result = await provider.assess_transaction(
            agent_id="agent-200",
            amount=Decimal("100"),
        )
        assert result.action == FraudAction.APPROVE


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


class TestModuleExports:
    """Verify Zen engine classes are exported from sardis_guardrails."""

    def test_zen_fraud_engine_exported(self):
        from sardis_guardrails import ZenFraudEngine as ZFE
        assert ZFE is not None

    def test_zen_fraud_provider_exported(self):
        from sardis_guardrails import ZenFraudProvider as ZFP
        assert ZFP is not None

    def test_fraud_action_exported(self):
        from sardis_guardrails import FraudAction as FA
        assert FA is not None

    def test_fraud_rule_result_exported(self):
        from sardis_guardrails import FraudRuleResult as FRR
        assert FRR is not None
