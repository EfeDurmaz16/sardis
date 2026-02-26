"""Alert channels for dispatching alerts to various destinations."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from sardis_v2_core.alert_rules import Alert, AlertSeverity

logger = logging.getLogger(__name__)


class AlertChannel(ABC):
    """Abstract base class for alert channels."""

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """
        Send an alert through this channel.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully, False otherwise
        """
        pass


@dataclass
class ChannelConfig:
    """Configuration for an alert channel."""
    channel_type: str
    enabled: bool = True
    config: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.config is None:
            self.config = {}


class WebSocketChannel(AlertChannel):
    """WebSocket channel for real-time alerts to connected clients."""

    def __init__(self, connection_manager: Optional[Any] = None) -> None:
        self.connection_manager = connection_manager

    async def send(self, alert: Alert) -> bool:
        """Send alert to all connected WebSocket clients."""
        if not self.connection_manager:
            logger.warning("WebSocketChannel: No connection manager configured")
            return False

        try:
            # Broadcast to all clients in the organization
            if alert.organization_id:
                await self.connection_manager.broadcast(
                    alert.organization_id,
                    alert.to_dict(),
                )
            return True
        except Exception as e:
            logger.error(f"WebSocketChannel send error: {e}")
            return False


class SlackChannel(AlertChannel):
    """Slack webhook channel for alerts."""

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    async def send(self, alert: Alert) -> bool:
        """Send alert to Slack via webhook."""
        try:
            import aiohttp

            # Color coding based on severity
            color_map = {
                AlertSeverity.INFO: "#36a64f",  # green
                AlertSeverity.WARNING: "#ff9900",  # amber
                AlertSeverity.CRITICAL: "#ff0000",  # red
            }

            # Build Slack message attachment
            attachment = {
                "fallback": alert.message,
                "color": color_map.get(alert.severity, "#808080"),
                "title": f"{alert.alert_type.value.replace('_', ' ').title()}",
                "text": alert.message,
                "fields": [
                    {
                        "title": "Severity",
                        "value": alert.severity.value.upper(),
                        "short": True,
                    },
                    {
                        "title": "Alert ID",
                        "value": alert.id,
                        "short": True,
                    },
                ],
                "footer": "Sardis Alert System",
                "ts": int(alert.timestamp.timestamp()),
            }

            if alert.agent_id:
                attachment["fields"].append({
                    "title": "Agent ID",
                    "value": alert.agent_id,
                    "short": True,
                })

            # Add relevant data fields
            for key, value in alert.data.items():
                if key in ["amount", "budget_used", "budget_total", "percentage"]:
                    attachment["fields"].append({
                        "title": key.replace("_", " ").title(),
                        "value": str(value),
                        "short": True,
                    })

            payload = {
                "attachments": [attachment],
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        logger.info(f"SlackChannel: Sent alert {alert.id}")
                        return True
                    else:
                        logger.error(
                            f"SlackChannel: Failed to send alert {alert.id}, "
                            f"status={response.status}"
                        )
                        return False

        except ImportError:
            logger.error("SlackChannel: aiohttp not installed")
            return False
        except Exception as e:
            logger.error(f"SlackChannel send error: {e}")
            return False


class DiscordChannel(AlertChannel):
    """Discord webhook channel for alerts."""

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    async def send(self, alert: Alert) -> bool:
        """Send alert to Discord via webhook."""
        try:
            import aiohttp

            # Color coding based on severity (decimal color codes)
            color_map = {
                AlertSeverity.INFO: 3447003,  # blue
                AlertSeverity.WARNING: 16763904,  # amber
                AlertSeverity.CRITICAL: 15158332,  # red
            }

            # Build Discord embed
            embed = {
                "title": f"{alert.alert_type.value.replace('_', ' ').title()}",
                "description": alert.message,
                "color": color_map.get(alert.severity, 8421504),
                "fields": [
                    {
                        "name": "Severity",
                        "value": alert.severity.value.upper(),
                        "inline": True,
                    },
                    {
                        "name": "Alert ID",
                        "value": alert.id,
                        "inline": True,
                    },
                ],
                "footer": {
                    "text": "Sardis Alert System",
                },
                "timestamp": alert.timestamp.isoformat(),
            }

            if alert.agent_id:
                embed["fields"].append({
                    "name": "Agent ID",
                    "value": alert.agent_id,
                    "inline": True,
                })

            # Add relevant data fields
            for key, value in alert.data.items():
                if key in ["amount", "budget_used", "budget_total", "percentage"]:
                    embed["fields"].append({
                        "name": key.replace("_", " ").title(),
                        "value": str(value),
                        "inline": True,
                    })

            payload = {
                "embeds": [embed],
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status in [200, 204]:
                        logger.info(f"DiscordChannel: Sent alert {alert.id}")
                        return True
                    else:
                        logger.error(
                            f"DiscordChannel: Failed to send alert {alert.id}, "
                            f"status={response.status}"
                        )
                        return False

        except ImportError:
            logger.error("DiscordChannel: aiohttp not installed")
            return False
        except Exception as e:
            logger.error(f"DiscordChannel send error: {e}")
            return False


class EmailChannel(AlertChannel):
    """Email channel for alerts via SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        to_emails: list[str],
        use_tls: bool = True,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls

    async def send(self, alert: Alert) -> bool:
        """Send alert via email."""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # Build email
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.alert_type.value}"
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)

            # Plain text version
            text_body = f"""
Sardis Alert

Type: {alert.alert_type.value}
Severity: {alert.severity.value.upper()}
Message: {alert.message}
Alert ID: {alert.id}
Timestamp: {alert.timestamp.isoformat()}

Agent ID: {alert.agent_id or 'N/A'}
Organization: {alert.organization_id or 'N/A'}

Details:
{json.dumps(alert.data, indent=2)}
"""

            # HTML version
            severity_color = {
                AlertSeverity.INFO: "#36a64f",
                AlertSeverity.WARNING: "#ff9900",
                AlertSeverity.CRITICAL: "#ff0000",
            }.get(alert.severity, "#808080")

            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <div style="border-left: 4px solid {severity_color}; padding-left: 15px;">
        <h2 style="color: {severity_color}; margin: 0;">
            {alert.alert_type.value.replace('_', ' ').title()}
        </h2>
        <p style="font-size: 16px; margin: 10px 0;">{alert.message}</p>
        <table style="margin-top: 15px;">
            <tr><td><b>Severity:</b></td><td>{alert.severity.value.upper()}</td></tr>
            <tr><td><b>Alert ID:</b></td><td>{alert.id}</td></tr>
            <tr><td><b>Timestamp:</b></td><td>{alert.timestamp.isoformat()}</td></tr>
            {f'<tr><td><b>Agent ID:</b></td><td>{alert.agent_id}</td></tr>' if alert.agent_id else ''}
        </table>
    </div>
</body>
</html>
"""

            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Send email in thread pool to avoid blocking
            def _send_smtp() -> None:
                if self.use_tls:
                    server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                    server.starttls()
                else:
                    server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)

                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, self.to_emails, msg.as_string())
                server.quit()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _send_smtp)

            logger.info(f"EmailChannel: Sent alert {alert.id}")
            return True

        except Exception as e:
            logger.error(f"EmailChannel send error: {e}")
            return False


class AlertDispatcher:
    """Routes alerts to configured channels based on severity and preferences."""

    def __init__(self) -> None:
        self.channels: dict[str, AlertChannel] = {}
        self.channel_configs: dict[str, ChannelConfig] = {}
        self._severity_channel_map: dict[AlertSeverity, list[str]] = {}
        self._channel_cooldowns_seconds: dict[str, int] = {}
        self._last_sent_at: dict[str, float] = {}

    def register_channel(self, name: str, channel: AlertChannel, enabled: bool = True) -> None:
        """Register an alert channel."""
        self.channels[name] = channel
        self.channel_configs[name] = ChannelConfig(
            channel_type=name,
            enabled=enabled,
        )
        logger.info(f"AlertDispatcher: Registered channel '{name}'")

    def unregister_channel(self, name: str) -> None:
        """Unregister an alert channel."""
        if name in self.channels:
            del self.channels[name]
            del self.channel_configs[name]
            logger.info(f"AlertDispatcher: Unregistered channel '{name}'")

    def set_channel_enabled(self, name: str, enabled: bool) -> None:
        """Enable or disable a channel."""
        if name in self.channel_configs:
            self.channel_configs[name].enabled = enabled

    def set_severity_channel_map(self, severity_map: dict[str, list[str]]) -> None:
        """Set default channels per alert severity."""
        parsed: dict[AlertSeverity, list[str]] = {}
        for severity_raw, channels in severity_map.items():
            if not isinstance(channels, list):
                continue
            try:
                severity = AlertSeverity(str(severity_raw).strip().lower())
            except ValueError:
                logger.warning("AlertDispatcher: unknown severity key '%s' ignored", severity_raw)
                continue
            parsed[severity] = [str(channel).strip() for channel in channels if str(channel).strip()]
        self._severity_channel_map = parsed

    def set_channel_cooldowns(self, cooldowns_seconds: dict[str, int]) -> None:
        """Set per-channel dedupe cooldown windows."""
        parsed: dict[str, int] = {}
        for channel_name, cooldown in cooldowns_seconds.items():
            try:
                value = int(cooldown)
            except (TypeError, ValueError):
                continue
            if value > 0:
                parsed[str(channel_name).strip()] = value
        self._channel_cooldowns_seconds = parsed

    def _resolve_target_channels(self, alert: Alert, channels: Optional[list[str]]) -> list[str]:
        if channels:
            return channels
        severity_channels = self._severity_channel_map.get(alert.severity)
        if severity_channels:
            return severity_channels
        return list(self.channels.keys())

    def _cooldown_key(self, channel_name: str, alert: Alert) -> str:
        org = alert.organization_id or "_"
        agent = alert.agent_id or "_"
        return f"{channel_name}:{alert.severity.value}:{alert.alert_type.value}:{org}:{agent}"

    def _within_cooldown(self, channel_name: str, alert: Alert) -> bool:
        cooldown = self._channel_cooldowns_seconds.get(channel_name, 0)
        if cooldown <= 0:
            return False
        key = self._cooldown_key(channel_name, alert)
        now = time.monotonic()
        previous = self._last_sent_at.get(key)
        if previous is not None and (now - previous) < cooldown:
            return True
        return False

    def _mark_sent(self, channel_name: str, alert: Alert) -> None:
        key = self._cooldown_key(channel_name, alert)
        self._last_sent_at[key] = time.monotonic()

    async def dispatch(self, alert: Alert, channels: Optional[list[str]] = None) -> dict[str, bool]:
        """
        Dispatch an alert to specified channels.

        Args:
            alert: Alert to dispatch
            channels: List of channel names to use, or None to use all enabled channels

        Returns:
            Dictionary mapping channel names to send success status
        """
        target_channels = self._resolve_target_channels(alert, channels)
        results: dict[str, bool] = {}

        # Filter to only enabled channels
        enabled_channels = [
            name for name in target_channels
            if name in self.channel_configs and self.channel_configs[name].enabled
        ]

        # Send to all channels concurrently
        tasks = []
        dispatched_channels: list[str] = []
        for channel_name in enabled_channels:
            if channel_name in self.channels:
                if self._within_cooldown(channel_name, alert):
                    logger.info(
                        "AlertDispatcher: cooldown skip channel=%s alert_type=%s severity=%s",
                        channel_name,
                        alert.alert_type.value,
                        alert.severity.value,
                    )
                    results[channel_name] = True
                    continue
                channel = self.channels[channel_name]
                tasks.append(self._send_with_name(channel_name, channel, alert))
                dispatched_channels.append(channel_name)

        if tasks:
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
            for i, channel_name in enumerate(dispatched_channels):
                result = results_list[i]
                if isinstance(result, Exception):
                    logger.error(f"Channel '{channel_name}' error: {result}")
                    results[channel_name] = False
                else:
                    results[channel_name] = result
                    if result:
                        self._mark_sent(channel_name, alert)

        return results

    async def _send_with_name(
        self,
        channel_name: str,
        channel: AlertChannel,
        alert: Alert,
    ) -> bool:
        """Helper to send alert and track channel name."""
        try:
            return await channel.send(alert)
        except Exception as e:
            logger.error(f"Error sending to channel '{channel_name}': {e}")
            return False
