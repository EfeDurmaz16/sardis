"""Tests for A2A agent discovery service."""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict

import pytest

from sardis_a2a.agent_card import (
    AgentCapability,
    PaymentCapability,
    SardisAgentCard,
)
from sardis_a2a.discovery import (
    DiscoveredAgent,
    AgentDiscoveryService,
)


class MockHttpClient:
    """Mock HTTP client for testing."""

    def __init__(self):
        self.responses: Dict[str, tuple[int, Dict[str, Any]]] = {}

    def add_response(self, url: str, status: int, data: Dict[str, Any]):
        """Add a mock response for a URL."""
        self.responses[url] = (status, data)

    async def get(
        self, url: str, headers: Dict[str, str] | None = None
    ) -> tuple[int, Dict[str, Any]]:
        """Mock GET request."""
        if url in self.responses:
            return self.responses[url]
        return 404, {"error": "Not found"}


class TestDiscoveredAgent:
    """Tests for DiscoveredAgent."""

    @pytest.fixture
    def agent(self):
        """Create a sample discovered agent."""
        card = SardisAgentCard(
            agent_id="agent_123",
            agent_name="Test Agent",
            capabilities=[
                AgentCapability.PAYMENT_EXECUTE,
                AgentCapability.CHECKOUT_CREATE,
            ],
            payment_capability=PaymentCapability(
                supported_tokens=["USDC", "USDT"],
                supported_chains=["base", "polygon"],
            ),
        )

        return DiscoveredAgent(
            agent_id="agent_123",
            agent_name="Test Agent",
            agent_url="https://agent.example.com",
            card=card,
            cache_ttl_seconds=3600,
        )

    def test_create_discovered_agent(self, agent):
        """Test creating a discovered agent."""
        assert agent.agent_id == "agent_123"
        assert agent.agent_name == "Test Agent"
        assert agent.agent_url == "https://agent.example.com"
        assert agent.available is True
        assert agent.card is not None

    def test_cache_valid_fresh(self, agent):
        """Test cache validity for fresh agent."""
        assert agent.is_cache_valid() is True

    def test_cache_invalid_expired(self, agent):
        """Test cache validity for expired agent."""
        agent.last_verified_at = datetime.now(timezone.utc) - timedelta(hours=2)
        assert agent.is_cache_valid() is False

    def test_supports_capability(self, agent):
        """Test capability checking."""
        assert agent.supports_capability(AgentCapability.PAYMENT_EXECUTE) is True
        assert agent.supports_capability(AgentCapability.CHECKOUT_CREATE) is True
        assert agent.supports_capability(AgentCapability.PAYMENT_REFUND) is False

    def test_supports_capability_no_card(self):
        """Test capability checking without card."""
        agent = DiscoveredAgent(
            agent_id="agent_1",
            agent_name="Agent",
            agent_url="https://example.com",
            card=None,
        )

        assert agent.supports_capability(AgentCapability.PAYMENT_EXECUTE) is False

    def test_supports_payment(self, agent):
        """Test payment support checking."""
        assert agent.supports_payment("USDC", "base") is True
        assert agent.supports_payment("USDT", "polygon") is True
        assert agent.supports_payment("USDC", "unknown") is False
        assert agent.supports_payment("UNKNOWN", "base") is False

    def test_supports_payment_no_card(self):
        """Test payment support without card."""
        agent = DiscoveredAgent(
            agent_id="agent_1",
            agent_name="Agent",
            agent_url="https://example.com",
            card=None,
        )

        assert agent.supports_payment("USDC", "base") is False


class TestAgentDiscoveryService:
    """Tests for AgentDiscoveryService."""

    @pytest.fixture
    def http_client(self):
        """Create a mock HTTP client."""
        return MockHttpClient()

    @pytest.fixture
    def discovery(self, http_client):
        """Create a discovery service."""
        return AgentDiscoveryService(
            http_client=http_client,
            cache_ttl_seconds=3600,
        )

    @pytest.fixture
    def agent_card_data(self):
        """Sample agent card JSON data."""
        return {
            "agent_id": "agent_test",
            "name": "Test Agent",
            "version": "1.0.0",
            "description": "A test agent",
            "operator": {
                "name": "Test Operator",
                "url": "https://test.com",
            },
            "capabilities": [
                "payment.execute",
                "payment.verify",
                "checkout.create",
            ],
            "payment": {
                "supported_tokens": ["USDC", "USDT"],
                "supported_chains": ["base", "polygon"],
                "min_amount_minor": 100,
                "max_amount_minor": 100_000_00,
                "ap2_compliant": True,
            },
        }

    @pytest.mark.asyncio
    async def test_discover_agent_success(self, discovery, http_client, agent_card_data):
        """Test successful agent discovery."""
        http_client.add_response(
            "https://agent.example.com/.well-known/agent-card.json",
            200,
            agent_card_data,
        )

        agent = await discovery.discover_agent("https://agent.example.com")

        assert agent.agent_id == "agent_test"
        assert agent.agent_name == "Test Agent"
        assert agent.available is True
        assert agent.card is not None
        assert agent.card.agent_version == "1.0.0"
        assert len(agent.card.capabilities) == 3

    @pytest.mark.asyncio
    async def test_discover_agent_with_trailing_slash(self, discovery, http_client, agent_card_data):
        """Test discovery with trailing slash in URL."""
        http_client.add_response(
            "https://agent.example.com/.well-known/agent-card.json",
            200,
            agent_card_data,
        )

        agent = await discovery.discover_agent("https://agent.example.com/")

        assert agent.agent_id == "agent_test"

    @pytest.mark.asyncio
    async def test_discover_agent_cached(self, discovery, http_client, agent_card_data):
        """Test that discovered agents are cached."""
        http_client.add_response(
            "https://agent.example.com/.well-known/agent-card.json",
            200,
            agent_card_data,
        )

        # First discovery
        agent1 = await discovery.discover_agent("https://agent.example.com")

        # Second discovery should use cache
        agent2 = await discovery.discover_agent("https://agent.example.com")

        assert agent1 is agent2

    @pytest.mark.asyncio
    async def test_discover_agent_force_refresh(self, discovery, http_client, agent_card_data):
        """Test force refresh bypasses cache."""
        http_client.add_response(
            "https://agent.example.com/.well-known/agent-card.json",
            200,
            agent_card_data,
        )

        agent1 = await discovery.discover_agent("https://agent.example.com")

        # Modify response
        agent_card_data["name"] = "Updated Agent"
        http_client.add_response(
            "https://agent.example.com/.well-known/agent-card.json",
            200,
            agent_card_data,
        )

        # Force refresh
        agent2 = await discovery.discover_agent(
            "https://agent.example.com", force_refresh=True
        )

        assert agent2.agent_name == "Updated Agent"

    @pytest.mark.asyncio
    async def test_discover_agent_http_error(self, discovery, http_client):
        """Test discovery with HTTP error."""
        http_client.add_response(
            "https://agent.example.com/.well-known/agent-card.json",
            500,
            {"error": "Internal server error"},
        )

        agent = await discovery.discover_agent("https://agent.example.com")

        assert agent.available is False
        assert agent.last_error is not None
        assert "500" in agent.last_error

    @pytest.mark.asyncio
    async def test_discover_agent_no_http_client(self):
        """Test discovery without HTTP client."""
        discovery = AgentDiscoveryService(http_client=None)

        agent = await discovery.discover_agent("https://agent.example.com")

        assert agent.available is False
        assert "HTTP client not configured" in agent.last_error

    def test_register_agent(self, discovery):
        """Test manual agent registration."""
        card = SardisAgentCard(
            agent_id="agent_manual",
            agent_name="Manual Agent",
        )

        agent = discovery.register_agent(
            agent_id="agent_manual",
            agent_name="Manual Agent",
            agent_url="https://manual.example.com",
            card=card,
        )

        assert agent.agent_id == "agent_manual"
        assert agent.agent_name == "Manual Agent"
        assert agent.available is True
        assert agent.card is card

    def test_register_agent_normalizes_url(self, discovery):
        """Test that registration normalizes URL."""
        discovery.register_agent(
            agent_id="agent_1",
            agent_name="Agent",
            agent_url="https://example.com/",
        )

        # Should be found without trailing slash
        agent = discovery.get_agent("https://example.com")
        assert agent is not None

    def test_get_agent(self, discovery):
        """Test getting agent by URL."""
        discovery.register_agent(
            agent_id="agent_1",
            agent_name="Agent",
            agent_url="https://agent.example.com",
        )

        agent = discovery.get_agent("https://agent.example.com")

        assert agent is not None
        assert agent.agent_id == "agent_1"

    def test_get_agent_not_found(self, discovery):
        """Test getting non-existent agent."""
        agent = discovery.get_agent("https://nonexistent.example.com")

        assert agent is None

    def test_get_agent_by_id(self, discovery):
        """Test getting agent by ID."""
        discovery.register_agent(
            agent_id="agent_test_id",
            agent_name="Test Agent",
            agent_url="https://agent.example.com",
        )

        agent = discovery.get_agent_by_id("agent_test_id")

        assert agent is not None
        assert agent.agent_url == "https://agent.example.com"

    def test_get_agent_by_id_not_found(self, discovery):
        """Test getting non-existent agent by ID."""
        agent = discovery.get_agent_by_id("nonexistent_id")

        assert agent is None

    def test_list_agents_all(self, discovery):
        """Test listing all agents."""
        discovery.register_agent("agent_1", "Agent 1", "https://agent1.example.com")
        discovery.register_agent("agent_2", "Agent 2", "https://agent2.example.com")
        discovery.register_agent("agent_3", "Agent 3", "https://agent3.example.com")

        agents = discovery.list_agents()

        assert len(agents) == 3

    def test_list_agents_available_only(self, discovery):
        """Test listing only available agents."""
        discovery.register_agent("agent_1", "Agent 1", "https://agent1.example.com")

        # Register unavailable agent
        unavailable = discovery.register_agent("agent_2", "Agent 2", "https://agent2.example.com")
        unavailable.available = False

        agents = discovery.list_agents(available_only=True)

        assert len(agents) == 1
        assert agents[0].agent_id == "agent_1"

    def test_list_agents_by_capability(self, discovery):
        """Test listing agents by capability."""
        card1 = SardisAgentCard(
            agent_id="agent_1",
            agent_name="Agent 1",
            capabilities=[AgentCapability.PAYMENT_EXECUTE],
        )
        discovery.register_agent("agent_1", "Agent 1", "https://agent1.example.com", card1)

        card2 = SardisAgentCard(
            agent_id="agent_2",
            agent_name="Agent 2",
            capabilities=[AgentCapability.CHECKOUT_CREATE],
        )
        discovery.register_agent("agent_2", "Agent 2", "https://agent2.example.com", card2)

        agents = discovery.list_agents(capability=AgentCapability.PAYMENT_EXECUTE)

        assert len(agents) == 1
        assert agents[0].agent_id == "agent_1"

    def test_list_agents_by_payment(self, discovery):
        """Test listing agents by payment support."""
        card1 = SardisAgentCard(
            agent_id="agent_1",
            agent_name="Agent 1",
            payment_capability=PaymentCapability(
                supported_tokens=["USDC"],
                supported_chains=["base"],
            ),
        )
        discovery.register_agent("agent_1", "Agent 1", "https://agent1.example.com", card1)

        card2 = SardisAgentCard(
            agent_id="agent_2",
            agent_name="Agent 2",
            payment_capability=PaymentCapability(
                supported_tokens=["USDT"],
                supported_chains=["polygon"],
            ),
        )
        discovery.register_agent("agent_2", "Agent 2", "https://agent2.example.com", card2)

        agents = discovery.list_agents(token="USDC", chain="base")

        assert len(agents) == 1
        assert agents[0].agent_id == "agent_1"

    def test_list_agents_by_token_only(self, discovery):
        """Test listing agents by token only."""
        card1 = SardisAgentCard(
            agent_id="agent_1",
            agent_name="Agent 1",
            payment_capability=PaymentCapability(
                supported_tokens=["USDC", "USDT"],
                supported_chains=["base"],
            ),
        )
        discovery.register_agent("agent_1", "Agent 1", "https://agent1.example.com", card1)

        agents = discovery.list_agents(token="USDT")

        assert len(agents) == 1

    def test_remove_agent(self, discovery):
        """Test removing an agent."""
        discovery.register_agent("agent_1", "Agent 1", "https://agent.example.com")

        result = discovery.remove_agent("https://agent.example.com")

        assert result is True
        assert discovery.get_agent("https://agent.example.com") is None

    def test_remove_agent_not_found(self, discovery):
        """Test removing non-existent agent."""
        result = discovery.remove_agent("https://nonexistent.example.com")

        assert result is False

    def test_clear_cache(self, discovery):
        """Test clearing all cached agents."""
        discovery.register_agent("agent_1", "Agent 1", "https://agent1.example.com")
        discovery.register_agent("agent_2", "Agent 2", "https://agent2.example.com")

        count = discovery.clear_cache()

        assert count == 2
        assert len(discovery.list_agents(available_only=False)) == 0
