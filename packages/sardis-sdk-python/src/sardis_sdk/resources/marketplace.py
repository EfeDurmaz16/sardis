"""
Marketplace resource for Sardis SDK.

This module provides both async and sync interfaces for A2A marketplace operations.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..models.marketplace import (
    CreateOfferRequest,
    CreateReviewRequest,
    CreateServiceRequest,
    OfferStatus,
    Service,
    ServiceCategory,
    ServiceOffer,
    ServiceReview,
)
from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import TimeoutConfig


class AsyncMarketplaceResource(AsyncBaseResource):
    """Async resource for A2A marketplace operations.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # Create a service
            service = await client.marketplace.create_service(
                name="AI Analysis",
                category=ServiceCategory.AI,
                price_amount=Decimal("10.00"),
            )

            # Search for services
            services = await client.marketplace.search_services(query="AI")
        ```
    """

    # ==================== Categories ====================

    async def list_categories(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[str]:
        """List all service categories.

        Args:
            timeout: Optional request timeout

        Returns:
            List of category names
        """
        response = await self._get("/api/v2/marketplace/categories", timeout=timeout)
        return response.get("categories", [])

    # ==================== Services ====================

    async def create_service(
        self,
        name: str,
        category: ServiceCategory,
        price_amount: Decimal,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        price_token: str = "USDC",
        capabilities: Optional[Dict[str, Any]] = None,
        api_endpoint: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Service:
        """Create a new service listing.

        Args:
            name: Service name
            category: Service category
            price_amount: Price amount
            description: Service description
            tags: Service tags
            price_token: Price token (default: USDC)
            capabilities: Service capabilities
            api_endpoint: API endpoint URL
            timeout: Optional request timeout

        Returns:
            Created service
        """
        request = CreateServiceRequest(
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            price_amount=price_amount,
            price_token=price_token,
            capabilities=capabilities or {},
            api_endpoint=api_endpoint,
        )
        response = await self._post("/api/v2/marketplace/services", request.to_dict(), timeout=timeout)
        return Service.model_validate(response)

    async def list_services(
        self,
        category: Optional[ServiceCategory] = None,
        limit: int = 50,
        offset: int = 0,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Service]:
        """List services in the marketplace.

        Args:
            category: Filter by category
            limit: Maximum number of services
            offset: Pagination offset
            timeout: Optional request timeout

        Returns:
            List of services
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if category:
            params["category"] = category.value
        response = await self._get("/api/v2/marketplace/services", params=params, timeout=timeout)
        return [Service.model_validate(s) for s in response.get("services", [])]

    async def get_service(
        self,
        service_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Service:
        """Get a service by ID.

        Args:
            service_id: The service ID
            timeout: Optional request timeout

        Returns:
            Service details
        """
        response = await self._get(f"/api/v2/marketplace/services/{service_id}", timeout=timeout)
        return Service.model_validate(response)

    async def search_services(
        self,
        query: Optional[str] = None,
        category: Optional[ServiceCategory] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        tags: Optional[List[str]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Service]:
        """Search for services.

        Args:
            query: Search query
            category: Filter by category
            min_price: Minimum price
            max_price: Maximum price
            tags: Filter by tags
            timeout: Optional request timeout

        Returns:
            List of matching services
        """
        data: Dict[str, Any] = {}
        if query:
            data["query"] = query
        if category:
            data["category"] = category.value
        if min_price is not None:
            data["min_price"] = str(min_price)
        if max_price is not None:
            data["max_price"] = str(max_price)
        if tags:
            data["tags"] = tags

        response = await self._post("/api/v2/marketplace/services/search", data, timeout=timeout)
        return [Service.model_validate(s) for s in response.get("services", [])]

    # ==================== Offers ====================

    async def create_offer(
        self,
        service_id: str,
        consumer_agent_id: str,
        total_amount: Decimal,
        token: str = "USDC",
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ServiceOffer:
        """Create an offer for a service.

        Args:
            service_id: The service ID
            consumer_agent_id: The consumer agent ID
            total_amount: Total offer amount
            token: Payment token (default: USDC)
            timeout: Optional request timeout

        Returns:
            Created offer
        """
        request = CreateOfferRequest(
            service_id=service_id,
            consumer_agent_id=consumer_agent_id,
            total_amount=total_amount,
            token=token,
        )
        response = await self._post("/api/v2/marketplace/offers", request.to_dict(), timeout=timeout)
        return ServiceOffer.model_validate(response)

    async def list_offers(
        self,
        status: Optional[OfferStatus] = None,
        as_provider: bool = False,
        as_consumer: bool = False,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[ServiceOffer]:
        """List offers.

        Args:
            status: Filter by status
            as_provider: Filter offers where you are the provider
            as_consumer: Filter offers where you are the consumer
            timeout: Optional request timeout

        Returns:
            List of offers
        """
        params: Dict[str, Any] = {}
        if status:
            params["status"] = status.value
        if as_provider:
            params["as_provider"] = "true"
        if as_consumer:
            params["as_consumer"] = "true"
        response = await self._get("/api/v2/marketplace/offers", params=params, timeout=timeout)
        return [ServiceOffer.model_validate(o) for o in response.get("offers", [])]

    async def accept_offer(
        self,
        offer_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ServiceOffer:
        """Accept an offer (as provider).

        Args:
            offer_id: The offer ID
            timeout: Optional request timeout

        Returns:
            Updated offer
        """
        response = await self._post(f"/api/v2/marketplace/offers/{offer_id}/accept", {}, timeout=timeout)
        return ServiceOffer.model_validate(response)

    async def reject_offer(
        self,
        offer_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ServiceOffer:
        """Reject an offer (as provider).

        Args:
            offer_id: The offer ID
            timeout: Optional request timeout

        Returns:
            Updated offer
        """
        response = await self._post(f"/api/v2/marketplace/offers/{offer_id}/reject", {}, timeout=timeout)
        return ServiceOffer.model_validate(response)

    async def complete_offer(
        self,
        offer_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ServiceOffer:
        """Mark an offer as completed.

        Args:
            offer_id: The offer ID
            timeout: Optional request timeout

        Returns:
            Updated offer
        """
        response = await self._post(f"/api/v2/marketplace/offers/{offer_id}/complete", {}, timeout=timeout)
        return ServiceOffer.model_validate(response)

    # ==================== Reviews ====================

    async def create_review(
        self,
        offer_id: str,
        rating: int,
        comment: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ServiceReview:
        """Create a review for a completed offer.

        Args:
            offer_id: The offer ID
            rating: Rating (1-5)
            comment: Optional review comment
            timeout: Optional request timeout

        Returns:
            Created review
        """
        request = CreateReviewRequest(rating=rating, comment=comment)
        response = await self._post(
            f"/api/v2/marketplace/offers/{offer_id}/review",
            request.to_dict(),
            timeout=timeout,
        )
        return ServiceReview.model_validate(response)


class MarketplaceResource(SyncBaseResource):
    """Sync resource for A2A marketplace operations.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # Create a service
            service = client.marketplace.create_service(
                name="AI Analysis",
                category=ServiceCategory.AI,
                price_amount=Decimal("10.00"),
            )

            # Search for services
            services = client.marketplace.search_services(query="AI")
        ```
    """

    # ==================== Categories ====================

    def list_categories(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[str]:
        """List all service categories.

        Args:
            timeout: Optional request timeout

        Returns:
            List of category names
        """
        response = self._get("/api/v2/marketplace/categories", timeout=timeout)
        return response.get("categories", [])

    # ==================== Services ====================

    def create_service(
        self,
        name: str,
        category: ServiceCategory,
        price_amount: Decimal,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        price_token: str = "USDC",
        capabilities: Optional[Dict[str, Any]] = None,
        api_endpoint: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Service:
        """Create a new service listing.

        Args:
            name: Service name
            category: Service category
            price_amount: Price amount
            description: Service description
            tags: Service tags
            price_token: Price token (default: USDC)
            capabilities: Service capabilities
            api_endpoint: API endpoint URL
            timeout: Optional request timeout

        Returns:
            Created service
        """
        request = CreateServiceRequest(
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            price_amount=price_amount,
            price_token=price_token,
            capabilities=capabilities or {},
            api_endpoint=api_endpoint,
        )
        response = self._post("/api/v2/marketplace/services", request.to_dict(), timeout=timeout)
        return Service.model_validate(response)

    def list_services(
        self,
        category: Optional[ServiceCategory] = None,
        limit: int = 50,
        offset: int = 0,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Service]:
        """List services in the marketplace.

        Args:
            category: Filter by category
            limit: Maximum number of services
            offset: Pagination offset
            timeout: Optional request timeout

        Returns:
            List of services
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if category:
            params["category"] = category.value
        response = self._get("/api/v2/marketplace/services", params=params, timeout=timeout)
        return [Service.model_validate(s) for s in response.get("services", [])]

    def get_service(
        self,
        service_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Service:
        """Get a service by ID.

        Args:
            service_id: The service ID
            timeout: Optional request timeout

        Returns:
            Service details
        """
        response = self._get(f"/api/v2/marketplace/services/{service_id}", timeout=timeout)
        return Service.model_validate(response)

    def search_services(
        self,
        query: Optional[str] = None,
        category: Optional[ServiceCategory] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        tags: Optional[List[str]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Service]:
        """Search for services.

        Args:
            query: Search query
            category: Filter by category
            min_price: Minimum price
            max_price: Maximum price
            tags: Filter by tags
            timeout: Optional request timeout

        Returns:
            List of matching services
        """
        data: Dict[str, Any] = {}
        if query:
            data["query"] = query
        if category:
            data["category"] = category.value
        if min_price is not None:
            data["min_price"] = str(min_price)
        if max_price is not None:
            data["max_price"] = str(max_price)
        if tags:
            data["tags"] = tags

        response = self._post("/api/v2/marketplace/services/search", data, timeout=timeout)
        return [Service.model_validate(s) for s in response.get("services", [])]

    # ==================== Offers ====================

    def create_offer(
        self,
        service_id: str,
        consumer_agent_id: str,
        total_amount: Decimal,
        token: str = "USDC",
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ServiceOffer:
        """Create an offer for a service.

        Args:
            service_id: The service ID
            consumer_agent_id: The consumer agent ID
            total_amount: Total offer amount
            token: Payment token (default: USDC)
            timeout: Optional request timeout

        Returns:
            Created offer
        """
        request = CreateOfferRequest(
            service_id=service_id,
            consumer_agent_id=consumer_agent_id,
            total_amount=total_amount,
            token=token,
        )
        response = self._post("/api/v2/marketplace/offers", request.to_dict(), timeout=timeout)
        return ServiceOffer.model_validate(response)

    def list_offers(
        self,
        status: Optional[OfferStatus] = None,
        as_provider: bool = False,
        as_consumer: bool = False,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[ServiceOffer]:
        """List offers.

        Args:
            status: Filter by status
            as_provider: Filter offers where you are the provider
            as_consumer: Filter offers where you are the consumer
            timeout: Optional request timeout

        Returns:
            List of offers
        """
        params: Dict[str, Any] = {}
        if status:
            params["status"] = status.value
        if as_provider:
            params["as_provider"] = "true"
        if as_consumer:
            params["as_consumer"] = "true"
        response = self._get("/api/v2/marketplace/offers", params=params, timeout=timeout)
        return [ServiceOffer.model_validate(o) for o in response.get("offers", [])]

    def accept_offer(
        self,
        offer_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ServiceOffer:
        """Accept an offer (as provider).

        Args:
            offer_id: The offer ID
            timeout: Optional request timeout

        Returns:
            Updated offer
        """
        response = self._post(f"/api/v2/marketplace/offers/{offer_id}/accept", {}, timeout=timeout)
        return ServiceOffer.model_validate(response)

    def reject_offer(
        self,
        offer_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ServiceOffer:
        """Reject an offer (as provider).

        Args:
            offer_id: The offer ID
            timeout: Optional request timeout

        Returns:
            Updated offer
        """
        response = self._post(f"/api/v2/marketplace/offers/{offer_id}/reject", {}, timeout=timeout)
        return ServiceOffer.model_validate(response)

    def complete_offer(
        self,
        offer_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ServiceOffer:
        """Mark an offer as completed.

        Args:
            offer_id: The offer ID
            timeout: Optional request timeout

        Returns:
            Updated offer
        """
        response = self._post(f"/api/v2/marketplace/offers/{offer_id}/complete", {}, timeout=timeout)
        return ServiceOffer.model_validate(response)

    # ==================== Reviews ====================

    def create_review(
        self,
        offer_id: str,
        rating: int,
        comment: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ServiceReview:
        """Create a review for a completed offer.

        Args:
            offer_id: The offer ID
            rating: Rating (1-5)
            comment: Optional review comment
            timeout: Optional request timeout

        Returns:
            Created review
        """
        request = CreateReviewRequest(rating=rating, comment=comment)
        response = self._post(
            f"/api/v2/marketplace/offers/{offer_id}/review",
            request.to_dict(),
            timeout=timeout,
        )
        return ServiceReview.model_validate(response)


__all__ = [
    "AsyncMarketplaceResource",
    "MarketplaceResource",
]
