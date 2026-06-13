"""Tests for cursor/offset pagination auto-iteration helpers.

Mirrors the Anthropic SDK's auto-paginating list iterators: iterating a
paginator transparently fetches subsequent pages until exhausted.
"""

from __future__ import annotations

import httpx
import respx

from sardis import Sardis
from sardis._client import RetryConfig
from sardis.pagination import (
    AsyncPaginator,
    Page,
    PageInfo,
    SyncPaginator,
    create_page_from_response,
)

BASE_URL = "https://api.test.sardis.sh"
API_KEY = "test-thin-client-key"


def _page(items: list[int], *, next_cursor: str | None) -> Page[int]:
    return Page(
        items=items,
        page_info=PageInfo(
            has_next=next_cursor is not None,
            next_cursor=next_cursor,
            page_size=len(items),
        ),
    )


class TestSyncPaginator:
    def test_auto_iterates_across_pages(self) -> None:
        pages = {
            None: _page([1, 2], next_cursor="c1"),
            "c1": _page([3, 4], next_cursor="c2"),
            "c2": _page([5], next_cursor=None),
        }

        def fetch_page(**params: object) -> Page[int]:
            return pages[params.get("cursor")]

        paginator = SyncPaginator(fetch_page=fetch_page)
        assert list(paginator) == [1, 2, 3, 4, 5]

    def test_max_items_stops_early(self) -> None:
        pages = {
            None: _page([1, 2], next_cursor="c1"),
            "c1": _page([3, 4], next_cursor="c2"),
        }

        def fetch_page(**params: object) -> Page[int]:
            return pages[params.get("cursor")]

        paginator = SyncPaginator(fetch_page=fetch_page, max_items=3)
        assert paginator.take(3) == [1, 2, 3]


class TestAsyncPaginator:
    async def test_auto_iterates_across_pages(self) -> None:
        pages = {
            None: _page([1], next_cursor="c1"),
            "c1": _page([2, 3], next_cursor=None),
        }

        async def fetch_page(**params: object) -> Page[int]:
            return pages[params.get("cursor")]

        paginator = AsyncPaginator(fetch_page=fetch_page)
        collected = [item async for item in paginator]
        assert collected == [1, 2, 3]

    async def test_all_collects_everything(self) -> None:
        pages = {
            None: _page([1, 2], next_cursor="c1"),
            "c1": _page([3], next_cursor=None),
        }

        async def fetch_page(**params: object) -> Page[int]:
            return pages[params.get("cursor")]

        paginator = AsyncPaginator(fetch_page=fetch_page)
        assert await paginator.all() == [1, 2, 3]


class TestResourcePageParsing:
    @respx.mock
    def test_agents_list_page_parses_pagination(self) -> None:
        respx.get(f"{BASE_URL}/api/v2/agents").mock(
            return_value=httpx.Response(
                200,
                json={
                    "agents": [
                        {
                            "id": "agent_1",
                            "name": "alpha",
                            "created_at": "2026-01-01T00:00:00Z",
                            "updated_at": "2026-01-01T00:00:00Z",
                        }
                    ],
                    "pagination": {"has_next": True, "next_cursor": "c_next"},
                },
            )
        )
        client = Sardis(
            api_key=API_KEY,
            base_url=BASE_URL,
            retry=RetryConfig(max_retries=0, initial_delay=0.0, jitter=False),
        )
        with client:
            page = client.agents.list_page(limit=1)

        assert len(page) == 1
        assert page.items[0].agent_id == "agent_1"
        assert page.has_next is True
        assert page.page_info.next_cursor == "c_next"


class TestCreatePageFromResponse:
    def test_infers_has_next_when_full_page(self) -> None:
        data = {"items": [{"v": 1}, {"v": 2}], "pagination": {"limit": 2}}
        page = create_page_from_response(
            data, items_key="items", item_parser=lambda x: x["v"]
        )
        assert page.items == [1, 2]
        # A full page (len == page_size) infers there may be more.
        assert page.has_next is True
