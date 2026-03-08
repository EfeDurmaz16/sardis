"""Approvals resource for Sardis SDK."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from .base import AsyncBaseResource, SyncBaseResource

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import TimeoutConfig


class AsyncApprovalsResource(AsyncBaseResource):
    """Manage approval workflows."""

    async def list_pending(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Dict[str, Any]]:
        """List pending approvals."""
        data = await self._get("approvals/pending", timeout=timeout)
        if isinstance(data, list):
            return data
        return data.get("approvals", data.get("items", []))

    async def list(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Dict[str, Any]]:
        """List approvals with optional filters."""
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        data = await self._get("approvals", params=params, timeout=timeout)
        if isinstance(data, list):
            return data
        return data.get("approvals", data.get("items", []))

    async def get(
        self,
        approval_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        """Get approval details."""
        return await self._get(f"approvals/{approval_id}", timeout=timeout)

    async def approve(
        self,
        approval_id: str,
        *,
        notes: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        """Approve a pending approval."""
        payload: Dict[str, Any] = {}
        if notes:
            payload["notes"] = notes
        return await self._post(f"approvals/{approval_id}/approve", payload, timeout=timeout)

    async def deny(
        self,
        approval_id: str,
        *,
        reason: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        """Deny a pending approval."""
        payload: Dict[str, Any] = {}
        if reason:
            payload["reason"] = reason
        return await self._post(f"approvals/{approval_id}/reject", payload, timeout=timeout)


class ApprovalsResource(SyncBaseResource):
    """Manage approval workflows."""

    def list_pending(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Dict[str, Any]]:
        """List pending approvals."""
        data = self._get("approvals/pending", timeout=timeout)
        if isinstance(data, list):
            return data
        return data.get("approvals", data.get("items", []))

    def list(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Dict[str, Any]]:
        """List approvals with optional filters."""
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        data = self._get("approvals", params=params, timeout=timeout)
        if isinstance(data, list):
            return data
        return data.get("approvals", data.get("items", []))

    def get(
        self,
        approval_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        """Get approval details."""
        return self._get(f"approvals/{approval_id}", timeout=timeout)

    def approve(
        self,
        approval_id: str,
        *,
        notes: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        """Approve a pending approval."""
        payload: Dict[str, Any] = {}
        if notes:
            payload["notes"] = notes
        return self._post(f"approvals/{approval_id}/approve", payload, timeout=timeout)

    def deny(
        self,
        approval_id: str,
        *,
        reason: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        """Deny a pending approval."""
        payload: Dict[str, Any] = {}
        if reason:
            payload["reason"] = reason
        return self._post(f"approvals/{approval_id}/reject", payload, timeout=timeout)
