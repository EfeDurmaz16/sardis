"""Webhooks API endpoint tests."""
from __future__ import annotations

import os
import pytest

# Skip database-dependent tests if no PostgreSQL database
_requires_db = pytest.mark.skipif(
    not (os.environ.get("DATABASE_URL", "").startswith("postgresql://") or 
         os.environ.get("DATABASE_URL", "").startswith("postgres://")),
    reason="Requires PostgreSQL database (set DATABASE_URL env var)"
)


@pytest.mark.anyio
async def test_list_event_types(test_client):
    """Test listing webhook event types."""
    response = await test_client.get("/api/v2/webhooks/event-types")
    
    assert response.status_code == 200
    data = response.json()
    assert "event_types" in data
    assert len(data["event_types"]) > 0
    assert "payment.completed" in data["event_types"]


@_requires_db
@pytest.mark.anyio
async def test_create_webhook(test_client, sample_webhook_request):
    """Test creating a webhook subscription."""
    response = await test_client.post(
        "/api/v2/webhooks",
        json=sample_webhook_request,
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "subscription_id" in data
    assert "secret" in data
    assert data["url"] == sample_webhook_request["url"]
    assert data["is_active"] is True


@_requires_db
@pytest.mark.anyio
async def test_list_webhooks(test_client, sample_webhook_request):
    """Test listing webhook subscriptions."""
    # Create a webhook first
    await test_client.post("/api/v2/webhooks", json=sample_webhook_request)
    
    # List webhooks
    response = await test_client.get("/api/v2/webhooks")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@_requires_db
@pytest.mark.anyio
async def test_get_webhook(test_client, sample_webhook_request):
    """Test getting a webhook by ID."""
    # Create webhook
    create_response = await test_client.post(
        "/api/v2/webhooks",
        json=sample_webhook_request,
    )
    subscription_id = create_response.json()["subscription_id"]
    
    # Get it
    response = await test_client.get(f"/api/v2/webhooks/{subscription_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["subscription_id"] == subscription_id


@_requires_db
@pytest.mark.anyio
async def test_update_webhook(test_client, sample_webhook_request):
    """Test updating a webhook subscription."""
    # Create webhook
    create_response = await test_client.post(
        "/api/v2/webhooks",
        json=sample_webhook_request,
    )
    subscription_id = create_response.json()["subscription_id"]
    
    # Update it
    response = await test_client.patch(
        f"/api/v2/webhooks/{subscription_id}",
        json={"is_active": False},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


@_requires_db
@pytest.mark.anyio
async def test_delete_webhook(test_client, sample_webhook_request):
    """Test deleting a webhook subscription."""
    # Create webhook
    create_response = await test_client.post(
        "/api/v2/webhooks",
        json=sample_webhook_request,
    )
    subscription_id = create_response.json()["subscription_id"]
    
    # Delete it
    response = await test_client.delete(f"/api/v2/webhooks/{subscription_id}")
    
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = await test_client.get(f"/api/v2/webhooks/{subscription_id}")
    assert get_response.status_code == 404


@_requires_db
@pytest.mark.anyio
async def test_webhook_not_found(test_client):
    """Test getting a non-existent webhook."""
    response = await test_client.get("/api/v2/webhooks/nonexistent_webhook")
    
    assert response.status_code == 404
