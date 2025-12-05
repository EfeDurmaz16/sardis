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
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "cache" in data


@pytest.mark.anyio
async def test_api_v2_health(test_client):
    """Test API v2 health endpoint."""
    response = await test_client.get("/api/v2/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
