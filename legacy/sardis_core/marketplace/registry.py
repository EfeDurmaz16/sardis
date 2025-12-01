"""Service Registry for Agent Marketplace.

Enables agents to register their capabilities and discover services
offered by other agents.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
import secrets


class ServiceCategory(str, Enum):
    """Categories of services offered by agents."""
    DATA = "data"              # Data processing, APIs, feeds
    COMPUTE = "compute"         # GPU, CPU, inference
    TASKS = "tasks"            # Task automation, workflows
    CONTENT = "content"        # Content generation, summarization
    TRANSLATION = "translation" # Language translation
    ANALYSIS = "analysis"      # Analysis, insights, predictions
    STORAGE = "storage"        # Data storage, hosting
    OTHER = "other"


class PricingModel(str, Enum):
    """Pricing models for services."""
    PER_CALL = "per_call"          # Price per API call or request
    PER_UNIT = "per_unit"          # Price per unit (word, minute, MB, etc.)
    SUBSCRIPTION = "subscription"   # Monthly/yearly subscription
    TIERED = "tiered"              # Volume-based pricing
    NEGOTIATED = "negotiated"      # Price negotiated per request


@dataclass
class ServicePricing:
    """Pricing configuration for a service."""
    model: PricingModel
    base_price: Decimal
    currency: str = "USDC"
    unit_name: Optional[str] = None  # e.g., "word", "minute", "request"
    min_charge: Optional[Decimal] = None
    max_charge: Optional[Decimal] = None
    
    # For subscription model
    billing_period: Optional[str] = None  # "monthly", "yearly"
    
    # For tiered model
    tiers: Optional[List[Dict[str, Any]]] = None
    
    def calculate_cost(self, units: int = 1) -> Decimal:
        """Calculate cost for given units."""
        if self.model == PricingModel.PER_CALL:
            return self.base_price
        elif self.model == PricingModel.PER_UNIT:
            cost = self.base_price * units
            if self.min_charge and cost < self.min_charge:
                return self.min_charge
            if self.max_charge and cost > self.max_charge:
                return self.max_charge
            return cost
        elif self.model == PricingModel.SUBSCRIPTION:
            return self.base_price
        else:
            return self.base_price


@dataclass
class ServiceRating:
    """Rating and reputation for a service."""
    total_ratings: int = 0
    average_score: float = 0.0  # 0-5
    successful_completions: int = 0
    total_requests: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_completions / self.total_requests
    
    @property
    def reputation_score(self) -> float:
        """Calculate overall reputation score (0-100)."""
        # Weighted: 60% rating, 40% success rate
        rating_component = (self.average_score / 5.0) * 60
        success_component = self.success_rate * 40
        
        # Bonus for high volume
        volume_bonus = min(10, self.total_requests / 100)
        
        return min(100, rating_component + success_component + volume_bonus)
    
    def add_rating(self, score: float, success: bool = True):
        """Add a new rating."""
        # Update average
        total_score = self.average_score * self.total_ratings + score
        self.total_ratings += 1
        self.average_score = total_score / self.total_ratings
        
        # Update completion stats
        self.total_requests += 1
        if success:
            self.successful_completions += 1
        
        self.last_updated = datetime.now(timezone.utc)


@dataclass
class AgentService:
    """A service offered by an agent."""
    service_id: str = field(default_factory=lambda: f"svc_{secrets.token_hex(8)}")
    provider_agent_id: str = ""
    provider_wallet_id: str = ""
    
    # Service details
    name: str = ""
    description: str = ""
    category: ServiceCategory = ServiceCategory.OTHER
    tags: List[str] = field(default_factory=list)
    
    # Capabilities
    capabilities: Dict[str, Any] = field(default_factory=dict)
    input_schema: Optional[Dict[str, Any]] = None  # JSON Schema for input
    output_schema: Optional[Dict[str, Any]] = None  # JSON Schema for output
    
    # Pricing
    pricing: Optional[ServicePricing] = None
    
    # Rating
    rating: ServiceRating = field(default_factory=ServiceRating)
    
    # Status
    is_active: bool = True
    is_verified: bool = False
    max_concurrent_requests: int = 10
    current_requests: int = 0
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_available(self) -> bool:
        """Check if service is available for new requests."""
        return (
            self.is_active and 
            self.current_requests < self.max_concurrent_requests
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "service_id": self.service_id,
            "provider_agent_id": self.provider_agent_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "tags": self.tags,
            "pricing": {
                "model": self.pricing.model.value if self.pricing else None,
                "base_price": str(self.pricing.base_price) if self.pricing else None,
                "currency": self.pricing.currency if self.pricing else "USDC",
                "unit_name": self.pricing.unit_name if self.pricing else None,
            } if self.pricing else None,
            "rating": {
                "average_score": self.rating.average_score,
                "total_ratings": self.rating.total_ratings,
                "success_rate": self.rating.success_rate,
                "reputation_score": self.rating.reputation_score,
            },
            "is_available": self.is_available,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat(),
        }


class ServiceRegistry:
    """
    Registry for agent services.
    
    Enables service discovery, search, and management.
    """
    
    def __init__(self):
        self._services: Dict[str, AgentService] = {}
        self._by_agent: Dict[str, List[str]] = {}  # agent_id -> service_ids
        self._by_category: Dict[ServiceCategory, List[str]] = {}
    
    def register_service(
        self,
        provider_agent_id: str,
        provider_wallet_id: str,
        name: str,
        description: str,
        category: ServiceCategory,
        pricing: ServicePricing,
        tags: Optional[List[str]] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentService:
        """
        Register a new service.
        
        Args:
            provider_agent_id: ID of the agent providing the service
            provider_wallet_id: Wallet ID to receive payments
            name: Service name
            description: Service description
            category: Service category
            pricing: Pricing configuration
            tags: Optional tags for search
            capabilities: Optional capability details
            input_schema: Optional JSON schema for input
            output_schema: Optional JSON schema for output
            metadata: Optional metadata
            
        Returns:
            Created AgentService
        """
        service = AgentService(
            provider_agent_id=provider_agent_id,
            provider_wallet_id=provider_wallet_id,
            name=name,
            description=description,
            category=category,
            pricing=pricing,
            tags=tags or [],
            capabilities=capabilities or {},
            input_schema=input_schema,
            output_schema=output_schema,
            metadata=metadata or {},
        )
        
        # Store service
        self._services[service.service_id] = service
        
        # Index by agent
        if provider_agent_id not in self._by_agent:
            self._by_agent[provider_agent_id] = []
        self._by_agent[provider_agent_id].append(service.service_id)
        
        # Index by category
        if category not in self._by_category:
            self._by_category[category] = []
        self._by_category[category].append(service.service_id)
        
        return service
    
    def get_service(self, service_id: str) -> Optional[AgentService]:
        """Get a service by ID."""
        return self._services.get(service_id)
    
    def list_services(
        self,
        category: Optional[ServiceCategory] = None,
        provider_agent_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_price: Optional[Decimal] = None,
        min_rating: Optional[float] = None,
        available_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AgentService]:
        """
        List services with optional filters.
        
        Args:
            category: Filter by category
            provider_agent_id: Filter by provider
            tags: Filter by tags (any match)
            max_price: Maximum base price
            min_rating: Minimum average rating
            available_only: Only show available services
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of matching services
        """
        # Start with all or category-filtered
        if category:
            service_ids = self._by_category.get(category, [])
        elif provider_agent_id:
            service_ids = self._by_agent.get(provider_agent_id, [])
        else:
            service_ids = list(self._services.keys())
        
        # Get services
        services = [self._services[sid] for sid in service_ids if sid in self._services]
        
        # Apply filters
        if available_only:
            services = [s for s in services if s.is_available]
        
        if tags:
            services = [s for s in services if any(t in s.tags for t in tags)]
        
        if max_price:
            services = [
                s for s in services 
                if s.pricing and s.pricing.base_price <= max_price
            ]
        
        if min_rating:
            services = [
                s for s in services 
                if s.rating.average_score >= min_rating
            ]
        
        # Sort by reputation
        services.sort(key=lambda s: s.rating.reputation_score, reverse=True)
        
        # Paginate
        return services[offset:offset + limit]
    
    def search_services(self, query: str, limit: int = 20) -> List[AgentService]:
        """
        Search services by name, description, or tags.
        
        Args:
            query: Search query
            limit: Max results
            
        Returns:
            Matching services sorted by relevance
        """
        query_lower = query.lower()
        results = []
        
        for service in self._services.values():
            if not service.is_available:
                continue
            
            # Calculate relevance score
            score = 0
            
            if query_lower in service.name.lower():
                score += 10
            if query_lower in service.description.lower():
                score += 5
            if any(query_lower in tag.lower() for tag in service.tags):
                score += 3
            if query_lower == service.category.value:
                score += 8
            
            if score > 0:
                results.append((score, service))
        
        # Sort by relevance then reputation
        results.sort(key=lambda x: (x[0], x[1].rating.reputation_score), reverse=True)
        
        return [s for _, s in results[:limit]]
    
    def update_service(
        self,
        service_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        pricing: Optional[ServicePricing] = None,
        tags: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        max_concurrent_requests: Optional[int] = None,
    ) -> Optional[AgentService]:
        """Update a service."""
        service = self._services.get(service_id)
        if not service:
            return None
        
        if name:
            service.name = name
        if description:
            service.description = description
        if pricing:
            service.pricing = pricing
        if tags is not None:
            service.tags = tags
        if is_active is not None:
            service.is_active = is_active
        if max_concurrent_requests is not None:
            service.max_concurrent_requests = max_concurrent_requests
        
        service.updated_at = datetime.now(timezone.utc)
        return service
    
    def deactivate_service(self, service_id: str) -> bool:
        """Deactivate a service."""
        service = self._services.get(service_id)
        if not service:
            return False
        
        service.is_active = False
        service.updated_at = datetime.now(timezone.utc)
        return True
    
    def rate_service(
        self,
        service_id: str,
        score: float,
        success: bool = True
    ) -> Optional[ServiceRating]:
        """
        Add a rating to a service.
        
        Args:
            service_id: Service to rate
            score: Rating score (1-5)
            success: Whether the request was successful
            
        Returns:
            Updated rating or None
        """
        service = self._services.get(service_id)
        if not service:
            return None
        
        # Validate score
        score = max(1.0, min(5.0, score))
        
        service.rating.add_rating(score, success)
        return service.rating
    
    def get_top_services(
        self,
        category: Optional[ServiceCategory] = None,
        limit: int = 10
    ) -> List[AgentService]:
        """Get top-rated services."""
        services = self.list_services(
            category=category,
            available_only=True,
            limit=limit
        )
        return services
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total = len(self._services)
        active = sum(1 for s in self._services.values() if s.is_active)
        available = sum(1 for s in self._services.values() if s.is_available)
        
        by_category = {
            cat.value: len(sids) 
            for cat, sids in self._by_category.items()
        }
        
        return {
            "total_services": total,
            "active_services": active,
            "available_services": available,
            "unique_providers": len(self._by_agent),
            "by_category": by_category,
        }


# Singleton instance
_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """Get or create the service registry singleton."""
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry

