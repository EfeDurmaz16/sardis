"""
Groups resource for Sardis SDK.

This module provides both async and sync interfaces for managing agent groups.
Agent groups enable multi-agent governance with shared budgets and merchant policies.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..models.group import AgentGroup
from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import AsyncSardisClient, SardisClient, TimeoutConfig


class AsyncGroupsResource(AsyncBaseResource):
    """Async resource for managing agent groups.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            group = await client.groups.create(name="engineering-team")
            await client.groups.add_agent(group.group_id, "agent_abc")
        ```
    """

    async def create(
        self,
        name: str,
        budget: Optional[Dict[str, Any]] = None,
        merchant_policy: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> AgentGroup:
        """Create a new agent group."""
        payload: Dict[str, Any] = {"name": name}
        if budget is not None:
            payload["budget"] = budget
        if merchant_policy is not None:
            payload["merchant_policy"] = merchant_policy
        if metadata is not None:
            payload["metadata"] = metadata

        data = await self._post("groups", payload, timeout=timeout)
        return AgentGroup.model_validate(data)

    async def get(
        self,
        group_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> AgentGroup:
        """Get a group by ID."""
        data = await self._get(f"groups/{group_id}", timeout=timeout)
        return AgentGroup.model_validate(data)

    async def list(
        self,
        limit: int = 50,
        offset: Optional[int] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[AgentGroup]:
        """List all agent groups."""
        params: Dict[str, Any] = {"limit": limit}
        if offset is not None:
            params["offset"] = offset

        data = await self._get("groups", params=params, timeout=timeout)
        if isinstance(data, list):
            return [AgentGroup.model_validate(item) for item in data]
        return [AgentGroup.model_validate(item) for item in data.get("groups", data.get("items", []))]

    async def update(
        self,
        group_id: str,
        name: Optional[str] = None,
        budget: Optional[Dict[str, Any]] = None,
        merchant_policy: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> AgentGroup:
        """Update a group."""
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if budget is not None:
            payload["budget"] = budget
        if merchant_policy is not None:
            payload["merchant_policy"] = merchant_policy
        if metadata is not None:
            payload["metadata"] = metadata

        data = await self._patch(f"groups/{group_id}", payload, timeout=timeout)
        return AgentGroup.model_validate(data)

    async def delete(
        self,
        group_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> None:
        """Delete a group."""
        await self._delete(f"groups/{group_id}", timeout=timeout)

    async def add_agent(
        self,
        group_id: str,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> AgentGroup:
        """Add an agent to a group."""
        data = await self._post(
            f"groups/{group_id}/agents",
            {"agent_id": agent_id},
            timeout=timeout,
        )
        return AgentGroup.model_validate(data)

    async def remove_agent(
        self,
        group_id: str,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> AgentGroup:
        """Remove an agent from a group."""
        data = await self._delete(
            f"groups/{group_id}/agents/{agent_id}",
            timeout=timeout,
        )
        return AgentGroup.model_validate(data)

    async def get_spending(
        self,
        group_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        """Get current spending for a group."""
        return await self._get(f"groups/{group_id}/spending", timeout=timeout)


class GroupsResource(SyncBaseResource):
    """Sync resource for managing agent groups.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            group = client.groups.create(name="engineering-team")
            client.groups.add_agent(group.group_id, "agent_abc")
        ```
    """

    def create(
        self,
        name: str,
        budget: Optional[Dict[str, Any]] = None,
        merchant_policy: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> AgentGroup:
        """Create a new agent group."""
        payload: Dict[str, Any] = {"name": name}
        if budget is not None:
            payload["budget"] = budget
        if merchant_policy is not None:
            payload["merchant_policy"] = merchant_policy
        if metadata is not None:
            payload["metadata"] = metadata

        data = self._post("groups", payload, timeout=timeout)
        return AgentGroup.model_validate(data)

    def get(
        self,
        group_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> AgentGroup:
        """Get a group by ID."""
        data = self._get(f"groups/{group_id}", timeout=timeout)
        return AgentGroup.model_validate(data)

    def list(
        self,
        limit: int = 50,
        offset: Optional[int] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[AgentGroup]:
        """List all agent groups."""
        params: Dict[str, Any] = {"limit": limit}
        if offset is not None:
            params["offset"] = offset

        data = self._get("groups", params=params, timeout=timeout)
        if isinstance(data, list):
            return [AgentGroup.model_validate(item) for item in data]
        return [AgentGroup.model_validate(item) for item in data.get("groups", data.get("items", []))]

    def update(
        self,
        group_id: str,
        name: Optional[str] = None,
        budget: Optional[Dict[str, Any]] = None,
        merchant_policy: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> AgentGroup:
        """Update a group."""
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if budget is not None:
            payload["budget"] = budget
        if merchant_policy is not None:
            payload["merchant_policy"] = merchant_policy
        if metadata is not None:
            payload["metadata"] = metadata

        data = self._patch(f"groups/{group_id}", payload, timeout=timeout)
        return AgentGroup.model_validate(data)

    def delete(
        self,
        group_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> None:
        """Delete a group."""
        self._delete(f"groups/{group_id}", timeout=timeout)

    def add_agent(
        self,
        group_id: str,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> AgentGroup:
        """Add an agent to a group."""
        data = self._post(
            f"groups/{group_id}/agents",
            {"agent_id": agent_id},
            timeout=timeout,
        )
        return AgentGroup.model_validate(data)

    def remove_agent(
        self,
        group_id: str,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> AgentGroup:
        """Remove an agent from a group."""
        data = self._delete(
            f"groups/{group_id}/agents/{agent_id}",
            timeout=timeout,
        )
        return AgentGroup.model_validate(data)

    def get_spending(
        self,
        group_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        """Get current spending for a group."""
        return self._get(f"groups/{group_id}/spending", timeout=timeout)


__all__ = [
    "AsyncGroupsResource",
    "GroupsResource",
]
