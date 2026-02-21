"""Alert rules engine for real-time spending alerts."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Alert types."""
    PAYMENT_EXECUTED = "payment_executed"
    POLICY_VIOLATION = "policy_violation"
    BUDGET_THRESHOLD = "budget_threshold"
    CARD_STATUS_CHANGE = "card_status_change"
    KYA_LEVEL_CHANGE = "kya_level_change"
    HIGH_FREQUENCY = "high_frequency"
    COMPLIANCE_ALERT = "compliance_alert"
    WALLET_CREATED = "wallet_created"


class ConditionType(str, Enum):
    """Alert condition types."""
    AMOUNT_EXCEEDS = "amount_exceeds"
    BUDGET_PERCENTAGE = "budget_percentage"
    TRANSACTION_COUNT = "transaction_count"
    STATUS_CHANGE = "status_change"
    POLICY_BLOCKED = "policy_blocked"
    LEVEL_CHANGE = "level_change"


@dataclass
class Alert:
    """Individual alert instance."""
    id: str = field(default_factory=lambda: f"alert_{uuid.uuid4().hex[:16]}")
    alert_type: AlertType = AlertType.PAYMENT_EXECUTED
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    agent_id: Optional[str] = None
    organization_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary for serialization."""
        return {
            "id": self.id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "agent_id": self.agent_id,
            "organization_id": self.organization_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


@dataclass
class AlertRule:
    """Alert rule configuration."""
    id: str = field(default_factory=lambda: f"rule_{uuid.uuid4().hex[:16]}")
    name: str = ""
    condition_type: ConditionType = ConditionType.AMOUNT_EXCEEDS
    threshold: Optional[Decimal] = None
    channels: list[str] = field(default_factory=list)
    enabled: bool = True
    organization_id: Optional[str] = None
    agent_id: Optional[str] = None  # If set, only applies to specific agent
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert rule to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "condition_type": self.condition_type.value,
            "threshold": str(self.threshold) if self.threshold else None,
            "channels": self.channels,
            "enabled": self.enabled,
            "organization_id": self.organization_id,
            "agent_id": self.agent_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class AlertRuleEngine:
    """Evaluates events against alert rules and generates alerts."""

    def __init__(self) -> None:
        self.rules: dict[str, AlertRule] = {}
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default system alert rules."""
        # Budget threshold alerts (50%, 75%, 90%, 100%)
        for percentage in [50, 75, 90, 100]:
            severity = AlertSeverity.INFO
            if percentage >= 75:
                severity = AlertSeverity.WARNING
            if percentage >= 90:
                severity = AlertSeverity.CRITICAL

            rule = AlertRule(
                name=f"Budget {percentage}% threshold",
                condition_type=ConditionType.BUDGET_PERCENTAGE,
                threshold=Decimal(str(percentage)),
                channels=["websocket", "email"],
                enabled=True,
                metadata={"default": True, "percentage": percentage},
            )
            self.rules[rule.id] = rule

        # High-value transaction alert
        rule = AlertRule(
            name="High-value transaction",
            condition_type=ConditionType.AMOUNT_EXCEEDS,
            threshold=Decimal("1000.00"),
            channels=["websocket", "slack"],
            enabled=True,
            metadata={"default": True},
        )
        self.rules[rule.id] = rule

        # Policy violation alert
        rule = AlertRule(
            name="Policy violation",
            condition_type=ConditionType.POLICY_BLOCKED,
            channels=["websocket", "email"],
            enabled=True,
            metadata={"default": True},
        )
        self.rules[rule.id] = rule

        # High frequency alert (more than 10 transactions in 5 minutes)
        rule = AlertRule(
            name="High transaction frequency",
            condition_type=ConditionType.TRANSACTION_COUNT,
            threshold=Decimal("10"),
            channels=["websocket", "slack"],
            enabled=True,
            metadata={"default": True, "window_seconds": 300},
        )
        self.rules[rule.id] = rule

    def add_rule(self, rule: AlertRule) -> None:
        """Add a new alert rule."""
        self.rules[rule.id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get a specific alert rule."""
        return self.rules.get(rule_id)

    def list_rules(
        self,
        organization_id: Optional[str] = None,
        enabled_only: bool = False,
    ) -> list[AlertRule]:
        """List all alert rules, optionally filtered."""
        rules = list(self.rules.values())

        if organization_id:
            rules = [
                r for r in rules
                if r.organization_id == organization_id or r.organization_id is None
            ]

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return rules

    def evaluate(self, event: dict[str, Any]) -> list[Alert]:
        """
        Evaluate an event against all active rules.

        Args:
            event: Event data dictionary with keys:
                - event_type: str (payment_executed, policy_violation, etc.)
                - agent_id: str
                - organization_id: str
                - amount: Decimal (for payment events)
                - budget_used: Decimal (for budget threshold checks)
                - budget_total: Decimal (for budget threshold checks)
                - transaction_count: int (for frequency checks)
                - status: str (for status change events)
                - kya_level: str (for KYA events)
                - Any other relevant data

        Returns:
            List of alerts generated from matching rules
        """
        alerts: list[Alert] = []
        event_type = event.get("event_type", "")
        agent_id = event.get("agent_id")
        organization_id = event.get("organization_id")

        # Filter rules applicable to this event
        applicable_rules = [
            r for r in self.rules.values()
            if r.enabled
            and (r.organization_id is None or r.organization_id == organization_id)
            and (r.agent_id is None or r.agent_id == agent_id)
        ]

        for rule in applicable_rules:
            alert = self._evaluate_rule(rule, event)
            if alert:
                alerts.append(alert)

        return alerts

    def _evaluate_rule(self, rule: AlertRule, event: dict[str, Any]) -> Optional[Alert]:
        """Evaluate a single rule against an event."""
        event_type = event.get("event_type", "")

        # Payment executed - check amount threshold
        if (
            rule.condition_type == ConditionType.AMOUNT_EXCEEDS
            and event_type == "payment_executed"
        ):
            amount = event.get("amount")
            if amount and rule.threshold and Decimal(str(amount)) > rule.threshold:
                return Alert(
                    alert_type=AlertType.PAYMENT_EXECUTED,
                    severity=AlertSeverity.WARNING,
                    message=f"High-value payment of ${amount} executed (threshold: ${rule.threshold})",
                    agent_id=event.get("agent_id"),
                    organization_id=event.get("organization_id"),
                    data={
                        "amount": str(amount),
                        "threshold": str(rule.threshold),
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        **{k: v for k, v in event.items() if k not in ["event_type"]},
                    },
                )

        # Policy violation
        if (
            rule.condition_type == ConditionType.POLICY_BLOCKED
            and event_type == "policy_violation"
        ):
            return Alert(
                alert_type=AlertType.POLICY_VIOLATION,
                severity=AlertSeverity.CRITICAL,
                message=event.get("message", "Policy violation detected"),
                agent_id=event.get("agent_id"),
                organization_id=event.get("organization_id"),
                data={
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "violation_reason": event.get("reason", "unknown"),
                    **{k: v for k, v in event.items() if k not in ["event_type"]},
                },
            )

        # Budget threshold
        if (
            rule.condition_type == ConditionType.BUDGET_PERCENTAGE
            and event_type in ["payment_executed", "budget_check"]
        ):
            budget_used = event.get("budget_used")
            budget_total = event.get("budget_total")

            if budget_used and budget_total:
                used_decimal = Decimal(str(budget_used))
                total_decimal = Decimal(str(budget_total))

                if total_decimal > 0:
                    percentage = (used_decimal / total_decimal) * 100
                    threshold_pct = rule.threshold or Decimal("50")

                    # Only alert when crossing threshold (check metadata for last alert)
                    if percentage >= threshold_pct:
                        severity = AlertSeverity.INFO
                        if percentage >= 75:
                            severity = AlertSeverity.WARNING
                        if percentage >= 90:
                            severity = AlertSeverity.CRITICAL

                        return Alert(
                            alert_type=AlertType.BUDGET_THRESHOLD,
                            severity=severity,
                            message=f"Budget at {percentage:.1f}% (${used_decimal} of ${total_decimal})",
                            agent_id=event.get("agent_id"),
                            organization_id=event.get("organization_id"),
                            data={
                                "budget_used": str(used_decimal),
                                "budget_total": str(total_decimal),
                                "percentage": float(percentage),
                                "threshold": float(threshold_pct),
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                            },
                        )

        # High frequency (transaction count)
        if (
            rule.condition_type == ConditionType.TRANSACTION_COUNT
            and event_type == "high_frequency"
        ):
            count = event.get("transaction_count", 0)
            threshold = rule.threshold or Decimal("10")

            if count >= int(threshold):
                window = rule.metadata.get("window_seconds", 300)
                return Alert(
                    alert_type=AlertType.HIGH_FREQUENCY,
                    severity=AlertSeverity.WARNING,
                    message=f"High transaction frequency: {count} transactions in {window}s (threshold: {int(threshold)})",
                    agent_id=event.get("agent_id"),
                    organization_id=event.get("organization_id"),
                    data={
                        "transaction_count": count,
                        "threshold": int(threshold),
                        "window_seconds": window,
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                    },
                )

        # Card status change
        if (
            rule.condition_type == ConditionType.STATUS_CHANGE
            and event_type == "card_status_change"
        ):
            status = event.get("status", "")
            severity = AlertSeverity.INFO
            if status in ["frozen", "cancelled"]:
                severity = AlertSeverity.WARNING

            return Alert(
                alert_type=AlertType.CARD_STATUS_CHANGE,
                severity=severity,
                message=f"Card status changed to: {status}",
                agent_id=event.get("agent_id"),
                organization_id=event.get("organization_id"),
                data={
                    "status": status,
                    "card_id": event.get("card_id"),
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                },
            )

        # KYA level change
        if (
            rule.condition_type == ConditionType.LEVEL_CHANGE
            and event_type == "kya_level_change"
        ):
            old_level = event.get("old_level", "")
            new_level = event.get("new_level", "")

            # Determine severity based on change direction
            severity = AlertSeverity.INFO
            if new_level in ["verified", "attested"]:
                severity = AlertSeverity.INFO  # Upgrade is positive
            elif old_level in ["verified", "attested"] and new_level == "basic":
                severity = AlertSeverity.WARNING  # Downgrade is concerning

            return Alert(
                alert_type=AlertType.KYA_LEVEL_CHANGE,
                severity=severity,
                message=f"KYA level changed from {old_level} to {new_level}",
                agent_id=event.get("agent_id"),
                organization_id=event.get("organization_id"),
                data={
                    "old_level": old_level,
                    "new_level": new_level,
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                },
            )

        return None
