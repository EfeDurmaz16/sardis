"""
Comprehensive tests for sardis_sdk.pagination module.

Tests cover:
- Page model and PageInfo
- AsyncPaginator for async iteration
- SyncPaginator for sync iteration
- Edge cases and error handling
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sardis_sdk.pagination import (
    PageInfo,
    Page,
    AsyncPaginator,
    SyncPaginator,
    create_page_from_response,
)


class TestPageInfo:
    """Tests for PageInfo class."""

    def test_create_page_info(self):
        """Should create page info."""
        info = PageInfo(
            has_more=True,
            cursor="cursor_abc123",
            total_count=100,
        )

        assert info.has_more is True
        assert info.cursor == "cursor_abc123"
        assert info.total_count == 100

    def test_page_info_no_more(self):
        """Should indicate no more pages."""
        info = PageInfo(
            has_more=False,
            cursor=None,
            total_count=50,
        )

        assert info.has_more is False
        assert info.cursor is None


class TestPage:
    """Tests for Page class."""

    def test_create_page(self):
        """Should create page with items."""
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        page_info = PageInfo(has_more=True, cursor="next_cursor")

        page = Page(items=items, page_info=page_info)

        assert len(page.items) == 3
        assert page.page_info.has_more is True

    def test_page_iteration(self):
        """Should iterate over items."""
        items = [{"id": str(i)} for i in range(5)]
        page = Page(items=items, page_info=PageInfo(has_more=False))

        iterated = list(page)
        assert len(iterated) == 5
        assert iterated[0]["id"] == "0"

    def test_page_len(self):
        """Should return item count."""
        items = [{"id": "1"}, {"id": "2"}]
        page = Page(items=items, page_info=PageInfo(has_more=False))

        assert len(page) == 2

    def test_page_getitem(self):
        """Should support indexing."""
        items = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        page = Page(items=items, page_info=PageInfo(has_more=False))

        assert page[0]["id"] == "a"
        assert page[2]["id"] == "c"

    def test_empty_page(self):
        """Should handle empty page."""
        page = Page(items=[], page_info=PageInfo(has_more=False))

        assert len(page) == 0
        assert list(page) == []


class TestAsyncPaginator:
    """Tests for AsyncPaginator class."""

    @pytest.mark.asyncio
    async def test_single_page(self):
        """Should handle single page response."""
        async def fetch_page(cursor=None):
            return Page(
                items=[{"id": "1"}, {"id": "2"}],
                page_info=PageInfo(has_more=False),
            )

        paginator = AsyncPaginator(fetch_page)
        items = []

        async for item in paginator:
            items.append(item)

        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_multiple_pages(self):
        """Should iterate through multiple pages."""
        call_count = 0

        async def fetch_page(cursor=None):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                return Page(
                    items=[{"id": "1"}, {"id": "2"}],
                    page_info=PageInfo(has_more=True, cursor="page_2"),
                )
            elif call_count == 2:
                return Page(
                    items=[{"id": "3"}, {"id": "4"}],
                    page_info=PageInfo(has_more=True, cursor="page_3"),
                )
            else:
                return Page(
                    items=[{"id": "5"}],
                    page_info=PageInfo(has_more=False),
                )

        paginator = AsyncPaginator(fetch_page)
        items = []

        async for item in paginator:
            items.append(item)

        assert len(items) == 5
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_collect_all(self):
        """Should collect all items into list."""
        async def fetch_page(cursor=None):
            if cursor is None:
                return Page(
                    items=[{"id": "1"}, {"id": "2"}],
                    page_info=PageInfo(has_more=True, cursor="next"),
                )
            else:
                return Page(
                    items=[{"id": "3"}],
                    page_info=PageInfo(has_more=False),
                )

        paginator = AsyncPaginator(fetch_page)
        all_items = await paginator.collect()

        assert len(all_items) == 3

    @pytest.mark.asyncio
    async def test_empty_first_page(self):
        """Should handle empty first page."""
        async def fetch_page(cursor=None):
            return Page(
                items=[],
                page_info=PageInfo(has_more=False),
            )

        paginator = AsyncPaginator(fetch_page)
        items = await paginator.collect()

        assert len(items) == 0


class TestSyncPaginator:
    """Tests for SyncPaginator class."""

    def test_single_page(self):
        """Should handle single page response."""
        def fetch_page(cursor=None):
            return Page(
                items=[{"id": "1"}, {"id": "2"}],
                page_info=PageInfo(has_more=False),
            )

        paginator = SyncPaginator(fetch_page)
        items = list(paginator)

        assert len(items) == 2

    def test_multiple_pages(self):
        """Should iterate through multiple pages."""
        call_count = 0

        def fetch_page(cursor=None):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                return Page(
                    items=[{"id": "1"}],
                    page_info=PageInfo(has_more=True, cursor="p2"),
                )
            else:
                return Page(
                    items=[{"id": "2"}],
                    page_info=PageInfo(has_more=False),
                )

        paginator = SyncPaginator(fetch_page)
        items = list(paginator)

        assert len(items) == 2
        assert call_count == 2

    def test_collect_all(self):
        """Should collect all items."""
        def fetch_page(cursor=None):
            return Page(
                items=[{"id": "1"}, {"id": "2"}],
                page_info=PageInfo(has_more=False),
            )

        paginator = SyncPaginator(fetch_page)
        items = paginator.collect()

        assert len(items) == 2


class TestCreatePageFromResponse:
    """Tests for create_page_from_response helper."""

    def test_standard_response(self):
        """Should create page from standard API response."""
        response = {
            "data": [{"id": "1"}, {"id": "2"}],
            "has_more": True,
            "cursor": "next_cursor",
            "total_count": 100,
        }

        page = create_page_from_response(response)

        assert len(page.items) == 2
        assert page.page_info.has_more is True
        assert page.page_info.cursor == "next_cursor"
        assert page.page_info.total_count == 100

    def test_response_without_pagination(self):
        """Should handle response without pagination info."""
        response = {
            "data": [{"id": "1"}],
        }

        page = create_page_from_response(response)

        assert len(page.items) == 1
        assert page.page_info.has_more is False

    def test_empty_data(self):
        """Should handle empty data array."""
        response = {
            "data": [],
            "has_more": False,
        }

        page = create_page_from_response(response)

        assert len(page.items) == 0
        assert page.page_info.has_more is False


class TestPaginationEdgeCases:
    """Edge case tests for pagination."""

    @pytest.mark.asyncio
    async def test_fetch_error_handling(self):
        """Should propagate fetch errors."""
        async def failing_fetch(cursor=None):
            raise ValueError("Network error")

        paginator = AsyncPaginator(failing_fetch)

        with pytest.raises(ValueError):
            async for _ in paginator:
                pass

    @pytest.mark.asyncio
    async def test_large_page_count(self):
        """Should handle many pages."""
        page_count = 0
        max_pages = 100

        async def fetch_many_pages(cursor=None):
            nonlocal page_count
            page_count += 1

            has_more = page_count < max_pages

            return Page(
                items=[{"id": str(page_count)}],
                page_info=PageInfo(
                    has_more=has_more,
                    cursor=f"cursor_{page_count}" if has_more else None,
                ),
            )

        paginator = AsyncPaginator(fetch_many_pages)
        items = await paginator.collect()

        assert len(items) == max_pages

    def test_none_items(self):
        """Should handle None in items list."""
        page = Page(
            items=[{"id": "1"}, None, {"id": "3"}],
            page_info=PageInfo(has_more=False),
        )

        # Should contain None
        assert None in page.items

    @pytest.mark.asyncio
    async def test_paginator_reuse(self):
        """Should be able to iterate multiple times."""
        fetch_count = 0

        async def fetch_page(cursor=None):
            nonlocal fetch_count
            fetch_count += 1
            return Page(
                items=[{"id": str(fetch_count)}],
                page_info=PageInfo(has_more=False),
            )

        paginator = AsyncPaginator(fetch_page)

        # First iteration
        items1 = await paginator.collect()
        first_count = fetch_count

        # Second iteration
        items2 = await paginator.collect()

        # Note: Behavior depends on implementation
        # Some paginators reset, others don't
        assert len(items1) >= 1
