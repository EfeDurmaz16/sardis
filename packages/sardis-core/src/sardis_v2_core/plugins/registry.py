"""
Plugin registry for managing installed and active plugins.

Provides thread-safe registration, execution, and lifecycle management
for Sardis plugins with timeout protection.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import uuid

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


# Plugin execution timeout (5 seconds)
PLUGIN_TIMEOUT_SECONDS = 5.0


@dataclass
class PluginInfo:
    """Information about an installed plugin."""

    id: str
    metadata: PluginMetadata
    enabled: bool
    installed_at: datetime = field(default_factory=datetime.utcnow)
    config: dict[str, Any] = field(default_factory=dict)


class PluginRegistry:
    """
    Registry for managing Sardis plugins.

    Handles plugin registration, lifecycle, and thread-safe execution
    with timeout protection.
    """

    def __init__(self):
        """Initialize plugin registry."""
        self._plugins: dict[str, SardisPlugin] = {}
        self._plugin_info: dict[str, PluginInfo] = {}
        self._lock = asyncio.Lock()

    async def register(
        self, plugin_class: type[SardisPlugin], config: dict[str, Any]
    ) -> str:
        """
        Install and register a plugin.

        Args:
            plugin_class: Plugin class to instantiate
            config: Plugin configuration

        Returns:
            plugin_id: Unique identifier for the installed plugin
        """
        async with self._lock:
            # Create plugin instance
            plugin = plugin_class()

            # Generate unique ID
            plugin_id = str(uuid.uuid4())

            # Initialize plugin
            await plugin.initialize(config)

            # Store plugin and info
            self._plugins[plugin_id] = plugin
            self._plugin_info[plugin_id] = PluginInfo(
                id=plugin_id,
                metadata=plugin.metadata,
                enabled=True,
                config=config,
            )

            return plugin_id

    async def unregister(self, plugin_id: str) -> None:
        """
        Uninstall a plugin.

        Args:
            plugin_id: ID of plugin to uninstall
        """
        async with self._lock:
            if plugin_id not in self._plugins:
                raise ValueError(f"Plugin not found: {plugin_id}")

            # Shutdown plugin
            plugin = self._plugins[plugin_id]
            await plugin.shutdown()

            # Remove from registry
            del self._plugins[plugin_id]
            del self._plugin_info[plugin_id]

    async def enable(self, plugin_id: str) -> None:
        """
        Enable a plugin.

        Args:
            plugin_id: ID of plugin to enable
        """
        async with self._lock:
            if plugin_id not in self._plugin_info:
                raise ValueError(f"Plugin not found: {plugin_id}")

            self._plugin_info[plugin_id].enabled = True

    async def disable(self, plugin_id: str) -> None:
        """
        Disable a plugin without uninstalling.

        Args:
            plugin_id: ID of plugin to disable
        """
        async with self._lock:
            if plugin_id not in self._plugin_info:
                raise ValueError(f"Plugin not found: {plugin_id}")

            self._plugin_info[plugin_id].enabled = False

    async def get_plugin(self, plugin_id: str) -> SardisPlugin:
        """
        Get plugin instance by ID.

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin instance
        """
        async with self._lock:
            if plugin_id not in self._plugins:
                raise ValueError(f"Plugin not found: {plugin_id}")

            return self._plugins[plugin_id]

    async def list_plugins(
        self, plugin_type: Optional[PluginType] = None
    ) -> list[PluginInfo]:
        """
        List all installed plugins, optionally filtered by type.

        Args:
            plugin_type: Optional filter by plugin type

        Returns:
            List of plugin information
        """
        async with self._lock:
            plugins = list(self._plugin_info.values())

            if plugin_type:
                plugins = [p for p in plugins if p.metadata.plugin_type == plugin_type]

            return plugins

    async def execute_policy_plugins(
        self, transaction: dict[str, Any]
    ) -> list[PolicyDecision]:
        """
        Execute all enabled policy plugins on a transaction.

        Args:
            transaction: Transaction to evaluate

        Returns:
            List of policy decisions from all plugins
        """
        policy_plugins = await self._get_enabled_plugins_by_type(PluginType.POLICY)

        decisions = []
        for plugin_id, plugin in policy_plugins:
            try:
                decision = await asyncio.wait_for(
                    plugin.evaluate(transaction), timeout=PLUGIN_TIMEOUT_SECONDS
                )
                decisions.append(decision)
            except asyncio.TimeoutError:
                # Plugin timed out, treat as rejection
                decisions.append(
                    PolicyDecision(
                        approved=False,
                        reason=f"Plugin {plugin.metadata.name} timed out",
                        plugin_name=plugin.metadata.name,
                        metadata={"error": "timeout"},
                    )
                )
            except Exception as e:
                # Plugin error, treat as rejection
                decisions.append(
                    PolicyDecision(
                        approved=False,
                        reason=f"Plugin {plugin.metadata.name} error: {str(e)}",
                        plugin_name=plugin.metadata.name,
                        metadata={"error": str(e)},
                    )
                )

        return decisions

    async def execute_approval_plugins(
        self, transaction: dict[str, Any]
    ) -> ApprovalResult:
        """
        Execute approval plugins until one approves or all reject.

        Args:
            transaction: Transaction requiring approval

        Returns:
            Approval result from first approving plugin or last rejection
        """
        approval_plugins = await self._get_enabled_plugins_by_type(PluginType.APPROVAL)

        if not approval_plugins:
            # No approval plugins, auto-reject
            return ApprovalResult(
                approved=False,
                approver=None,
                reason="No approval plugins configured",
                plugin_name="system",
            )

        last_result = None
        for plugin_id, plugin in approval_plugins:
            try:
                result = await asyncio.wait_for(
                    plugin.request_approval(transaction), timeout=PLUGIN_TIMEOUT_SECONDS
                )

                if result.approved:
                    # First approval wins
                    return result

                last_result = result

            except asyncio.TimeoutError:
                last_result = ApprovalResult(
                    approved=False,
                    approver=None,
                    reason=f"Plugin {plugin.metadata.name} timed out",
                    plugin_name=plugin.metadata.name,
                    metadata={"error": "timeout"},
                )
            except Exception as e:
                last_result = ApprovalResult(
                    approved=False,
                    approver=None,
                    reason=f"Plugin {plugin.metadata.name} error: {str(e)}",
                    plugin_name=plugin.metadata.name,
                    metadata={"error": str(e)},
                )

        # All plugins rejected, return last rejection
        return last_result or ApprovalResult(
            approved=False,
            approver=None,
            reason="All approval plugins rejected",
            plugin_name="system",
        )

    async def execute_notification_plugins(self, event: dict[str, Any]) -> None:
        """
        Execute all enabled notification plugins for an event.

        Args:
            event: Event to notify about
        """
        notification_plugins = await self._get_enabled_plugins_by_type(
            PluginType.NOTIFICATION
        )

        # Execute all notification plugins concurrently
        tasks = []
        for plugin_id, plugin in notification_plugins:
            task = asyncio.create_task(
                self._execute_notification_plugin(plugin, event)
            )
            tasks.append(task)

        if tasks:
            # Wait for all notifications, ignore failures
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_notification_plugin(
        self, plugin: NotificationPlugin, event: dict[str, Any]
    ) -> None:
        """Execute single notification plugin with timeout."""
        try:
            await asyncio.wait_for(
                plugin.notify(event), timeout=PLUGIN_TIMEOUT_SECONDS
            )
        except (asyncio.TimeoutError, Exception):
            # Notification failures are non-fatal, just log
            pass

    async def _get_enabled_plugins_by_type(
        self, plugin_type: PluginType
    ) -> list[tuple[str, SardisPlugin]]:
        """
        Get all enabled plugins of a specific type.

        Args:
            plugin_type: Type of plugins to retrieve

        Returns:
            List of (plugin_id, plugin) tuples
        """
        async with self._lock:
            enabled_plugins = []
            for plugin_id, info in self._plugin_info.items():
                if info.enabled and info.metadata.plugin_type == plugin_type:
                    plugin = self._plugins[plugin_id]
                    enabled_plugins.append((plugin_id, plugin))

            return enabled_plugins

    async def update_config(self, plugin_id: str, config: dict[str, Any]) -> None:
        """
        Update plugin configuration.

        Args:
            plugin_id: Plugin to update
            config: New configuration
        """
        async with self._lock:
            if plugin_id not in self._plugins:
                raise ValueError(f"Plugin not found: {plugin_id}")

            plugin = self._plugins[plugin_id]
            await plugin.initialize(config)

            self._plugin_info[plugin_id].config = config

    async def get_config(self, plugin_id: str) -> dict[str, Any]:
        """
        Get plugin configuration.

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin configuration
        """
        async with self._lock:
            if plugin_id not in self._plugin_info:
                raise ValueError(f"Plugin not found: {plugin_id}")

            return self._plugin_info[plugin_id].config
