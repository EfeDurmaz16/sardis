"""Tests for the smart provider router."""

import pytest
from sardis_chain.provider_tracker import ProviderTracker
from sardis_chain.smart_router import SmartRouter


@pytest.mark.asyncio
async def test_default_provider_without_tracker():
    """Returns default provider when no tracker configured."""
    router = SmartRouter()
    provider = await router.select_provider("base")
    assert provider == "alchemy"


@pytest.mark.asyncio
async def test_selects_best_provider():
    """Selects best provider based on tracker data."""
    tracker = ProviderTracker()

    # Alchemy: all successes, low latency
    for _ in range(20):
        await tracker.record_event("alchemy", "base", "rpc_call", True, 30)

    # Infura: some failures, higher latency
    for _ in range(10):
        await tracker.record_event("infura", "base", "rpc_call", True, 200)
    for _ in range(10):
        await tracker.record_event("infura", "base", "rpc_call", False, 5000)

    router = SmartRouter(tracker=tracker)
    provider = await router.select_provider("base")
    assert provider == "alchemy"


@pytest.mark.asyncio
async def test_routing_explanation():
    """Get routing explanation with candidates."""
    tracker = ProviderTracker()
    for _ in range(5):
        await tracker.record_event("alchemy", "base", "rpc_call", True, 50)

    router = SmartRouter(tracker=tracker)
    explanation = await router.get_routing_explanation("base")

    assert explanation["chain"] == "base"
    assert explanation["selected"] == "alchemy"
    assert len(explanation["candidates"]) >= 1
    assert explanation["candidates"][0]["provider"] == "alchemy"


@pytest.mark.asyncio
async def test_routing_explanation_no_tracker():
    """Explanation without tracker shows default."""
    router = SmartRouter()
    explanation = await router.get_routing_explanation("base")

    assert explanation["selected"] == "alchemy"
    assert "No tracker" in explanation["reason"]


@pytest.mark.asyncio
async def test_routing_explanation_no_data():
    """Explanation with tracker but no data for chain."""
    tracker = ProviderTracker()
    router = SmartRouter(tracker=tracker)
    explanation = await router.get_routing_explanation("arbitrum")

    assert "No scorecard" in explanation["reason"]
