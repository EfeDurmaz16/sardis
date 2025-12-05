"""Holds API endpoint tests."""
from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_create_hold(test_client, sample_hold_request):
    """Test creating a hold."""
    response = await test_client.post(
        "/api/v2/holds",
        json=sample_hold_request,
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "hold_id" in data
    assert data["status"] == "active"
    assert data["wallet_id"] == sample_hold_request["wallet_id"]
    assert data["amount"] == sample_hold_request["amount"]


@pytest.mark.anyio
async def test_get_hold(test_client, sample_hold_request):
    """Test getting a hold by ID."""
    # First create a hold
    create_response = await test_client.post(
        "/api/v2/holds",
        json=sample_hold_request,
    )
    hold_id = create_response.json()["hold_id"]
    
    # Then get it
    response = await test_client.get(f"/api/v2/holds/{hold_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["hold_id"] == hold_id


@pytest.mark.anyio
async def test_capture_hold(test_client, sample_hold_request):
    """Test capturing a hold."""
    # Create hold
    create_response = await test_client.post(
        "/api/v2/holds",
        json=sample_hold_request,
    )
    hold_id = create_response.json()["hold_id"]
    
    # Capture it
    response = await test_client.post(
        f"/api/v2/holds/{hold_id}/capture",
        json={"amount": "500"},  # Partial capture
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "captured"


@pytest.mark.anyio
async def test_void_hold(test_client, sample_hold_request):
    """Test voiding a hold."""
    # Create hold
    create_response = await test_client.post(
        "/api/v2/holds",
        json=sample_hold_request,
    )
    hold_id = create_response.json()["hold_id"]
    
    # Void it
    response = await test_client.post(f"/api/v2/holds/{hold_id}/void")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "voided"


@pytest.mark.anyio
async def test_list_holds(test_client, sample_hold_request):
    """Test listing active holds."""
    # Create a hold first
    await test_client.post("/api/v2/holds", json=sample_hold_request)
    
    # List holds
    response = await test_client.get("/api/v2/holds")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_hold_not_found(test_client):
    """Test getting a non-existent hold."""
    response = await test_client.get("/api/v2/holds/nonexistent_hold")
    
    assert response.status_code == 404
