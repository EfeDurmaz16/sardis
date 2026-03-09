"""Tests for per-period TTL behaviour in InMemoryGroupSpendingTracker.

Validates the fix for TDD-flagged bug where monthly and total counters
previously shared the daily 24-hour TTL, allowing monthly budgets to
reset every 24 hours (30x overspend).
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from sardis_v2_core.group_policy import (
    InMemoryGroupSpendingTracker,
    _TTL_DAILY,
    _TTL_MONTHLY,
    _TTL_TOTAL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class SpyStateStore:
    """A thin wrapper that records (key, ttl) pairs for every ``set`` call."""

    def __init__(self):
        self._memory: dict[str, dict] = {}
        self.set_calls: list[tuple[str, dict, int | None]] = []

    async def get(self, key: str) -> dict | None:
        return self._memory.get(key)

    async def set(self, key: str, value, ttl: int | None = None) -> None:
        self._memory[key] = value
        self.set_calls.append((key, value, ttl))


def _make_tracker_with_spy() -> tuple[InMemoryGroupSpendingTracker, SpyStateStore]:
    """Create a tracker whose internal store is replaced with a spy."""
    tracker = InMemoryGroupSpendingTracker.__new__(InMemoryGroupSpendingTracker)
    spy = SpyStateStore()
    tracker._store = spy
    return tracker, spy


# ---------------------------------------------------------------------------
# TTL constant sanity checks
# ---------------------------------------------------------------------------

def test_ttl_constants_are_correct():
    assert _TTL_DAILY == 86_400
    assert _TTL_MONTHLY == 2_678_400
    assert _TTL_TOTAL == 31_536_000


# ---------------------------------------------------------------------------
# Per-period TTL tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_daily_counter_uses_daily_ttl():
    """Daily spend counter must use a 24-hour TTL."""
    tracker, spy = _make_tracker_with_spy()

    await tracker.record_spend("grp_1", Decimal("10"))

    daily_sets = [(k, ttl) for k, _, ttl in spy.set_calls if ":daily" in k]
    assert len(daily_sets) == 1
    assert daily_sets[0][1] == _TTL_DAILY


@pytest.mark.asyncio
async def test_monthly_counter_uses_monthly_ttl():
    """Monthly spend counter must use a 31-day TTL, not the daily 24h TTL."""
    tracker, spy = _make_tracker_with_spy()

    await tracker.record_spend("grp_1", Decimal("10"))

    monthly_sets = [(k, ttl) for k, _, ttl in spy.set_calls if ":monthly" in k]
    assert len(monthly_sets) == 1
    assert monthly_sets[0][1] == _TTL_MONTHLY


@pytest.mark.asyncio
async def test_total_counter_uses_long_ttl():
    """Total spend counter must use a long TTL (365 days), not 24h."""
    tracker, spy = _make_tracker_with_spy()

    await tracker.record_spend("grp_1", Decimal("10"))

    total_sets = [(k, ttl) for k, _, ttl in spy.set_calls if ":total" in k]
    assert len(total_sets) == 1
    assert total_sets[0][1] == _TTL_TOTAL


# ---------------------------------------------------------------------------
# Per-period key isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_per_period_keys_are_independent():
    """Each period counter is stored under its own key and can be read back."""
    tracker, spy = _make_tracker_with_spy()

    await tracker.record_spend("grp_a", Decimal("50"))
    await tracker.record_spend("grp_a", Decimal("25"))

    spending = await tracker.get_group_spending("grp_a")
    assert spending.daily == Decimal("75")
    assert spending.monthly == Decimal("75")
    assert spending.total == Decimal("75")


@pytest.mark.asyncio
async def test_all_three_period_keys_written_on_record():
    """A single record_spend must write exactly three keys (daily, monthly, total)."""
    tracker, spy = _make_tracker_with_spy()

    await tracker.record_spend("grp_x", Decimal("1"))

    written_keys = [k for k, _, _ in spy.set_calls]
    assert "grp_x:daily" in written_keys
    assert "grp_x:monthly" in written_keys
    assert "grp_x:total" in written_keys
    assert len(written_keys) == 3


@pytest.mark.asyncio
async def test_get_spending_returns_zeros_for_new_group():
    """A group with no recorded spend should return zero for all periods."""
    tracker, _ = _make_tracker_with_spy()

    spending = await tracker.get_group_spending("grp_nonexistent")
    assert spending.daily == Decimal("0")
    assert spending.monthly == Decimal("0")
    assert spending.total == Decimal("0")
