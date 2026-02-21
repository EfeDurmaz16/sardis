"""
Plugin API — install, configure, and manage Sardis plugins.

Plugins extend Sardis with custom policies, approvals, notifications,
audit, and webhook handlers.

Endpoints:
    GET  /plugins                       — List installed plugins
    POST /plugins                       — Install a plugin
    DELETE /plugins/{plugin_id}         — Uninstall a plugin
    PUT  /plugins/{plugin_id}/enable    — Enable a plugin
    PUT  /plugins/{plugin_id}/disable   — Disable a plugin
    GET  /plugins/{plugin_id}/config    — Get plugin configuration
    PUT  /plugins/{plugin_id}/config    — Update plugin configuration
    GET  /plugins/builtins              — List available built-in plugins
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import require_principal, Principal
from sardis_v2_core.plugins import PluginRegistry, PluginType, PluginInfo
from sardis_v2_core.plugins.builtins import (
    CustomPolicyPlugin,
    EmailNotificationPlugin,
    SlackApprovalPlugin,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])


# ============================================================================
# Dependencies
# ============================================================================


def get_plugin_registry() -> PluginRegistry:
    """Get plugin registry instance."""
    raise NotImplementedError("Dependency override required")


# ============================================================================
# Request/Response Models
# ============================================================================


class PluginInstallRequest(BaseModel):
    """Request to install a plugin."""

    plugin_type: str = Field(
        ...,
        description="Built-in plugin type or custom plugin class path",
        examples=["slack-approval", "email-notification", "custom-policy"],
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Plugin-specific configuration",
    )


class PluginConfigUpdateRequest(BaseModel):
    """Request to update plugin configuration."""

    config: dict[str, Any] = Field(..., description="New plugin configuration")


class PluginInfoResponse(BaseModel):
    """Plugin information response."""

    id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: str
    enabled: bool
    installed_at: str
    config_schema: dict[str, Any]


class PluginInstallResponse(BaseModel):
    """Plugin installation response."""

    plugin_id: str
    name: str
    version: str
    message: str


class BuiltinPluginInfo(BaseModel):
    """Information about a built-in plugin."""

    type: str
    name: str
    version: str
    description: str
    plugin_type: str
    config_schema: dict[str, Any]


# ============================================================================
# Built-in Plugin Registry
# ============================================================================

BUILTIN_PLUGINS = {
    "slack-approval": SlackApprovalPlugin,
    "email-notification": EmailNotificationPlugin,
    "custom-policy": CustomPolicyPlugin,
}


# ============================================================================
# Routes
# ============================================================================


@router.get("/plugins/builtins", response_model=list[BuiltinPluginInfo])
async def list_builtin_plugins(
    principal: Principal = Depends(require_principal),
) -> list[BuiltinPluginInfo]:
    """
    List available built-in plugins.

    Returns information about all built-in plugins that can be installed.
    """
    builtins = []

    for plugin_type, plugin_class in BUILTIN_PLUGINS.items():
        # Instantiate temporarily to get metadata
        plugin = plugin_class()
        metadata = plugin.metadata

        builtins.append(
            BuiltinPluginInfo(
                type=plugin_type,
                name=metadata.name,
                version=metadata.version,
                description=metadata.description,
                plugin_type=metadata.plugin_type.value,
                config_schema=metadata.config_schema,
            )
        )

    return builtins


@router.get("/plugins", response_model=list[PluginInfoResponse])
async def list_plugins(
    plugin_type: Optional[str] = None,
    registry: PluginRegistry = Depends(get_plugin_registry),
    principal: Principal = Depends(require_principal),
) -> list[PluginInfoResponse]:
    """
    List installed plugins.

    Optionally filter by plugin type.

    Args:
        plugin_type: Optional filter by type (policy, approval, notification, audit, webhook)
    """
    plugin_type_enum = None
    if plugin_type:
        try:
            plugin_type_enum = PluginType(plugin_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plugin type: {plugin_type}",
            )

    plugins = await registry.list_plugins(plugin_type=plugin_type_enum)

    return [
        PluginInfoResponse(
            id=p.id,
            name=p.metadata.name,
            version=p.metadata.version,
            author=p.metadata.author,
            description=p.metadata.description,
            plugin_type=p.metadata.plugin_type.value,
            enabled=p.enabled,
            installed_at=p.installed_at.isoformat(),
            config_schema=p.metadata.config_schema,
        )
        for p in plugins
    ]


@router.post("/plugins", response_model=PluginInstallResponse, status_code=status.HTTP_201_CREATED)
async def install_plugin(
    request: PluginInstallRequest,
    registry: PluginRegistry = Depends(get_plugin_registry),
    principal: Principal = Depends(require_principal),
) -> PluginInstallResponse:
    """
    Install a plugin.

    Install a built-in plugin or custom plugin class.

    Args:
        request: Plugin type and configuration

    Returns:
        Plugin ID and installation details
    """
    # Check if it's a built-in plugin
    plugin_class = BUILTIN_PLUGINS.get(request.plugin_type)

    if not plugin_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plugin type: {request.plugin_type}. Available built-ins: {list(BUILTIN_PLUGINS.keys())}",
        )

    try:
        # Install plugin
        plugin_id = await registry.register(plugin_class, request.config)

        # Get metadata
        plugin = await registry.get_plugin(plugin_id)
        metadata = plugin.metadata

        logger.info(
            f"Installed plugin {metadata.name} v{metadata.version} with ID {plugin_id}",
            extra={"principal": principal.agent_id, "plugin_id": plugin_id},
        )

        return PluginInstallResponse(
            plugin_id=plugin_id,
            name=metadata.name,
            version=metadata.version,
            message=f"Plugin {metadata.name} installed successfully",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plugin installation failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Failed to install plugin: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plugin installation failed",
        )


@router.delete("/plugins/{plugin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_plugin(
    plugin_id: str,
    registry: PluginRegistry = Depends(get_plugin_registry),
    principal: Principal = Depends(require_principal),
) -> None:
    """
    Uninstall a plugin.

    Permanently removes the plugin and its configuration.

    Args:
        plugin_id: Plugin ID to uninstall
    """
    try:
        await registry.unregister(plugin_id)

        logger.info(
            f"Uninstalled plugin {plugin_id}",
            extra={"principal": principal.agent_id, "plugin_id": plugin_id},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to uninstall plugin: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plugin uninstallation failed",
        )


@router.put("/plugins/{plugin_id}/enable", status_code=status.HTTP_204_NO_CONTENT)
async def enable_plugin(
    plugin_id: str,
    registry: PluginRegistry = Depends(get_plugin_registry),
    principal: Principal = Depends(require_principal),
) -> None:
    """
    Enable a plugin.

    Makes the plugin active for processing.

    Args:
        plugin_id: Plugin ID to enable
    """
    try:
        await registry.enable(plugin_id)

        logger.info(
            f"Enabled plugin {plugin_id}",
            extra={"principal": principal.agent_id, "plugin_id": plugin_id},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to enable plugin: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plugin enable failed",
        )


@router.put("/plugins/{plugin_id}/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_plugin(
    plugin_id: str,
    registry: PluginRegistry = Depends(get_plugin_registry),
    principal: Principal = Depends(require_principal),
) -> None:
    """
    Disable a plugin.

    Deactivates the plugin without uninstalling it.

    Args:
        plugin_id: Plugin ID to disable
    """
    try:
        await registry.disable(plugin_id)

        logger.info(
            f"Disabled plugin {plugin_id}",
            extra={"principal": principal.agent_id, "plugin_id": plugin_id},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to disable plugin: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plugin disable failed",
        )


@router.get("/plugins/{plugin_id}/config", response_model=dict[str, Any])
async def get_plugin_config(
    plugin_id: str,
    registry: PluginRegistry = Depends(get_plugin_registry),
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """
    Get plugin configuration.

    Returns the current configuration for a plugin.

    Args:
        plugin_id: Plugin ID
    """
    try:
        config = await registry.get_config(plugin_id)
        return config

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get plugin config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get plugin configuration",
        )


@router.put("/plugins/{plugin_id}/config", status_code=status.HTTP_204_NO_CONTENT)
async def update_plugin_config(
    plugin_id: str,
    request: PluginConfigUpdateRequest,
    registry: PluginRegistry = Depends(get_plugin_registry),
    principal: Principal = Depends(require_principal),
) -> None:
    """
    Update plugin configuration.

    Updates the configuration and reinitializes the plugin.

    Args:
        plugin_id: Plugin ID
        request: New configuration
    """
    try:
        await registry.update_config(plugin_id, request.config)

        logger.info(
            f"Updated config for plugin {plugin_id}",
            extra={"principal": principal.agent_id, "plugin_id": plugin_id},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to update plugin config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update plugin configuration",
        )
