"""Tests for the Policy DSL — compile, decompile, validate."""

from decimal import Decimal

import pytest
from sardis_v2_core.policy_dsl import (
    PolicyDefinition,
    PolicyRule,
    compile_policy,
    decompile_policy,
    validate_definition,
)
from sardis_v2_core.spending_policy import SpendingPolicy, SpendingScope, TrustLevel


class TestValidateDefinition:
    """Test DSL validation logic."""

    def test_validate_empty_rules(self):
        defn = PolicyDefinition(rules=[])
        errors = validate_definition(defn)
        assert len(errors) == 1
        assert "at least one rule" in errors[0]

    def test_validate_unknown_rule_type(self):
        defn = PolicyDefinition(rules=[PolicyRule(type="unknown_rule")])
        errors = validate_definition(defn)
        assert any("unknown rule type" in e for e in errors)

    def test_validate_limit_per_tx_missing_amount(self):
        defn = PolicyDefinition(rules=[PolicyRule(type="limit_per_tx", params={})])
        errors = validate_definition(defn)
        assert any("missing 'amount'" in e for e in errors)

    def test_validate_limit_per_tx_negative(self):
        defn = PolicyDefinition(rules=[PolicyRule(type="limit_per_tx", params={"amount": "-10"})])
        errors = validate_definition(defn)
        assert any("positive number" in e for e in errors)

    def test_validate_valid_definition(self):
        defn = PolicyDefinition(rules=[
            PolicyRule(type="limit_per_tx", params={"amount": "500"}),
            PolicyRule(type="limit_total", params={"amount": "10000"}),
        ])
        errors = validate_definition(defn)
        assert errors == []

    def test_validate_scope_unknown(self):
        defn = PolicyDefinition(rules=[PolicyRule(type="scope", params={"allowed": ["rocket_fuel"]})])
        errors = validate_definition(defn)
        assert any("unknown scope" in e for e in errors)

    def test_validate_time_window_bad_window(self):
        defn = PolicyDefinition(rules=[PolicyRule(type="time_window", params={"window": "yearly", "amount": "100"})])
        errors = validate_definition(defn)
        assert any("daily/weekly/monthly" in e for e in errors)

    def test_validate_trust_level_bad(self):
        defn = PolicyDefinition(rules=[PolicyRule(type="trust_level", params={"level": "ultra"})])
        errors = validate_definition(defn)
        assert any("must be one of" in e for e in errors)


class TestCompilePolicy:
    """Test DSL compilation to SpendingPolicy."""

    def test_compile_basic_limits(self):
        defn = PolicyDefinition(rules=[
            PolicyRule(type="limit_per_tx", params={"amount": "200"}),
            PolicyRule(type="limit_total", params={"amount": "5000"}),
        ])
        policy = compile_policy(defn, "agent-123")
        assert policy.agent_id == "agent-123"
        assert policy.limit_per_tx == Decimal("200")
        assert policy.limit_total == Decimal("5000")

    def test_compile_with_time_windows(self):
        defn = PolicyDefinition(rules=[
            PolicyRule(type="limit_per_tx", params={"amount": "100"}),
            PolicyRule(type="time_window", params={"window": "daily", "amount": "500"}),
            PolicyRule(type="time_window", params={"window": "weekly", "amount": "2000"}),
        ])
        policy = compile_policy(defn, "agent-456")
        assert policy.daily_limit is not None
        assert policy.daily_limit.limit_amount == Decimal("500")
        assert policy.weekly_limit is not None
        assert policy.weekly_limit.limit_amount == Decimal("2000")

    def test_compile_with_trust_level(self):
        defn = PolicyDefinition(rules=[
            PolicyRule(type="trust_level", params={"level": "medium"}),
        ])
        policy = compile_policy(defn, "agent-789")
        assert policy.trust_level == TrustLevel.MEDIUM
        assert policy.limit_per_tx == Decimal("500.00")

    def test_compile_with_merchant_rules(self):
        defn = PolicyDefinition(rules=[
            PolicyRule(type="limit_per_tx", params={"amount": "100"}),
            PolicyRule(type="merchant_allow", params={"merchant_id": "aws", "max_per_tx": "200"}),
            PolicyRule(type="merchant_block", params={"category": "gambling"}),
        ])
        policy = compile_policy(defn, "agent-123")
        assert len(policy.merchant_rules) == 2
        assert policy.merchant_rules[0].rule_type == "deny"  # deny added first (insert 0)
        assert policy.merchant_rules[1].rule_type == "allow"

    def test_compile_with_scope(self):
        defn = PolicyDefinition(rules=[
            PolicyRule(type="limit_per_tx", params={"amount": "100"}),
            PolicyRule(type="scope", params={"allowed": ["compute", "data"]}),
        ])
        policy = compile_policy(defn, "agent-123")
        assert SpendingScope.COMPUTE in policy.allowed_scopes
        assert SpendingScope.DATA in policy.allowed_scopes
        assert SpendingScope.ALL not in policy.allowed_scopes

    def test_compile_invalid_raises(self):
        defn = PolicyDefinition(rules=[PolicyRule(type="unknown")])
        with pytest.raises(ValueError, match="Invalid policy definition"):
            compile_policy(defn, "agent-123")

    def test_compile_with_mcc_block(self):
        defn = PolicyDefinition(rules=[
            PolicyRule(type="limit_per_tx", params={"amount": "100"}),
            PolicyRule(type="mcc_block", params={"categories": ["gambling", "alcohol"]}),
        ])
        policy = compile_policy(defn, "agent-123")
        assert "gambling" in policy.blocked_merchant_categories
        assert "alcohol" in policy.blocked_merchant_categories

    def test_compile_with_goal_drift(self):
        defn = PolicyDefinition(rules=[
            PolicyRule(type="limit_per_tx", params={"amount": "100"}),
            PolicyRule(type="goal_drift_max", params={"threshold": "0.3"}),
        ])
        policy = compile_policy(defn, "agent-123")
        assert policy.max_drift_score == Decimal("0.3")

    def test_compile_with_chain_token_allowlists(self):
        defn = PolicyDefinition(rules=[
            PolicyRule(type="limit_per_tx", params={"amount": "100"}),
            PolicyRule(type="chain_allowlist", params={"chains": ["base", "polygon"]}),
            PolicyRule(type="token_allowlist", params={"tokens": ["USDC", "EURC"]}),
        ])
        policy = compile_policy(defn, "agent-123")
        assert "base" in policy.allowed_chains
        assert "USDC" in policy.allowed_tokens


class TestDecompilePolicy:
    """Test reverse: SpendingPolicy → DSL."""

    def test_roundtrip_basic(self):
        """Compile → decompile preserves key semantics."""
        original = PolicyDefinition(rules=[
            PolicyRule(type="limit_per_tx", params={"amount": "200"}),
            PolicyRule(type="limit_total", params={"amount": "5000"}),
            PolicyRule(type="mcc_block", params={"categories": ["gambling"]}),
        ])
        policy = compile_policy(original, "agent-123")
        decompiled = decompile_policy(policy)

        # Recompile from decompiled definition
        recompiled = compile_policy(decompiled, "agent-123")
        assert recompiled.limit_per_tx == Decimal("200")
        assert recompiled.limit_total == Decimal("5000")
        assert "gambling" in recompiled.blocked_merchant_categories

    def test_decompile_includes_time_windows(self):
        policy = SpendingPolicy(
            agent_id="agent-123",
            limit_per_tx=Decimal("100"),
            limit_total=Decimal("1000"),
        )
        from sardis_v2_core.spending_policy import TimeWindowLimit
        policy.daily_limit = TimeWindowLimit(window_type="daily", limit_amount=Decimal("500"))

        defn = decompile_policy(policy)
        time_rules = [r for r in defn.rules if r.type == "time_window"]
        assert len(time_rules) == 1
        assert time_rules[0].params["window"] == "daily"
        assert time_rules[0].params["amount"] == "500"


class TestPolicyDefinitionSerialization:
    """Test serialization/deserialization."""

    def test_to_dict_from_dict_roundtrip(self):
        defn = PolicyDefinition(
            version="1.0",
            rules=[
                PolicyRule(type="limit_per_tx", params={"amount": "500"}),
                PolicyRule(type="scope", params={"allowed": ["compute"]}),
            ],
            metadata={"name": "test-policy"},
        )
        data = defn.to_dict()
        restored = PolicyDefinition.from_dict(data)
        assert len(restored.rules) == 2
        assert restored.rules[0].type == "limit_per_tx"
        assert restored.metadata["name"] == "test-policy"

    def test_snapshot_hash_deterministic(self):
        defn = PolicyDefinition(
            rules=[PolicyRule(type="limit_per_tx", params={"amount": "500"})],
        )
        h1 = defn.snapshot_hash()
        h2 = defn.snapshot_hash()
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex
