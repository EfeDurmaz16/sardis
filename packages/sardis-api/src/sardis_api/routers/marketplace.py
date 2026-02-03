"""Marketplace API routes for A2A service discovery and offers."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from pydantic import BaseModel, Field

from sardis_v2_core.marketplace import (
    MarketplaceRepository,
    ServiceListing,
    ServiceOffer,
    ServiceReview,
    Milestone,
    ServiceCategory,
    ServiceStatus,
    OfferStatus,
    MilestoneStatus,
)

from sardis_api.authz import require_principal


router = APIRouter(dependencies=[Depends(require_principal)], tags=["marketplace"])


# Request/Response Models

class CreateServiceRequest(BaseModel):
    """Request to create a service listing."""
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=2000)
    category: str = Field(default="other")
    tags: List[str] = Field(default_factory=list)
    price_amount: str = Field(..., description="Price in token units")
    price_token: str = Field(default="USDC")
    price_type: str = Field(default="fixed", description="fixed, hourly, per_request")
    capabilities: dict = Field(default_factory=dict)
    api_endpoint: Optional[str] = None


class ServiceResponse(BaseModel):
    """Service listing response."""
    service_id: str
    provider_agent_id: str
    name: str
    description: str
    category: str
    tags: List[str]
    price_amount: str
    price_token: str
    price_type: str
    status: str
    rating: Optional[str]
    total_orders: int
    completed_orders: int
    created_at: datetime

    @classmethod
    def from_service(cls, s: ServiceListing) -> "ServiceResponse":
        return cls(
            service_id=s.service_id,
            provider_agent_id=s.provider_agent_id,
            name=s.name,
            description=s.description,
            category=s.category.value,
            tags=s.tags,
            price_amount=str(s.price_amount),
            price_token=s.price_token,
            price_type=s.price_type,
            status=s.status.value,
            rating=str(s.rating) if s.rating else None,
            total_orders=s.total_orders,
            completed_orders=s.completed_orders,
            created_at=s.created_at,
        )


class CreateOfferRequest(BaseModel):
    """Request to create a service offer."""
    service_id: str
    total_amount: str
    token: str = "USDC"
    milestones: List[dict] = Field(default_factory=list)


class OfferResponse(BaseModel):
    """Service offer response."""
    offer_id: str
    service_id: str
    provider_agent_id: str
    consumer_agent_id: str
    total_amount: str
    token: str
    status: str
    escrow_amount: str
    released_amount: str
    created_at: datetime
    accepted_at: Optional[datetime]
    completed_at: Optional[datetime]

    @classmethod
    def from_offer(cls, o: ServiceOffer) -> "OfferResponse":
        return cls(
            offer_id=o.offer_id,
            service_id=o.service_id,
            provider_agent_id=o.provider_agent_id,
            consumer_agent_id=o.consumer_agent_id,
            total_amount=str(o.total_amount),
            token=o.token,
            status=o.status.value,
            escrow_amount=str(o.escrow_amount),
            released_amount=str(o.released_amount),
            created_at=o.created_at,
            accepted_at=o.accepted_at,
            completed_at=o.completed_at,
        )


class CreateReviewRequest(BaseModel):
    """Request to create a review."""
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class ReviewResponse(BaseModel):
    """Review response."""
    review_id: str
    offer_id: str
    service_id: str
    reviewer_agent_id: str
    rating: int
    comment: str
    created_at: datetime

    @classmethod
    def from_review(cls, r: ServiceReview) -> "ReviewResponse":
        return cls(
            review_id=r.review_id,
            offer_id=r.offer_id,
            service_id=r.service_id,
            reviewer_agent_id=r.reviewer_agent_id,
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at,
        )


class SearchRequest(BaseModel):
    """Search request."""
    query: str = Field(..., min_length=1)
    category: Optional[str] = None
    min_rating: Optional[str] = None
    max_price: Optional[str] = None


# Dependencies

class MarketplaceDependencies:
    """Dependencies for marketplace routes."""
    def __init__(self, repository: MarketplaceRepository):
        self.repository = repository


def get_deps() -> MarketplaceDependencies:
    """Dependency injection placeholder."""
    raise NotImplementedError("Must be overridden")


# Routes - Services

@router.get("/categories")
async def list_categories():
    """List all service categories."""
    return {
        "categories": [
            {"value": c.value, "name": c.name.replace("_", " ").title()}
            for c in ServiceCategory
        ]
    }


@router.post("/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    request: CreateServiceRequest,
    deps: MarketplaceDependencies = Depends(get_deps),
    x_agent_id: str = Header(..., alias="X-Agent-Id", description="Agent ID for this operation"),
):
    """Create a new service listing."""
    provider_agent_id = x_agent_id
    try:
        category = ServiceCategory(request.category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {request.category}",
        )
    
    service = ServiceListing(
        provider_agent_id=provider_agent_id,
        name=request.name,
        description=request.description,
        category=category,
        tags=request.tags,
        price_amount=Decimal(request.price_amount),
        price_token=request.price_token,
        price_type=request.price_type,
        capabilities=request.capabilities,
        api_endpoint=request.api_endpoint,
        status=ServiceStatus.ACTIVE,
    )
    
    service = await deps.repository.create_service(service)
    return ServiceResponse.from_service(service)


@router.get("/services", response_model=List[ServiceResponse])
async def list_services(
    category: Optional[str] = None,
    provider_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    deps: MarketplaceDependencies = Depends(get_deps),
):
    """List active services."""
    cat = ServiceCategory(category) if category else None
    services = await deps.repository.list_services(
        category=cat,
        provider_id=provider_id,
        limit=limit,
    )
    return [ServiceResponse.from_service(s) for s in services]


@router.get("/services/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: str,
    deps: MarketplaceDependencies = Depends(get_deps),
):
    """Get a service by ID."""
    service = await deps.repository.get_service(service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found",
        )
    return ServiceResponse.from_service(service)


@router.patch("/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    deps: MarketplaceDependencies = Depends(get_deps),
):
    """Update a service listing."""
    updates = {}
    if name:
        updates["name"] = name
    if description:
        updates["description"] = description
    if status:
        updates["status"] = ServiceStatus(status)
    
    service = await deps.repository.update_service(service_id, **updates)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found",
        )
    return ServiceResponse.from_service(service)


@router.post("/services/search", response_model=List[ServiceResponse])
async def search_services(
    request: SearchRequest,
    limit: int = Query(default=50, ge=1, le=100),
    deps: MarketplaceDependencies = Depends(get_deps),
):
    """Search for services."""
    cat = ServiceCategory(request.category) if request.category else None
    min_rating = Decimal(request.min_rating) if request.min_rating else None
    max_price = Decimal(request.max_price) if request.max_price else None
    
    services = await deps.repository.search_services(
        query=request.query,
        category=cat,
        min_rating=min_rating,
        max_price=max_price,
        limit=limit,
    )
    return [ServiceResponse.from_service(s) for s in services]


# Routes - Offers

@router.post("/offers", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(
    request: CreateOfferRequest,
    deps: MarketplaceDependencies = Depends(get_deps),
    x_agent_id: str = Header(..., alias="X-Agent-Id", description="Agent ID for this operation"),
):
    """Create a service offer."""
    consumer_agent_id = x_agent_id
    # Get the service to find provider
    service = await deps.repository.get_service(request.service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {request.service_id} not found",
        )
    
    # Create milestones
    milestones = []
    for m in request.milestones:
        milestones.append(Milestone(
            name=m.get("name", ""),
            description=m.get("description", ""),
            amount=Decimal(m.get("amount", "0")),
        ))
    
    offer = ServiceOffer(
        service_id=request.service_id,
        provider_agent_id=service.provider_agent_id,
        consumer_agent_id=consumer_agent_id,
        total_amount=Decimal(request.total_amount),
        token=request.token,
        milestones=milestones,
    )
    
    offer = await deps.repository.create_offer(offer)
    return OfferResponse.from_offer(offer)


@router.get("/offers", response_model=List[OfferResponse])
async def list_offers(
    role: str = Query(default="any", pattern="^(provider|consumer|any)$"),
    x_agent_id: str = Header(..., alias="X-Agent-Id", description="Agent ID for this operation"),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    deps: MarketplaceDependencies = Depends(get_deps),
):
    """List offers for an agent."""
    agent_id = x_agent_id
    offer_status = OfferStatus(status_filter) if status_filter else None
    offers = await deps.repository.list_offers(
        agent_id=agent_id,
        role=role,
        status=offer_status,
        limit=limit,
    )
    return [OfferResponse.from_offer(o) for o in offers]


@router.get("/offers/{offer_id}", response_model=OfferResponse)
async def get_offer(
    offer_id: str,
    deps: MarketplaceDependencies = Depends(get_deps),
):
    """Get an offer by ID."""
    offer = await deps.repository.get_offer(offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {offer_id} not found",
        )
    return OfferResponse.from_offer(offer)


@router.post("/offers/{offer_id}/accept", response_model=OfferResponse)
async def accept_offer(
    offer_id: str,
    deps: MarketplaceDependencies = Depends(get_deps),
):
    """Accept an offer (provider action)."""
    offer = await deps.repository.update_offer_status(offer_id, OfferStatus.ACCEPTED)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {offer_id} not found",
        )
    return OfferResponse.from_offer(offer)


@router.post("/offers/{offer_id}/reject", response_model=OfferResponse)
async def reject_offer(
    offer_id: str,
    deps: MarketplaceDependencies = Depends(get_deps),
):
    """Reject an offer (provider action)."""
    offer = await deps.repository.update_offer_status(offer_id, OfferStatus.REJECTED)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {offer_id} not found",
        )
    return OfferResponse.from_offer(offer)


@router.post("/offers/{offer_id}/complete", response_model=OfferResponse)
async def complete_offer(
    offer_id: str,
    deps: MarketplaceDependencies = Depends(get_deps),
):
    """Mark an offer as completed."""
    offer = await deps.repository.update_offer_status(offer_id, OfferStatus.COMPLETED)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {offer_id} not found",
        )
    return OfferResponse.from_offer(offer)


# Routes - Reviews

@router.post("/offers/{offer_id}/review", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    offer_id: str,
    request: CreateReviewRequest,
    deps: MarketplaceDependencies = Depends(get_deps),
    x_agent_id: str = Header(..., alias="X-Agent-Id", description="Agent ID for this operation"),
):
    """Create a review for a completed offer."""
    reviewer_agent_id = x_agent_id
    offer = await deps.repository.get_offer(offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {offer_id} not found",
        )
    
    if offer.status != OfferStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only review completed offers",
        )
    
    review = ServiceReview(
        offer_id=offer_id,
        service_id=offer.service_id,
        reviewer_agent_id=reviewer_agent_id,
        rating=request.rating,
        comment=request.comment,
    )
    
    review = await deps.repository.create_review(review)
    return ReviewResponse.from_review(review)


@router.get("/services/{service_id}/reviews", response_model=List[ReviewResponse])
async def list_reviews(
    service_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    deps: MarketplaceDependencies = Depends(get_deps),
):
    """List reviews for a service."""
    reviews = await deps.repository.list_reviews(service_id, limit=limit)
    return [ReviewResponse.from_review(r) for r in reviews]
