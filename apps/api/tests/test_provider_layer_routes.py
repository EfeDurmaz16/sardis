"""Integration tests: the provider-layer execution surface is reachable.

Proves the unified registry is wired into the FastAPI app and that every
capability resolves through ONE registry (sandbox fallback in test, since no
live keys are set).  These are read/quote/screen calls — no money moves.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_provider_matrix_lists_every_capability(client):
    resp = await client.get("/api/v2/providers/matrix")
    assert resp.status_code == 200
    rows = {r["capability"]: r for r in resp.json()["providers"]}
    # All nine capability ports resolve (sandbox fallback when unconfigured).
    for cap in (
        "custody",
        "fiat_account",
        "onramp",
        "offramp",
        "swap",
        "bridge",
        "card",
        "kyc",
        "kyt",
    ):
        assert cap in rows, f"{cap} missing from matrix"
        assert rows[cap]["sandbox"] is True
        assert rows[cap]["custody_model"] == "simulated"


@pytest.mark.asyncio
async def test_swap_quote_via_port(client):
    resp = await client.post(
        "/api/v2/providers/swap/quote",
        json={
            "chain": "base",
            "sell_token": "USDC",
            "buy_token": "EURC",
            "sell_amount": "10.00",
            "sell_decimals": 6,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sandbox"] is True
    assert body["status"] == "quoted"


@pytest.mark.asyncio
async def test_bridge_quote_via_port(client):
    resp = await client.post(
        "/api/v2/providers/bridge/quote",
        json={
            "from_chain": "base",
            "to_chain": "tempo",
            "token": "USDC",
            "amount": "25.00",
            "decimals": 6,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "quoted"


@pytest.mark.asyncio
async def test_kyt_screen_reports_verdict_only(client):
    resp = await client.post(
        "/api/v2/providers/kyt/screen",
        json={"address": "0xabc", "chain": "base"},
    )
    assert resp.status_code == 200
    # Port reports; the moat (orchestrator Phase 2) decides allow/deny.
    assert resp.json()["status"] == "clear"


@pytest.mark.asyncio
async def test_swap_quote_rejects_excess_precision(client):
    # 7 decimals on a 6-decimal token is a money-precision error -> 400.
    resp = await client.post(
        "/api/v2/providers/swap/quote",
        json={
            "chain": "base",
            "sell_token": "USDC",
            "buy_token": "EURC",
            "sell_amount": "10.0000001",
            "sell_decimals": 6,
        },
    )
    assert resp.status_code == 400
