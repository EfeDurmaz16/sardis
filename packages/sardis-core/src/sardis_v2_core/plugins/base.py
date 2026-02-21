"""
Base plugin system for Sardis extensibility.

Provides abstract base classes and interfaces for building plugins that extend
Sardis functionality across policy evaluation, approvals, notifications, audit,
and webhook handling.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class PluginType(str, Enum):
    """Type of plugin functionality."""

    POLICY = "policy"
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    AUDIT = "audit"
    WEBHOOK = "webhook"


@dataclass
class PluginMetadata:
    """Metadata describing a plugin."""

    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    config_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyDecision:
    """Result of policy evaluation."""

    approved: bool
    reason: str
    plugin_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalResult:
    """Result of approval request."""

    approved: bool
    approver: Optional[str]
    reason: str
    plugin_name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class SardisPlugin(ABC):
    """
    Abstract base class for all Sardis plugins.

    Plugins extend Sardis with custom business logic for policies,
    approvals, notifications, audit, and webhooks.
    """

    def __init__(self):
        """Initialize plugin."""
        self._initialized = False
        self._config: dict[str, Any] = {}

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        pass

    async def initialize(self, config: dict[str, Any]) -> None:
        """
        Initialize plugin with configuration.

        Args:
            config: Plugin-specific configuration
        """
        self._config = config
        self._initialized = True

    async def shutdown(self) -> None:
        """Clean up plugin resources."""
        self._initialized = False

    async def health_check(self) -> bool:
        """
        Check if plugin is healthy and operational.

        Returns:
            True if healthy, False otherwise
        """
        return self._initialized


class PolicyPlugin(SardisPlugin):
    """Plugin for custom policy evaluation."""

    @abstractmethod
    async def evaluate(self, transaction: dict[str, Any]) -> PolicyDecision:
        """
        Evaluate if transaction passes policy.

        Args:
            transaction: Transaction data to evaluate

        Returns:
            PolicyDecision with approval status and reason
        """
        pass


class ApprovalPlugin(SardisPlugin):
    """Plugin for requesting external approvals."""

    @abstractmethod
    async def request_approval(self, transaction: dict[str, Any]) -> ApprovalResult:
        """
        Request approval for a transaction.

        Args:
            transaction: Transaction requiring approval

        Returns:
            ApprovalResult with approval decision
        """
        pass


class NotificationPlugin(SardisPlugin):
    """Plugin for sending notifications."""

    @abstractmethod
    async def notify(self, event: dict[str, Any]) -> None:
        """
        Send notification for an event.

        Args:
            event: Event data to notify about
        """
        pass


class AuditPlugin(SardisPlugin):
    """Plugin for logging audit events."""

    @abstractmethod
    async def log_event(self, event: dict[str, Any]) -> None:
        """
        Log an audit event.

        Args:
            event: Event data to log
        """
        pass


class WebhookPlugin(SardisPlugin):
    """Plugin for handling webhook payloads."""

    @abstractmethod
    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Handle incoming webhook payload.

        Args:
            payload: Webhook payload data

        Returns:
            Response data to return to webhook caller
        """
        pass
