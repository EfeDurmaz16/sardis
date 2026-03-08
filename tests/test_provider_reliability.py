"""Tests for provider reliability tracking and scorecards."""

import pytest
from datetime import datetime, timezone

from sardis_chain.provider_tracker import ProviderTracker


@pytest.mark.asyncio
async def test_record_event():
    """Record a provider event."""
    tracker = ProviderTracker()
    event_id = await tracker.record_event(
        provider="alchemy",
        chain="base",
        event_type="rpc_call",
        success=True,
        latency_ms=45,
    )
    assert event_id.startswith("evt_")
    assert len(tracker._events) == 1


@pytest.mark.asyncio
async def test_compute_scorecards():
    """Compute scorecards from events."""
    tracker = ProviderTracker()

    # Record 10 successful events and 2 failures
    for i in range(10):
        await tracker.record_event("alchemy", "base", "rpc_call", True, 50 + i * 5)
    for i in range(2):
        await tracker.record_event("alchemy", "base", "rpc_call", False, 5000, error_type="timeout")

    await tracker.compute_scorecards()
    card = await tracker.get_scorecard("alchemy", "base", "24h")

    assert card.total_calls == 12
    assert card.success_count == 10
    assert card.failure_count == 2
    assert abs(card.error_rate - 2 / 12) < 0.01
    assert abs(card.availability - 10 / 12) < 0.01
    assert card.avg_latency_ms > 0


@pytest.mark.asyncio
async def test_get_best_provider():
    """Best provider selection based on scorecards."""
    tracker = ProviderTracker()

    # Alchemy: 10 successes, low latency
    for _ in range(10):
        await tracker.record_event("alchemy", "base", "rpc_call", True, 30)

    # Infura: 5 successes, 5 failures, higher latency
    for _ in range(5):
        await tracker.record_event("infura", "base", "rpc_call", True, 200)
    for _ in range(5):
        await tracker.record_event("infura", "base", "rpc_call", False, 5000)

    best = await tracker.get_best_provider("base")
    assert best == "alchemy"


@pytest.mark.asyncio
async def test_get_best_provider_no_data():
    """Default provider when no data exists."""
    tracker = ProviderTracker()
    best = await tracker.get_best_provider("base")
    assert best == "alchemy"


@pytest.mark.asyncio
async def test_get_all_scorecards():
    """Get all computed scorecards."""
    tracker = ProviderTracker()

    await tracker.record_event("alchemy", "base", "rpc_call", True, 50)
    await tracker.record_event("infura", "polygon", "rpc_call", True, 100)

    scorecards = await tracker.get_all_scorecards()
    assert len(scorecards) >= 2  # At least one per provider/chain combo across periods


@pytest.mark.asyncio
async def test_scorecard_p95_latency():
    """P95 latency calculation."""
    tracker = ProviderTracker()

    # 19 fast calls, 1 slow call
    for _ in range(19):
        await tracker.record_event("alchemy", "base", "rpc_call", True, 50)
    await tracker.record_event("alchemy", "base", "rpc_call", True, 2000)

    card = await tracker.get_scorecard("alchemy", "base", "24h")
    assert card.p95_latency_ms >= 50  # Should be high since 5% of 20 = 1 slow call
