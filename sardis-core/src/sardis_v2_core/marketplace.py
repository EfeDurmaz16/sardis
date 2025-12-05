"""A2A Marketplace - Service discovery and agent-to-agent payments."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4


class ServiceCategory(str, Enum):
    """Categories of agent services."""
    PAYMENT = "payment"
    DATA = "data"
    COMPUTE = "compute"
    STORAGE = "storage"
    AI = "ai"
    ORACLE = "oracle"
    BRIDGE = "bridge"
    OTHER = "other"


class ServiceStatus(str, Enum):
    """Service listing status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class OfferStatus(str, Enum):
    """Service offer status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class MilestoneStatus(str, Enum):
    """Milestone status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    DISPUTED = "disputed"
    RELEASED = "released"


@dataclass
class ServiceListing:
    """A service offered by an agent."""
    service_id: str = field(default_factory=lambda: f"svc_{uuid4().hex[:16]}")
    provider_agent_id: str = ""
    
    # Service details
    name: str = ""
    description: str = ""
    category: ServiceCategory = ServiceCategory.OTHER
    tags: List[str] = field(default_factory=list)
    
    # Pricing
    price_amount: Decimal = Decimal("0")
    price_token: str = "USDC"
    price_type: str = "fixed"  # fixed, hourly, per_request
    
    # Capabilities
    capabilities: Dict[str, Any] = field(default_factory=dict)
    api_endpoint: Optional[str] = None
    
    # Status
    status: ServiceStatus = ServiceStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Stats
    total_orders: int = 0
    completed_orders: int = 0
    rating: Optional[Decimal] = None


@dataclass
class Milestone:
    """A milestone in a service agreement."""
    milestone_id: str = field(default_factory=lambda: f"ms_{uuid4().hex[:12]}")
    name: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    status: MilestoneStatus = MilestoneStatus.PENDING
    due_date: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    released_at: Optional[datetime] = None


@dataclass
class ServiceOffer:
    """An offer/agreement between two agents for a service."""
    offer_id: str = field(default_factory=lambda: f"offer_{uuid4().hex[:16]}")
    service_id: str = ""
    
    # Parties
    provider_agent_id: str = ""
    consumer_agent_id: str = ""
    
    # Terms
    total_amount: Decimal = Decimal("0")
    token: str = "USDC"
    milestones: List[Milestone] = field(default_factory=list)
    
    # Status
    status: OfferStatus = OfferStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Escrow
    escrow_tx_hash: Optional[str] = None
    escrow_amount: Decimal = Decimal("0")
    released_amount: Decimal = Decimal("0")


@dataclass
class ServiceReview:
    """A review of a service."""
    review_id: str = field(default_factory=lambda: f"rev_{uuid4().hex[:12]}")
    offer_id: str = ""
    service_id: str = ""
    reviewer_agent_id: str = ""
    rating: int = 5  # 1-5
    comment: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MarketplaceRepository:
    """Repository for marketplace data."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pg_pool = None
        self._use_postgres = dsn.startswith("postgresql://") or dsn.startswith("postgres://")
        
        # In-memory storage for dev
        self._services: Dict[str, ServiceListing] = {}
        self._offers: Dict[str, ServiceOffer] = {}
        self._reviews: Dict[str, ServiceReview] = {}

    async def _get_pool(self):
        """Lazy initialization of PostgreSQL pool."""
        if self._pg_pool is None and self._use_postgres:
            import asyncpg
            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pg_pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return self._pg_pool

    # Service Listings

    async def create_service(self, service: ServiceListing) -> ServiceListing:
        """Create a new service listing."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO marketplace_services (
                        external_id, provider_agent_id, name, description,
                        category, tags, price_amount, price_token, price_type,
                        capabilities, api_endpoint, status, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
                    """,
                    service.service_id,
                    service.provider_agent_id,
                    service.name,
                    service.description,
                    service.category.value,
                    service.tags,
                    float(service.price_amount),
                    service.price_token,
                    service.price_type,
                    service.capabilities,
                    service.api_endpoint,
                    service.status.value,
                )
        else:
            self._services[service.service_id] = service
        
        return service

    async def get_service(self, service_id: str) -> Optional[ServiceListing]:
        """Get a service by ID."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM marketplace_services WHERE external_id = $1",
                    service_id,
                )
                if row:
                    return self._row_to_service(row)
                return None
        else:
            return self._services.get(service_id)

    async def list_services(
        self,
        category: Optional[ServiceCategory] = None,
        provider_id: Optional[str] = None,
        status: ServiceStatus = ServiceStatus.ACTIVE,
        limit: int = 50,
    ) -> List[ServiceListing]:
        """List services with optional filters."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                query = "SELECT * FROM marketplace_services WHERE status = $1"
                params = [status.value]
                
                if category:
                    query += f" AND category = ${len(params) + 1}"
                    params.append(category.value)
                
                if provider_id:
                    query += f" AND provider_agent_id = ${len(params) + 1}"
                    params.append(provider_id)
                
                query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1}"
                params.append(limit)
                
                rows = await conn.fetch(query, *params)
                return [self._row_to_service(row) for row in rows]
        else:
            services = list(self._services.values())
            if status:
                services = [s for s in services if s.status == status]
            if category:
                services = [s for s in services if s.category == category]
            if provider_id:
                services = [s for s in services if s.provider_agent_id == provider_id]
            return sorted(services, key=lambda s: s.created_at, reverse=True)[:limit]

    async def update_service(
        self,
        service_id: str,
        **updates,
    ) -> Optional[ServiceListing]:
        """Update a service listing."""
        service = await self.get_service(service_id)
        if not service:
            return None
        
        for key, value in updates.items():
            if hasattr(service, key):
                setattr(service, key, value)
        
        service.updated_at = datetime.now(timezone.utc)
        
        if self._use_postgres:
            # Update in database
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE marketplace_services SET
                        name = $2, description = $3, status = $4, updated_at = NOW()
                    WHERE external_id = $1
                    """,
                    service_id,
                    service.name,
                    service.description,
                    service.status.value,
                )
        else:
            self._services[service_id] = service
        
        return service

    # Service Offers

    async def create_offer(self, offer: ServiceOffer) -> ServiceOffer:
        """Create a new service offer."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO marketplace_offers (
                        external_id, service_id, provider_agent_id, consumer_agent_id,
                        total_amount, token, status, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    """,
                    offer.offer_id,
                    offer.service_id,
                    offer.provider_agent_id,
                    offer.consumer_agent_id,
                    float(offer.total_amount),
                    offer.token,
                    offer.status.value,
                )
        else:
            self._offers[offer.offer_id] = offer
        
        return offer

    async def get_offer(self, offer_id: str) -> Optional[ServiceOffer]:
        """Get an offer by ID."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM marketplace_offers WHERE external_id = $1",
                    offer_id,
                )
                if row:
                    return self._row_to_offer(row)
                return None
        else:
            return self._offers.get(offer_id)

    async def list_offers(
        self,
        agent_id: str,
        role: str = "any",  # provider, consumer, any
        status: Optional[OfferStatus] = None,
        limit: int = 50,
    ) -> List[ServiceOffer]:
        """List offers for an agent."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                if role == "provider":
                    query = "SELECT * FROM marketplace_offers WHERE provider_agent_id = $1"
                elif role == "consumer":
                    query = "SELECT * FROM marketplace_offers WHERE consumer_agent_id = $1"
                else:
                    query = "SELECT * FROM marketplace_offers WHERE provider_agent_id = $1 OR consumer_agent_id = $1"
                
                params = [agent_id]
                
                if status:
                    query += f" AND status = ${len(params) + 1}"
                    params.append(status.value)
                
                query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1}"
                params.append(limit)
                
                rows = await conn.fetch(query, *params)
                return [self._row_to_offer(row) for row in rows]
        else:
            offers = list(self._offers.values())
            if role == "provider":
                offers = [o for o in offers if o.provider_agent_id == agent_id]
            elif role == "consumer":
                offers = [o for o in offers if o.consumer_agent_id == agent_id]
            else:
                offers = [o for o in offers if o.provider_agent_id == agent_id or o.consumer_agent_id == agent_id]
            if status:
                offers = [o for o in offers if o.status == status]
            return sorted(offers, key=lambda o: o.created_at, reverse=True)[:limit]

    async def update_offer_status(
        self,
        offer_id: str,
        status: OfferStatus,
    ) -> Optional[ServiceOffer]:
        """Update offer status."""
        offer = await self.get_offer(offer_id)
        if not offer:
            return None
        
        offer.status = status
        
        if status == OfferStatus.ACCEPTED:
            offer.accepted_at = datetime.now(timezone.utc)
        elif status == OfferStatus.COMPLETED:
            offer.completed_at = datetime.now(timezone.utc)
        
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE marketplace_offers SET
                        status = $2, accepted_at = $3, completed_at = $4
                    WHERE external_id = $1
                    """,
                    offer_id,
                    status.value,
                    offer.accepted_at,
                    offer.completed_at,
                )
        else:
            self._offers[offer_id] = offer
        
        return offer

    # Reviews

    async def create_review(self, review: ServiceReview) -> ServiceReview:
        """Create a service review."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO marketplace_reviews (
                        external_id, offer_id, service_id, reviewer_agent_id,
                        rating, comment, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    """,
                    review.review_id,
                    review.offer_id,
                    review.service_id,
                    review.reviewer_agent_id,
                    review.rating,
                    review.comment,
                )
                
                # Update service rating
                await conn.execute(
                    """
                    UPDATE marketplace_services SET
                        rating = (
                            SELECT AVG(rating) FROM marketplace_reviews
                            WHERE service_id = $1
                        ),
                        completed_orders = completed_orders + 1
                    WHERE external_id = $1
                    """,
                    review.service_id,
                )
        else:
            self._reviews[review.review_id] = review
            # Update service stats
            service = self._services.get(review.service_id)
            if service:
                service.completed_orders += 1
                reviews = [r for r in self._reviews.values() if r.service_id == review.service_id]
                if reviews:
                    service.rating = Decimal(sum(r.rating for r in reviews)) / len(reviews)
        
        return review

    async def list_reviews(
        self,
        service_id: str,
        limit: int = 50,
    ) -> List[ServiceReview]:
        """List reviews for a service."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM marketplace_reviews
                    WHERE service_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    service_id,
                    limit,
                )
                return [self._row_to_review(row) for row in rows]
        else:
            reviews = [r for r in self._reviews.values() if r.service_id == service_id]
            return sorted(reviews, key=lambda r: r.created_at, reverse=True)[:limit]

    # Search

    async def search_services(
        self,
        query: str,
        category: Optional[ServiceCategory] = None,
        min_rating: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        limit: int = 50,
    ) -> List[ServiceListing]:
        """Search services by query."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                sql = """
                    SELECT * FROM marketplace_services
                    WHERE status = 'active'
                    AND (name ILIKE $1 OR description ILIKE $1 OR $1 = ANY(tags))
                """
                params = [f"%{query}%"]
                
                if category:
                    sql += f" AND category = ${len(params) + 1}"
                    params.append(category.value)
                
                if min_rating:
                    sql += f" AND rating >= ${len(params) + 1}"
                    params.append(float(min_rating))
                
                if max_price:
                    sql += f" AND price_amount <= ${len(params) + 1}"
                    params.append(float(max_price))
                
                sql += f" ORDER BY rating DESC NULLS LAST, completed_orders DESC LIMIT ${len(params) + 1}"
                params.append(limit)
                
                rows = await conn.fetch(sql, *params)
                return [self._row_to_service(row) for row in rows]
        else:
            query_lower = query.lower()
            services = [
                s for s in self._services.values()
                if s.status == ServiceStatus.ACTIVE and (
                    query_lower in s.name.lower() or
                    query_lower in s.description.lower() or
                    any(query_lower in tag.lower() for tag in s.tags)
                )
            ]
            if category:
                services = [s for s in services if s.category == category]
            if min_rating:
                services = [s for s in services if s.rating and s.rating >= min_rating]
            if max_price:
                services = [s for s in services if s.price_amount <= max_price]
            return sorted(services, key=lambda s: (s.rating or 0, s.completed_orders), reverse=True)[:limit]

    def _row_to_service(self, row) -> ServiceListing:
        """Convert database row to ServiceListing."""
        return ServiceListing(
            service_id=row["external_id"],
            provider_agent_id=row["provider_agent_id"],
            name=row["name"],
            description=row["description"],
            category=ServiceCategory(row["category"]),
            tags=row["tags"] or [],
            price_amount=Decimal(str(row["price_amount"])),
            price_token=row["price_token"],
            price_type=row["price_type"],
            capabilities=row.get("capabilities") or {},
            api_endpoint=row.get("api_endpoint"),
            status=ServiceStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row.get("updated_at") or row["created_at"],
            total_orders=row.get("total_orders") or 0,
            completed_orders=row.get("completed_orders") or 0,
            rating=Decimal(str(row["rating"])) if row.get("rating") else None,
        )

    def _row_to_offer(self, row) -> ServiceOffer:
        """Convert database row to ServiceOffer."""
        return ServiceOffer(
            offer_id=row["external_id"],
            service_id=row["service_id"],
            provider_agent_id=row["provider_agent_id"],
            consumer_agent_id=row["consumer_agent_id"],
            total_amount=Decimal(str(row["total_amount"])),
            token=row["token"],
            status=OfferStatus(row["status"]),
            created_at=row["created_at"],
            accepted_at=row.get("accepted_at"),
            completed_at=row.get("completed_at"),
            escrow_tx_hash=row.get("escrow_tx_hash"),
            escrow_amount=Decimal(str(row.get("escrow_amount") or 0)),
            released_amount=Decimal(str(row.get("released_amount") or 0)),
        )

    def _row_to_review(self, row) -> ServiceReview:
        """Convert database row to ServiceReview."""
        return ServiceReview(
            review_id=row["external_id"],
            offer_id=row["offer_id"],
            service_id=row["service_id"],
            reviewer_agent_id=row["reviewer_agent_id"],
            rating=row["rating"],
            comment=row["comment"],
            created_at=row["created_at"],
        )
