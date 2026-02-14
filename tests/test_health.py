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


@pytest.mark.anyio
async def test_api_root_discovery(test_client):
    """Test API root discovery endpoint."""
    response = await test_client.get("/api")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["latest"] == "/api/v2"
    assert data["docs"] == "/api/v2/docs"


@pytest.mark.anyio
async def test_api_v2_root_discovery(test_client):
    """Test API v2 root discovery endpoint."""
    response = await test_client.get("/api/v2")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["docs"] == "/api/v2/docs"
    assert data["openapi"] == "/api/v2/openapi.json"
