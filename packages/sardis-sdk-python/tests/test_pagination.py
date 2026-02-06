"""Tests for sardis_sdk.pagination."""

from __future__ import annotations

import pytest

from sardis_sdk.pagination import (
    AsyncPaginator,
    Page,
    PageInfo,
    SyncPaginator,
    create_page_from_response,
)


class TestPageInfo:
    def test_from_response_with_pagination(self):
        info = PageInfo.from_response(
            {
                "pagination": {
                    "has_next": True,
                    "has_previous": False,
                    "total_count": 123,
                    "page_size": 2,
                    "current_page": 3,
                    "total_pages": 10,
                    "next_cursor": "next",
                    "previous_cursor": "prev",
                }
            }
        )
        assert info.has_next is True
        assert info.has_previous is False
        assert info.total_count == 123
        assert info.page_size == 2
        assert info.current_page == 3
        assert info.total_pages == 10
        assert info.next_cursor == "next"
        assert info.previous_cursor == "prev"

    def test_from_response_with_meta_aliases(self):
        info = PageInfo.from_response({"meta": {"has_next": True, "limit": 50, "next": "cursor-1"}})
        assert info.has_next is True
        assert info.page_size == 50
        assert info.next_cursor == "cursor-1"


class TestPage:
    def test_page_basics(self):
        page = Page(items=[{"id": "a"}, {"id": "b"}], page_info=PageInfo(has_next=True))
        assert len(page) == 2
        assert page[0]["id"] == "a"
        assert list(page) == [{"id": "a"}, {"id": "b"}]
        assert page.has_next is True
        assert page.is_empty is False

    def test_empty_page(self):
        page = Page(items=[], page_info=PageInfo())
        assert page.is_empty is True
        assert page.has_next is False


class TestCreatePageFromResponse:
    def test_create_page_from_response(self):
        page = create_page_from_response(
            data={
                "agents": [{"id": "agent_1"}, {"id": "agent_2"}],
                "pagination": {"has_next": True, "page_size": 2, "next_cursor": "c2"},
            },
            items_key="agents",
            item_parser=lambda x: x,
        )
        assert len(page.items) == 2
        assert page.page_info.has_next is True
        assert page.page_info.next_cursor == "c2"


class TestAsyncPaginator:
    @pytest.mark.asyncio
    async def test_iterates_cursor_pages(self):
        async def fetch_page(cursor=None):
            if cursor is None:
                return Page(
                    items=[1, 2],
                    page_info=PageInfo(has_next=True, next_cursor="c2"),
                )
            return Page(items=[3], page_info=PageInfo(has_next=False))

        paginator = AsyncPaginator(fetch_page)
        assert [item async for item in paginator] == [1, 2, 3]
        assert await paginator.all() == [1, 2, 3]
        assert await paginator.take(2) == [1, 2]

    @pytest.mark.asyncio
    async def test_iterates_offset_pages(self):
        async def fetch_page(limit=2, offset=0):
            items = list(range(offset, min(offset + limit, 5)))
            has_next = (offset + len(items)) < 5
            return Page(items=items, page_info=PageInfo(has_next=has_next, page_size=limit))

        paginator = AsyncPaginator(fetch_page, initial_params={"limit": 2, "offset": 0})
        assert [item async for item in paginator] == [0, 1, 2, 3, 4]


class TestSyncPaginator:
    def test_iterates_cursor_pages(self):
        def fetch_page(cursor=None):
            if cursor is None:
                return Page(items=["a"], page_info=PageInfo(has_next=True, next_cursor="c2"))
            return Page(items=["b"], page_info=PageInfo(has_next=False))

        paginator = SyncPaginator(fetch_page)
        assert list(paginator) == ["a", "b"]
        assert paginator.all() == ["a", "b"]
