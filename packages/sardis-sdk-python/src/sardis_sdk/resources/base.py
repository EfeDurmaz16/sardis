"""
Base resource classes for Sardis SDK.

This module provides the foundation for all API resource classes,
supporting both synchronous and asynchronous clients with full type hints.
"""
from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from ..client import RequestContext, TimeoutConfig
from ..pagination import AsyncPaginator, Page, PageInfo, SyncPaginator, create_page_from_response

if TYPE_CHECKING:
    from ..client import AsyncSardisClient, SardisClient

# Type variable for model types
T = TypeVar("T")


class AsyncBaseResource:
    """Base class for async API resources.

    Provides common methods for making HTTP requests to the API.
    All resource-specific classes should inherit from this class
    when working with the AsyncSardisClient.

    Attributes:
        _client: The async client instance
    """

    def __init__(self, client: "AsyncSardisClient") -> None:
        """Initialize the resource.

        Args:
            client: The async client instance
        """
        self._client = client

    async def _get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        context: Optional[RequestContext] = None,
    ) -> Dict[str, Any]:
        """Make a GET request.

        Args:
            path: API endpoint path
            params: Query parameters
            timeout: Optional timeout override
            context: Optional request context

        Returns:
            Response data as dictionary
        """
        return await self._client._request(
            "GET",
            path,
            params=params,
            timeout=timeout,
            context=context,
        )

    async def _post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        context: Optional[RequestContext] = None,
    ) -> Dict[str, Any]:
        """Make a POST request.

        Args:
            path: API endpoint path
            data: Request body
            timeout: Optional timeout override
            context: Optional request context

        Returns:
            Response data as dictionary
        """
        return await self._client._request(
            "POST",
            path,
            json=data,
            timeout=timeout,
            context=context,
        )

    async def _put(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        context: Optional[RequestContext] = None,
    ) -> Dict[str, Any]:
        """Make a PUT request.

        Args:
            path: API endpoint path
            data: Request body
            timeout: Optional timeout override
            context: Optional request context

        Returns:
            Response data as dictionary
        """
        return await self._client._request(
            "PUT",
            path,
            json=data,
            timeout=timeout,
            context=context,
        )

    async def _patch(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        context: Optional[RequestContext] = None,
    ) -> Dict[str, Any]:
        """Make a PATCH request.

        Args:
            path: API endpoint path
            data: Request body
            timeout: Optional timeout override
            context: Optional request context

        Returns:
            Response data as dictionary
        """
        return await self._client._request(
            "PATCH",
            path,
            json=data,
            timeout=timeout,
            context=context,
        )

    async def _delete(
        self,
        path: str,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        context: Optional[RequestContext] = None,
    ) -> Dict[str, Any]:
        """Make a DELETE request.

        Args:
            path: API endpoint path
            timeout: Optional timeout override
            context: Optional request context

        Returns:
            Response data as dictionary
        """
        return await self._client._request(
            "DELETE",
            path,
            timeout=timeout,
            context=context,
        )

    def _create_paginator(
        self,
        fetch_page: Callable[..., Page[T]],
        initial_params: Optional[Dict[str, Any]] = None,
        max_items: Optional[int] = None,
        max_pages: Optional[int] = None,
    ) -> AsyncPaginator[T]:
        """Create an async paginator for list operations.

        Args:
            fetch_page: Function to fetch a single page
            initial_params: Initial parameters for pagination
            max_items: Maximum items to fetch
            max_pages: Maximum pages to fetch

        Returns:
            AsyncPaginator instance
        """
        return AsyncPaginator(
            fetch_page=fetch_page,
            initial_params=initial_params,
            max_items=max_items,
            max_pages=max_pages,
        )


class SyncBaseResource:
    """Base class for sync API resources.

    Provides common methods for making HTTP requests to the API.
    All resource-specific classes should inherit from this class
    when working with the synchronous SardisClient.

    Attributes:
        _client: The sync client instance
    """

    def __init__(self, client: "SardisClient") -> None:
        """Initialize the resource.

        Args:
            client: The sync client instance
        """
        self._client = client

    def _get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        context: Optional[RequestContext] = None,
    ) -> Dict[str, Any]:
        """Make a GET request.

        Args:
            path: API endpoint path
            params: Query parameters
            timeout: Optional timeout override
            context: Optional request context

        Returns:
            Response data as dictionary
        """
        return self._client._request(
            "GET",
            path,
            params=params,
            timeout=timeout,
            context=context,
        )

    def _post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        context: Optional[RequestContext] = None,
    ) -> Dict[str, Any]:
        """Make a POST request.

        Args:
            path: API endpoint path
            data: Request body
            timeout: Optional timeout override
            context: Optional request context

        Returns:
            Response data as dictionary
        """
        return self._client._request(
            "POST",
            path,
            json=data,
            timeout=timeout,
            context=context,
        )

    def _put(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        context: Optional[RequestContext] = None,
    ) -> Dict[str, Any]:
        """Make a PUT request.

        Args:
            path: API endpoint path
            data: Request body
            timeout: Optional timeout override
            context: Optional request context

        Returns:
            Response data as dictionary
        """
        return self._client._request(
            "PUT",
            path,
            json=data,
            timeout=timeout,
            context=context,
        )

    def _patch(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        context: Optional[RequestContext] = None,
    ) -> Dict[str, Any]:
        """Make a PATCH request.

        Args:
            path: API endpoint path
            data: Request body
            timeout: Optional timeout override
            context: Optional request context

        Returns:
            Response data as dictionary
        """
        return self._client._request(
            "PATCH",
            path,
            json=data,
            timeout=timeout,
            context=context,
        )

    def _delete(
        self,
        path: str,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        context: Optional[RequestContext] = None,
    ) -> Dict[str, Any]:
        """Make a DELETE request.

        Args:
            path: API endpoint path
            timeout: Optional timeout override
            context: Optional request context

        Returns:
            Response data as dictionary
        """
        return self._client._request(
            "DELETE",
            path,
            timeout=timeout,
            context=context,
        )

    def _create_paginator(
        self,
        fetch_page: Callable[..., Page[T]],
        initial_params: Optional[Dict[str, Any]] = None,
        max_items: Optional[int] = None,
        max_pages: Optional[int] = None,
    ) -> SyncPaginator[T]:
        """Create a sync paginator for list operations.

        Args:
            fetch_page: Function to fetch a single page
            initial_params: Initial parameters for pagination
            max_items: Maximum items to fetch
            max_pages: Maximum pages to fetch

        Returns:
            SyncPaginator instance
        """
        return SyncPaginator(
            fetch_page=fetch_page,
            initial_params=initial_params,
            max_items=max_items,
            max_pages=max_pages,
        )


# Legacy aliases for backwards compatibility
BaseResource = AsyncBaseResource
Resource = AsyncBaseResource


__all__ = [
    "AsyncBaseResource",
    "SyncBaseResource",
    "BaseResource",
    "Resource",
]
