"""Operational alert dispatching for critical system events.

Initializes AlertDispatcher with Slack/PagerDuty channels from env vars
and exposes helper functions for common operational alerts.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from sardis_v2_core.alert_channels import (
    AlertDispatcher,
    PagerDutyChannel,
    SlackChannel,
)
from sardis_v2_core.alert_rules import Alert, AlertSeverity, AlertType

logger = logging.getLogger("sardis.api.ops_alerts")

_dispatcher: Optional[AlertDispatcher] = None


def init_ops_dispatcher() -> AlertDispatcher:
    """Initialize the operational alert dispatcher from environment variables."""
    global _dispatcher

    dispatcher = AlertDispatcher()

    slack_url = os.getenv("SARDIS_OPS_SLACK_WEBHOOK_URL", "")
    if slack_url:
        dispatcher.register_channel("slack", SlackChannel(slack_url))
        logger.info("Ops alerting: Slack channel registered")

    pd_key = os.getenv("SARDIS_OPS_PAGERDUTY_ROUTING_KEY", "")
    if pd_key:
        dispatcher.register_channel("pagerduty", PagerDutyChannel(pd_key))
        logger.info("Ops alerting: PagerDuty channel registered")

    # Route critical alerts to PagerDuty, all alerts to Slack
    severity_map: dict[str, list[str]] = {}
    if slack_url:
        severity_map["info"] = ["slack"]
        severity_map["warning"] = ["slack"]
    if pd_key and slack_url:
        severity_map["critical"] = ["slack", "pagerduty"]
    elif pd_key:
        severity_map["critical"] = ["pagerduty"]
    elif slack_url:
        severity_map["critical"] = ["slack"]

    if severity_map:
        dispatcher.set_severity_channel_map(severity_map)

    # Dedupe cooldowns: 5 min per channel to avoid alert storms
    dispatcher.set_channel_cooldowns({
        "slack": 300,
        "pagerduty": 600,
    })

    _dispatcher = dispatcher
    return dispatcher


def get_ops_dispatcher() -> Optional[AlertDispatcher]:
    """Get the global operational alert dispatcher (None if not initialized)."""
    return _dispatcher


async def alert_kill_switch_activated(
    scope: str,
    target: str,
    reason: str,
    activated_by: str | None = None,
) -> None:
    """Fire alert when a kill switch is activated."""
    if _dispatcher is None or not _dispatcher.channels:
        return

    alert = Alert(
        alert_type=AlertType.COMPLIANCE_ALERT,
        severity=AlertSeverity.CRITICAL,
        message=f"Kill switch activated: scope={scope} target={target} reason={reason}",
        data={
            "event": "kill_switch_activated",
            "scope": scope,
            "target": target,
            "reason": reason,
            "activated_by": activated_by or "system",
        },
    )
    try:
        await _dispatcher.dispatch(alert)
    except Exception as e:
        logger.error("Failed to dispatch kill switch alert: %s", e)


async def alert_cap_exceeded(
    cap_type: str,
    org_id: str | None = None,
    agent_id: str | None = None,
    amount: str = "",
    daily_total: str = "",
) -> None:
    """Fire alert when a transaction cap is exceeded."""
    if _dispatcher is None or not _dispatcher.channels:
        return

    alert = Alert(
        alert_type=AlertType.BUDGET_THRESHOLD,
        severity=AlertSeverity.WARNING,
        message=f"Transaction cap exceeded: type={cap_type} org={org_id} agent={agent_id}",
        organization_id=org_id,
        agent_id=agent_id,
        data={
            "event": "transaction_cap_exceeded",
            "cap_type": cap_type,
            "amount": amount,
            "daily_total": daily_total,
        },
    )
    try:
        await _dispatcher.dispatch(alert)
    except Exception as e:
        logger.error("Failed to dispatch cap exceeded alert: %s", e)


async def alert_payment_failure(
    error: str,
    org_id: str | None = None,
    agent_id: str | None = None,
    tx_id: str | None = None,
) -> None:
    """Fire alert on payment execution failure."""
    if _dispatcher is None or not _dispatcher.channels:
        return

    alert = Alert(
        alert_type=AlertType.PAYMENT_EXECUTED,
        severity=AlertSeverity.WARNING,
        message=f"Payment failure: {error}",
        organization_id=org_id,
        agent_id=agent_id,
        data={
            "event": "payment_failure",
            "error": error,
            "tx_id": tx_id or "",
        },
    )
    try:
        await _dispatcher.dispatch(alert)
    except Exception as e:
        logger.error("Failed to dispatch payment failure alert: %s", e)
