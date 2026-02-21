"""
Email notification plugin for sending event notifications via email.

Sends email notifications for transaction events using SMTP.
"""

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

try:
    import aiosmtplib
except ImportError:
    aiosmtplib = None

from ..base import NotificationPlugin, PluginMetadata, PluginType


class EmailNotificationPlugin(NotificationPlugin):
    """
    Send notifications via email.

    Sends event notifications to configured email addresses using SMTP.
    """

    def __init__(self):
        """Initialize email notification plugin."""
        super().__init__()
        self._smtp_host: Optional[str] = None
        self._smtp_port: int = 587
        self._from_email: Optional[str] = None
        self._to_emails: list[str] = []
        self._use_tls: bool = True
        self._username: Optional[str] = None
        self._password: Optional[str] = None

    @property
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        return PluginMetadata(
            name="email-notification",
            version="1.0.0",
            author="Sardis",
            description="Send event notifications via email",
            plugin_type=PluginType.NOTIFICATION,
            config_schema={
                "smtp_host": {"type": "string", "required": True},
                "smtp_port": {"type": "integer", "default": 587},
                "from_email": {"type": "string", "required": True},
                "to_emails": {"type": "array", "items": {"type": "string"}},
                "use_tls": {"type": "boolean", "default": True},
                "username": {"type": "string", "required": False},
                "password": {"type": "string", "required": False},
            },
        )

    async def initialize(self, config: dict[str, Any]) -> None:
        """
        Initialize plugin with SMTP configuration.

        Args:
            config: Must contain smtp_host, from_email, to_emails
        """
        await super().initialize(config)

        self._smtp_host = config.get("smtp_host")
        if not self._smtp_host:
            raise ValueError("smtp_host is required for email notification plugin")

        self._from_email = config.get("from_email")
        if not self._from_email:
            raise ValueError("from_email is required for email notification plugin")

        self._to_emails = config.get("to_emails", [])
        if not self._to_emails:
            raise ValueError("to_emails is required for email notification plugin")

        self._smtp_port = config.get("smtp_port", 587)
        self._use_tls = config.get("use_tls", True)
        self._username = config.get("username")
        self._password = config.get("password")

    async def notify(self, event: dict[str, Any]) -> None:
        """
        Send email notification for event.

        Args:
            event: Event data to notify about
        """
        if not aiosmtplib:
            # Silently skip if aiosmtplib not installed
            return

        if not self._smtp_host or not self._from_email or not self._to_emails:
            raise ValueError("Email plugin not properly configured")

        # Create email message
        subject, body = self._create_email_content(event)

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self._from_email
        message["To"] = ", ".join(self._to_emails)

        # Add HTML and plain text parts
        text_part = MIMEText(body, "plain")
        html_part = MIMEText(self._create_html_body(event), "html")

        message.attach(text_part)
        message.attach(html_part)

        # Send email
        await self._send_email(message)

    def _create_email_content(self, event: dict[str, Any]) -> tuple[str, str]:
        """
        Create email subject and plain text body.

        Args:
            event: Event data

        Returns:
            Tuple of (subject, body)
        """
        event_type = event.get("type", "unknown")
        agent_id = event.get("agent_id", "unknown")

        if event_type == "transaction.created":
            amount = event.get("amount", "unknown")
            currency = event.get("currency", "USD")
            subject = f"Sardis: New Transaction - {amount} {currency}"
            body = f"""
New transaction created

Agent: {agent_id}
Amount: {amount} {currency}
Recipient: {event.get('recipient', 'unknown')}
Description: {event.get('description', 'N/A')}
Status: {event.get('status', 'unknown')}
Timestamp: {event.get('timestamp', 'unknown')}
"""

        elif event_type == "transaction.approved":
            amount = event.get("amount", "unknown")
            currency = event.get("currency", "USD")
            subject = f"Sardis: Transaction Approved - {amount} {currency}"
            body = f"""
Transaction approved

Agent: {agent_id}
Amount: {amount} {currency}
Approver: {event.get('approver', 'system')}
Timestamp: {event.get('timestamp', 'unknown')}
"""

        elif event_type == "transaction.rejected":
            amount = event.get("amount", "unknown")
            currency = event.get("currency", "USD")
            subject = f"Sardis: Transaction Rejected - {amount} {currency}"
            body = f"""
Transaction rejected

Agent: {agent_id}
Amount: {amount} {currency}
Reason: {event.get('reason', 'N/A')}
Timestamp: {event.get('timestamp', 'unknown')}
"""

        elif event_type == "policy.violated":
            subject = f"Sardis: Policy Violation - {agent_id}"
            body = f"""
Policy violation detected

Agent: {agent_id}
Policy: {event.get('policy_name', 'unknown')}
Violation: {event.get('violation', 'unknown')}
Timestamp: {event.get('timestamp', 'unknown')}
"""

        else:
            subject = f"Sardis: Event - {event_type}"
            body = f"""
Event notification

Type: {event_type}
Agent: {agent_id}
Data: {event}
"""

        return subject, body.strip()

    def _create_html_body(self, event: dict[str, Any]) -> str:
        """
        Create HTML email body.

        Args:
            event: Event data

        Returns:
            HTML body string
        """
        event_type = event.get("type", "unknown")
        agent_id = event.get("agent_id", "unknown")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
        .content {{ background: #f9fafb; padding: 20px; margin-top: 20px; }}
        .field {{ margin: 10px 0; }}
        .label {{ font-weight: bold; color: #555; }}
        .value {{ color: #333; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Sardis Notification</h2>
        </div>
        <div class="content">
            <div class="field">
                <span class="label">Event Type:</span>
                <span class="value">{event_type}</span>
            </div>
            <div class="field">
                <span class="label">Agent ID:</span>
                <span class="value">{agent_id}</span>
            </div>
"""

        # Add event-specific fields
        for key, value in event.items():
            if key not in ["type", "agent_id"]:
                html += f"""
            <div class="field">
                <span class="label">{key.replace('_', ' ').title()}:</span>
                <span class="value">{value}</span>
            </div>
"""

        html += """
        </div>
        <div class="footer">
            <p>Sardis - Payment OS for the Agent Economy</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    async def _send_email(self, message: MIMEMultipart) -> None:
        """
        Send email via SMTP.

        Args:
            message: Email message to send
        """
        try:
            if self._use_tls:
                await aiosmtplib.send(
                    message,
                    hostname=self._smtp_host,
                    port=self._smtp_port,
                    username=self._username,
                    password=self._password,
                    start_tls=True,
                )
            else:
                await aiosmtplib.send(
                    message,
                    hostname=self._smtp_host,
                    port=self._smtp_port,
                    username=self._username,
                    password=self._password,
                )
        except Exception as e:
            # Log error but don't raise - notifications are non-fatal
            print(f"Failed to send email notification: {e}")
