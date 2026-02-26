"""REST API endpoints for alert management."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_v2_core.alert_rules import (
    Alert,
    AlertRule,
    AlertRuleEngine,
    AlertSeverity,
    AlertType,
    ConditionType,
)
from sardis_v2_core.alert_channels import (
    AlertDispatcher,
    SlackChannel,
    DiscordChannel,
    EmailChannel,
    PagerDutyChannel,
    WebSocketChannel,
)
from sardis_api.authz import Principal, require_principal
from sardis_api.routers.ws_alerts import get_connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])


# Request/Response Models
class CreateAlertRuleRequest(BaseModel):
    name: str = Field(..., description="Rule name")
    condition_type: str = Field(..., description="Condition type (amount_exceeds, budget_percentage, etc.)")
    threshold: Optional[Decimal] = Field(None, description="Threshold value")
    channels: List[str] = Field(default_factory=list, description="Channel names to send alerts to")
    enabled: bool = Field(default=True, description="Whether the rule is enabled")
    agent_id: Optional[str] = Field(None, description="Specific agent ID to apply rule to")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class UpdateAlertRuleRequest(BaseModel):
    name: Optional[str] = None
    threshold: Optional[Decimal] = None
    channels: Optional[List[str]] = None
    enabled: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class AlertRuleResponse(BaseModel):
    id: str
    name: str
    condition_type: str
    threshold: Optional[str]
    channels: List[str]
    enabled: bool
    organization_id: Optional[str]
    agent_id: Optional[str]
    metadata: dict[str, Any]
    created_at: str


class AlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    message: str
    agent_id: Optional[str]
    organization_id: Optional[str]
    timestamp: str
    data: dict[str, Any]


class ConfigureChannelRequest(BaseModel):
    channel_type: str = Field(..., description="Channel type (slack, discord, email, pagerduty, websocket)")
    enabled: bool = Field(default=True, description="Whether the channel is enabled")
    config: dict[str, Any] = Field(default_factory=dict, description="Channel-specific configuration")


class ChannelConfigResponse(BaseModel):
    channel_type: str
    enabled: bool
    configured: bool


class TestAlertRequest(BaseModel):
    alert_type: str = Field(default="payment_executed", description="Alert type to test")
    severity: str = Field(default="info", description="Alert severity (info, warning, critical)")
    message: str = Field(default="Test alert", description="Alert message")
    channels: Optional[List[str]] = Field(None, description="Channels to send to (default: all)")


# Dependencies
class AlertDependencies:
    def __init__(
        self,
        rule_engine: AlertRuleEngine,
        dispatcher: AlertDispatcher,
    ):
        self.rule_engine = rule_engine
        self.dispatcher = dispatcher


# Global instances (initialized at startup)
_rule_engine: Optional[AlertRuleEngine] = None
_dispatcher: Optional[AlertDispatcher] = None
_alert_store: dict[str, Alert] = {}  # In-memory store for recent alerts


def get_deps() -> AlertDependencies:
    """Get alert dependencies."""
    global _rule_engine, _dispatcher

    if _rule_engine is None:
        _rule_engine = AlertRuleEngine()

    if _dispatcher is None:
        _dispatcher = AlertDispatcher()

        # Register WebSocket channel
        ws_manager = get_connection_manager()
        _dispatcher.register_channel("websocket", WebSocketChannel(ws_manager))

        # Register Slack channel if configured
        slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        if slack_webhook:
            _dispatcher.register_channel("slack", SlackChannel(slack_webhook))

        # Register Discord channel if configured
        discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        if discord_webhook:
            _dispatcher.register_channel("discord", DiscordChannel(discord_webhook))

        # Register Email channel if configured
        smtp_host = os.getenv("SMTP_HOST")
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("SMTP_FROM_EMAIL")
        to_emails = os.getenv("SMTP_TO_EMAILS", "").split(",")

        if all([smtp_host, smtp_user, smtp_password, from_email]) and to_emails:
            _dispatcher.register_channel(
                "email",
                EmailChannel(
                    smtp_host=smtp_host,
                    smtp_port=int(os.getenv("SMTP_PORT", "587")),
                    smtp_user=smtp_user,
                    smtp_password=smtp_password,
                    from_email=from_email,
                    to_emails=[e.strip() for e in to_emails if e.strip()],
                    use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
                ),
            )

        pagerduty_routing_key = os.getenv("PAGERDUTY_ROUTING_KEY", "").strip()
        if pagerduty_routing_key:
            _dispatcher.register_channel(
                "pagerduty",
                PagerDutyChannel(
                    routing_key=pagerduty_routing_key,
                    source=os.getenv("PAGERDUTY_SOURCE", "sardis.api"),
                ),
            )

        severity_channels_raw = os.getenv("SARDIS_ALERT_SEVERITY_CHANNELS_JSON", "")
        if severity_channels_raw.strip():
            try:
                parsed_map = json.loads(severity_channels_raw)
                if isinstance(parsed_map, dict):
                    _dispatcher.set_severity_channel_map(parsed_map)
            except json.JSONDecodeError:
                logger.warning("Invalid SARDIS_ALERT_SEVERITY_CHANNELS_JSON; ignored")

        channel_cooldowns_raw = os.getenv("SARDIS_ALERT_CHANNEL_COOLDOWNS_JSON", "")
        if channel_cooldowns_raw.strip():
            try:
                parsed_cooldowns = json.loads(channel_cooldowns_raw)
                if isinstance(parsed_cooldowns, dict):
                    _dispatcher.set_channel_cooldowns(parsed_cooldowns)
            except json.JSONDecodeError:
                logger.warning("Invalid SARDIS_ALERT_CHANNEL_COOLDOWNS_JSON; ignored")

    return AlertDependencies(
        rule_engine=_rule_engine,
        dispatcher=_dispatcher,
    )


# Endpoints
@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    deps: AlertDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
) -> List[AlertResponse]:
    """List recent alerts with optional filtering."""
    # Filter alerts from in-memory store
    alerts = list(_alert_store.values())

    # Filter by organization
    alerts = [
        a for a in alerts
        if a.organization_id == principal.organization_id or principal.is_admin
    ]

    # Apply filters
    if severity:
        alerts = [a for a in alerts if a.severity.value == severity.lower()]

    if alert_type:
        alerts = [a for a in alerts if a.alert_type.value == alert_type.lower()]

    if agent_id:
        alerts = [a for a in alerts if a.agent_id == agent_id]

    # Sort by timestamp (newest first)
    alerts.sort(key=lambda a: a.timestamp, reverse=True)

    # Pagination
    paginated = alerts[offset : offset + limit]

    return [
        AlertResponse(
            id=a.id,
            alert_type=a.alert_type.value,
            severity=a.severity.value,
            message=a.message,
            agent_id=a.agent_id,
            organization_id=a.organization_id,
            timestamp=a.timestamp.isoformat(),
            data=a.data,
        )
        for a in paginated
    ]


@router.get("/rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    enabled_only: bool = Query(default=False),
    deps: AlertDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
) -> List[AlertRuleResponse]:
    """List all alert rules."""
    rules = deps.rule_engine.list_rules(
        organization_id=principal.organization_id if not principal.is_admin else None,
        enabled_only=enabled_only,
    )

    return [
        AlertRuleResponse(
            id=r.id,
            name=r.name,
            condition_type=r.condition_type.value,
            threshold=str(r.threshold) if r.threshold else None,
            channels=r.channels,
            enabled=r.enabled,
            organization_id=r.organization_id,
            agent_id=r.agent_id,
            metadata=r.metadata,
            created_at=r.created_at.isoformat(),
        )
        for r in rules
    ]


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    request: CreateAlertRuleRequest,
    deps: AlertDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
) -> AlertRuleResponse:
    """Create a new alert rule."""
    # Validate condition type
    try:
        condition_type = ConditionType(request.condition_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid condition_type. Must be one of: {', '.join(c.value for c in ConditionType)}",
        )

    # Create rule
    rule = AlertRule(
        name=request.name,
        condition_type=condition_type,
        threshold=request.threshold,
        channels=request.channels,
        enabled=request.enabled,
        organization_id=principal.organization_id,
        agent_id=request.agent_id,
        metadata=request.metadata,
    )

    deps.rule_engine.add_rule(rule)

    return AlertRuleResponse(
        id=rule.id,
        name=rule.name,
        condition_type=rule.condition_type.value,
        threshold=str(rule.threshold) if rule.threshold else None,
        channels=rule.channels,
        enabled=rule.enabled,
        organization_id=rule.organization_id,
        agent_id=rule.agent_id,
        metadata=rule.metadata,
        created_at=rule.created_at.isoformat(),
    )


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: str,
    request: UpdateAlertRuleRequest,
    deps: AlertDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
) -> AlertRuleResponse:
    """Update an existing alert rule."""
    rule = deps.rule_engine.get_rule(rule_id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )

    # Check authorization
    if not principal.is_admin and rule.organization_id != principal.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Update fields
    if request.name is not None:
        rule.name = request.name
    if request.threshold is not None:
        rule.threshold = request.threshold
    if request.channels is not None:
        rule.channels = request.channels
    if request.enabled is not None:
        rule.enabled = request.enabled
    if request.metadata is not None:
        rule.metadata = request.metadata

    return AlertRuleResponse(
        id=rule.id,
        name=rule.name,
        condition_type=rule.condition_type.value,
        threshold=str(rule.threshold) if rule.threshold else None,
        channels=rule.channels,
        enabled=rule.enabled,
        organization_id=rule.organization_id,
        agent_id=rule.agent_id,
        metadata=rule.metadata,
        created_at=rule.created_at.isoformat(),
    )


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: str,
    deps: AlertDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
) -> None:
    """Delete an alert rule."""
    rule = deps.rule_engine.get_rule(rule_id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )

    # Check authorization
    if not principal.is_admin and rule.organization_id != principal.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Don't allow deleting default rules
    if rule.metadata.get("default"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default system rules",
        )

    deleted = deps.rule_engine.remove_rule(rule_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )


@router.post("/test", response_model=dict)
async def send_test_alert(
    request: TestAlertRequest,
    deps: AlertDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Send a test alert to verify channel configuration."""
    # Validate alert type and severity
    try:
        alert_type = AlertType(request.alert_type.lower())
        severity = AlertSeverity(request.severity.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid alert_type or severity",
        )

    # Create test alert
    test_alert = Alert(
        alert_type=alert_type,
        severity=severity,
        message=request.message,
        organization_id=principal.organization_id,
        data={
            "test": True,
            "requested_by": principal.organization_id,
        },
    )

    # Store alert
    _alert_store[test_alert.id] = test_alert

    # Dispatch to channels
    results = await deps.dispatcher.dispatch(test_alert, channels=request.channels)

    return {
        "alert_id": test_alert.id,
        "message": "Test alert sent",
        "channels": results,
    }


@router.get("/channels", response_model=List[ChannelConfigResponse])
async def list_channels(
    deps: AlertDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
) -> List[ChannelConfigResponse]:
    """List configured alert channels."""
    channels = []

    for name, config in deps.dispatcher.channel_configs.items():
        channels.append(
            ChannelConfigResponse(
                channel_type=name,
                enabled=config.enabled,
                configured=name in deps.dispatcher.channels,
            )
        )

    return channels


@router.post("/channels", response_model=ChannelConfigResponse)
async def configure_channel(
    request: ConfigureChannelRequest,
    deps: AlertDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
) -> ChannelConfigResponse:
    """Configure an alert channel."""
    # Only admins can configure channels
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    channel_type = request.channel_type.lower()

    # Configure channel based on type
    if channel_type == "slack":
        webhook_url = request.config.get("webhook_url")
        if not webhook_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="webhook_url required for Slack channel",
            )
        deps.dispatcher.register_channel(
            "slack",
            SlackChannel(webhook_url),
            enabled=request.enabled,
        )

    elif channel_type == "discord":
        webhook_url = request.config.get("webhook_url")
        if not webhook_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="webhook_url required for Discord channel",
            )
        deps.dispatcher.register_channel(
            "discord",
            DiscordChannel(webhook_url),
            enabled=request.enabled,
        )

    elif channel_type == "email":
        required_fields = ["smtp_host", "smtp_user", "smtp_password", "from_email", "to_emails"]
        missing = [f for f in required_fields if f not in request.config]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {', '.join(missing)}",
            )

        to_emails = request.config["to_emails"]
        if isinstance(to_emails, str):
            to_emails = [e.strip() for e in to_emails.split(",")]

        deps.dispatcher.register_channel(
            "email",
            EmailChannel(
                smtp_host=request.config["smtp_host"],
                smtp_port=request.config.get("smtp_port", 587),
                smtp_user=request.config["smtp_user"],
                smtp_password=request.config["smtp_password"],
                from_email=request.config["from_email"],
                to_emails=to_emails,
                use_tls=request.config.get("use_tls", True),
            ),
            enabled=request.enabled,
        )

    elif channel_type == "pagerduty":
        routing_key = request.config.get("routing_key")
        if not routing_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="routing_key required for PagerDuty channel",
            )
        deps.dispatcher.register_channel(
            "pagerduty",
            PagerDutyChannel(
                routing_key=routing_key,
                source=request.config.get("source", "sardis.api"),
            ),
            enabled=request.enabled,
        )

    elif channel_type == "websocket":
        # WebSocket is always enabled
        deps.dispatcher.set_channel_enabled("websocket", request.enabled)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown channel type: {channel_type}",
        )

    return ChannelConfigResponse(
        channel_type=channel_type,
        enabled=request.enabled,
        configured=True,
    )


# Helper function to dispatch alerts (used by other routers)
async def dispatch_alert(alert: Alert) -> None:
    """
    Dispatch an alert to configured channels.

    This function can be called from other routers to send alerts.
    """
    deps = get_deps()

    # Store alert
    _alert_store[alert.id] = alert

    # Trim alert store if too large (keep last 1000 alerts)
    if len(_alert_store) > 1000:
        sorted_alerts = sorted(_alert_store.values(), key=lambda a: a.timestamp, reverse=True)
        _alert_store.clear()
        for a in sorted_alerts[:1000]:
            _alert_store[a.id] = a

    # Evaluate rules and dispatch
    matching_alerts = deps.rule_engine.evaluate({
        "event_type": alert.alert_type.value,
        "agent_id": alert.agent_id,
        "organization_id": alert.organization_id,
        **alert.data,
    })

    # Dispatch original alert plus any rule-generated alerts
    all_alerts = [alert] + matching_alerts
    for a in all_alerts:
        # Determine channels from alert data or use defaults
        channels = a.data.get("channels")
        await deps.dispatcher.dispatch(a, channels=channels)
