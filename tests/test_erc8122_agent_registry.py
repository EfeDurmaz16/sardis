"""Tests for ERC-8122 Minimal Agent Registry.

Covers issue #145. Tests agent registration, batch registration,
metadata management, service discovery, display formatting,
suspension/revocation, and calldata builders.
"""
from __future__ import annotations

import pytest

from sardis_protocol.erc8122 import (
    METADATA_AGENT_ACCOUNT,
    METADATA_DESCRIPTION,
    METADATA_NAME,
    METADATA_SERVICE,
    METADATA_SERVICE_TYPE,
    STANDARD_METADATA_KEYS,
    AgentRegistration,
    AgentRegistryManager,
    MetadataEntry,
    RegistryInfo,
    RegistryStatus,
    ServiceType,
    build_owner_of_calldata,
    build_register_calldata,
    build_register_with_metadata_calldata,
    create_agent_registry,
)


# ============ Registration Tests ============


class TestRegistration:
    def test_register_agent(self):
        registry = AgentRegistryManager()
        agent = registry.register(
            owner="0x1234",
            name="PaymentBot",
            service_type=ServiceType.SARDIS_MCP,
            service_uri="https://mcp.sardis.sh/payment",
        )
        assert isinstance(agent, AgentRegistration)
        assert agent.agent_id == 1
        assert agent.owner == "0x1234"
        assert agent.name == "PaymentBot"
        assert agent.is_active is True

    def test_register_increments_id(self):
        registry = AgentRegistryManager()
        a1 = registry.register(owner="0x1")
        a2 = registry.register(owner="0x2")
        assert a2.agent_id == a1.agent_id + 1

    def test_register_with_all_metadata(self):
        registry = AgentRegistryManager()
        agent = registry.register(
            owner="0x1234",
            name="FullAgent",
            description="A fully described agent",
            service_type=ServiceType.A2A,
            service_uri="https://a2a.example.com",
            agent_account="0xABCD",
            additional_metadata={"version": "1.0"},
        )
        assert agent.description == "A fully described agent"
        assert agent.service_type == "a2a"
        assert agent.agent_account == "0xABCD"
        assert agent.metadata.get("version") == "1.0"

    def test_register_minimal(self):
        registry = AgentRegistryManager()
        agent = registry.register(owner="0x1234")
        assert agent.agent_id >= 1
        assert agent.name == ""


# ============ Batch Registration Tests ============


class TestBatchRegistration:
    def test_batch_register(self):
        registry = AgentRegistryManager()
        agents = registry.register_batch([
            {"owner": "0x1", "name": "Agent1"},
            {"owner": "0x2", "name": "Agent2"},
            {"owner": "0x3", "name": "Agent3"},
        ])
        assert len(agents) == 3
        assert agents[0].name == "Agent1"
        assert agents[2].name == "Agent3"

    def test_batch_register_empty(self):
        registry = AgentRegistryManager()
        agents = registry.register_batch([])
        assert agents == []


# ============ Query Tests ============


class TestQuerying:
    def _setup_registry(self) -> AgentRegistryManager:
        registry = AgentRegistryManager()
        registry.register(owner="0x1", name="PayBot", service_type=ServiceType.SARDIS_MCP)
        registry.register(owner="0x1", name="TradeBot", service_type=ServiceType.A2A)
        registry.register(owner="0x2", name="PayAgent", service_type=ServiceType.SARDIS_MCP)
        return registry

    def test_get_agent(self):
        registry = self._setup_registry()
        agent = registry.get_agent(1)
        assert agent is not None
        assert agent.name == "PayBot"

    def test_get_agent_not_found(self):
        registry = AgentRegistryManager()
        assert registry.get_agent(999) is None

    def test_owner_of(self):
        registry = self._setup_registry()
        assert registry.owner_of(1) == "0x1"
        assert registry.owner_of(3) == "0x2"
        assert registry.owner_of(999) is None

    def test_find_by_service_type(self):
        registry = self._setup_registry()
        mcp_agents = registry.find_by_service_type(ServiceType.SARDIS_MCP)
        assert len(mcp_agents) == 2

    def test_find_by_owner(self):
        registry = self._setup_registry()
        agents = registry.find_by_owner("0x1")
        assert len(agents) == 2

    def test_find_by_name(self):
        registry = self._setup_registry()
        agents = registry.find_by_name("Pay")
        assert len(agents) == 2  # PayBot and PayAgent

    def test_find_by_name_case_insensitive(self):
        registry = self._setup_registry()
        agents = registry.find_by_name("paybot")
        assert len(agents) == 1

    def test_total_agents(self):
        registry = self._setup_registry()
        assert registry.total_agents() == 3


# ============ Metadata Tests ============


class TestMetadata:
    def test_update_metadata(self):
        registry = AgentRegistryManager()
        agent = registry.register(owner="0x1", name="Bot")
        registry.update_metadata(agent.agent_id, {"version": "2.0"})
        updated = registry.get_agent(agent.agent_id)
        assert updated.metadata.get("version") == "2.0"

    def test_update_metadata_not_found(self):
        registry = AgentRegistryManager()
        with pytest.raises(ValueError, match="not found"):
            registry.update_metadata(999, {"key": "val"})

    def test_metadata_entries(self):
        agent = AgentRegistration(
            agent_id=1,
            owner="0x1",
            metadata={"name": "Bot", "version": "1.0"},
        )
        entries = agent.get_metadata_entries()
        assert len(entries) == 2
        assert all(isinstance(e, MetadataEntry) for e in entries)

    def test_metadata_entry_to_bytes(self):
        entry = MetadataEntry(key="name", value="TestBot")
        k, v = entry.to_bytes()
        assert k == b"name"
        assert v == b"TestBot"


# ============ Status Management Tests ============


class TestStatusManagement:
    def test_suspend(self):
        registry = AgentRegistryManager()
        agent = registry.register(owner="0x1")
        registry.suspend(agent.agent_id)
        assert agent.status == RegistryStatus.SUSPENDED
        assert agent.is_active is False

    def test_revoke(self):
        registry = AgentRegistryManager()
        agent = registry.register(owner="0x1")
        registry.revoke(agent.agent_id)
        assert agent.status == RegistryStatus.REVOKED

    def test_suspend_not_found(self):
        registry = AgentRegistryManager()
        with pytest.raises(ValueError, match="not found"):
            registry.suspend(999)

    def test_revoke_not_found(self):
        registry = AgentRegistryManager()
        with pytest.raises(ValueError, match="not found"):
            registry.revoke(999)

    def test_suspended_not_in_queries(self):
        registry = AgentRegistryManager()
        agent = registry.register(
            owner="0x1", name="Bot", service_type=ServiceType.MCP,
        )
        registry.suspend(agent.agent_id)
        results = registry.find_by_service_type(ServiceType.MCP)
        assert len(results) == 0


# ============ Display Format Tests ============


class TestDisplayFormat:
    def test_display_with_name(self):
        agent = AgentRegistration(
            agent_id=42,
            owner="0x1",
            metadata={"name": "Payment Bot"},
        )
        assert agent.display_name == "payment-bot.42"

    def test_display_without_name(self):
        agent = AgentRegistration(agent_id=42, owner="0x1")
        assert agent.display_name == "42"

    def test_format_display_full(self):
        registry = AgentRegistryManager(
            registry_address="0x00010000ABCD",
        )
        agent = registry.register(owner="0x1", name="MyBot")
        display = registry.format_display(agent.agent_id)
        assert "mybot" in display
        assert "@" in display

    def test_format_display_not_found(self):
        registry = AgentRegistryManager()
        display = registry.format_display(999)
        assert "999@" in display


# ============ Registry Info Tests ============


class TestRegistryInfo:
    def test_registry_info(self):
        registry = AgentRegistryManager(
            registry_name="TestRegistry",
            chain="base",
        )
        info = registry.registry_info
        assert isinstance(info, RegistryInfo)
        assert info.name == "TestRegistry"
        assert info.chain == "base"
        assert info.chain_id == 8453

    def test_registry_display(self):
        info = RegistryInfo(
            name="Test",
            address="0x1234567890abcdef",
            chain="base",
            chain_id=8453,
        )
        assert "@base" in info.display_format


# ============ Calldata Tests ============


class TestCalldata:
    def test_register_calldata(self):
        cd = build_register_calldata(
            owner="0x1234",
            service_type="mcp",
            service="https://example.com",
            agent_account="0xABCD",
        )
        assert len(cd) > 4
        assert cd[:4] == bytes.fromhex("f2c298be")

    def test_register_with_metadata_calldata(self):
        entries = [
            MetadataEntry("name", "TestBot"),
            MetadataEntry("version", "1.0"),
        ]
        cd = build_register_with_metadata_calldata("0x1234", entries)
        assert len(cd) > 4

    def test_owner_of_calldata(self):
        cd = build_owner_of_calldata(42)
        assert len(cd) == 36  # 4 + 32
        assert cd[:4] == bytes.fromhex("6352211e")


# ============ Enum Tests ============


class TestEnums:
    def test_service_types(self):
        assert len(ServiceType) == 8
        assert ServiceType.MCP.value == "mcp"

    def test_registry_statuses(self):
        assert len(RegistryStatus) == 3
        assert RegistryStatus.ACTIVE.value == "active"


# ============ Constants Tests ============


class TestConstants:
    def test_standard_metadata_keys(self):
        assert METADATA_NAME in STANDARD_METADATA_KEYS
        assert METADATA_SERVICE_TYPE in STANDARD_METADATA_KEYS
        assert len(STANDARD_METADATA_KEYS) == 9


# ============ Factory Tests ============


class TestFactory:
    def test_create_registry(self):
        registry = create_agent_registry()
        assert isinstance(registry, AgentRegistryManager)

    def test_create_custom(self):
        registry = create_agent_registry(
            registry_name="CustomRegistry",
            chain="polygon",
        )
        assert registry._name == "CustomRegistry"
        assert registry._chain == "polygon"


# ============ Module Export Tests ============


class TestModuleExports:
    def test_imports_from_protocol(self):
        from sardis_protocol import (
            AgentRegistration,
            AgentRegistryManager,
            MetadataEntry,
            RegistryStatus,
            ServiceType,
            create_agent_registry,
        )
        assert all([
            AgentRegistration, AgentRegistryManager,
            MetadataEntry, RegistryStatus, ServiceType,
            create_agent_registry,
        ])
