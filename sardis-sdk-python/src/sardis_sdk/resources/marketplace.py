"""Marketplace resource for Sardis SDK."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

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
from .base import BaseResource


class MarketplaceResource(BaseResource):
    """Resource for A2A marketplace operations."""
    
    # ==================== Categories ====================
    
    async def list_categories(self) -> list[str]:
        """
        List all service categories.
        
        Returns:
            List of category names
        """
        response = await self._get("/api/v2/marketplace/categories")
        return response.get("categories", [])
    
    # ==================== Services ====================
    
    async def create_service(
        self,
        name: str,
        category: ServiceCategory,
        price_amount: Decimal,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        price_token: str = "USDC",
        capabilities: Optional[dict[str, Any]] = None,
        api_endpoint: Optional[str] = None,
    ) -> Service:
        """
        Create a new service listing.
        
        Args:
            name: Service name
            category: Service category
            price_amount: Price amount
            description: Service description
            tags: Service tags
            price_token: Price token (default: USDC)
            capabilities: Service capabilities
            api_endpoint: API endpoint URL
            
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
        response = await self._post("/api/v2/marketplace/services", request.to_dict())
        return Service.model_validate(response)
    
    async def list_services(
        self,
        category: Optional[ServiceCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Service]:
        """
        List services in the marketplace.
        
        Args:
            category: Filter by category
            limit: Maximum number of services
            offset: Pagination offset
            
        Returns:
            List of services
        """
        params = {"limit": limit, "offset": offset}
        if category:
            params["category"] = category.value
        response = await self._get("/api/v2/marketplace/services", params=params)
        return [Service.model_validate(s) for s in response.get("services", [])]
    
    async def get_service(self, service_id: str) -> Service:
        """
        Get a service by ID.
        
        Args:
            service_id: The service ID
            
        Returns:
            Service details
        """
        response = await self._get(f"/api/v2/marketplace/services/{service_id}")
        return Service.model_validate(response)
    
    async def search_services(
        self,
        query: Optional[str] = None,
        category: Optional[ServiceCategory] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        tags: Optional[list[str]] = None,
    ) -> list[Service]:
        """
        Search for services.
        
        Args:
            query: Search query
            category: Filter by category
            min_price: Minimum price
            max_price: Maximum price
            tags: Filter by tags
            
        Returns:
            List of matching services
        """
        data: dict[str, Any] = {}
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
        
        response = await self._post("/api/v2/marketplace/services/search", data)
        return [Service.model_validate(s) for s in response.get("services", [])]
    
    # ==================== Offers ====================
    
    async def create_offer(
        self,
        service_id: str,
        consumer_agent_id: str,
        total_amount: Decimal,
        token: str = "USDC",
    ) -> ServiceOffer:
        """
        Create an offer for a service.
        
        Args:
            service_id: The service ID
            consumer_agent_id: The consumer agent ID
            total_amount: Total offer amount
            token: Payment token (default: USDC)
            
        Returns:
            Created offer
        """
        request = CreateOfferRequest(
            service_id=service_id,
            consumer_agent_id=consumer_agent_id,
            total_amount=total_amount,
            token=token,
        )
        response = await self._post("/api/v2/marketplace/offers", request.to_dict())
        return ServiceOffer.model_validate(response)
    
    async def list_offers(
        self,
        status: Optional[OfferStatus] = None,
        as_provider: bool = False,
        as_consumer: bool = False,
    ) -> list[ServiceOffer]:
        """
        List offers.
        
        Args:
            status: Filter by status
            as_provider: Filter offers where you are the provider
            as_consumer: Filter offers where you are the consumer
            
        Returns:
            List of offers
        """
        params: dict[str, Any] = {}
        if status:
            params["status"] = status.value
        if as_provider:
            params["as_provider"] = "true"
        if as_consumer:
            params["as_consumer"] = "true"
        response = await self._get("/api/v2/marketplace/offers", params=params)
        return [ServiceOffer.model_validate(o) for o in response.get("offers", [])]
    
    async def accept_offer(self, offer_id: str) -> ServiceOffer:
        """
        Accept an offer (as provider).
        
        Args:
            offer_id: The offer ID
            
        Returns:
            Updated offer
        """
        response = await self._post(f"/api/v2/marketplace/offers/{offer_id}/accept", {})
        return ServiceOffer.model_validate(response)
    
    async def reject_offer(self, offer_id: str) -> ServiceOffer:
        """
        Reject an offer (as provider).
        
        Args:
            offer_id: The offer ID
            
        Returns:
            Updated offer
        """
        response = await self._post(f"/api/v2/marketplace/offers/{offer_id}/reject", {})
        return ServiceOffer.model_validate(response)
    
    async def complete_offer(self, offer_id: str) -> ServiceOffer:
        """
        Mark an offer as completed.
        
        Args:
            offer_id: The offer ID
            
        Returns:
            Updated offer
        """
        response = await self._post(f"/api/v2/marketplace/offers/{offer_id}/complete", {})
        return ServiceOffer.model_validate(response)
    
    # ==================== Reviews ====================
    
    async def create_review(
        self,
        offer_id: str,
        rating: int,
        comment: Optional[str] = None,
    ) -> ServiceReview:
        """
        Create a review for a completed offer.
        
        Args:
            offer_id: The offer ID
            rating: Rating (1-5)
            comment: Optional review comment
            
        Returns:
            Created review
        """
        request = CreateReviewRequest(rating=rating, comment=comment)
        response = await self._post(
            f"/api/v2/marketplace/offers/{offer_id}/review",
            request.to_dict(),
        )
        return ServiceReview.model_validate(response)
