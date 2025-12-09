"""Marketplace models for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import Field

from .base import SardisModel


class ServiceCategory(str, Enum):
    """Service categories."""
    
    PAYMENT = "payment"
    DATA = "data"
    COMPUTE = "compute"
    AI = "ai"
    STORAGE = "storage"
    ORACLE = "oracle"
    OTHER = "other"


class ServiceStatus(str, Enum):
    """Service status."""
    
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class OfferStatus(str, Enum):
    """Offer status."""
    
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class Service(SardisModel):
    """A service listing in the marketplace."""
    
    service_id: str = Field(alias="id")
    provider_agent_id: str
    name: str
    description: Optional[str] = None
    category: ServiceCategory
    tags: list[str] = Field(default_factory=list)
    price_amount: Decimal
    price_token: str = "USDC"
    price_type: str = "fixed"
    capabilities: dict[str, Any] = Field(default_factory=dict)
    api_endpoint: Optional[str] = None
    status: ServiceStatus = ServiceStatus.DRAFT
    total_orders: int = 0
    completed_orders: int = 0
    rating: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime


class ServiceOffer(SardisModel):
    """An offer for a service."""
    
    offer_id: str = Field(alias="id")
    service_id: str
    provider_agent_id: str
    consumer_agent_id: str
    total_amount: Decimal
    token: str = "USDC"
    status: OfferStatus
    escrow_tx_hash: Optional[str] = None
    escrow_amount: Decimal = Decimal("0")
    released_amount: Decimal = Decimal("0")
    created_at: datetime
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ServiceReview(SardisModel):
    """A review for a service."""
    
    review_id: str = Field(alias="id")
    offer_id: str
    service_id: str
    reviewer_agent_id: str
    rating: int  # 1-5
    comment: Optional[str] = None
    created_at: datetime


class CreateServiceRequest(SardisModel):
    """Request to create a service listing."""
    
    name: str
    description: Optional[str] = None
    category: ServiceCategory
    tags: list[str] = Field(default_factory=list)
    price_amount: Decimal
    price_token: str = "USDC"
    price_type: str = "fixed"
    capabilities: dict[str, Any] = Field(default_factory=dict)
    api_endpoint: Optional[str] = None


class CreateOfferRequest(SardisModel):
    """Request to create a service offer."""
    
    service_id: str
    consumer_agent_id: str
    total_amount: Decimal
    token: str = "USDC"


class CreateReviewRequest(SardisModel):
    """Request to create a service review."""
    
    rating: int  # 1-5
    comment: Optional[str] = None
