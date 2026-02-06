"""Tests for AgentsResource."""
import pytest


class TestCreateAgent:
    """Tests for creating agents."""

    async def test_create_agent_successfully(self, client, httpx_mock):
        """Should create an agent with required fields."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/agents",
            method="POST",
            json={
                "id": "agent_001",
                "name": "Test Agent",
                "description": "A test agent",
                "is_active": True,
                "metadata": {"env": "test"},
                "created_at": "2025-01-20T00:00:00Z",
                "updated_at": "2025-01-20T00:00:00Z",
            },
        )

        agent = await client.agents.create(
            name="Test Agent",
            description="A test agent",
            spending_limits={"daily": "500"},
            policy={"allowed_categories": ["SaaS"]},
            metadata={"env": "test"},
        )

        assert agent.agent_id == "agent_001"
        assert agent.name == "Test Agent"
        assert agent.is_active is True

    async def test_create_agent_with_minimal_fields(self, client, httpx_mock):
        """Should create an agent with only required name field."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/agents",
            method="POST",
            json={
                "id": "agent_002",
                "name": "Minimal Agent",
                "is_active": True,
                "created_at": "2025-01-20T00:00:00Z",
                "updated_at": "2025-01-20T00:00:00Z",
            },
        )

        agent = await client.agents.create(name="Minimal Agent")
        assert agent.name == "Minimal Agent"


class TestGetAgent:
    """Tests for getting an agent."""

    async def test_get_agent_successfully(self, client, httpx_mock):
        """Should get an agent by ID."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/agents/agent_001",
            method="GET",
            json={
                "id": "agent_001",
                "name": "Test Agent",
                "is_active": True,
                "created_at": "2025-01-20T00:00:00Z",
                "updated_at": "2025-01-20T00:00:00Z",
            },
        )

        agent = await client.agents.get("agent_001")
        assert agent.agent_id == "agent_001"


class TestListAgents:
    """Tests for listing agents."""

    async def test_list_all_agents(self, client, httpx_mock):
        """Should list all agents."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/agents?limit=100",
            method="GET",
            json=[
                {
                    "id": "agent_001",
                    "name": "Agent 1",
                    "is_active": True,
                    "created_at": "2025-01-20T00:00:00Z",
                    "updated_at": "2025-01-20T00:00:00Z",
                },
                {
                    "id": "agent_002",
                    "name": "Agent 2",
                    "is_active": True,
                    "created_at": "2025-01-20T00:00:00Z",
                    "updated_at": "2025-01-20T00:00:00Z",
                },
            ],
        )

        agents = await client.agents.list()
        assert len(agents) == 2
        assert agents[0].agent_id == "agent_001"

    async def test_list_with_pagination(self, client, httpx_mock):
        """Should list agents with pagination."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/agents?limit=10&offset=5",
            method="GET",
            json=[
                {
                    "id": "agent_006",
                    "name": "Agent 6",
                    "is_active": True,
                    "created_at": "2025-01-20T00:00:00Z",
                    "updated_at": "2025-01-20T00:00:00Z",
                },
            ],
        )

        agents = await client.agents.list(limit=10, offset=5)
        assert len(agents) == 1
        assert agents[0].agent_id == "agent_006"


class TestUpdateAgent:
    """Tests for updating agents."""

    async def test_update_agent_name(self, client, httpx_mock):
        """Should update an agent's name."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/agents/agent_001",
            method="PATCH",
            json={
                "id": "agent_001",
                "name": "Updated Name",
                "is_active": True,
                "created_at": "2025-01-20T00:00:00Z",
                "updated_at": "2025-01-20T00:00:00Z",
            },
        )

        agent = await client.agents.update("agent_001", name="Updated Name")
        assert agent.name == "Updated Name"

    async def test_update_agent_metadata(self, client, httpx_mock):
        """Should update an agent's metadata."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/agents/agent_001",
            method="PATCH",
            json={
                "id": "agent_001",
                "name": "Test Agent",
                "metadata": {"version": "2.0"},
                "is_active": True,
                "created_at": "2025-01-20T00:00:00Z",
                "updated_at": "2025-01-20T00:00:00Z",
            },
        )

        agent = await client.agents.update("agent_001", metadata={"version": "2.0"})
        assert agent.metadata.get("version") == "2.0"

    async def test_deactivate_agent(self, client, httpx_mock):
        """Should deactivate an agent."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/agents/agent_001",
            method="PATCH",
            json={
                "id": "agent_001",
                "name": "Test Agent",
                "is_active": False,
                "created_at": "2025-01-20T00:00:00Z",
                "updated_at": "2025-01-20T00:00:00Z",
            },
        )

        agent = await client.agents.update("agent_001", is_active=False)
        assert agent.is_active is False
