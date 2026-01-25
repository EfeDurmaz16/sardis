"""
Agents resource for Sardis SDK.

This module provides both async and sync interfaces for managing agents.
Agents are the core identity entities in Sardis that can own wallets,
issue mandates, and be subject to policies.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..models import Agent, AgentCreate, AgentUpdate
from ..pagination import Page, PageInfo, create_page_from_response
from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import AsyncSardisClient, SardisClient, TimeoutConfig


class AsyncAgentsResource(AsyncBaseResource):
    """Async resource for managing agents.

    Agents are the core identity entities in Sardis. They can:
    - Own wallets
    - Issue mandates
    - Be subject to policies

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # Create an agent
            agent = await client.agents.create(
                name="my-agent",
                description="My AI agent",
            )

            # List all agents
            agents = await client.agents.list()

            # Get a specific agent
            agent = await client.agents.get("agent_123")

            # Update an agent
            agent = await client.agents.update(
                "agent_123",
                name="updated-name",
            )
        ```
    """

    async def create(
        self,
        name: str,
        description: Optional[str] = None,
        spending_limits: Optional[Dict[str, Any]] = None,
        policy: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Agent:
        """Create a new agent.

        Args:
            name: Display name for the agent
            description: Optional description
            spending_limits: Dictionary of spending limits
            policy: Dictionary of policy rules
            metadata: Arbitrary key-value metadata
            timeout: Optional request timeout

        Returns:
            The created Agent object
        """
        payload: Dict[str, Any] = {"name": name}

        if description is not None:
            payload["description"] = description
        if spending_limits is not None:
            payload["spending_limits"] = spending_limits
        if policy is not None:
            payload["policy"] = policy
        if metadata is not None:
            payload["metadata"] = metadata

        data = await self._post("agents", payload, timeout=timeout)
        return Agent.model_validate(data)

    async def get(
        self,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Agent:
        """Get an agent by ID.

        Args:
            agent_id: The ID of the agent to retrieve
            timeout: Optional request timeout

        Returns:
            The Agent object
        """
        data = await self._get(f"agents/{agent_id}", timeout=timeout)
        return Agent.model_validate(data)

    async def list(
        self,
        limit: int = 100,
        offset: Optional[int] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Agent]:
        """List all agents.

        Args:
            limit: Maximum number of agents to return
            offset: Pagination offset
            timeout: Optional request timeout

        Returns:
            List of Agent objects
        """
        params: Dict[str, Any] = {"limit": limit}
        if offset is not None:
            params["offset"] = offset

        data = await self._get("agents", params=params, timeout=timeout)

        # Handle both list response and paginated response
        if isinstance(data, list):
            return [Agent.model_validate(item) for item in data]
        return [Agent.model_validate(item) for item in data.get("agents", data.get("items", []))]

    async def list_page(
        self,
        limit: int = 100,
        offset: int = 0,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Page[Agent]:
        """List agents with pagination info.

        Args:
            limit: Maximum number of agents per page
            offset: Pagination offset
            timeout: Optional request timeout

        Returns:
            Page of Agent objects with pagination metadata
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        data = await self._get("agents", params=params, timeout=timeout)

        return create_page_from_response(
            data=data,
            items_key="agents",
            item_parser=lambda x: Agent.model_validate(x),
        )

    async def update(
        self,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Agent:
        """Update an agent.

        Args:
            agent_id: The ID of the agent to update
            name: New display name
            description: New description
            metadata: New metadata (merges with existing)
            is_active: Enable/disable the agent
            timeout: Optional request timeout

        Returns:
            The updated Agent object
        """
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if metadata is not None:
            payload["metadata"] = metadata
        if is_active is not None:
            payload["is_active"] = is_active

        data = await self._patch(f"agents/{agent_id}", payload, timeout=timeout)
        return Agent.model_validate(data)

    async def delete(
        self,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> None:
        """Delete an agent.

        Args:
            agent_id: The ID of the agent to delete
            timeout: Optional request timeout
        """
        await self._delete(f"agents/{agent_id}", timeout=timeout)


class AgentsResource(SyncBaseResource):
    """Sync resource for managing agents.

    Agents are the core identity entities in Sardis. They can:
    - Own wallets
    - Issue mandates
    - Be subject to policies

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # Create an agent
            agent = client.agents.create(
                name="my-agent",
                description="My AI agent",
            )

            # List all agents
            agents = client.agents.list()

            # Get a specific agent
            agent = client.agents.get("agent_123")

            # Update an agent
            agent = client.agents.update(
                "agent_123",
                name="updated-name",
            )
        ```
    """

    def create(
        self,
        name: str,
        description: Optional[str] = None,
        spending_limits: Optional[Dict[str, Any]] = None,
        policy: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Agent:
        """Create a new agent.

        Args:
            name: Display name for the agent
            description: Optional description
            spending_limits: Dictionary of spending limits
            policy: Dictionary of policy rules
            metadata: Arbitrary key-value metadata
            timeout: Optional request timeout

        Returns:
            The created Agent object
        """
        payload: Dict[str, Any] = {"name": name}

        if description is not None:
            payload["description"] = description
        if spending_limits is not None:
            payload["spending_limits"] = spending_limits
        if policy is not None:
            payload["policy"] = policy
        if metadata is not None:
            payload["metadata"] = metadata

        data = self._post("agents", payload, timeout=timeout)
        return Agent.model_validate(data)

    def get(
        self,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Agent:
        """Get an agent by ID.

        Args:
            agent_id: The ID of the agent to retrieve
            timeout: Optional request timeout

        Returns:
            The Agent object
        """
        data = self._get(f"agents/{agent_id}", timeout=timeout)
        return Agent.model_validate(data)

    def list(
        self,
        limit: int = 100,
        offset: Optional[int] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Agent]:
        """List all agents.

        Args:
            limit: Maximum number of agents to return
            offset: Pagination offset
            timeout: Optional request timeout

        Returns:
            List of Agent objects
        """
        params: Dict[str, Any] = {"limit": limit}
        if offset is not None:
            params["offset"] = offset

        data = self._get("agents", params=params, timeout=timeout)

        # Handle both list response and paginated response
        if isinstance(data, list):
            return [Agent.model_validate(item) for item in data]
        return [Agent.model_validate(item) for item in data.get("agents", data.get("items", []))]

    def list_page(
        self,
        limit: int = 100,
        offset: int = 0,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Page[Agent]:
        """List agents with pagination info.

        Args:
            limit: Maximum number of agents per page
            offset: Pagination offset
            timeout: Optional request timeout

        Returns:
            Page of Agent objects with pagination metadata
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        data = self._get("agents", params=params, timeout=timeout)

        return create_page_from_response(
            data=data,
            items_key="agents",
            item_parser=lambda x: Agent.model_validate(x),
        )

    def update(
        self,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Agent:
        """Update an agent.

        Args:
            agent_id: The ID of the agent to update
            name: New display name
            description: New description
            metadata: New metadata (merges with existing)
            is_active: Enable/disable the agent
            timeout: Optional request timeout

        Returns:
            The updated Agent object
        """
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if metadata is not None:
            payload["metadata"] = metadata
        if is_active is not None:
            payload["is_active"] = is_active

        data = self._patch(f"agents/{agent_id}", payload, timeout=timeout)
        return Agent.model_validate(data)

    def delete(
        self,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> None:
        """Delete an agent.

        Args:
            agent_id: The ID of the agent to delete
            timeout: Optional request timeout
        """
        self._delete(f"agents/{agent_id}", timeout=timeout)


__all__ = [
    "AsyncAgentsResource",
    "AgentsResource",
]
