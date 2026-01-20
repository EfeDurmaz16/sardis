"""Base resource class for Sardis SDK."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..client import SardisClient


class BaseResource:
    """Base class for API resources."""
    
    def __init__(self, client: "SardisClient"):
        self._client = client
    
    async def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Make a GET request."""
        return await self._client._request("GET", path, params=params)
    
    async def _post(self, path: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Make a POST request."""
        return await self._client._request("POST", path, json=data)
    
    async def _patch(self, path: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Make a PATCH request."""
        return await self._client._request("PATCH", path, json=data)
    
    async def _delete(self, path: str) -> dict[str, Any]:
        """Make a DELETE request."""
        return await self._client._request("DELETE", path)


# Alias
Resource = BaseResource
