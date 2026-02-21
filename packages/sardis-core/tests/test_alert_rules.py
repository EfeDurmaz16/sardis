"""Tests for alert rules engine."""
import pytest
from decimal import Decimal

from sardis_v2_core.alert_rules import (
    Alert,
    AlertRule,
    AlertRuleEngine,
    AlertSeverity,
    AlertType,
    ConditionType,
)


def test_alert_creation():
    """Test creating an alert."""
    alert = Alert(
        alert_type=AlertType.PAYMENT_EXECUTED,
        severity=AlertSeverity.INFO,
        message="Test alert",
        agent_id="agent_123",
        organization_id="org_456",
        data={"amount": "100.00"},
    )

    assert alert.alert_type == AlertType.PAYMENT_EXECUTED
    assert alert.severity == AlertSeverity.INFO
    assert alert.message == "Test alert"
    assert alert.agent_id == "agent_123"
    assert alert.organization_id == "org_456"
    assert alert.data["amount"] == "100.00"


def test_alert_to_dict():
    """Test alert serialization."""
    alert = Alert(
        alert_type=AlertType.PAYMENT_EXECUTED,
        severity=AlertSeverity.WARNING,
        message="High value payment",
        agent_id="agent_123",
        data={"amount": "1500.00"},
    )

    alert_dict = alert.to_dict()

    assert alert_dict["alert_type"] == "payment_executed"
    assert alert_dict["severity"] == "warning"
    assert alert_dict["message"] == "High value payment"
    assert alert_dict["agent_id"] == "agent_123"
    assert alert_dict["data"]["amount"] == "1500.00"


def test_alert_rule_creation():
    """Test creating an alert rule."""
    rule = AlertRule(
        name="High value transactions",
        condition_type=ConditionType.AMOUNT_EXCEEDS,
        threshold=Decimal("1000.00"),
        channels=["websocket", "slack"],
        enabled=True,
    )

    assert rule.name == "High value transactions"
    assert rule.condition_type == ConditionType.AMOUNT_EXCEEDS
    assert rule.threshold == Decimal("1000.00")
    assert "websocket" in rule.channels
    assert rule.enabled is True


def test_rule_engine_initialization():
    """Test rule engine initializes with default rules."""
    engine = AlertRuleEngine()

    assert len(engine.rules) > 0

    # Check default budget threshold rules exist
    budget_rules = [
        r for r in engine.rules.values()
        if r.condition_type == ConditionType.BUDGET_PERCENTAGE
    ]
    assert len(budget_rules) == 4  # 50%, 75%, 90%, 100%


def test_rule_engine_add_rule():
    """Test adding a custom rule."""
    engine = AlertRuleEngine()
    initial_count = len(engine.rules)

    rule = AlertRule(
        name="Custom rule",
        condition_type=ConditionType.AMOUNT_EXCEEDS,
        threshold=Decimal("500.00"),
        channels=["email"],
    )

    engine.add_rule(rule)

    assert len(engine.rules) == initial_count + 1
    assert engine.get_rule(rule.id) == rule


def test_rule_engine_remove_rule():
    """Test removing a rule."""
    engine = AlertRuleEngine()

    rule = AlertRule(
        name="Temporary rule",
        condition_type=ConditionType.AMOUNT_EXCEEDS,
        threshold=Decimal("100.00"),
    )

    engine.add_rule(rule)
    assert rule.id in engine.rules

    removed = engine.remove_rule(rule.id)
    assert removed is True
    assert rule.id not in engine.rules


def test_evaluate_amount_exceeds():
    """Test evaluating amount_exceeds condition."""
    engine = AlertRuleEngine()

    # Add custom rule
    rule = AlertRule(
        name="Test rule",
        condition_type=ConditionType.AMOUNT_EXCEEDS,
        threshold=Decimal("1000.00"),
        channels=["websocket"],
    )
    engine.add_rule(rule)

    # Event that exceeds threshold
    event = {
        "event_type": "payment_executed",
        "amount": Decimal("1500.00"),
        "agent_id": "agent_123",
        "organization_id": "org_456",
    }

    alerts = engine.evaluate(event)

    # Should generate alerts (from default rule + custom rule)
    assert len(alerts) > 0
    high_value_alerts = [a for a in alerts if a.alert_type == AlertType.PAYMENT_EXECUTED]
    assert len(high_value_alerts) > 0


def test_evaluate_budget_threshold():
    """Test evaluating budget_percentage condition."""
    engine = AlertRuleEngine()

    # Event at 90% budget
    event = {
        "event_type": "payment_executed",
        "budget_used": Decimal("9000.00"),
        "budget_total": Decimal("10000.00"),
        "agent_id": "agent_123",
        "organization_id": "org_456",
    }

    alerts = engine.evaluate(event)

    # Should trigger 50%, 75%, and 90% alerts
    budget_alerts = [a for a in alerts if a.alert_type == AlertType.BUDGET_THRESHOLD]
    assert len(budget_alerts) > 0

    # Check that critical severity is used for 90%
    critical_alerts = [a for a in budget_alerts if a.severity == AlertSeverity.CRITICAL]
    assert len(critical_alerts) > 0


def test_evaluate_policy_violation():
    """Test evaluating policy_blocked condition."""
    engine = AlertRuleEngine()

    event = {
        "event_type": "policy_violation",
        "message": "Merchant not in allowlist",
        "reason": "blocked_merchant",
        "agent_id": "agent_123",
        "organization_id": "org_456",
    }

    alerts = engine.evaluate(event)

    # Should generate policy violation alert
    policy_alerts = [a for a in alerts if a.alert_type == AlertType.POLICY_VIOLATION]
    assert len(policy_alerts) > 0
    assert policy_alerts[0].severity == AlertSeverity.CRITICAL


def test_evaluate_high_frequency():
    """Test evaluating transaction_count condition."""
    engine = AlertRuleEngine()

    event = {
        "event_type": "high_frequency",
        "transaction_count": 15,
        "agent_id": "agent_123",
        "organization_id": "org_456",
    }

    alerts = engine.evaluate(event)

    # Should generate high frequency alert
    freq_alerts = [a for a in alerts if a.alert_type == AlertType.HIGH_FREQUENCY]
    assert len(freq_alerts) > 0
    assert freq_alerts[0].severity == AlertSeverity.WARNING


def test_list_rules_filter_organization():
    """Test filtering rules by organization."""
    engine = AlertRuleEngine()

    # Add organization-specific rule
    org_rule = AlertRule(
        name="Org rule",
        condition_type=ConditionType.AMOUNT_EXCEEDS,
        threshold=Decimal("100.00"),
        organization_id="org_123",
    )
    engine.add_rule(org_rule)

    # List rules for org_123
    org_rules = engine.list_rules(organization_id="org_123")

    # Should include default rules (no org_id) and org-specific rule
    assert len(org_rules) > 0
    assert any(r.id == org_rule.id for r in org_rules)


def test_list_rules_enabled_only():
    """Test filtering rules by enabled status."""
    engine = AlertRuleEngine()

    # Add disabled rule
    disabled_rule = AlertRule(
        name="Disabled rule",
        condition_type=ConditionType.AMOUNT_EXCEEDS,
        threshold=Decimal("100.00"),
        enabled=False,
    )
    engine.add_rule(disabled_rule)

    # List enabled rules only
    enabled_rules = engine.list_rules(enabled_only=True)

    # Should not include disabled rule
    assert all(r.enabled for r in enabled_rules)
    assert not any(r.id == disabled_rule.id for r in enabled_rules)


def test_rule_agent_id_filter():
    """Test that rules can be filtered by agent_id."""
    engine = AlertRuleEngine()

    # Add agent-specific rule
    agent_rule = AlertRule(
        name="Agent rule",
        condition_type=ConditionType.AMOUNT_EXCEEDS,
        threshold=Decimal("100.00"),
        agent_id="agent_123",
    )
    engine.add_rule(agent_rule)

    # Event from different agent
    event = {
        "event_type": "payment_executed",
        "amount": Decimal("150.00"),
        "agent_id": "agent_456",
        "organization_id": "org_789",
    }

    alerts = engine.evaluate(event)

    # Agent-specific rule should not trigger for different agent
    # (though default rules might still trigger)
    agent_specific_alerts = [
        a for a in alerts
        if a.data.get("rule_id") == agent_rule.id
    ]
    assert len(agent_specific_alerts) == 0
