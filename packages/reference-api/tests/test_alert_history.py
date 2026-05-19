"""Tests for alert history listing endpoint."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_alerts_with_filters(client):
    """GET /api/v2/alerts?severity=critical&limit=10 returns 200."""
    resp = await client.get("/api/v2/alerts?severity=critical&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # All returned alerts must match the requested severity
    for alert in data:
        assert alert["severity"] == "critical"


@pytest.mark.asyncio
async def test_list_alerts_pagination(client):
    """GET /api/v2/alerts?limit=5&offset=0 returns 200 with at most 5 items."""
    resp = await client.get("/api/v2/alerts?limit=5&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 5


@pytest.mark.asyncio
async def test_list_alerts_alert_type_filter(client):
    """GET /api/v2/alerts?alert_type=payment_executed returns only matching type."""
    resp = await client.get("/api/v2/alerts?alert_type=payment_executed")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    for alert in data:
        assert alert["alert_type"] == "payment_executed"


@pytest.mark.asyncio
async def test_list_alerts_default_limit(client):
    """GET /api/v2/alerts without params returns 200."""
    resp = await client.get("/api/v2/alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_alerts_date_filter(client):
    """GET /api/v2/alerts with from_date/to_date params returns 200."""
    resp = await client.get(
        "/api/v2/alerts?from_date=2020-01-01T00:00:00Z&to_date=2030-01-01T00:00:00Z"
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
