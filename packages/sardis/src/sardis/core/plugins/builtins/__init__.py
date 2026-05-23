"""
Built-in plugins for Sardis.

Provides ready-to-use plugins for common use cases:
- Slack approval requests
- Email notifications
- Custom policy rules
"""

from .custom_policy import CustomPolicyPlugin
from .email_notification import EmailNotificationPlugin
from .slack_approval import SlackApprovalPlugin

__all__ = [
    "SlackApprovalPlugin",
    "EmailNotificationPlugin",
    "CustomPolicyPlugin",
]
