"""Marble (CheckMarble) evaluation framework for fraud rule scoring.

Implements an offline decision engine inspired by CheckMarble's architecture
for real-time scenario-based fraud scoring with case management. Key concepts:

- **Rules**: Individual conditions evaluated against a transaction context
- **Scenarios**: Groups of rules triggered by specific event types
- **Decisions**: Outcome of evaluation (approve / review / block)
- **Lists**: Named value sets for blocklist/allowlist matching
- **Triggers**: Event types that activate scenario evaluation

This is NOT a direct CheckMarble API integration — it is a standalone
evaluation engine that follows Marble's decision-engine pattern.

Reference: https://www.checkmarble.com (BSL license, Go/TS)
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ============ Enums ============


class MarbleDecision(str, Enum):
    """Decision outcome from scenario evaluation."""
    APPROVE = "approve"
    REVIEW = "review"
    BLOCK_AND_REVIEW = "block_and_review"
    BLOCK = "block"


class MarbleTriggerType(str, Enum):
    """Event types that trigger scenario evaluation."""
    TRANSACTION = "transaction"
    CARD_AUTH = "card_auth"
    WALLET_CREATE = "wallet_create"
    POLICY_CHANGE = "policy_change"
    LOGIN = "login"
    API_CALL = "api_call"


class MarbleRuleOperator(str, Enum):
    """Comparison operators for rule evaluation."""
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    BETWEEN = "between"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


class MarbleScoreThreshold(str, Enum):
    """Named score threshold tiers."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============ Constants ============

DEFAULT_REVIEW_THRESHOLD = 50
DEFAULT_BLOCK_THRESHOLD = 80

GAMBLING_MCCS: frozenset[str] = frozenset({"7995", "7801", "7802"})
HIGH_RISK_COUNTRIES: frozenset[str] = frozenset({"KP", "IR", "SY", "CU", "RU"})

# Decision severity ordering (higher index = more severe)
_DECISION_SEVERITY: dict[MarbleDecision, int] = {
    MarbleDecision.APPROVE: 0,
    MarbleDecision.REVIEW: 1,
    MarbleDecision.BLOCK_AND_REVIEW: 2,
    MarbleDecision.BLOCK: 3,
}


# ============ Data Classes ============


@dataclass
class MarbleList:
    """Named value set for blocklist/allowlist matching.

    Uses frozenset for immutable, hashable value storage.
    """
    list_id: str
    name: str
    values: frozenset[str] = field(default_factory=frozenset)
    description: str = ""

    def contains(self, value: str) -> bool:
        """Check if a value exists in this list."""
        return value in self.values


@dataclass
class MarbleRule:
    """Individual fraud detection rule.

    Evaluates a single condition against a context dictionary using
    the specified operator. Score (0-100) indicates severity weight
    when the rule triggers.
    """
    rule_id: str
    field: str
    operator: MarbleRuleOperator
    value: Any
    score: int  # 0-100
    description: str = ""
    is_active: bool = True

    def evaluate(self, context: dict) -> bool:
        """Evaluate this rule against a context dictionary.

        Returns True if the rule condition is met (rule triggers).
        Returns False if the field is missing from context or the
        condition is not met, or if the rule is inactive.
        """
        if not self.is_active:
            return False

        # IS_TRUE / IS_FALSE do not require the field to exist with a
        # specific value — they check truthiness of the field value.
        if self.field not in context:
            return False

        ctx_value = context[self.field]

        try:
            return self._apply_operator(ctx_value)
        except (TypeError, ValueError):
            logger.warning(
                "Rule %s: operator %s failed for field '%s' (value=%r)",
                self.rule_id, self.operator.value, self.field, ctx_value,
            )
            return False

    def _apply_operator(self, ctx_value: Any) -> bool:
        """Apply the operator comparison."""
        op = self.operator

        if op == MarbleRuleOperator.GT:
            return ctx_value > self.value
        elif op == MarbleRuleOperator.GTE:
            return ctx_value >= self.value
        elif op == MarbleRuleOperator.LT:
            return ctx_value < self.value
        elif op == MarbleRuleOperator.LTE:
            return ctx_value <= self.value
        elif op == MarbleRuleOperator.EQ:
            return ctx_value == self.value
        elif op == MarbleRuleOperator.NEQ:
            return ctx_value != self.value
        elif op == MarbleRuleOperator.IN:
            return ctx_value in self.value
        elif op == MarbleRuleOperator.NOT_IN:
            return ctx_value not in self.value
        elif op == MarbleRuleOperator.CONTAINS:
            return self.value in ctx_value
        elif op == MarbleRuleOperator.BETWEEN:
            low, high = self.value
            return low <= ctx_value <= high
        elif op == MarbleRuleOperator.IS_TRUE:
            return bool(ctx_value) is True
        elif op == MarbleRuleOperator.IS_FALSE:
            return bool(ctx_value) is False

        return False


@dataclass
class MarbleScenarioResult:
    """Result of evaluating a single scenario."""
    scenario_id: str
    triggered_rules: list[str] = field(default_factory=list)
    total_score: int = 0
    decision: MarbleDecision = MarbleDecision.APPROVE
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MarbleScenario:
    """A group of rules evaluated together for a specific trigger type.

    When a scenario is evaluated, all active rules are checked against
    the context. The total score is the sum of triggered rule scores.
    If the total score meets or exceeds `score_threshold`, the scenario
    returns `decision_on_match`; otherwise APPROVE.
    """
    scenario_id: str
    name: str
    description: str
    trigger_type: MarbleTriggerType
    rules: list[MarbleRule] = field(default_factory=list)
    score_threshold: int = DEFAULT_REVIEW_THRESHOLD
    decision_on_match: MarbleDecision = MarbleDecision.REVIEW
    is_active: bool = True
    version: int = 1

    def evaluate(self, context: dict) -> MarbleScenarioResult:
        """Evaluate all rules in this scenario against the context.

        Returns a MarbleScenarioResult with triggered rules, total score,
        and the resulting decision. If the scenario is inactive, returns
        an APPROVE result with zero score.
        """
        if not self.is_active:
            return MarbleScenarioResult(
                scenario_id=self.scenario_id,
                decision=MarbleDecision.APPROVE,
            )

        triggered_rules: list[str] = []
        total_score = 0

        for rule in self.rules:
            if rule.evaluate(context):
                triggered_rules.append(rule.rule_id)
                total_score += rule.score

        decision = (
            self.decision_on_match
            if total_score >= self.score_threshold
            else MarbleDecision.APPROVE
        )

        return MarbleScenarioResult(
            scenario_id=self.scenario_id,
            triggered_rules=triggered_rules,
            total_score=total_score,
            decision=decision,
        )


@dataclass
class MarbleDecisionResult:
    """Aggregated result across all evaluated scenarios.

    The final_decision is the most severe decision from any triggered
    scenario. Severity order: APPROVE < REVIEW < BLOCK_AND_REVIEW < BLOCK.
    """
    trigger_type: MarbleTriggerType
    scenario_results: list[MarbleScenarioResult] = field(default_factory=list)
    final_decision: MarbleDecision = MarbleDecision.APPROVE
    total_score: int = 0
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    context_snapshot: dict = field(default_factory=dict)

    @property
    def is_blocked(self) -> bool:
        """True if the final decision is BLOCK or BLOCK_AND_REVIEW."""
        return self.final_decision in (
            MarbleDecision.BLOCK,
            MarbleDecision.BLOCK_AND_REVIEW,
        )

    @property
    def requires_review(self) -> bool:
        """True if the final decision requires human review."""
        return self.final_decision in (
            MarbleDecision.REVIEW,
            MarbleDecision.BLOCK_AND_REVIEW,
        )

    @property
    def triggered_scenario_ids(self) -> list[str]:
        """IDs of scenarios that produced a non-APPROVE decision."""
        return [
            r.scenario_id
            for r in self.scenario_results
            if r.decision != MarbleDecision.APPROVE
        ]


# ============ Decision Engine ============


class MarbleDecisionEngine:
    """Core Marble decision engine for fraud rule evaluation.

    Manages scenarios and lists, evaluates transaction contexts against
    matching scenarios, and aggregates results using worst-case decision
    logic.

    Usage::

        engine = create_marble_engine(with_defaults=True)
        result = engine.evaluate_transaction({
            "amount": 15000,
            "country": "US",
            "tx_count_1h": 3,
        })
        if result.is_blocked:
            # handle blocked transaction
            ...
    """

    def __init__(
        self,
        scenarios: list[MarbleScenario] | None = None,
        lists: list[MarbleList] | None = None,
    ) -> None:
        self._scenarios: dict[str, MarbleScenario] = {}
        self._lists: dict[str, MarbleList] = {}

        for scenario in (scenarios or []):
            self._scenarios[scenario.scenario_id] = scenario
        for marble_list in (lists or []):
            self._lists[marble_list.list_id] = marble_list

    # --- Scenario management ---

    def add_scenario(self, scenario: MarbleScenario) -> None:
        """Add a scenario to the engine."""
        self._scenarios[scenario.scenario_id] = scenario
        logger.debug("Added scenario %s (%s)", scenario.scenario_id, scenario.name)

    def remove_scenario(self, scenario_id: str) -> None:
        """Remove a scenario by ID. No-op if not found."""
        self._scenarios.pop(scenario_id, None)

    def get_scenario(self, scenario_id: str) -> MarbleScenario | None:
        """Get a scenario by ID."""
        return self._scenarios.get(scenario_id)

    # --- List management ---

    def add_list(self, marble_list: MarbleList) -> None:
        """Add a named list to the engine."""
        self._lists[marble_list.list_id] = marble_list

    def get_list(self, list_id: str) -> MarbleList | None:
        """Get a list by ID."""
        return self._lists.get(list_id)

    # --- Properties ---

    @property
    def active_scenarios(self) -> list[MarbleScenario]:
        """Return all active scenarios."""
        return [s for s in self._scenarios.values() if s.is_active]

    @property
    def scenario_count(self) -> int:
        """Total number of scenarios (active and inactive)."""
        return len(self._scenarios)

    # --- Evaluation ---

    def evaluate(
        self,
        trigger_type: MarbleTriggerType,
        context: dict,
    ) -> MarbleDecisionResult:
        """Evaluate all active scenarios matching the trigger type.

        Args:
            trigger_type: The event type that triggered evaluation.
            context: Dictionary of contextual data for rule evaluation.

        Returns:
            MarbleDecisionResult with aggregated scores and worst-case decision.
        """
        matching_scenarios = [
            s for s in self._scenarios.values()
            if s.is_active and s.trigger_type == trigger_type
        ]

        scenario_results: list[MarbleScenarioResult] = []
        total_score = 0
        worst_decision = MarbleDecision.APPROVE

        for scenario in matching_scenarios:
            result = scenario.evaluate(context)
            scenario_results.append(result)
            total_score += result.total_score

            if _DECISION_SEVERITY[result.decision] > _DECISION_SEVERITY[worst_decision]:
                worst_decision = result.decision

        return MarbleDecisionResult(
            trigger_type=trigger_type,
            scenario_results=scenario_results,
            final_decision=worst_decision,
            total_score=total_score,
            context_snapshot=dict(context),
        )

    def evaluate_transaction(self, tx_context: dict) -> MarbleDecisionResult:
        """Convenience method for evaluating TRANSACTION triggers."""
        return self.evaluate(MarbleTriggerType.TRANSACTION, tx_context)

    def evaluate_card_auth(self, auth_context: dict) -> MarbleDecisionResult:
        """Convenience method for evaluating CARD_AUTH triggers."""
        return self.evaluate(MarbleTriggerType.CARD_AUTH, auth_context)

    # --- Default scenarios ---

    @staticmethod
    def create_default_scenarios() -> list[MarbleScenario]:
        """Create built-in fraud detection scenarios.

        Returns a set of production-ready scenarios covering common
        fraud patterns: high-value transactions, velocity abuse,
        new-wallet risk, blocked countries, and gambling MCCs.
        """
        scenarios: list[MarbleScenario] = []

        # 1. High-value transaction
        scenarios.append(MarbleScenario(
            scenario_id="high_value_transaction",
            name="High Value Transaction",
            description="Flag transactions above $10,000 for review",
            trigger_type=MarbleTriggerType.TRANSACTION,
            rules=[
                MarbleRule(
                    rule_id="hvt_amount_gt_10k",
                    field="amount",
                    operator=MarbleRuleOperator.GT,
                    value=10000,
                    score=60,
                    description="Transaction amount exceeds $10,000",
                ),
            ],
            score_threshold=DEFAULT_REVIEW_THRESHOLD,
            decision_on_match=MarbleDecision.REVIEW,
        ))

        # 2. Velocity check
        scenarios.append(MarbleScenario(
            scenario_id="velocity_check",
            name="Velocity Check",
            description="Block accounts with excessive transaction frequency",
            trigger_type=MarbleTriggerType.TRANSACTION,
            rules=[
                MarbleRule(
                    rule_id="vel_tx_count_1h",
                    field="tx_count_1h",
                    operator=MarbleRuleOperator.GT,
                    value=10,
                    score=90,
                    description="More than 10 transactions in 1 hour",
                ),
            ],
            score_threshold=DEFAULT_BLOCK_THRESHOLD,
            decision_on_match=MarbleDecision.BLOCK_AND_REVIEW,
        ))

        # 3. New wallet + large transaction
        scenarios.append(MarbleScenario(
            scenario_id="new_wallet_large_tx",
            name="New Wallet Large Transaction",
            description="Review large transactions from recently created wallets",
            trigger_type=MarbleTriggerType.TRANSACTION,
            rules=[
                MarbleRule(
                    rule_id="nwlt_wallet_age",
                    field="wallet_age_hours",
                    operator=MarbleRuleOperator.LT,
                    value=24,
                    score=30,
                    description="Wallet created less than 24 hours ago",
                ),
                MarbleRule(
                    rule_id="nwlt_amount",
                    field="amount",
                    operator=MarbleRuleOperator.GT,
                    value=1000,
                    score=30,
                    description="Transaction amount exceeds $1,000",
                ),
            ],
            score_threshold=DEFAULT_REVIEW_THRESHOLD,
            decision_on_match=MarbleDecision.REVIEW,
        ))

        # 4. Blocked country
        scenarios.append(MarbleScenario(
            scenario_id="blocked_country",
            name="Blocked Country",
            description="Block transactions from sanctioned countries",
            trigger_type=MarbleTriggerType.TRANSACTION,
            rules=[
                MarbleRule(
                    rule_id="bc_country_in",
                    field="country",
                    operator=MarbleRuleOperator.IN,
                    value=HIGH_RISK_COUNTRIES,
                    score=100,
                    description="Country is on the blocked list",
                ),
            ],
            score_threshold=DEFAULT_BLOCK_THRESHOLD,
            decision_on_match=MarbleDecision.BLOCK,
        ))

        # 5. Gambling MCC
        scenarios.append(MarbleScenario(
            scenario_id="mcc_gambling",
            name="Gambling MCC",
            description="Block card transactions at gambling merchants",
            trigger_type=MarbleTriggerType.CARD_AUTH,
            rules=[
                MarbleRule(
                    rule_id="mcc_gambling_in",
                    field="mcc",
                    operator=MarbleRuleOperator.IN,
                    value=GAMBLING_MCCS,
                    score=100,
                    description="MCC is in the gambling category",
                ),
            ],
            score_threshold=DEFAULT_BLOCK_THRESHOLD,
            decision_on_match=MarbleDecision.BLOCK,
        ))

        return scenarios


# ============ Factory Functions ============


def create_marble_engine(with_defaults: bool = True) -> MarbleDecisionEngine:
    """Factory function to create a MarbleDecisionEngine.

    Args:
        with_defaults: If True, loads built-in fraud scenarios.

    Returns:
        Configured MarbleDecisionEngine instance.
    """
    scenarios = MarbleDecisionEngine.create_default_scenarios() if with_defaults else []
    return MarbleDecisionEngine(scenarios=scenarios)


def create_rule(
    field: str,
    operator: MarbleRuleOperator,
    value: Any,
    score: int,
    description: str = "",
) -> MarbleRule:
    """Helper to create a MarbleRule with an auto-generated ID.

    Args:
        field: Context dictionary key to evaluate.
        operator: Comparison operator.
        value: Value to compare against.
        score: Score (0-100) when rule triggers.
        description: Human-readable description.

    Returns:
        New MarbleRule instance.
    """
    return MarbleRule(
        rule_id=f"rule_{uuid.uuid4().hex[:12]}",
        field=field,
        operator=operator,
        value=value,
        score=score,
        description=description,
    )
