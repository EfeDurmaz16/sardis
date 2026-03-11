"""Tests for Marble (CheckMarble) evaluation framework.

Covers rule evaluation, scenario evaluation, decision engine aggregation,
list matching, enums, constants, factory functions, and module exports.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sardis_compliance.marble import (
    DEFAULT_BLOCK_THRESHOLD,
    DEFAULT_REVIEW_THRESHOLD,
    GAMBLING_MCCS,
    HIGH_RISK_COUNTRIES,
    MarbleDecision,
    MarbleDecisionEngine,
    MarbleDecisionResult,
    MarbleList,
    MarbleRule,
    MarbleRuleOperator,
    MarbleScenario,
    MarbleScenarioResult,
    MarbleScoreThreshold,
    MarbleTriggerType,
    create_marble_engine,
    create_rule,
)


# ============ TestMarbleRule ============


class TestMarbleRule:
    """Tests for MarbleRule.evaluate with all operators."""

    def test_gt_true(self):
        rule = MarbleRule("r1", "amount", MarbleRuleOperator.GT, 100, 50)
        assert rule.evaluate({"amount": 200}) is True

    def test_gt_false(self):
        rule = MarbleRule("r1", "amount", MarbleRuleOperator.GT, 100, 50)
        assert rule.evaluate({"amount": 50}) is False

    def test_gt_equal_is_false(self):
        rule = MarbleRule("r1", "amount", MarbleRuleOperator.GT, 100, 50)
        assert rule.evaluate({"amount": 100}) is False

    def test_gte_true(self):
        rule = MarbleRule("r1", "amount", MarbleRuleOperator.GTE, 100, 50)
        assert rule.evaluate({"amount": 100}) is True

    def test_gte_false(self):
        rule = MarbleRule("r1", "amount", MarbleRuleOperator.GTE, 100, 50)
        assert rule.evaluate({"amount": 99}) is False

    def test_lt_true(self):
        rule = MarbleRule("r1", "age", MarbleRuleOperator.LT, 18, 30)
        assert rule.evaluate({"age": 10}) is True

    def test_lt_false(self):
        rule = MarbleRule("r1", "age", MarbleRuleOperator.LT, 18, 30)
        assert rule.evaluate({"age": 20}) is False

    def test_lte_true(self):
        rule = MarbleRule("r1", "age", MarbleRuleOperator.LTE, 18, 30)
        assert rule.evaluate({"age": 18}) is True

    def test_lte_false(self):
        rule = MarbleRule("r1", "age", MarbleRuleOperator.LTE, 18, 30)
        assert rule.evaluate({"age": 19}) is False

    def test_eq_true(self):
        rule = MarbleRule("r1", "status", MarbleRuleOperator.EQ, "blocked", 80)
        assert rule.evaluate({"status": "blocked"}) is True

    def test_eq_false(self):
        rule = MarbleRule("r1", "status", MarbleRuleOperator.EQ, "blocked", 80)
        assert rule.evaluate({"status": "active"}) is False

    def test_neq_true(self):
        rule = MarbleRule("r1", "status", MarbleRuleOperator.NEQ, "blocked", 20)
        assert rule.evaluate({"status": "active"}) is True

    def test_neq_false(self):
        rule = MarbleRule("r1", "status", MarbleRuleOperator.NEQ, "blocked", 20)
        assert rule.evaluate({"status": "blocked"}) is False

    def test_in_true(self):
        rule = MarbleRule("r1", "country", MarbleRuleOperator.IN, {"US", "GB"}, 40)
        assert rule.evaluate({"country": "US"}) is True

    def test_in_false(self):
        rule = MarbleRule("r1", "country", MarbleRuleOperator.IN, {"US", "GB"}, 40)
        assert rule.evaluate({"country": "DE"}) is False

    def test_in_frozenset(self):
        rule = MarbleRule("r1", "country", MarbleRuleOperator.IN, frozenset({"KP", "IR"}), 100)
        assert rule.evaluate({"country": "KP"}) is True

    def test_not_in_true(self):
        rule = MarbleRule("r1", "country", MarbleRuleOperator.NOT_IN, {"US", "GB"}, 40)
        assert rule.evaluate({"country": "DE"}) is True

    def test_not_in_false(self):
        rule = MarbleRule("r1", "country", MarbleRuleOperator.NOT_IN, {"US", "GB"}, 40)
        assert rule.evaluate({"country": "US"}) is False

    def test_contains_true(self):
        rule = MarbleRule("r1", "email", MarbleRuleOperator.CONTAINS, "@test.com", 30)
        assert rule.evaluate({"email": "user@test.com"}) is True

    def test_contains_false(self):
        rule = MarbleRule("r1", "email", MarbleRuleOperator.CONTAINS, "@test.com", 30)
        assert rule.evaluate({"email": "user@real.com"}) is False

    def test_between_true(self):
        rule = MarbleRule("r1", "amount", MarbleRuleOperator.BETWEEN, (100, 500), 40)
        assert rule.evaluate({"amount": 250}) is True

    def test_between_inclusive_low(self):
        rule = MarbleRule("r1", "amount", MarbleRuleOperator.BETWEEN, (100, 500), 40)
        assert rule.evaluate({"amount": 100}) is True

    def test_between_inclusive_high(self):
        rule = MarbleRule("r1", "amount", MarbleRuleOperator.BETWEEN, (100, 500), 40)
        assert rule.evaluate({"amount": 500}) is True

    def test_between_false(self):
        rule = MarbleRule("r1", "amount", MarbleRuleOperator.BETWEEN, (100, 500), 40)
        assert rule.evaluate({"amount": 600}) is False

    def test_is_true_true(self):
        rule = MarbleRule("r1", "is_vpn", MarbleRuleOperator.IS_TRUE, None, 50)
        assert rule.evaluate({"is_vpn": True}) is True

    def test_is_true_truthy(self):
        rule = MarbleRule("r1", "is_vpn", MarbleRuleOperator.IS_TRUE, None, 50)
        assert rule.evaluate({"is_vpn": 1}) is True

    def test_is_true_false(self):
        rule = MarbleRule("r1", "is_vpn", MarbleRuleOperator.IS_TRUE, None, 50)
        assert rule.evaluate({"is_vpn": False}) is False

    def test_is_false_true(self):
        rule = MarbleRule("r1", "verified", MarbleRuleOperator.IS_FALSE, None, 60)
        assert rule.evaluate({"verified": False}) is True

    def test_is_false_falsy(self):
        rule = MarbleRule("r1", "verified", MarbleRuleOperator.IS_FALSE, None, 60)
        assert rule.evaluate({"verified": 0}) is True

    def test_is_false_false(self):
        rule = MarbleRule("r1", "verified", MarbleRuleOperator.IS_FALSE, None, 60)
        assert rule.evaluate({"verified": True}) is False

    def test_missing_field_returns_false(self):
        rule = MarbleRule("r1", "nonexistent", MarbleRuleOperator.GT, 10, 50)
        assert rule.evaluate({"amount": 100}) is False

    def test_inactive_rule_returns_false(self):
        rule = MarbleRule("r1", "amount", MarbleRuleOperator.GT, 10, 50, is_active=False)
        assert rule.evaluate({"amount": 100}) is False

    def test_type_error_returns_false(self):
        """Comparing incompatible types should return False, not raise."""
        rule = MarbleRule("r1", "amount", MarbleRuleOperator.GT, 100, 50)
        assert rule.evaluate({"amount": "not_a_number"}) is False


# ============ TestMarbleScenario ============


class TestMarbleScenario:
    """Tests for MarbleScenario.evaluate."""

    def _make_scenario(
        self,
        rules: list[MarbleRule] | None = None,
        threshold: int = 50,
        decision: MarbleDecision = MarbleDecision.REVIEW,
        is_active: bool = True,
    ) -> MarbleScenario:
        return MarbleScenario(
            scenario_id="test_scenario",
            name="Test Scenario",
            description="Test",
            trigger_type=MarbleTriggerType.TRANSACTION,
            rules=rules or [],
            score_threshold=threshold,
            decision_on_match=decision,
            is_active=is_active,
        )

    def test_matching_rules_trigger(self):
        rules = [
            MarbleRule("r1", "amount", MarbleRuleOperator.GT, 100, 60),
        ]
        scenario = self._make_scenario(rules=rules, threshold=50)
        result = scenario.evaluate({"amount": 200})

        assert result.scenario_id == "test_scenario"
        assert result.triggered_rules == ["r1"]
        assert result.total_score == 60
        assert result.decision == MarbleDecision.REVIEW

    def test_non_matching_rules_approve(self):
        rules = [
            MarbleRule("r1", "amount", MarbleRuleOperator.GT, 100, 60),
        ]
        scenario = self._make_scenario(rules=rules, threshold=50)
        result = scenario.evaluate({"amount": 50})

        assert result.triggered_rules == []
        assert result.total_score == 0
        assert result.decision == MarbleDecision.APPROVE

    def test_score_below_threshold_approves(self):
        """Even if rules trigger, if total score < threshold => APPROVE."""
        rules = [
            MarbleRule("r1", "amount", MarbleRuleOperator.GT, 100, 30),
        ]
        scenario = self._make_scenario(rules=rules, threshold=50)
        result = scenario.evaluate({"amount": 200})

        assert result.triggered_rules == ["r1"]
        assert result.total_score == 30
        assert result.decision == MarbleDecision.APPROVE

    def test_multiple_rules_score_aggregation(self):
        rules = [
            MarbleRule("r1", "amount", MarbleRuleOperator.GT, 100, 30),
            MarbleRule("r2", "country", MarbleRuleOperator.IN, {"KP"}, 40),
        ]
        scenario = self._make_scenario(rules=rules, threshold=50)
        result = scenario.evaluate({"amount": 200, "country": "KP"})

        assert set(result.triggered_rules) == {"r1", "r2"}
        assert result.total_score == 70
        assert result.decision == MarbleDecision.REVIEW

    def test_inactive_scenario_returns_approve(self):
        rules = [
            MarbleRule("r1", "amount", MarbleRuleOperator.GT, 0, 100),
        ]
        scenario = self._make_scenario(rules=rules, threshold=50, is_active=False)
        result = scenario.evaluate({"amount": 999999})

        assert result.triggered_rules == []
        assert result.total_score == 0
        assert result.decision == MarbleDecision.APPROVE

    def test_evaluated_at_is_set(self):
        scenario = self._make_scenario()
        before = datetime.now(UTC)
        result = scenario.evaluate({})
        after = datetime.now(UTC)

        assert before <= result.evaluated_at <= after


# ============ TestMarbleList ============


class TestMarbleList:
    """Tests for MarbleList."""

    def test_contains_true(self):
        ml = MarbleList("l1", "Blocked Countries", frozenset({"KP", "IR", "SY"}))
        assert ml.contains("KP") is True

    def test_contains_false(self):
        ml = MarbleList("l1", "Blocked Countries", frozenset({"KP", "IR", "SY"}))
        assert ml.contains("US") is False

    def test_empty_list(self):
        ml = MarbleList("l1", "Empty List")
        assert ml.contains("anything") is False

    def test_list_description(self):
        ml = MarbleList("l1", "Test", frozenset(), description="A test list")
        assert ml.description == "A test list"


# ============ TestMarbleDecisionEngine ============


class TestMarbleDecisionEngine:
    """Tests for MarbleDecisionEngine."""

    def test_add_and_get_scenario(self):
        engine = MarbleDecisionEngine()
        scenario = MarbleScenario(
            scenario_id="s1", name="S1", description="",
            trigger_type=MarbleTriggerType.TRANSACTION,
        )
        engine.add_scenario(scenario)
        assert engine.get_scenario("s1") is scenario

    def test_remove_scenario(self):
        engine = MarbleDecisionEngine()
        scenario = MarbleScenario(
            scenario_id="s1", name="S1", description="",
            trigger_type=MarbleTriggerType.TRANSACTION,
        )
        engine.add_scenario(scenario)
        engine.remove_scenario("s1")
        assert engine.get_scenario("s1") is None

    def test_remove_nonexistent_no_error(self):
        engine = MarbleDecisionEngine()
        engine.remove_scenario("nonexistent")  # should not raise

    def test_add_and_get_list(self):
        engine = MarbleDecisionEngine()
        ml = MarbleList("l1", "Test List", frozenset({"a", "b"}))
        engine.add_list(ml)
        assert engine.get_list("l1") is ml

    def test_get_nonexistent_list(self):
        engine = MarbleDecisionEngine()
        assert engine.get_list("nope") is None

    def test_active_scenarios_property(self):
        engine = MarbleDecisionEngine()
        active = MarbleScenario(
            scenario_id="s1", name="Active", description="",
            trigger_type=MarbleTriggerType.TRANSACTION, is_active=True,
        )
        inactive = MarbleScenario(
            scenario_id="s2", name="Inactive", description="",
            trigger_type=MarbleTriggerType.TRANSACTION, is_active=False,
        )
        engine.add_scenario(active)
        engine.add_scenario(inactive)

        actives = engine.active_scenarios
        assert len(actives) == 1
        assert actives[0].scenario_id == "s1"

    def test_scenario_count(self):
        engine = MarbleDecisionEngine()
        assert engine.scenario_count == 0
        engine.add_scenario(MarbleScenario(
            scenario_id="s1", name="S1", description="",
            trigger_type=MarbleTriggerType.TRANSACTION,
        ))
        assert engine.scenario_count == 1

    def test_evaluate_transaction(self):
        engine = MarbleDecisionEngine()
        engine.add_scenario(MarbleScenario(
            scenario_id="hvt",
            name="High Value",
            description="",
            trigger_type=MarbleTriggerType.TRANSACTION,
            rules=[MarbleRule("r1", "amount", MarbleRuleOperator.GT, 10000, 60)],
            score_threshold=50,
            decision_on_match=MarbleDecision.REVIEW,
        ))

        result = engine.evaluate_transaction({"amount": 15000})
        assert result.final_decision == MarbleDecision.REVIEW
        assert result.trigger_type == MarbleTriggerType.TRANSACTION

    def test_evaluate_card_auth(self):
        engine = MarbleDecisionEngine()
        engine.add_scenario(MarbleScenario(
            scenario_id="gambling",
            name="Gambling",
            description="",
            trigger_type=MarbleTriggerType.CARD_AUTH,
            rules=[MarbleRule("r1", "mcc", MarbleRuleOperator.IN, GAMBLING_MCCS, 100)],
            score_threshold=80,
            decision_on_match=MarbleDecision.BLOCK,
        ))

        result = engine.evaluate_card_auth({"mcc": "7995"})
        assert result.final_decision == MarbleDecision.BLOCK

    def test_decision_aggregation_worst_case_wins(self):
        """When multiple scenarios trigger, the most severe decision wins."""
        engine = MarbleDecisionEngine()

        # Scenario 1: REVIEW
        engine.add_scenario(MarbleScenario(
            scenario_id="s1",
            name="Review Scenario",
            description="",
            trigger_type=MarbleTriggerType.TRANSACTION,
            rules=[MarbleRule("r1", "amount", MarbleRuleOperator.GT, 100, 60)],
            score_threshold=50,
            decision_on_match=MarbleDecision.REVIEW,
        ))

        # Scenario 2: BLOCK
        engine.add_scenario(MarbleScenario(
            scenario_id="s2",
            name="Block Scenario",
            description="",
            trigger_type=MarbleTriggerType.TRANSACTION,
            rules=[MarbleRule("r2", "country", MarbleRuleOperator.IN, {"KP"}, 100)],
            score_threshold=80,
            decision_on_match=MarbleDecision.BLOCK,
        ))

        result = engine.evaluate_transaction({"amount": 200, "country": "KP"})
        assert result.final_decision == MarbleDecision.BLOCK

    def test_no_matching_scenarios_returns_approve(self):
        engine = MarbleDecisionEngine()
        # Add a CARD_AUTH scenario but evaluate as TRANSACTION
        engine.add_scenario(MarbleScenario(
            scenario_id="s1",
            name="Card Only",
            description="",
            trigger_type=MarbleTriggerType.CARD_AUTH,
            rules=[MarbleRule("r1", "mcc", MarbleRuleOperator.IN, GAMBLING_MCCS, 100)],
            score_threshold=50,
            decision_on_match=MarbleDecision.BLOCK,
        ))

        result = engine.evaluate_transaction({"mcc": "7995"})
        assert result.final_decision == MarbleDecision.APPROVE
        assert result.scenario_results == []

    def test_default_scenarios_are_created(self):
        defaults = MarbleDecisionEngine.create_default_scenarios()
        assert len(defaults) == 5
        ids = {s.scenario_id for s in defaults}
        assert ids == {
            "high_value_transaction",
            "velocity_check",
            "new_wallet_large_tx",
            "blocked_country",
            "mcc_gambling",
        }

    def test_default_scenarios_high_value_triggers(self):
        engine = create_marble_engine(with_defaults=True)
        result = engine.evaluate_transaction({"amount": 15000})
        assert result.final_decision == MarbleDecision.REVIEW

    def test_default_scenarios_velocity_triggers(self):
        engine = create_marble_engine(with_defaults=True)
        result = engine.evaluate_transaction({"tx_count_1h": 15})
        assert result.final_decision == MarbleDecision.BLOCK_AND_REVIEW

    def test_default_scenarios_blocked_country_triggers(self):
        engine = create_marble_engine(with_defaults=True)
        result = engine.evaluate_transaction({"country": "KP", "amount": 50})
        assert result.final_decision == MarbleDecision.BLOCK

    def test_default_scenarios_gambling_mcc_triggers(self):
        engine = create_marble_engine(with_defaults=True)
        result = engine.evaluate_card_auth({"mcc": "7995"})
        assert result.final_decision == MarbleDecision.BLOCK

    def test_default_scenarios_new_wallet_large_tx_triggers(self):
        engine = create_marble_engine(with_defaults=True)
        result = engine.evaluate_transaction({
            "wallet_age_hours": 2,
            "amount": 5000,
        })
        # new_wallet_large_tx has threshold 50, both rules score 30 each = 60 >= 50
        assert result.final_decision == MarbleDecision.REVIEW

    def test_context_snapshot_is_stored(self):
        engine = create_marble_engine(with_defaults=False)
        context = {"amount": 100, "country": "US"}
        result = engine.evaluate_transaction(context)
        assert result.context_snapshot == context

    def test_context_snapshot_is_copy(self):
        """Modifying original context should not affect snapshot."""
        engine = create_marble_engine(with_defaults=False)
        context = {"amount": 100}
        result = engine.evaluate_transaction(context)
        context["amount"] = 999
        assert result.context_snapshot["amount"] == 100

    def test_total_score_sums_across_scenarios(self):
        engine = MarbleDecisionEngine()
        engine.add_scenario(MarbleScenario(
            scenario_id="s1", name="S1", description="",
            trigger_type=MarbleTriggerType.TRANSACTION,
            rules=[MarbleRule("r1", "amount", MarbleRuleOperator.GT, 100, 30)],
            score_threshold=10,
            decision_on_match=MarbleDecision.REVIEW,
        ))
        engine.add_scenario(MarbleScenario(
            scenario_id="s2", name="S2", description="",
            trigger_type=MarbleTriggerType.TRANSACTION,
            rules=[MarbleRule("r2", "amount", MarbleRuleOperator.GT, 100, 40)],
            score_threshold=10,
            decision_on_match=MarbleDecision.REVIEW,
        ))

        result = engine.evaluate_transaction({"amount": 200})
        assert result.total_score == 70

    def test_evaluate_with_empty_engine(self):
        engine = MarbleDecisionEngine()
        result = engine.evaluate_transaction({"amount": 100})
        assert result.final_decision == MarbleDecision.APPROVE
        assert result.total_score == 0


# ============ TestMarbleDecisionResult ============


class TestMarbleDecisionResult:
    """Tests for MarbleDecisionResult properties."""

    def test_is_blocked_block(self):
        result = MarbleDecisionResult(
            trigger_type=MarbleTriggerType.TRANSACTION,
            final_decision=MarbleDecision.BLOCK,
        )
        assert result.is_blocked is True

    def test_is_blocked_block_and_review(self):
        result = MarbleDecisionResult(
            trigger_type=MarbleTriggerType.TRANSACTION,
            final_decision=MarbleDecision.BLOCK_AND_REVIEW,
        )
        assert result.is_blocked is True

    def test_is_blocked_review(self):
        result = MarbleDecisionResult(
            trigger_type=MarbleTriggerType.TRANSACTION,
            final_decision=MarbleDecision.REVIEW,
        )
        assert result.is_blocked is False

    def test_is_blocked_approve(self):
        result = MarbleDecisionResult(
            trigger_type=MarbleTriggerType.TRANSACTION,
            final_decision=MarbleDecision.APPROVE,
        )
        assert result.is_blocked is False

    def test_requires_review_review(self):
        result = MarbleDecisionResult(
            trigger_type=MarbleTriggerType.TRANSACTION,
            final_decision=MarbleDecision.REVIEW,
        )
        assert result.requires_review is True

    def test_requires_review_block_and_review(self):
        result = MarbleDecisionResult(
            trigger_type=MarbleTriggerType.TRANSACTION,
            final_decision=MarbleDecision.BLOCK_AND_REVIEW,
        )
        assert result.requires_review is True

    def test_requires_review_block(self):
        result = MarbleDecisionResult(
            trigger_type=MarbleTriggerType.TRANSACTION,
            final_decision=MarbleDecision.BLOCK,
        )
        assert result.requires_review is False

    def test_requires_review_approve(self):
        result = MarbleDecisionResult(
            trigger_type=MarbleTriggerType.TRANSACTION,
            final_decision=MarbleDecision.APPROVE,
        )
        assert result.requires_review is False

    def test_triggered_scenario_ids(self):
        result = MarbleDecisionResult(
            trigger_type=MarbleTriggerType.TRANSACTION,
            scenario_results=[
                MarbleScenarioResult("s1", decision=MarbleDecision.REVIEW),
                MarbleScenarioResult("s2", decision=MarbleDecision.APPROVE),
                MarbleScenarioResult("s3", decision=MarbleDecision.BLOCK),
            ],
        )
        assert result.triggered_scenario_ids == ["s1", "s3"]

    def test_triggered_scenario_ids_empty(self):
        result = MarbleDecisionResult(
            trigger_type=MarbleTriggerType.TRANSACTION,
            scenario_results=[
                MarbleScenarioResult("s1", decision=MarbleDecision.APPROVE),
            ],
        )
        assert result.triggered_scenario_ids == []


# ============ TestEnums ============


class TestEnums:
    """Tests for all enum types."""

    def test_marble_decision_values(self):
        assert MarbleDecision.APPROVE.value == "approve"
        assert MarbleDecision.REVIEW.value == "review"
        assert MarbleDecision.BLOCK_AND_REVIEW.value == "block_and_review"
        assert MarbleDecision.BLOCK.value == "block"

    def test_marble_decision_count(self):
        assert len(MarbleDecision) == 4

    def test_marble_trigger_type_values(self):
        assert MarbleTriggerType.TRANSACTION.value == "transaction"
        assert MarbleTriggerType.CARD_AUTH.value == "card_auth"
        assert MarbleTriggerType.WALLET_CREATE.value == "wallet_create"
        assert MarbleTriggerType.POLICY_CHANGE.value == "policy_change"
        assert MarbleTriggerType.LOGIN.value == "login"
        assert MarbleTriggerType.API_CALL.value == "api_call"

    def test_marble_trigger_type_count(self):
        assert len(MarbleTriggerType) == 6

    def test_marble_rule_operator_values(self):
        assert MarbleRuleOperator.GT.value == "gt"
        assert MarbleRuleOperator.GTE.value == "gte"
        assert MarbleRuleOperator.LT.value == "lt"
        assert MarbleRuleOperator.LTE.value == "lte"
        assert MarbleRuleOperator.EQ.value == "eq"
        assert MarbleRuleOperator.NEQ.value == "neq"
        assert MarbleRuleOperator.IN.value == "in"
        assert MarbleRuleOperator.NOT_IN.value == "not_in"
        assert MarbleRuleOperator.CONTAINS.value == "contains"
        assert MarbleRuleOperator.BETWEEN.value == "between"
        assert MarbleRuleOperator.IS_TRUE.value == "is_true"
        assert MarbleRuleOperator.IS_FALSE.value == "is_false"

    def test_marble_rule_operator_count(self):
        assert len(MarbleRuleOperator) == 12

    def test_marble_score_threshold_values(self):
        assert MarbleScoreThreshold.LOW.value == "low"
        assert MarbleScoreThreshold.MEDIUM.value == "medium"
        assert MarbleScoreThreshold.HIGH.value == "high"
        assert MarbleScoreThreshold.CRITICAL.value == "critical"

    def test_marble_score_threshold_count(self):
        assert len(MarbleScoreThreshold) == 4

    def test_enums_are_str(self):
        """All enums should be str subclasses for JSON serialization."""
        assert isinstance(MarbleDecision.APPROVE, str)
        assert isinstance(MarbleTriggerType.TRANSACTION, str)
        assert isinstance(MarbleRuleOperator.GT, str)
        assert isinstance(MarbleScoreThreshold.LOW, str)


# ============ TestConstants ============


class TestConstants:
    """Tests for module-level constants."""

    def test_default_review_threshold(self):
        assert DEFAULT_REVIEW_THRESHOLD == 50

    def test_default_block_threshold(self):
        assert DEFAULT_BLOCK_THRESHOLD == 80

    def test_gambling_mccs(self):
        assert GAMBLING_MCCS == frozenset({"7995", "7801", "7802"})
        assert isinstance(GAMBLING_MCCS, frozenset)

    def test_high_risk_countries(self):
        assert HIGH_RISK_COUNTRIES == frozenset({"KP", "IR", "SY", "CU", "RU"})
        assert isinstance(HIGH_RISK_COUNTRIES, frozenset)


# ============ TestFactory ============


class TestFactory:
    """Tests for factory functions."""

    def test_create_marble_engine_with_defaults(self):
        engine = create_marble_engine(with_defaults=True)
        assert engine.scenario_count == 5

    def test_create_marble_engine_without_defaults(self):
        engine = create_marble_engine(with_defaults=False)
        assert engine.scenario_count == 0

    def test_create_rule_auto_id(self):
        rule = create_rule("amount", MarbleRuleOperator.GT, 100, 50, "Test rule")
        assert rule.rule_id.startswith("rule_")
        assert len(rule.rule_id) == 17  # "rule_" + 12 hex chars
        assert rule.field == "amount"
        assert rule.operator == MarbleRuleOperator.GT
        assert rule.value == 100
        assert rule.score == 50
        assert rule.description == "Test rule"
        assert rule.is_active is True

    def test_create_rule_unique_ids(self):
        r1 = create_rule("a", MarbleRuleOperator.GT, 1, 10)
        r2 = create_rule("a", MarbleRuleOperator.GT, 1, 10)
        assert r1.rule_id != r2.rule_id


# ============ TestModuleExports ============


class TestModuleExports:
    """Tests for sardis_compliance package exports."""

    def test_import_from_sardis_compliance(self):
        from sardis_compliance import (
            MarbleDecision,
            MarbleDecisionEngine,
            MarbleDecisionResult,
            MarbleList,
            MarbleRule,
            MarbleRuleOperator,
            MarbleScenario,
            MarbleScenarioResult,
            MarbleScoreThreshold,
            MarbleTriggerType,
            create_marble_engine,
            create_rule,
        )
        # Just verify they are importable; the rest of the tests verify behavior
        assert MarbleDecision is not None
        assert MarbleDecisionEngine is not None
        assert MarbleDecisionResult is not None
        assert MarbleList is not None
        assert MarbleRule is not None
        assert MarbleRuleOperator is not None
        assert MarbleScenario is not None
        assert MarbleScenarioResult is not None
        assert MarbleScoreThreshold is not None
        assert MarbleTriggerType is not None
        assert create_marble_engine is not None
        assert create_rule is not None
