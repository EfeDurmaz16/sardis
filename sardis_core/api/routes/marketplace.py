"""Marketplace API endpoints for service discovery and agent-to-agent payments."""

from decimal import Decimal
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_core.marketplace.registry import (
    get_service_registry,
    ServiceCategory,
    PricingModel,
    ServicePricing,
)
from sardis_core.marketplace.protocol import (
    get_marketplace_protocol,
    PaymentTerms,
    RequestStatus,
)


router = APIRouter(prefix="/marketplace", tags=["marketplace"])


# ========== Request/Response Models ==========

class RegisterServiceRequest(BaseModel):
    """Request to register a new service."""
    provider_agent_id: str
    provider_wallet_id: str
    name: str
    description: str
    category: str
    pricing_model: str
    base_price: str
    unit_name: Optional[str] = None
    tags: Optional[List[str]] = None
    capabilities: Optional[dict] = None


class ServiceResponse(BaseModel):
    """Response containing service details."""
    service_id: str
    provider_agent_id: str
    name: str
    description: str
    category: str
    tags: List[str]
    pricing: Optional[dict]
    rating: dict
    is_available: bool
    is_verified: bool
    created_at: str


class CreateRequestRequest(BaseModel):
    """Request to create a service request."""
    requester_agent_id: str
    requester_wallet_id: str
    service_id: str
    total_amount: str
    input_data: Optional[dict] = None
    parameters: Optional[dict] = None
    use_escrow: bool = True


class RequestResponse(BaseModel):
    """Response containing request details."""
    request_id: str
    requester_agent_id: str
    provider_agent_id: str
    service_id: str
    service_name: str
    status: str
    payment_terms: Optional[dict]
    escrow: Optional[dict]
    created_at: str


class CompleteRequestRequest(BaseModel):
    """Request to complete a service request."""
    output_data: dict
    processing_time_ms: int = 0
    units_consumed: int = 0


class DisputeRequest(BaseModel):
    """Request to dispute a service request."""
    disputer_agent_id: str
    reason: str


class RateServiceRequest(BaseModel):
    """Request to rate a service."""
    score: float = Field(..., ge=1.0, le=5.0)
    success: bool = True


# ========== Service Registry Endpoints ==========

@router.post(
    "/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new service",
    description="Register a service that an agent offers in the marketplace."
)
async def register_service(request: RegisterServiceRequest) -> ServiceResponse:
    """Register a new service."""
    registry = get_service_registry()
    
    try:
        category = ServiceCategory(request.category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Valid: {[c.value for c in ServiceCategory]}"
        )
    
    try:
        pricing_model = PricingModel(request.pricing_model)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pricing model. Valid: {[p.value for p in PricingModel]}"
        )
    
    pricing = ServicePricing(
        model=pricing_model,
        base_price=Decimal(request.base_price),
        unit_name=request.unit_name,
    )
    
    service = registry.register_service(
        provider_agent_id=request.provider_agent_id,
        provider_wallet_id=request.provider_wallet_id,
        name=request.name,
        description=request.description,
        category=category,
        pricing=pricing,
        tags=request.tags,
        capabilities=request.capabilities,
    )
    
    return ServiceResponse(**service.to_dict())


@router.get(
    "/services",
    response_model=List[ServiceResponse],
    summary="List available services",
    description="Browse services in the marketplace with optional filters."
)
async def list_services(
    category: Optional[str] = None,
    provider_agent_id: Optional[str] = None,
    tags: Optional[str] = None,
    max_price: Optional[str] = None,
    min_rating: Optional[float] = None,
    available_only: bool = True,
    limit: int = Query(50, le=100),
    offset: int = 0,
) -> List[ServiceResponse]:
    """List services with optional filters."""
    registry = get_service_registry()
    
    cat = None
    if category:
        try:
            cat = ServiceCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    tag_list = tags.split(",") if tags else None
    price = Decimal(max_price) if max_price else None
    
    services = registry.list_services(
        category=cat,
        provider_agent_id=provider_agent_id,
        tags=tag_list,
        max_price=price,
        min_rating=min_rating,
        available_only=available_only,
        limit=limit,
        offset=offset,
    )
    
    return [ServiceResponse(**s.to_dict()) for s in services]


@router.get(
    "/services/search",
    response_model=List[ServiceResponse],
    summary="Search services",
    description="Search services by name, description, or tags."
)
async def search_services(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, le=50),
) -> List[ServiceResponse]:
    """Search services."""
    registry = get_service_registry()
    services = registry.search_services(q, limit=limit)
    return [ServiceResponse(**s.to_dict()) for s in services]


@router.get(
    "/services/{service_id}",
    response_model=ServiceResponse,
    summary="Get service by ID",
    description="Get details of a specific service."
)
async def get_service(service_id: str) -> ServiceResponse:
    """Get service by ID."""
    registry = get_service_registry()
    service = registry.get_service(service_id)
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return ServiceResponse(**service.to_dict())


@router.post(
    "/services/{service_id}/rate",
    summary="Rate a service",
    description="Add a rating to a service after using it."
)
async def rate_service(service_id: str, request: RateServiceRequest):
    """Rate a service."""
    registry = get_service_registry()
    
    rating = registry.rate_service(service_id, request.score, request.success)
    if not rating:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return {
        "message": "Rating added",
        "new_average": rating.average_score,
        "total_ratings": rating.total_ratings,
    }


@router.get(
    "/services/top",
    response_model=List[ServiceResponse],
    summary="Get top-rated services",
    description="Get the highest-rated services in the marketplace."
)
async def get_top_services(
    category: Optional[str] = None,
    limit: int = Query(10, le=50),
) -> List[ServiceResponse]:
    """Get top-rated services."""
    registry = get_service_registry()
    
    cat = None
    if category:
        try:
            cat = ServiceCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    services = registry.get_top_services(category=cat, limit=limit)
    return [ServiceResponse(**s.to_dict()) for s in services]


# ========== Service Request Endpoints ==========

@router.post(
    "/requests",
    response_model=RequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a service request",
    description="Request a service from another agent."
)
async def create_request(request: CreateRequestRequest) -> RequestResponse:
    """Create a service request."""
    registry = get_service_registry()
    protocol = get_marketplace_protocol()
    
    # Get service
    service = registry.get_service(request.service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if not service.is_available:
        raise HTTPException(status_code=400, detail="Service is not available")
    
    # Create payment terms
    payment_terms = PaymentTerms(
        total_amount=Decimal(request.total_amount),
        use_escrow=request.use_escrow,
    )
    
    # Create request
    service_request = protocol.create_request(
        requester_agent_id=request.requester_agent_id,
        requester_wallet_id=request.requester_wallet_id,
        provider_agent_id=service.provider_agent_id,
        provider_wallet_id=service.provider_wallet_id,
        service_id=service.service_id,
        service_name=service.name,
        payment_terms=payment_terms,
        input_data=request.input_data,
        parameters=request.parameters,
    )
    
    return RequestResponse(**service_request.to_dict())


@router.get(
    "/requests",
    response_model=List[RequestResponse],
    summary="List service requests",
    description="List service requests for an agent."
)
async def list_requests(
    agent_id: str,
    status: Optional[str] = None,
    as_requester: bool = True,
    as_provider: bool = True,
    limit: int = Query(50, le=100),
) -> List[RequestResponse]:
    """List requests for an agent."""
    protocol = get_marketplace_protocol()
    
    req_status = None
    if status:
        try:
            req_status = RequestStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    requests = protocol.list_requests(
        agent_id=agent_id,
        status=req_status,
        as_requester=as_requester,
        as_provider=as_provider,
        limit=limit,
    )
    
    return [RequestResponse(**r.to_dict()) for r in requests]


@router.get(
    "/requests/{request_id}",
    response_model=RequestResponse,
    summary="Get request by ID",
    description="Get details of a specific service request."
)
async def get_request(request_id: str) -> RequestResponse:
    """Get request by ID."""
    protocol = get_marketplace_protocol()
    request = protocol.get_request(request_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return RequestResponse(**request.to_dict())


@router.post(
    "/requests/{request_id}/accept",
    response_model=RequestResponse,
    summary="Accept a request",
    description="Provider accepts a service request."
)
async def accept_request(request_id: str) -> RequestResponse:
    """Accept a service request."""
    protocol = get_marketplace_protocol()
    
    request = protocol.accept_request(request_id)
    if not request:
        raise HTTPException(status_code=400, detail="Cannot accept request")
    
    return RequestResponse(**request.to_dict())


@router.post(
    "/requests/{request_id}/start",
    response_model=RequestResponse,
    summary="Start processing request",
    description="Mark request as in progress."
)
async def start_request(request_id: str) -> RequestResponse:
    """Start processing a request."""
    protocol = get_marketplace_protocol()
    
    request = protocol.start_request(request_id)
    if not request:
        raise HTTPException(status_code=400, detail="Cannot start request")
    
    return RequestResponse(**request.to_dict())


@router.post(
    "/requests/{request_id}/complete",
    summary="Complete a request",
    description="Mark request as completed and deliver results."
)
async def complete_request(
    request_id: str,
    body: CompleteRequestRequest
):
    """Complete a service request."""
    protocol = get_marketplace_protocol()
    
    response = protocol.complete_request(
        request_id=request_id,
        output_data=body.output_data,
        processing_time_ms=body.processing_time_ms,
        units_consumed=body.units_consumed,
    )
    
    if not response:
        raise HTTPException(status_code=400, detail="Cannot complete request")
    
    return response.to_dict()


@router.post(
    "/requests/{request_id}/dispute",
    response_model=RequestResponse,
    summary="Dispute a request",
    description="Open a dispute for a completed request."
)
async def dispute_request(request_id: str, body: DisputeRequest) -> RequestResponse:
    """Dispute a service request."""
    protocol = get_marketplace_protocol()
    
    request = protocol.dispute_request(
        request_id=request_id,
        reason=body.reason,
        disputer_agent_id=body.disputer_agent_id,
    )
    
    if not request:
        raise HTTPException(status_code=400, detail="Cannot dispute request")
    
    return RequestResponse(**request.to_dict())


# ========== Stats Endpoints ==========

@router.get(
    "/stats",
    summary="Get marketplace statistics",
    description="Get overall marketplace statistics."
)
async def get_marketplace_stats():
    """Get marketplace statistics."""
    registry = get_service_registry()
    return registry.get_stats()

