from __future__ import annotations

from typing import Any, List, Optional

from ..models import Agent, AgentCreate, AgentUpdate
from .base import Resource


class AgentsResource(Resource):
    """
    Resource for managing agents.
    
    Agents are the core identity entities in Sardis. They can:
    - Own wallets
    - Issue mandates
    - Be subject to policies
    """
    
    async def create(
        self,
        name: str,
        description: Optional[str] = None,
        spending_limits: Optional[dict[str, Any]] = None,
        policy: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Agent:
        """
        Create a new agent.
        
        Args:
            name: Display name for the agent
            description: Optional description
            spending_limits: Dictionary of spending limits
            policy: Dictionary of policy rules
            metadata: Arbitrary key-value metadata
        
        Returns:
            The created Agent object
        """
        payload = {
            "name": name,
            "description": description,
            "spending_limits": spending_limits,
            "policy": policy,
            "metadata": metadata or {},
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        data = await self._client._request("POST", "agents", json=payload)
        return Agent.parse_obj(data)

    async def get(self, agent_id: str) -> Agent:
        """
        Get an agent by ID.
        
        Args:
            agent_id: The ID of the agent to retrieve
        
        Returns:
            The Agent object
        """
        data = await self._client._request("GET", f"agents/{agent_id}")
        return Agent.parse_obj(data)

    async def list(
        self,
        limit: int = 100,
        cursor: Optional[int] = None,
    ) -> List[Agent]:
        """
        List all agents.
        
        Args:
            limit: Maximum number of agents to return
            cursor: Pagination offset (int)
            
        Returns:
            List of Agent objects
        """
        params = {"limit": limit}
        if cursor is not None:
            params["offset"] = cursor
            
        data = await self._client._request("GET", "agents", params=params)
        return [Agent.parse_obj(item) for item in data]

    async def update(
        self,
        agent_id: str,
        name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        is_active: Optional[bool] = None,
    ) -> Agent:
        """
        Update an agent.
        
        Args:
            agent_id: The ID of the agent to update
            name: New display name
            metadata: New metadata (merges with existing)
            is_active: Enable/disable the agent
            
        Returns:
            The updated Agent object
        """
        payload = {}
        if name is not None:
            payload["name"] = name
        if metadata is not None:
            payload["metadata"] = metadata
        if is_active is not None:
            payload["is_active"] = is_active
            
        data = await self._client._request("PATCH", f"/agents/{agent_id}", json=payload)
        return Agent.parse_obj(data)
