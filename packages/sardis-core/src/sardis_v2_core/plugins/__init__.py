"""
Sardis plugin system for extensibility.

Provides base classes, registry, and built-in plugins for extending
Sardis with custom policies, approvals, notifications, audit, and webhooks.
"""

from .base import (
    ApprovalPlugin,
    ApprovalResult,
    AuditPlugin,
    NotificationPlugin,
    PolicyDecision,
    PolicyPlugin,
    PluginMetadata,
    PluginType,
    SardisPlugin,
    WebhookPlugin,
)
from .registry import PluginInfo, PluginRegistry

__all__ = [
    # Base classes
    "SardisPlugin",
    "PolicyPlugin",
    "ApprovalPlugin",
    "NotificationPlugin",
    "AuditPlugin",
    "WebhookPlugin",
    # Types
    "PluginType",
    "PluginMetadata",
    "PolicyDecision",
    "ApprovalResult",
    # Registry
    "PluginRegistry",
    "PluginInfo",
]
