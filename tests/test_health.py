"""Health check endpoint tests."""
from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_root_endpoint(test_client):
    """Test root endpoint returns service info."""
    response = await test_client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Sardis API"
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.anyio
async def test_health_endpoint(test_client):
    """Test health endpoint returns component status."""
    response = await test_client.get("/health")

    # In test environment without full infrastructure, may return 503 (degraded)
    assert response.status_code in (200, 503)
    data = response.json()
    # In test environment without full infrastructure, status may vary
    assert data["status"] in ("healthy", "degraded", "partial")
    assert "components" in data
    assert "database" in data["components"]


@pytest.mark.anyio
async def test_api_v2_health(test_client):
    """Test API v2 health endpoint."""
    response = await test_client.get("/api/v2/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"
