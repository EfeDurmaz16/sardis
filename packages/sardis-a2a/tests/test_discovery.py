"""Tests for Google A2A spec-compliant agent discovery service."""

import pytest
from datetime import UTC, datetime, timedelta

from sardis_a2a.discovery import AgentDiscoveryService, DiscoveredAgent
from sardis_a2a.types import (
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)


def _make_card(name="Test Agent", url="https://test.com/a2a"):
    return AgentCard(
        name=name,
        description="A test agent",
        url=url,
        version="1",
        capabilities=AgentCapabilities(streaming=True),
        authentication=AgentAuthentication(schemes=["Bearer"]),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(id="payment-execute", name="Pay", description="Execute payment", tags=["payment"]),
            AgentSkill(id="echo", name="Echo", description="Echo input", tags=["test"]),
        ],
    )


def _card_json():
    return _make_card().to_dict()


class MockHttpClient:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.get_calls = []

    async def get(self, url, headers=None):
        self.get_calls.append(url)
        if url in self.responses:
            return self.responses[url]
        return (200, _card_json())


class TestDiscoveredAgent:
    def test_basic(self):
        agent = DiscoveredAgent(agent_url="https://test.com", card=_make_card())
        assert agent.name == "Test Agent"
        assert agent.available is True
        assert agent.a2a_url == "https://test.com/a2a"

    def test_cache_valid(self):
        agent = DiscoveredAgent(agent_url="https://test.com", cache_ttl_seconds=3600)
        assert agent.is_cache_valid()

    def test_cache_expired(self):
        agent = DiscoveredAgent(
            agent_url="https://test.com",
            last_verified_at=datetime.now(UTC) - timedelta(hours=2),
            cache_ttl_seconds=3600,
        )
        assert not agent.is_cache_valid()

    def test_has_skill(self):
        agent = DiscoveredAgent(agent_url="https://test.com", card=_make_card())
        assert agent.has_skill("payment-execute")
        assert agent.has_skill("echo")
        assert not agent.has_skill("nonexistent")

    def test_supports_streaming(self):
        agent = DiscoveredAgent(agent_url="https://test.com", card=_make_card())
        assert agent.supports_streaming()


class TestAgentDiscoveryService:
    @pytest.mark.asyncio
    async def test_discover_agent(self):
        http = MockHttpClient()
        svc = AgentDiscoveryService(http_client=http)
        agent = await svc.discover_agent("https://test.com")
        assert agent.available is True
        assert agent.card.name == "Test Agent"
        assert "/.well-known/agent.json" in http.get_calls[0]

    @pytest.mark.asyncio
    async def test_discover_caches(self):
        http = MockHttpClient()
        svc = AgentDiscoveryService(http_client=http)
        await svc.discover_agent("https://test.com")
        await svc.discover_agent("https://test.com")
        assert len(http.get_calls) == 1

    @pytest.mark.asyncio
    async def test_discover_force_refresh(self):
        http = MockHttpClient()
        svc = AgentDiscoveryService(http_client=http)
        await svc.discover_agent("https://test.com")
        await svc.discover_agent("https://test.com", force_refresh=True)
        assert len(http.get_calls) == 2

    @pytest.mark.asyncio
    async def test_discover_failure(self):
        http = MockHttpClient(responses={
            "https://bad.com/.well-known/agent.json": (404, {}),
        })
        svc = AgentDiscoveryService(http_client=http)
        agent = await svc.discover_agent("https://bad.com")
        assert not agent.available
        assert agent.last_error is not None

    @pytest.mark.asyncio
    async def test_discover_no_http_client(self):
        svc = AgentDiscoveryService()
        agent = await svc.discover_agent("https://test.com")
        assert not agent.available

    def test_register_agent(self):
        svc = AgentDiscoveryService()
        card = _make_card()
        agent = svc.register_agent("https://test.com", card)
        assert agent.available
        assert agent.card.name == "Test Agent"

    def test_get_agent(self):
        svc = AgentDiscoveryService()
        svc.register_agent("https://test.com", _make_card())
        assert svc.get_agent("https://test.com") is not None
        assert svc.get_agent("https://other.com") is None

    def test_list_agents(self):
        svc = AgentDiscoveryService()
        svc.register_agent("https://a.com", _make_card("A"))
        svc.register_agent("https://b.com", _make_card("B"))
        agents = svc.list_agents()
        assert len(agents) == 2

    def test_list_agents_by_skill(self):
        svc = AgentDiscoveryService()
        svc.register_agent("https://a.com", _make_card())
        agents = svc.list_agents(skill_id="payment-execute")
        assert len(agents) == 1
        agents = svc.list_agents(skill_id="nonexistent")
        assert len(agents) == 0

    def test_remove_agent(self):
        svc = AgentDiscoveryService()
        svc.register_agent("https://test.com", _make_card())
        assert svc.remove_agent("https://test.com")
        assert not svc.remove_agent("https://test.com")

    def test_clear_cache(self):
        svc = AgentDiscoveryService()
        svc.register_agent("https://a.com", _make_card())
        svc.register_agent("https://b.com", _make_card())
        assert svc.clear_cache() == 2
        assert len(svc.list_agents()) == 0
