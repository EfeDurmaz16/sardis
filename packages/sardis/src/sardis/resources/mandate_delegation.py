"""
Mandate delegation resource for Sardis SDK.

Sardis Protocol v1.0 -- Delegate spending mandates to sub-agents with
scoped authority. Supports hierarchical delegation trees for
multi-agent workflows.

This module provides both async and sync interfaces.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import TimeoutConfig


class AsyncMandateDelegationResource(AsyncBaseResource):
    """Async resource for mandate delegation operations.

    Delegate mandates to sub-agents and inspect delegation
    hierarchies.

    Example:
        ```python
        async with AsyncSardis(api_key="...") as client:
            # Delegate a mandate to a sub-agent
            delegation = await client.mandate_delegation.delegate(
                mandate_id="mnd_abc123",
                delegate_agent_id="agt_sub001",
                max_amount="500.00",
                allowed_tokens=["USDC"],
            )

            # View the delegation tree
            tree = await client.mandate_delegation.get_tree(
                mandate_id="mnd_abc123",
            )
        ```
    """

    async def delegate(
        self,
        mandate_id: str,
        delegate_agent_id: str,
        max_amount: str | None = None,
        allowed_tokens: list[str] | None = None,
        allowed_chains: list[str] | None = None,
        expires_at: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Delegate a mandate to a sub-agent.

        Creates a child mandate with scoped authority derived from
        the parent mandate. The child mandate cannot exceed the
        parent's remaining limits.

        Args:
            mandate_id: Parent mandate ID to delegate from
            delegate_agent_id: Agent ID to delegate to
            max_amount: Optional maximum amount for the child mandate
            allowed_tokens: Optional list of allowed tokens
            allowed_chains: Optional list of allowed chains
            expires_at: Optional expiry timestamp (ISO 8601)
            metadata: Optional metadata dict
            timeout: Optional request timeout

        Returns:
            Delegation result with child mandate details
        """
        payload: dict[str, Any] = {
            "delegate_agent_id": delegate_agent_id,
        }

        if max_amount is not None:
            payload["max_amount"] = max_amount

        if allowed_tokens is not None:
            payload["allowed_tokens"] = allowed_tokens

        if allowed_chains is not None:
            payload["allowed_chains"] = allowed_chains

        if expires_at is not None:
            payload["expires_at"] = expires_at

        if metadata is not None:
            payload["metadata"] = metadata

        return await self._post(
            f"mandates/{mandate_id}/delegate", payload, timeout=timeout
        )

    async def get_tree(
        self,
        mandate_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get the delegation tree for a mandate.

        Returns the full hierarchy of delegated mandates rooted at
        the specified mandate, including consumption status at each level.

        Args:
            mandate_id: Root mandate ID
            timeout: Optional request timeout

        Returns:
            Delegation tree with nested children and consumption data
        """
        return await self._get(
            f"mandates/{mandate_id}/tree", timeout=timeout
        )


class MandateDelegationResource(SyncBaseResource):
    """Sync resource for mandate delegation operations.

    Delegate mandates to sub-agents and inspect delegation
    hierarchies.

    Example:
        ```python
        with Sardis(api_key="...") as client:
            # Delegate a mandate to a sub-agent
            delegation = client.mandate_delegation.delegate(
                mandate_id="mnd_abc123",
                delegate_agent_id="agt_sub001",
                max_amount="500.00",
                allowed_tokens=["USDC"],
            )

            # View the delegation tree
            tree = client.mandate_delegation.get_tree(
                mandate_id="mnd_abc123",
            )
        ```
    """

    def delegate(
        self,
        mandate_id: str,
        delegate_agent_id: str,
        max_amount: str | None = None,
        allowed_tokens: list[str] | None = None,
        allowed_chains: list[str] | None = None,
        expires_at: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Delegate a mandate to a sub-agent.

        Creates a child mandate with scoped authority derived from
        the parent mandate. The child mandate cannot exceed the
        parent's remaining limits.

        Args:
            mandate_id: Parent mandate ID to delegate from
            delegate_agent_id: Agent ID to delegate to
            max_amount: Optional maximum amount for the child mandate
            allowed_tokens: Optional list of allowed tokens
            allowed_chains: Optional list of allowed chains
            expires_at: Optional expiry timestamp (ISO 8601)
            metadata: Optional metadata dict
            timeout: Optional request timeout

        Returns:
            Delegation result with child mandate details
        """
        payload: dict[str, Any] = {
            "delegate_agent_id": delegate_agent_id,
        }

        if max_amount is not None:
            payload["max_amount"] = max_amount

        if allowed_tokens is not None:
            payload["allowed_tokens"] = allowed_tokens

        if allowed_chains is not None:
            payload["allowed_chains"] = allowed_chains

        if expires_at is not None:
            payload["expires_at"] = expires_at

        if metadata is not None:
            payload["metadata"] = metadata

        return self._post(
            f"mandates/{mandate_id}/delegate", payload, timeout=timeout
        )

    def get_tree(
        self,
        mandate_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get the delegation tree for a mandate.

        Returns the full hierarchy of delegated mandates rooted at
        the specified mandate, including consumption status at each level.

        Args:
            mandate_id: Root mandate ID
            timeout: Optional request timeout

        Returns:
            Delegation tree with nested children and consumption data
        """
        return self._get(
            f"mandates/{mandate_id}/tree", timeout=timeout
        )


__all__ = [
    "AsyncMandateDelegationResource",
    "MandateDelegationResource",
]
