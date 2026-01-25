"""
Pagination utilities for the Sardis SDK.

This module provides helpers for working with paginated API responses,
including automatic iteration, cursor management, and bulk fetching.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    TypeVar,
    Union,
)

# Type variable for paginated items
T = TypeVar("T")


@dataclass
class PageInfo:
    """Information about a page of results.

    Attributes:
        has_next: Whether there are more pages
        has_previous: Whether there are previous pages
        total_count: Total number of items (if known)
        page_size: Number of items per page
        current_page: Current page number (1-indexed)
        total_pages: Total number of pages (if known)
        next_cursor: Cursor for the next page
        previous_cursor: Cursor for the previous page
    """

    has_next: bool = False
    has_previous: bool = False
    total_count: Optional[int] = None
    page_size: int = 0
    current_page: int = 1
    total_pages: Optional[int] = None
    next_cursor: Optional[str] = None
    previous_cursor: Optional[str] = None

    @classmethod
    def from_response(cls, data: Dict[str, Any]) -> "PageInfo":
        """Create PageInfo from API response.

        Args:
            data: Response data containing pagination info

        Returns:
            PageInfo instance
        """
        pagination = data.get("pagination", data.get("meta", {}))

        return cls(
            has_next=pagination.get("has_next", False),
            has_previous=pagination.get("has_previous", False),
            total_count=pagination.get("total_count") or pagination.get("total"),
            page_size=pagination.get("page_size") or pagination.get("limit", 0),
            current_page=pagination.get("current_page") or pagination.get("page", 1),
            total_pages=pagination.get("total_pages"),
            next_cursor=pagination.get("next_cursor") or pagination.get("next"),
            previous_cursor=pagination.get("previous_cursor") or pagination.get("previous"),
        )


@dataclass
class Page(Generic[T]):
    """A single page of results.

    Attributes:
        items: List of items on this page
        page_info: Pagination metadata
        raw_response: The raw API response (for debugging)
    """

    items: List[T]
    page_info: PageInfo
    raw_response: Optional[Dict[str, Any]] = None

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[T]:
        return iter(self.items)

    def __getitem__(self, index: int) -> T:
        return self.items[index]

    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        return self.page_info.has_next

    @property
    def has_previous(self) -> bool:
        """Check if there are previous pages."""
        return self.page_info.has_previous

    @property
    def is_empty(self) -> bool:
        """Check if the page is empty."""
        return len(self.items) == 0

    @property
    def total_count(self) -> Optional[int]:
        """Get total count if available."""
        return self.page_info.total_count


class AsyncPaginator(Generic[T]):
    """Async paginator for iterating through paginated results.

    This class provides an async iterator that automatically fetches
    subsequent pages as needed.

    Example:
        ```python
        paginator = client.agents.list_paginated(limit=50)

        async for agent in paginator:
            print(agent.name)

        # Or fetch all at once
        all_agents = await paginator.all()

        # Or fetch pages one at a time
        async for page in paginator.pages():
            print(f"Page {page.page_info.current_page}: {len(page)} items")
        ```
    """

    def __init__(
        self,
        fetch_page: Callable[..., Awaitable[Page[T]]],
        initial_params: Optional[Dict[str, Any]] = None,
        max_items: Optional[int] = None,
        max_pages: Optional[int] = None,
    ):
        """Initialize the paginator.

        Args:
            fetch_page: Async function that fetches a page of results
            initial_params: Initial parameters for the first request
            max_items: Maximum number of items to fetch (None for unlimited)
            max_pages: Maximum number of pages to fetch (None for unlimited)
        """
        self._fetch_page = fetch_page
        self._initial_params = initial_params or {}
        self._max_items = max_items
        self._max_pages = max_pages
        self._current_page: Optional[Page[T]] = None
        self._items_fetched = 0
        self._pages_fetched = 0

    async def __aiter__(self) -> AsyncIterator[T]:
        """Async iterator over all items across all pages."""
        async for page in self.pages():
            for item in page.items:
                if self._max_items and self._items_fetched >= self._max_items:
                    return
                yield item
                self._items_fetched += 1

    async def pages(self) -> AsyncIterator[Page[T]]:
        """Async iterator over pages."""
        params = self._initial_params.copy()
        cursor: Optional[str] = None

        while True:
            if self._max_pages and self._pages_fetched >= self._max_pages:
                break

            if cursor:
                params["cursor"] = cursor
            elif "offset" in params:
                # Offset-based pagination
                pass
            else:
                # First page, no cursor needed
                pass

            page = await self._fetch_page(**params)
            self._current_page = page
            self._pages_fetched += 1

            yield page

            if not page.has_next or page.is_empty:
                break

            # Update cursor or offset for next page
            if page.page_info.next_cursor:
                cursor = page.page_info.next_cursor
            elif "offset" in params:
                params["offset"] = params.get("offset", 0) + len(page.items)
            else:
                break

    async def first_page(self) -> Page[T]:
        """Fetch only the first page.

        Returns:
            The first page of results
        """
        async for page in self.pages():
            return page
        return Page(items=[], page_info=PageInfo())

    async def all(self) -> List[T]:
        """Fetch all items across all pages.

        Returns:
            List of all items

        Warning:
            This can be slow and memory-intensive for large datasets.
            Consider using the async iterator or setting max_items.
        """
        items: List[T] = []
        async for item in self:
            items.append(item)
        return items

    async def take(self, n: int) -> List[T]:
        """Fetch up to n items.

        Args:
            n: Maximum number of items to fetch

        Returns:
            List of up to n items
        """
        items: List[T] = []
        count = 0
        async for item in self:
            items.append(item)
            count += 1
            if count >= n:
                break
        return items

    async def count(self) -> int:
        """Count total items (fetches first page if total_count available).

        Returns:
            Total count of items, or count from iterating if not available

        Note:
            If total_count is not available from the API, this will
            iterate through all pages to count items.
        """
        page = await self.first_page()
        if page.total_count is not None:
            return page.total_count

        # Fall back to counting all items
        total = len(page.items)
        async for p in self.pages():
            if p != page:  # Skip first page, already counted
                total += len(p.items)
        return total


class SyncPaginator(Generic[T]):
    """Sync paginator for iterating through paginated results.

    This class provides a synchronous iterator that automatically fetches
    subsequent pages as needed.

    Example:
        ```python
        paginator = client.agents.list_paginated(limit=50)

        for agent in paginator:
            print(agent.name)

        # Or fetch all at once
        all_agents = paginator.all()

        # Or fetch pages one at a time
        for page in paginator.pages():
            print(f"Page {page.page_info.current_page}: {len(page)} items")
        ```
    """

    def __init__(
        self,
        fetch_page: Callable[..., Page[T]],
        initial_params: Optional[Dict[str, Any]] = None,
        max_items: Optional[int] = None,
        max_pages: Optional[int] = None,
    ):
        """Initialize the paginator.

        Args:
            fetch_page: Function that fetches a page of results
            initial_params: Initial parameters for the first request
            max_items: Maximum number of items to fetch (None for unlimited)
            max_pages: Maximum number of pages to fetch (None for unlimited)
        """
        self._fetch_page = fetch_page
        self._initial_params = initial_params or {}
        self._max_items = max_items
        self._max_pages = max_pages
        self._current_page: Optional[Page[T]] = None
        self._items_fetched = 0
        self._pages_fetched = 0

    def __iter__(self) -> Iterator[T]:
        """Iterator over all items across all pages."""
        for page in self.pages():
            for item in page.items:
                if self._max_items and self._items_fetched >= self._max_items:
                    return
                yield item
                self._items_fetched += 1

    def pages(self) -> Iterator[Page[T]]:
        """Iterator over pages."""
        params = self._initial_params.copy()
        cursor: Optional[str] = None

        while True:
            if self._max_pages and self._pages_fetched >= self._max_pages:
                break

            if cursor:
                params["cursor"] = cursor
            elif "offset" in params:
                # Offset-based pagination
                pass
            else:
                # First page, no cursor needed
                pass

            page = self._fetch_page(**params)
            self._current_page = page
            self._pages_fetched += 1

            yield page

            if not page.has_next or page.is_empty:
                break

            # Update cursor or offset for next page
            if page.page_info.next_cursor:
                cursor = page.page_info.next_cursor
            elif "offset" in params:
                params["offset"] = params.get("offset", 0) + len(page.items)
            else:
                break

    def first_page(self) -> Page[T]:
        """Fetch only the first page.

        Returns:
            The first page of results
        """
        for page in self.pages():
            return page
        return Page(items=[], page_info=PageInfo())

    def all(self) -> List[T]:
        """Fetch all items across all pages.

        Returns:
            List of all items

        Warning:
            This can be slow and memory-intensive for large datasets.
            Consider using the iterator or setting max_items.
        """
        return list(self)

    def take(self, n: int) -> List[T]:
        """Fetch up to n items.

        Args:
            n: Maximum number of items to fetch

        Returns:
            List of up to n items
        """
        items: List[T] = []
        count = 0
        for item in self:
            items.append(item)
            count += 1
            if count >= n:
                break
        return items

    def count(self) -> int:
        """Count total items (fetches first page if total_count available).

        Returns:
            Total count of items, or count from iterating if not available

        Note:
            If total_count is not available from the API, this will
            iterate through all pages to count items.
        """
        page = self.first_page()
        if page.total_count is not None:
            return page.total_count

        # Fall back to counting all items
        total = len(page.items)
        for p in self.pages():
            if p != page:  # Skip first page, already counted
                total += len(p.items)
        return total


def create_page_from_response(
    data: Dict[str, Any],
    items_key: str,
    item_parser: Callable[[Dict[str, Any]], T],
) -> Page[T]:
    """Create a Page from an API response.

    Args:
        data: Raw API response
        items_key: Key containing the list of items
        item_parser: Function to parse each item

    Returns:
        Page instance with parsed items
    """
    raw_items = data.get(items_key, [])
    items = [item_parser(item) for item in raw_items]
    page_info = PageInfo.from_response(data)

    # Infer has_next from response if not explicitly provided
    if not page_info.has_next and len(items) == page_info.page_size:
        page_info.has_next = True

    return Page(
        items=items,
        page_info=page_info,
        raw_response=data,
    )


__all__ = [
    "PageInfo",
    "Page",
    "AsyncPaginator",
    "SyncPaginator",
    "create_page_from_response",
]
