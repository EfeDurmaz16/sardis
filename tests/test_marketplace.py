"""Marketplace API endpoint tests."""
from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_list_categories(test_client):
    """Test listing marketplace categories."""
    response = await test_client.get("/api/v2/marketplace/categories")
    
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert len(data["categories"]) > 0


@pytest.mark.anyio
async def test_create_service(test_client, sample_service_request):
    """Test creating a service listing."""
    response = await test_client.post(
        "/api/v2/marketplace/services",
        json=sample_service_request,
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "service_id" in data
    assert data["name"] == sample_service_request["name"]
    assert data["status"] == "active"


@pytest.mark.anyio
async def test_list_services(test_client, sample_service_request):
    """Test listing services."""
    # Create a service first
    await test_client.post(
        "/api/v2/marketplace/services",
        json=sample_service_request,
    )
    
    # List services
    response = await test_client.get("/api/v2/marketplace/services")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_get_service(test_client, sample_service_request):
    """Test getting a service by ID."""
    # Create service
    create_response = await test_client.post(
        "/api/v2/marketplace/services",
        json=sample_service_request,
    )
    service_id = create_response.json()["service_id"]
    
    # Get it
    response = await test_client.get(f"/api/v2/marketplace/services/{service_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["service_id"] == service_id


@pytest.mark.anyio
async def test_search_services(test_client, sample_service_request):
    """Test searching for services."""
    # Create a service first
    await test_client.post(
        "/api/v2/marketplace/services",
        json=sample_service_request,
    )
    
    # Search for it
    response = await test_client.post(
        "/api/v2/marketplace/services/search",
        json={"query": "AI"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_create_offer(test_client, sample_service_request):
    """Test creating a service offer."""
    # Create service first
    create_response = await test_client.post(
        "/api/v2/marketplace/services",
        json=sample_service_request,
    )
    service_id = create_response.json()["service_id"]
    
    # Create offer
    response = await test_client.post(
        "/api/v2/marketplace/offers",
        json={
            "service_id": service_id,
            "total_amount": "100.00",
            "token": "USDC",
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "offer_id" in data
    assert data["status"] == "pending"


@pytest.mark.anyio
async def test_accept_offer(test_client, sample_service_request):
    """Test accepting an offer."""
    # Create service
    service_response = await test_client.post(
        "/api/v2/marketplace/services",
        json=sample_service_request,
    )
    service_id = service_response.json()["service_id"]
    
    # Create offer
    offer_response = await test_client.post(
        "/api/v2/marketplace/offers",
        json={
            "service_id": service_id,
            "total_amount": "100.00",
        },
    )
    offer_id = offer_response.json()["offer_id"]
    
    # Accept offer
    response = await test_client.post(f"/api/v2/marketplace/offers/{offer_id}/accept")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"


@pytest.mark.anyio
async def test_service_not_found(test_client):
    """Test getting a non-existent service."""
    response = await test_client.get("/api/v2/marketplace/services/nonexistent_service")
    
    assert response.status_code == 404
