"""Google A2A spec-compliant agent discovery service.

Discovers and caches agent cards from /.well-known/agent.json endpoints
per the Google A2A specification.

Spec: https://google.github.io/A2A/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from .types import AgentCard

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DiscoveredAgent:
    """A discovered agent with cached card data."""

    agent_url: str  # Base URL for the agent
    card: AgentCard | None = None
    card_raw: dict[str, Any] | None = None

    # Cache metadata
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_verified_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    cache_ttl_seconds: int = 3600  # 1 hour default

    # Status
    available: bool = True
    last_error: str | None = None

    @property
    def name(self) -> str:
        return self.card.name if self.card else "Unknown"

    @property
    def a2a_url(self) -> str:
        """The agent's A2A JSON-RPC endpoint (defaults to {base_url}/a2a)."""
        if self.card:
            return self.card.url
        return f"{self.agent_url}/a2a"

    def is_cache_valid(self) -> bool:
        expiry = self.last_verified_at + timedelta(seconds=self.cache_ttl_seconds)
        return datetime.now(UTC) < expiry

    def has_skill(self, skill_id: str) -> bool:
        """Check if this agent has a specific skill."""
        if self.card:
            return any(s.id == skill_id for s in self.card.skills)
        return False

    def supports_streaming(self) -> bool:
        if self.card:
            return self.card.capabilities.streaming
        return False


class HttpClient(Protocol):
    """Protocol for HTTP client operations."""

    async def get(
        self, url: str, headers: dict[str, str] | None = None
    ) -> tuple[int, dict[str, Any]]:
        ...


class AgentDiscoveryService:
    """Service for discovering and caching A2A agent cards.

    Fetches agent cards from /.well-known/agent.json per the Google A2A spec.
    """

    def __init__(
        self,
        http_client: HttpClient | None = None,
        cache_ttl_seconds: int = 3600,
    ) -> None:
        self._http_client = http_client
        self._cache_ttl = cache_ttl_seconds
        self._agents: dict[str, DiscoveredAgent] = {}

    async def discover_agent(
        self,
        agent_url: str,
        force_refresh: bool = False,
    ) -> DiscoveredAgent:
        """Discover an agent from /.well-known/agent.json"""
        agent_url = agent_url.rstrip("/")

        if agent_url in self._agents and not force_refresh:
            cached = self._agents[agent_url]
            if cached.is_cache_valid():
                return cached

        # Google A2A spec: agent card at /.well-known/agent.json
        card_url = f"{agent_url}/.well-known/agent.json"

        if self._http_client is None:
            agent = DiscoveredAgent(
                agent_url=agent_url,
                cache_ttl_seconds=self._cache_ttl,
                available=False,
                last_error="HTTP client not configured",
            )
            self._agents[agent_url] = agent
            return agent

        try:
            status, data = await self._http_client.get(card_url)
            if status != 200:
                raise Exception(f"HTTP {status} from {card_url}")

            card = AgentCard.from_dict(data)

            agent = DiscoveredAgent(
                agent_url=agent_url,
                card=card,
                card_raw=data,
                cache_ttl_seconds=self._cache_ttl,
                available=True,
            )
            self._agents[agent_url] = agent
            logger.info(f"Discovered agent: {card.name} at {agent_url}")
            return agent

        except Exception as e:
            logger.warning(f"Failed to discover agent at {agent_url}: {e}")

            if agent_url in self._agents:
                self._agents[agent_url].available = False
                self._agents[agent_url].last_error = str(e)
                return self._agents[agent_url]

            agent = DiscoveredAgent(
                agent_url=agent_url,
                cache_ttl_seconds=self._cache_ttl,
                available=False,
                last_error=str(e),
            )
            self._agents[agent_url] = agent
            return agent

    def register_agent(
        self,
        agent_url: str,
        card: AgentCard,
    ) -> DiscoveredAgent:
        """Manually register an agent with a known card."""
        agent_url = agent_url.rstrip("/")
        agent = DiscoveredAgent(
            agent_url=agent_url,
            card=card,
            cache_ttl_seconds=self._cache_ttl,
            available=True,
        )
        self._agents[agent_url] = agent
        return agent

    def get_agent(self, agent_url: str) -> DiscoveredAgent | None:
        return self._agents.get(agent_url.rstrip("/"))

    def list_agents(
        self,
        skill_id: str | None = None,
        available_only: bool = True,
    ) -> list[DiscoveredAgent]:
        agents = list(self._agents.values())
        if available_only:
            agents = [a for a in agents if a.available]
        if skill_id:
            agents = [a for a in agents if a.has_skill(skill_id)]
        return agents

    def remove_agent(self, agent_url: str) -> bool:
        agent_url = agent_url.rstrip("/")
        if agent_url in self._agents:
            del self._agents[agent_url]
            return True
        return False

    def clear_cache(self) -> int:
        count = len(self._agents)
        self._agents.clear()
        return count


__all__ = [
    "DiscoveredAgent",
    "HttpClient",
    "AgentDiscoveryService",
]
