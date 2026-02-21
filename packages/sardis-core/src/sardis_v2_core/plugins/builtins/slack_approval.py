"""
Slack approval plugin for requesting transaction approvals via Slack.

Sends approval requests to Slack channels with interactive buttons
and waits for user response.
"""

import asyncio
from typing import Any, Optional
from datetime import datetime

try:
    import aiohttp
except ImportError:
    aiohttp = None

from ..base import ApprovalPlugin, ApprovalResult, PluginMetadata, PluginType


class SlackApprovalPlugin(ApprovalPlugin):
    """
    Request approvals via Slack interactive messages.

    Sends transaction details to a Slack channel with approve/reject buttons.
    Waits for user response within configured timeout.
    """

    def __init__(self):
        """Initialize Slack approval plugin."""
        super().__init__()
        self._webhook_url: Optional[str] = None
        self._channel: Optional[str] = None
        self._timeout_seconds: int = 300  # 5 minutes default
        self._pending_approvals: dict[str, asyncio.Future] = {}

    @property
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        return PluginMetadata(
            name="slack-approval",
            version="1.0.0",
            author="Sardis",
            description="Request transaction approvals via Slack interactive messages",
            plugin_type=PluginType.APPROVAL,
            config_schema={
                "webhook_url": {"type": "string", "required": True},
                "channel": {"type": "string", "required": False},
                "timeout_seconds": {"type": "integer", "default": 300},
            },
        )

    async def initialize(self, config: dict[str, Any]) -> None:
        """
        Initialize plugin with Slack configuration.

        Args:
            config: Must contain webhook_url, optional channel and timeout_seconds
        """
        await super().initialize(config)

        self._webhook_url = config.get("webhook_url")
        if not self._webhook_url:
            raise ValueError("webhook_url is required for Slack approval plugin")

        self._channel = config.get("channel")
        self._timeout_seconds = config.get("timeout_seconds", 300)

    async def request_approval(self, transaction: dict[str, Any]) -> ApprovalResult:
        """
        Request approval via Slack.

        Args:
            transaction: Transaction requiring approval

        Returns:
            ApprovalResult with user's decision
        """
        if not aiohttp:
            return ApprovalResult(
                approved=False,
                approver=None,
                reason="aiohttp not installed",
                plugin_name=self.metadata.name,
            )

        if not self._webhook_url:
            return ApprovalResult(
                approved=False,
                approver=None,
                reason="Slack webhook URL not configured",
                plugin_name=self.metadata.name,
            )

        # Create approval message
        message = self._create_approval_message(transaction)

        # Create future for response
        approval_id = transaction.get("id", "unknown")
        response_future = asyncio.Future()
        self._pending_approvals[approval_id] = response_future

        try:
            # Send to Slack
            await self._send_slack_message(message)

            # Wait for response with timeout
            try:
                result = await asyncio.wait_for(
                    response_future, timeout=self._timeout_seconds
                )
                return result
            except asyncio.TimeoutError:
                return ApprovalResult(
                    approved=False,
                    approver=None,
                    reason=f"No response within {self._timeout_seconds} seconds",
                    plugin_name=self.metadata.name,
                    metadata={"timeout": True},
                )

        finally:
            # Cleanup pending approval
            if approval_id in self._pending_approvals:
                del self._pending_approvals[approval_id]

    async def handle_approval_response(
        self, approval_id: str, approved: bool, approver: str, reason: str = ""
    ) -> None:
        """
        Handle approval response from Slack webhook.

        This would be called by a webhook handler when user clicks approve/reject.

        Args:
            approval_id: Transaction ID
            approved: Whether approved
            approver: Slack user who responded
            reason: Optional reason text
        """
        if approval_id in self._pending_approvals:
            result = ApprovalResult(
                approved=approved,
                approver=approver,
                reason=reason or ("Approved" if approved else "Rejected"),
                plugin_name=self.metadata.name,
                timestamp=datetime.utcnow(),
            )
            self._pending_approvals[approval_id].set_result(result)

    def _create_approval_message(self, transaction: dict[str, Any]) -> dict[str, Any]:
        """Create Slack message with approval buttons."""
        amount = transaction.get("amount", "unknown")
        currency = transaction.get("currency", "USD")
        recipient = transaction.get("recipient", "unknown")
        description = transaction.get("description", "No description")

        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🔔 Transaction Approval Required",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Amount:*\n{amount} {currency}"},
                        {"type": "mrkdwn", "text": f"*Recipient:*\n{recipient}"},
                    ],
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Description:*\n{description}"},
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "✅ Approve"},
                            "style": "primary",
                            "value": "approve",
                            "action_id": f"approve_{transaction.get('id')}",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "❌ Reject"},
                            "style": "danger",
                            "value": "reject",
                            "action_id": f"reject_{transaction.get('id')}",
                        },
                    ],
                },
            ]
        }

        if self._channel:
            message["channel"] = self._channel

        return message

    async def _send_slack_message(self, message: dict[str, Any]) -> None:
        """Send message to Slack webhook."""
        async with aiohttp.ClientSession() as session:
            async with session.post(self._webhook_url, json=message) as resp:
                if resp.status != 200:
                    raise Exception(f"Slack API error: {resp.status}")
