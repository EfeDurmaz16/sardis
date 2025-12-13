"""Integration tests for A2A marketplace flow."""
from __future__ import annotations

import os
import time
import pytest
from httpx import AsyncClient

# All tests in this module require a PostgreSQL database
pytestmark = pytest.mark.skipif(
    not (os.environ.get("DATABASE_URL", "").startswith("postgresql://") or 
         os.environ.get("DATABASE_URL", "").startswith("postgres://")),
    reason="Requires PostgreSQL database (set DATABASE_URL env var)"
)


def create_service_request(
    name: str = "Test AI Service",
    category: str = "ai",
    price: str = "100.00",
) -> dict:
    """Create a test service request."""
    return {
        "name": name,
        "description": f"A test {category} service for automated tasks",
        "category": category,
        "tags": [category, "automation", "test"],
        "price_amount": price,
        "price_token": "USDC",
        "price_type": "fixed",
    }


class TestServiceCreation:
    """Tests for creating marketplace services."""

    @pytest.mark.asyncio
    async def test_create_service_success(self, test_client: AsyncClient):
        """Test creating a service successfully."""
        service_request = create_service_request()
        
        response = await test_client.post(
            "/api/v2/marketplace/services",
            json=service_request,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "service_id" in data
        assert data["name"] == "Test AI Service"
        assert data["category"] == "ai"
        assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_create_service_with_capabilities(self, test_client: AsyncClient):
        """Test creating a service with capabilities."""
        service_request = create_service_request()
        service_request["capabilities"] = {
            "max_concurrent_requests": 10,
            "supported_formats": ["json", "xml"],
            "rate_limit": "1000/hour",
        }
        
        response = await test_client.post(
            "/api/v2/marketplace/services",
            json=service_request,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "capabilities" in data

    @pytest.mark.asyncio
    async def test_create_service_invalid_category(self, test_client: AsyncClient):
        """Test creating a service with invalid category."""
        service_request = create_service_request(category="invalid_category")
        
        response = await test_client.post(
            "/api/v2/marketplace/services",
            json=service_request,
        )
        
        # Should fail or be rejected
        assert response.status_code in [400, 422]


class TestServiceDiscovery:
    """Tests for service discovery."""

    @pytest.mark.asyncio
    async def test_list_services(self, test_client: AsyncClient):
        """Test listing all services."""
        response = await test_client.get("/api/v2/marketplace/services")
        
        assert response.status_code == 200
        data = response.json()
        assert "services" in data

    @pytest.mark.asyncio
    async def test_list_categories(self, test_client: AsyncClient):
        """Test listing service categories."""
        response = await test_client.get("/api/v2/marketplace/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        # Should have predefined categories
        categories = data["categories"]
        assert len(categories) > 0

    @pytest.mark.asyncio
    async def test_search_services(self, test_client: AsyncClient):
        """Test searching for services."""
        # Create a service first
        service_request = create_service_request(
            name="Premium Data Analysis",
            category="data",
        )
        await test_client.post("/api/v2/marketplace/services", json=service_request)
        
        # Search for it
        search_request = {
            "query": "data analysis",
            "category": "data",
        }
        
        response = await test_client.post(
            "/api/v2/marketplace/services/search",
            json=search_request,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "services" in data

    @pytest.mark.asyncio
    async def test_get_service_by_id(self, test_client: AsyncClient):
        """Test getting a service by ID."""
        # Create service
        service_request = create_service_request()
        create_response = await test_client.post(
            "/api/v2/marketplace/services",
            json=service_request,
        )
        service_id = create_response.json()["service_id"]
        
        # Get service
        get_response = await test_client.get(f"/api/v2/marketplace/services/{service_id}")
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["service_id"] == service_id


class TestOfferCreation:
    """Tests for creating service offers."""

    @pytest.fixture
    async def test_service(self, test_client: AsyncClient) -> dict:
        """Create a test service for offer tests."""
        service_request = create_service_request(
            name=f"Offer Test Service {int(time.time())}",
        )
        response = await test_client.post(
            "/api/v2/marketplace/services",
            json=service_request,
        )
        return response.json()

    @pytest.mark.asyncio
    async def test_create_offer_success(self, test_client: AsyncClient, test_service: dict):
        """Test creating an offer successfully."""
        offer_request = {
            "service_id": test_service["service_id"],
            "consumer_agent_id": "consumer_agent_001",
            "total_amount": "100.00",
            "token": "USDC",
        }
        
        response = await test_client.post(
            "/api/v2/marketplace/offers",
            json=offer_request,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "offer_id" in data
        assert data["status"] == "pending"
        assert data["total_amount"] == "100.00"

    @pytest.mark.asyncio
    async def test_create_offer_with_milestones(self, test_client: AsyncClient, test_service: dict):
        """Test creating an offer with milestones."""
        offer_request = {
            "service_id": test_service["service_id"],
            "consumer_agent_id": "consumer_agent_002",
            "total_amount": "300.00",
            "token": "USDC",
            "milestones": [
                {"description": "Initial setup", "amount": "100.00"},
                {"description": "Development", "amount": "150.00"},
                {"description": "Delivery", "amount": "50.00"},
            ],
        }
        
        response = await test_client.post(
            "/api/v2/marketplace/offers",
            json=offer_request,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"


class TestOfferLifecycle:
    """Tests for offer lifecycle management."""

    @pytest.fixture
    async def pending_offer(self, test_client: AsyncClient) -> dict:
        """Create a pending offer for lifecycle tests."""
        # Create service
        service_request = create_service_request(
            name=f"Lifecycle Test Service {int(time.time())}",
        )
        service_response = await test_client.post(
            "/api/v2/marketplace/services",
            json=service_request,
        )
        service = service_response.json()
        
        # Create offer
        offer_request = {
            "service_id": service["service_id"],
            "consumer_agent_id": "consumer_agent_lifecycle",
            "total_amount": "200.00",
            "token": "USDC",
        }
        offer_response = await test_client.post(
            "/api/v2/marketplace/offers",
            json=offer_request,
        )
        return offer_response.json()

    @pytest.mark.asyncio
    async def test_accept_offer(self, test_client: AsyncClient, pending_offer: dict):
        """Test accepting an offer."""
        offer_id = pending_offer["offer_id"]
        
        response = await test_client.post(f"/api/v2/marketplace/offers/{offer_id}/accept")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_reject_offer(self, test_client: AsyncClient, pending_offer: dict):
        """Test rejecting an offer."""
        offer_id = pending_offer["offer_id"]
        
        response = await test_client.post(f"/api/v2/marketplace/offers/{offer_id}/reject")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_complete_offer(self, test_client: AsyncClient, pending_offer: dict):
        """Test completing an offer after acceptance."""
        offer_id = pending_offer["offer_id"]
        
        # First accept
        await test_client.post(f"/api/v2/marketplace/offers/{offer_id}/accept")
        
        # Then complete
        response = await test_client.post(f"/api/v2/marketplace/offers/{offer_id}/complete")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_cannot_complete_pending_offer(self, test_client: AsyncClient, pending_offer: dict):
        """Test that pending offer cannot be completed directly."""
        offer_id = pending_offer["offer_id"]
        
        response = await test_client.post(f"/api/v2/marketplace/offers/{offer_id}/complete")
        
        assert response.status_code == 400


class TestReviews:
    """Tests for service reviews."""

    @pytest.fixture
    async def completed_offer(self, test_client: AsyncClient) -> dict:
        """Create a completed offer for review tests."""
        # Create service
        service_request = create_service_request(
            name=f"Review Test Service {int(time.time())}",
        )
        service_response = await test_client.post(
            "/api/v2/marketplace/services",
            json=service_request,
        )
        service = service_response.json()
        
        # Create offer
        offer_request = {
            "service_id": service["service_id"],
            "consumer_agent_id": "consumer_agent_review",
            "total_amount": "100.00",
            "token": "USDC",
        }
        offer_response = await test_client.post(
            "/api/v2/marketplace/offers",
            json=offer_request,
        )
        offer = offer_response.json()
        
        # Accept and complete
        await test_client.post(f"/api/v2/marketplace/offers/{offer['offer_id']}/accept")
        await test_client.post(f"/api/v2/marketplace/offers/{offer['offer_id']}/complete")
        
        return {**offer, "service_id": service["service_id"]}

    @pytest.mark.asyncio
    async def test_create_review(self, test_client: AsyncClient, completed_offer: dict):
        """Test creating a review for completed offer."""
        offer_id = completed_offer["offer_id"]
        
        review_request = {
            "rating": 5,
            "comment": "Excellent service, highly recommended!",
        }
        
        response = await test_client.post(
            f"/api/v2/marketplace/offers/{offer_id}/review",
            json=review_request,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "review_id" in data
        assert data["rating"] == 5

    @pytest.mark.asyncio
    async def test_review_invalid_rating(self, test_client: AsyncClient, completed_offer: dict):
        """Test review with invalid rating fails."""
        offer_id = completed_offer["offer_id"]
        
        review_request = {
            "rating": 10,  # Invalid: max is 5
            "comment": "Invalid rating",
        }
        
        response = await test_client.post(
            f"/api/v2/marketplace/offers/{offer_id}/review",
            json=review_request,
        )
        
        assert response.status_code in [400, 422]


class TestMarketplaceFullFlow:
    """Tests for complete marketplace flow scenarios."""

    @pytest.mark.asyncio
    async def test_complete_a2a_transaction_flow(self, test_client: AsyncClient):
        """Test complete A2A transaction from listing to review."""
        timestamp = int(time.time())
        
        # 1. Provider creates service
        service_request = {
            "name": f"Premium Code Review Service {timestamp}",
            "description": "Expert code review by AI agent",
            "category": "compute",
            "tags": ["code", "review", "ai"],
            "price_amount": "50.00",
            "price_token": "USDC",
            "price_type": "fixed",
        }
        
        service_response = await test_client.post(
            "/api/v2/marketplace/services",
            json=service_request,
        )
        assert service_response.status_code == 200
        service = service_response.json()
        service_id = service["service_id"]
        
        # 2. Consumer finds service via search
        search_response = await test_client.post(
            "/api/v2/marketplace/services/search",
            json={"query": "code review"},
        )
        assert search_response.status_code == 200
        
        # 3. Consumer creates offer
        offer_request = {
            "service_id": service_id,
            "consumer_agent_id": f"consumer_{timestamp}",
            "total_amount": "50.00",
            "token": "USDC",
        }
        
        offer_response = await test_client.post(
            "/api/v2/marketplace/offers",
            json=offer_request,
        )
        assert offer_response.status_code == 200
        offer = offer_response.json()
        offer_id = offer["offer_id"]
        assert offer["status"] == "pending"
        
        # 4. Provider accepts offer
        accept_response = await test_client.post(
            f"/api/v2/marketplace/offers/{offer_id}/accept"
        )
        assert accept_response.status_code == 200
        assert accept_response.json()["status"] == "accepted"
        
        # 5. Work is done, provider completes
        complete_response = await test_client.post(
            f"/api/v2/marketplace/offers/{offer_id}/complete"
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"
        
        # 6. Consumer leaves review
        review_request = {
            "rating": 5,
            "comment": "Excellent code review, very thorough!",
        }
        
        review_response = await test_client.post(
            f"/api/v2/marketplace/offers/{offer_id}/review",
            json=review_request,
        )
        assert review_response.status_code == 200
        assert review_response.json()["rating"] == 5
        
        # 7. Verify service shows in provider's listings
        list_response = await test_client.get("/api/v2/marketplace/offers")
        assert list_response.status_code == 200





