"""Agent discovery service for A2A protocol.

Discovers and caches agent cards from:
- /.well-known/agent-card.json endpoints
- Manual registrations
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Protocol

from .agent_card import SardisAgentCard, AgentCapability, PaymentCapability

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DiscoveredAgent:
    """A discovered agent with cached card data."""

    agent_id: str
    agent_name: str
    agent_url: str  # Base URL for the agent

    # Cached agent card
    card: Optional[SardisAgentCard] = None
    card_raw: Optional[Dict[str, Any]] = None

    # Cache metadata
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cache_ttl_seconds: int = 3600  # 1 hour default

    # Status
    available: bool = True
    last_error: Optional[str] = None

    def is_cache_valid(self) -> bool:
        """Check if the cached data is still valid."""
        expiry = self.last_verified_at + timedelta(seconds=self.cache_ttl_seconds)
        return datetime.now(timezone.utc) < expiry

    def supports_capability(self, capability: AgentCapability) -> bool:
        """Check if this agent supports a specific capability."""
        if self.card:
            return self.card.supports_capability(capability)
        return False

    def supports_payment(self, token: str, chain: str) -> bool:
        """Check if this agent supports a specific payment type."""
        if self.card:
            return self.card.supports_token(token) and self.card.supports_chain(chain)
        return False


class HttpClient(Protocol):
    """Protocol for HTTP client operations."""

    async def get(self, url: str, headers: Dict[str, str] | None = None) -> tuple[int, Dict[str, Any]]:
        """Make an HTTP GET request.

        Returns:
            Tuple of (status_code, json_response)
        """
        ...


class AgentDiscoveryService:
    """
    Service for discovering and caching A2A agent cards.

    Discovery methods:
    1. Fetch /.well-known/agent-card.json from agent URLs
    2. Manual registration of known agents
    3. UCP profiles at /.well-known/ucp.json (fallback)

    Features:
    - TTL-based caching (1 hour default)
    - Capability filtering
    - Payment capability validation
    """

    def __init__(
        self,
        http_client: HttpClient | None = None,
        cache_ttl_seconds: int = 3600,
    ) -> None:
        """
        Initialize the discovery service.

        Args:
            http_client: HTTP client for fetching agent cards
            cache_ttl_seconds: Cache TTL in seconds (default: 1 hour)
        """
        self._http_client = http_client
        self._cache_ttl = cache_ttl_seconds
        self._agents: Dict[str, DiscoveredAgent] = {}

    async def discover_agent(
        self,
        agent_url: str,
        force_refresh: bool = False,
    ) -> DiscoveredAgent:
        """
        Discover an agent from its base URL.

        Fetches the agent card from /.well-known/agent-card.json

        Args:
            agent_url: Base URL of the agent (e.g., https://agent.example.com)
            force_refresh: Force refresh even if cache is valid

        Returns:
            DiscoveredAgent with cached card data
        """
        # Normalize URL
        agent_url = agent_url.rstrip("/")

        # Check cache
        if agent_url in self._agents and not force_refresh:
            cached = self._agents[agent_url]
            if cached.is_cache_valid():
                logger.debug(f"Using cached agent card for {agent_url}")
                return cached

        # Fetch agent card
        agent_card_url = f"{agent_url}/.well-known/agent-card.json"

        logger.info(f"Discovering agent at {agent_card_url}")

        if self._http_client is None:
            # Create a mock agent for testing without HTTP client
            agent = DiscoveredAgent(
                agent_id=f"agent_{hash(agent_url) % 10000}",
                agent_name=f"Agent at {agent_url}",
                agent_url=agent_url,
                cache_ttl_seconds=self._cache_ttl,
                available=False,
                last_error="HTTP client not configured",
            )
            self._agents[agent_url] = agent
            return agent

        try:
            status, data = await self._http_client.get(agent_card_url)

            if status != 200:
                raise Exception(f"HTTP {status} from {agent_card_url}")

            # Parse agent card
            card = self._parse_agent_card(data)

            agent = DiscoveredAgent(
                agent_id=card.agent_id,
                agent_name=card.agent_name,
                agent_url=agent_url,
                card=card,
                card_raw=data,
                cache_ttl_seconds=self._cache_ttl,
                available=True,
            )

            self._agents[agent_url] = agent

            logger.info(
                f"Discovered agent: id={card.agent_id}, name={card.agent_name}, "
                f"capabilities={len(card.capabilities)}"
            )

            return agent

        except Exception as e:
            logger.warning(f"Failed to discover agent at {agent_url}: {e}")

            # Return or update with error status
            if agent_url in self._agents:
                self._agents[agent_url].available = False
                self._agents[agent_url].last_error = str(e)
                return self._agents[agent_url]

            agent = DiscoveredAgent(
                agent_id=f"unknown_{hash(agent_url) % 10000}",
                agent_name=f"Unknown Agent",
                agent_url=agent_url,
                cache_ttl_seconds=self._cache_ttl,
                available=False,
                last_error=str(e),
            )
            self._agents[agent_url] = agent
            return agent

    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        agent_url: str,
        card: SardisAgentCard | None = None,
    ) -> DiscoveredAgent:
        """
        Manually register an agent.

        Args:
            agent_id: Unique agent identifier
            agent_name: Display name
            agent_url: Base URL
            card: Optional pre-populated agent card

        Returns:
            Registered DiscoveredAgent
        """
        agent_url = agent_url.rstrip("/")

        agent = DiscoveredAgent(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_url=agent_url,
            card=card,
            cache_ttl_seconds=self._cache_ttl,
            available=True,
        )

        self._agents[agent_url] = agent

        logger.info(f"Registered agent: id={agent_id}, name={agent_name}, url={agent_url}")

        return agent

    def get_agent(self, agent_url: str) -> Optional[DiscoveredAgent]:
        """Get a cached agent by URL."""
        return self._agents.get(agent_url.rstrip("/"))

    def get_agent_by_id(self, agent_id: str) -> Optional[DiscoveredAgent]:
        """Get a cached agent by ID."""
        for agent in self._agents.values():
            if agent.agent_id == agent_id:
                return agent
        return None

    def list_agents(
        self,
        capability: AgentCapability | None = None,
        token: str | None = None,
        chain: str | None = None,
        available_only: bool = True,
    ) -> List[DiscoveredAgent]:
        """
        List discovered agents with optional filtering.

        Args:
            capability: Filter by required capability
            token: Filter by supported token
            chain: Filter by supported chain
            available_only: Only return available agents

        Returns:
            List of matching agents
        """
        agents = list(self._agents.values())

        if available_only:
            agents = [a for a in agents if a.available]

        if capability:
            agents = [a for a in agents if a.supports_capability(capability)]

        if token and chain:
            agents = [a for a in agents if a.supports_payment(token, chain)]
        elif token:
            agents = [a for a in agents if a.card and a.card.supports_token(token)]
        elif chain:
            agents = [a for a in agents if a.card and a.card.supports_chain(chain)]

        return agents

    def remove_agent(self, agent_url: str) -> bool:
        """Remove an agent from the cache."""
        agent_url = agent_url.rstrip("/")
        if agent_url in self._agents:
            del self._agents[agent_url]
            return True
        return False

    def clear_cache(self) -> int:
        """Clear all cached agents. Returns count of removed agents."""
        count = len(self._agents)
        self._agents.clear()
        return count

    def _parse_agent_card(self, data: Dict[str, Any]) -> SardisAgentCard:
        """Parse an agent card from JSON data."""
        # Parse capabilities
        capabilities = []
        for cap_str in data.get("capabilities", []):
            try:
                capabilities.append(AgentCapability(cap_str))
            except ValueError:
                logger.debug(f"Unknown capability: {cap_str}")

        # Parse payment capability
        payment_data = data.get("payment", {})
        payment_cap = PaymentCapability(
            supported_tokens=payment_data.get("supported_tokens", ["USDC"]),
            supported_chains=payment_data.get("supported_chains", ["base"]),
            min_amount_minor=payment_data.get("min_amount_minor", 100),
            max_amount_minor=payment_data.get("max_amount_minor", 100_000_00),
            ap2_compliant=payment_data.get("ap2_compliant", True),
            x402_compliant=payment_data.get("x402_compliant", True),
            ucp_compliant=payment_data.get("ucp_compliant", True),
        )

        return SardisAgentCard(
            agent_id=data.get("agent_id", ""),
            agent_name=data.get("name", ""),
            agent_version=data.get("version", "1.0.0"),
            agent_description=data.get("description", ""),
            operator_name=data.get("operator", {}).get("name", ""),
            operator_url=data.get("operator", {}).get("url", ""),
            operator_contact=data.get("operator", {}).get("contact"),
            capabilities=capabilities,
            payment_capability=payment_cap,
        )


__all__ = [
    "DiscoveredAgent",
    "HttpClient",
    "AgentDiscoveryService",
]
