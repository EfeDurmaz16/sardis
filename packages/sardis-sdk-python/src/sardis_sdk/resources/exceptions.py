"""Exceptions resource for Sardis SDK."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    import builtins

    from ..client import TimeoutConfig


class AsyncExceptionsResource(AsyncBaseResource):
    """Manage payment and policy exceptions requiring human review."""

    async def list(
        self,
        *,
        agent_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """List exceptions with optional filters.

        Args:
            agent_id: Optional agent ID to filter exceptions.
            status: Optional status filter (e.g. "open", "resolved", "escalated").
            limit: Maximum number of exceptions to return.
            timeout: Optional timeout override.
        """
        params: dict[str, Any] = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        if status:
            params["status"] = status
        data = await self._get("exceptions", params=params, timeout=timeout)
        if isinstance(data, list):
            return data
        return data.get("exceptions", data.get("items", []))

    async def get(
        self,
        exception_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get exception details.

        Args:
            exception_id: The exception ID.
            timeout: Optional timeout override.
        """
        return await self._get(f"exceptions/{exception_id}", timeout=timeout)

    async def resolve(
        self,
        exception_id: str,
        *,
        notes: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Mark an exception as resolved.

        Args:
            exception_id: The exception ID.
            notes: Optional resolution notes.
            timeout: Optional timeout override.
        """
        payload: dict[str, Any] = {}
        if notes:
            payload["notes"] = notes
        return await self._post(f"exceptions/{exception_id}/resolve", payload, timeout=timeout)

    async def escalate(
        self,
        exception_id: str,
        *,
        notes: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Escalate an exception for higher-level review.

        Args:
            exception_id: The exception ID.
            notes: Optional escalation notes.
            timeout: Optional timeout override.
        """
        payload: dict[str, Any] = {}
        if notes:
            payload["notes"] = notes
        return await self._post(f"exceptions/{exception_id}/escalate", payload, timeout=timeout)

    async def retry(
        self,
        exception_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Retry the failed operation associated with an exception.

        Args:
            exception_id: The exception ID.
            timeout: Optional timeout override.
        """
        return await self._post(f"exceptions/{exception_id}/retry", timeout=timeout)


class ExceptionsResource(SyncBaseResource):
    """Manage payment and policy exceptions requiring human review."""

    def list(
        self,
        *,
        agent_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """List exceptions with optional filters.

        Args:
            agent_id: Optional agent ID to filter exceptions.
            status: Optional status filter (e.g. "open", "resolved", "escalated").
            limit: Maximum number of exceptions to return.
            timeout: Optional timeout override.
        """
        params: dict[str, Any] = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        if status:
            params["status"] = status
        data = self._get("exceptions", params=params, timeout=timeout)
        if isinstance(data, list):
            return data
        return data.get("exceptions", data.get("items", []))

    def get(
        self,
        exception_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get exception details.

        Args:
            exception_id: The exception ID.
            timeout: Optional timeout override.
        """
        return self._get(f"exceptions/{exception_id}", timeout=timeout)

    def resolve(
        self,
        exception_id: str,
        *,
        notes: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Mark an exception as resolved.

        Args:
            exception_id: The exception ID.
            notes: Optional resolution notes.
            timeout: Optional timeout override.
        """
        payload: dict[str, Any] = {}
        if notes:
            payload["notes"] = notes
        return self._post(f"exceptions/{exception_id}/resolve", payload, timeout=timeout)

    def escalate(
        self,
        exception_id: str,
        *,
        notes: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Escalate an exception for higher-level review.

        Args:
            exception_id: The exception ID.
            notes: Optional escalation notes.
            timeout: Optional timeout override.
        """
        payload: dict[str, Any] = {}
        if notes:
            payload["notes"] = notes
        return self._post(f"exceptions/{exception_id}/escalate", payload, timeout=timeout)

    def retry(
        self,
        exception_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Retry the failed operation associated with an exception.

        Args:
            exception_id: The exception ID.
            timeout: Optional timeout override.
        """
        return self._post(f"exceptions/{exception_id}/retry", timeout=timeout)
