"""Tests for MarketplaceResource."""
import pytest
from decimal import Decimal

from sardis_sdk.models.marketplace import ServiceCategory


MOCK_SERVICE = {
    "id": "svc_123",
    "provider_agent_id": "agent_001",
    "name": "Test Service",
    "description": "A test service",
    "category": "payment",
    "tags": ["test", "demo"],
    "price_amount": "50.00",
    "price_token": "USDC",
    "price_type": "fixed",
    "capabilities": {"api_access": True},
    "api_endpoint": "https://api.example.com",
    "status": "active",
    "total_orders": 10,
    "completed_orders": 8,
    "rating": "4.5",
    "created_at": "2025-01-20T00:00:00Z",
    "updated_at": "2025-01-20T00:00:00Z",
}

MOCK_OFFER = {
    "id": "offer_456",
    "service_id": "svc_123",
    "provider_agent_id": "agent_001",
    "consumer_agent_id": "agent_002",
    "status": "pending",
    "total_amount": "50.00",
    "token": "USDC",
    "escrow_amount": "0",
    "released_amount": "0",
    "created_at": "2025-01-20T00:00:00Z",
}

MOCK_REVIEW = {
    "id": "review_789",
    "offer_id": "offer_456",
    "service_id": "svc_123",
    "reviewer_agent_id": "agent_002",
    "rating": 5,
    "comment": "Great service!",
    "created_at": "2025-01-20T00:00:00Z",
}


class TestListCategories:
    """Tests for listing categories."""

    async def test_list_categories(self, client, httpx_mock):
        """Should list all categories."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/categories",
            method="GET",
            json={"categories": ["payment", "data", "compute"]},
        )

        categories = await client.marketplace.list_categories()
        assert len(categories) == 3
        assert "payment" in categories

    async def test_list_empty_categories(self, client, httpx_mock):
        """Should handle empty categories."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/categories",
            method="GET",
            json={"categories": []},
        )

        categories = await client.marketplace.list_categories()
        assert len(categories) == 0


class TestCreateService:
    """Tests for creating services."""

    async def test_create_service(self, client, httpx_mock):
        """Should create a service."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/services",
            method="POST",
            json=MOCK_SERVICE,
        )

        service = await client.marketplace.create_service(
            name="Test Service",
            category=ServiceCategory.PAYMENT,
            price_amount=Decimal("50.00"),
            description="A test service",
            tags=["test", "demo"],
        )

        assert service.service_id == "svc_123"
        assert service.name == "Test Service"

    async def test_create_service_with_all_options(self, client, httpx_mock):
        """Should create a service with all options."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/services",
            method="POST",
            json=MOCK_SERVICE,
        )

        service = await client.marketplace.create_service(
            name="Test Service",
            category=ServiceCategory.PAYMENT,
            price_amount=Decimal("50.00"),
            description="A test service",
            tags=["test"],
            price_token="USDC",
            capabilities={"api_access": True},
            api_endpoint="https://api.example.com",
        )

        assert service.api_endpoint == "https://api.example.com"


class TestListServices:
    """Tests for listing services."""

    async def test_list_all_services(self, client, httpx_mock):
        """Should list all services."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/services?limit=50&offset=0",
            method="GET",
            json={"services": [MOCK_SERVICE]},
        )

        services = await client.marketplace.list_services()
        assert len(services) == 1
        assert services[0].service_id == "svc_123"

    async def test_list_services_with_category_filter(self, client, httpx_mock):
        """Should list services with category filter."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/services?limit=50&offset=0&category=payment",
            method="GET",
            json={"services": [MOCK_SERVICE]},
        )

        services = await client.marketplace.list_services(category=ServiceCategory.PAYMENT)
        assert len(services) == 1

    async def test_list_empty_services(self, client, httpx_mock):
        """Should handle empty services list."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/services?limit=50&offset=0",
            method="GET",
            json={"services": []},
        )

        services = await client.marketplace.list_services()
        assert len(services) == 0


class TestGetService:
    """Tests for getting a service."""

    async def test_get_service(self, client, httpx_mock):
        """Should get a service by ID."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/services/svc_123",
            method="GET",
            json=MOCK_SERVICE,
        )

        service = await client.marketplace.get_service("svc_123")
        assert service.service_id == "svc_123"
        assert service.rating == Decimal("4.5")


class TestSearchServices:
    """Tests for searching services."""

    async def test_search_services(self, client, httpx_mock):
        """Should search services."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/services/search",
            method="POST",
            json={"services": [MOCK_SERVICE]},
        )

        services = await client.marketplace.search_services(query="test")
        assert len(services) == 1

    async def test_search_with_filters(self, client, httpx_mock):
        """Should search with all filters."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/services/search",
            method="POST",
            json={"services": [MOCK_SERVICE]},
        )

        services = await client.marketplace.search_services(
            query="test",
            category=ServiceCategory.PAYMENT,
            min_price=Decimal("10.00"),
            max_price=Decimal("100.00"),
            tags=["test"],
        )

        assert len(services) == 1

    async def test_search_empty_results(self, client, httpx_mock):
        """Should handle empty search results."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/services/search",
            method="POST",
            json={"services": []},
        )

        services = await client.marketplace.search_services(query="nonexistent")
        assert len(services) == 0


class TestCreateOffer:
    """Tests for creating offers."""

    async def test_create_offer(self, client, httpx_mock):
        """Should create an offer."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/offers",
            method="POST",
            json=MOCK_OFFER,
        )

        offer = await client.marketplace.create_offer(
            service_id="svc_123",
            consumer_agent_id="agent_002",
            total_amount=Decimal("50.00"),
        )

        assert offer.offer_id == "offer_456"
        assert offer.status == "pending"


class TestListOffers:
    """Tests for listing offers."""

    async def test_list_all_offers(self, client, httpx_mock):
        """Should list all offers."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/offers",
            method="GET",
            json={"offers": [MOCK_OFFER]},
        )

        offers = await client.marketplace.list_offers()
        assert len(offers) == 1

    async def test_list_offers_as_provider(self, client, httpx_mock):
        """Should list offers as provider."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/offers?as_provider=true",
            method="GET",
            json={"offers": [MOCK_OFFER]},
        )

        offers = await client.marketplace.list_offers(as_provider=True)
        assert len(offers) == 1

    async def test_list_offers_as_consumer(self, client, httpx_mock):
        """Should list offers as consumer."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/offers?as_consumer=true",
            method="GET",
            json={"offers": [MOCK_OFFER]},
        )

        offers = await client.marketplace.list_offers(as_consumer=True)
        assert len(offers) == 1

    async def test_list_offers_with_status_filter(self, client, httpx_mock):
        """Should list offers with status filter."""
        from sardis_sdk.models.marketplace import OfferStatus

        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/offers?status=pending",
            method="GET",
            json={"offers": [MOCK_OFFER]},
        )

        offers = await client.marketplace.list_offers(status=OfferStatus.PENDING)
        assert len(offers) == 1

    async def test_list_empty_offers(self, client, httpx_mock):
        """Should handle empty offers list."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/offers",
            method="GET",
            json={"offers": []},
        )

        offers = await client.marketplace.list_offers()
        assert len(offers) == 0


class TestAcceptOffer:
    """Tests for accepting offers."""

    async def test_accept_offer(self, client, httpx_mock):
        """Should accept an offer."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/offers/offer_456/accept",
            method="POST",
            json={**MOCK_OFFER, "status": "accepted"},
        )

        offer = await client.marketplace.accept_offer("offer_456")
        assert offer.status == "accepted"


class TestRejectOffer:
    """Tests for rejecting offers."""

    async def test_reject_offer(self, client, httpx_mock):
        """Should reject an offer."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/offers/offer_456/reject",
            method="POST",
            json={**MOCK_OFFER, "status": "rejected"},
        )

        offer = await client.marketplace.reject_offer("offer_456")
        assert offer.status == "rejected"


class TestCompleteOffer:
    """Tests for completing offers."""

    async def test_complete_offer(self, client, httpx_mock):
        """Should complete an offer."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/offers/offer_456/complete",
            method="POST",
            json={**MOCK_OFFER, "status": "completed"},
        )

        offer = await client.marketplace.complete_offer("offer_456")
        assert offer.status == "completed"


class TestCreateReview:
    """Tests for creating reviews."""

    async def test_create_review(self, client, httpx_mock):
        """Should create a review."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/offers/offer_456/review",
            method="POST",
            json=MOCK_REVIEW,
        )

        review = await client.marketplace.create_review(
            offer_id="offer_456",
            rating=5,
            comment="Great service!",
        )

        assert review.rating == 5
        assert review.comment == "Great service!"

    async def test_create_review_without_comment(self, client, httpx_mock):
        """Should create a review without comment."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/marketplace/offers/offer_456/review",
            method="POST",
            json={**MOCK_REVIEW, "comment": None, "rating": 4},
        )

        review = await client.marketplace.create_review(
            offer_id="offer_456",
            rating=4,
        )

        assert review.rating == 4
