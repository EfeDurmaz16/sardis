"""Tests for ERC-8004 Trustless Agents integration.

Covers issue #137. Tests registration file generation, calldata encoding,
EIP-712 wallet binding, reputation feedback, and namespace building.
"""
from __future__ import annotations

import json

import pytest
from eth_abi import decode
from web3 import Web3

from sardis_v2_core.erc8004 import (
    ERC8004_ADDRESSES,
    GIVE_FEEDBACK_SELECTOR,
    REGISTER_SELECTOR,
    REVOKE_FEEDBACK_SELECTOR,
    SERVICE_TYPE_A2A,
    SERVICE_TYPE_MCP,
    SERVICE_TYPE_WEB,
    SET_AGENT_URI_SELECTOR,
    SET_AGENT_WALLET_SELECTOR,
    SET_METADATA_SELECTOR,
    TRUST_REPUTATION,
    UNSET_AGENT_WALLET_SELECTOR,
    AgentRegistrationFile,
    AgentService,
    ReputationFeedback,
    ReputationSummary,
    build_agent_global_id,
    build_agent_namespace,
    build_give_feedback_calldata,
    build_register_calldata,
    build_revoke_feedback_calldata,
    build_sardis_agent_registration,
    build_set_agent_uri_calldata,
    build_set_agent_wallet_calldata,
    build_set_metadata_calldata,
    build_unset_agent_wallet_calldata,
    build_wallet_binding_digest,
    # Legacy types (backward compatibility)
    AgentIdentity,
    AgentMetadata,
    ERC8004Registry,
    InMemoryERC8004Registry,
    ReputationEntry,
    ValidationResult,
)

TEST_AGENT_ADDR = "0x1234567890AbcdEF1234567890aBcdef12345678"
TEST_WALLET = "0xDeaDbeefdEAdbeefdEadbEEFdeadbeEFdEaDbeeF"


# ============ Agent Registration File Tests ============

class TestAgentRegistrationFile:
    def test_to_json(self):
        reg = AgentRegistrationFile(
            name="SardisPayAgent",
            description="Payment agent powered by Sardis",
            services=[
                AgentService(name="A2A", endpoint="https://api.sardis.sh/a2a"),
                AgentService(name="MCP", endpoint="https://api.sardis.sh/mcp"),
            ],
            x402_support=True,
            active=True,
        )

        raw = reg.to_json()
        data = json.loads(raw)

        assert data["type"] == "https://eips.ethereum.org/EIPS/eip-8004#registration-v1"
        assert data["name"] == "SardisPayAgent"
        assert data["x402Support"] is True
        assert data["active"] is True
        assert len(data["services"]) == 2
        assert data["services"][0]["name"] == "A2A"

    def test_from_json_roundtrip(self):
        original = AgentRegistrationFile(
            name="TestAgent",
            description="A test agent",
            services=[AgentService(name="web", endpoint="https://example.com")],
            image="https://example.com/avatar.png",
            x402_support=True,
            supported_trust=["reputation", "tee-attestation"],
        )

        raw = original.to_json()
        parsed = AgentRegistrationFile.from_json(raw)

        assert parsed.name == original.name
        assert parsed.description == original.description
        assert parsed.x402_support is True
        assert len(parsed.services) == 1
        assert parsed.services[0].endpoint == "https://example.com"
        assert parsed.image == "https://example.com/avatar.png"
        assert "tee-attestation" in parsed.supported_trust

    def test_registrations_included(self):
        reg = AgentRegistrationFile(
            name="Agent",
            description="Test",
            registrations=[{
                "agentId": 42,
                "agentRegistry": "erc8004:8453:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
            }],
        )
        data = json.loads(reg.to_json())
        assert data["registrations"][0]["agentId"] == 42

    def test_no_image_omitted(self):
        reg = AgentRegistrationFile(name="Agent", description="Test")
        data = json.loads(reg.to_json())
        assert "image" not in data


# ============ Sardis Registration Builder Tests ============

class TestBuildSardisAgentRegistration:
    def test_basic_registration(self):
        reg = build_sardis_agent_registration(
            agent_name="PayBot",
            description="Sardis payment agent",
            api_endpoint="https://api.sardis.sh/v2",
        )

        assert reg.name == "PayBot"
        assert reg.x402_support is True
        assert TRUST_REPUTATION in reg.supported_trust
        assert len(reg.services) == 1
        assert reg.services[0].name == SERVICE_TYPE_WEB

    def test_all_endpoints(self):
        reg = build_sardis_agent_registration(
            agent_name="FullAgent",
            description="Full-featured agent",
            api_endpoint="https://api.sardis.sh/v2",
            a2a_endpoint="https://api.sardis.sh/a2a",
            mcp_endpoint="https://api.sardis.sh/mcp",
        )

        assert len(reg.services) == 3
        names = {s.name for s in reg.services}
        assert names == {SERVICE_TYPE_WEB, SERVICE_TYPE_A2A, SERVICE_TYPE_MCP}

    def test_with_agent_id(self):
        reg = build_sardis_agent_registration(
            agent_name="RegisteredAgent",
            description="Already registered",
            agent_id=42,
            chain_id=8453,
        )

        assert len(reg.registrations) == 1
        assert reg.registrations[0]["agentId"] == 42
        assert "erc8004:8453:" in reg.registrations[0]["agentRegistry"]

    def test_json_valid(self):
        reg = build_sardis_agent_registration(
            agent_name="JSONAgent",
            description="JSON test",
            image_url="https://sardis.sh/agent.png",
        )
        data = json.loads(reg.to_json())
        assert data["image"] == "https://sardis.sh/agent.png"


# ============ Calldata Builder Tests ============

class TestBuildRegisterCalldata:
    def test_basic_register(self):
        calldata = build_register_calldata(
            agent_uri="ipfs://QmTest123",
        )
        assert calldata[:4] == REGISTER_SELECTOR
        assert len(calldata) > 4

    def test_register_with_metadata(self):
        calldata = build_register_calldata(
            agent_uri="https://example.com/agent.json",
            metadata=[("version", b"1.0")],
        )
        assert calldata[:4] == REGISTER_SELECTOR


class TestBuildSetAgentUri:
    def test_encodes_correctly(self):
        calldata = build_set_agent_uri_calldata(42, "ipfs://QmNewUri")
        assert calldata[:4] == SET_AGENT_URI_SELECTOR
        decoded = decode(["uint256", "string"], calldata[4:])
        assert decoded[0] == 42
        assert decoded[1] == "ipfs://QmNewUri"


class TestBuildSetAgentWallet:
    def test_encodes_correctly(self):
        sig = b"\x01" * 65
        calldata = build_set_agent_wallet_calldata(
            agent_id=42,
            wallet_address=TEST_WALLET,
            deadline=1700000000,
            signature=sig,
        )
        assert calldata[:4] == SET_AGENT_WALLET_SELECTOR

    def test_checksum_address(self):
        sig = b"\x02" * 65
        calldata = build_set_agent_wallet_calldata(
            agent_id=1,
            wallet_address="0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            deadline=2000000000,
            signature=sig,
        )
        # Should encode without error (address gets checksummed internally)
        assert len(calldata) > 4


class TestBuildUnsetAgentWallet:
    def test_encodes_correctly(self):
        calldata = build_unset_agent_wallet_calldata(42)
        assert calldata[:4] == UNSET_AGENT_WALLET_SELECTOR
        decoded = decode(["uint256"], calldata[4:])
        assert decoded[0] == 42


class TestBuildSetMetadata:
    def test_encodes_correctly(self):
        calldata = build_set_metadata_calldata(
            agent_id=42,
            key="sardis_wallet_id",
            value=b"wal_abc123",
        )
        assert calldata[:4] == SET_METADATA_SELECTOR


# ============ Reputation Calldata Tests ============

class TestBuildGiveFeedback:
    def test_positive_feedback(self):
        feedback = ReputationFeedback(
            agent_id=42,
            value=85,  # +0.85 score
            value_decimals=2,
            tag1="reliability",
            tag2="payment",
            endpoint="https://api.sardis.sh/v2",
        )
        calldata = build_give_feedback_calldata(feedback)
        assert calldata[:4] == GIVE_FEEDBACK_SELECTOR
        assert len(calldata) > 4

    def test_negative_feedback(self):
        feedback = ReputationFeedback(
            agent_id=10,
            value=-50,  # -0.50 score
            value_decimals=2,
            tag1="speed",
        )
        calldata = build_give_feedback_calldata(feedback)
        assert calldata[:4] == GIVE_FEEDBACK_SELECTOR


class TestBuildRevokeFeedback:
    def test_encodes_correctly(self):
        calldata = build_revoke_feedback_calldata(agent_id=42, feedback_index=3)
        assert calldata[:4] == REVOKE_FEEDBACK_SELECTOR


# ============ Reputation Summary Tests ============

class TestReputationSummary:
    def test_normalized_score_positive(self):
        summary = ReputationSummary(
            agent_id=42, count=10, value=8500, value_decimals=2
        )
        # value = 85.00, normalized = (85+100)/200 = 0.925
        assert abs(summary.normalized_score - 0.925) < 0.001

    def test_normalized_score_zero(self):
        summary = ReputationSummary(
            agent_id=1, count=0, value=0, value_decimals=2
        )
        assert abs(summary.normalized_score - 0.5) < 0.001

    def test_normalized_score_negative(self):
        summary = ReputationSummary(
            agent_id=1, count=5, value=-5000, value_decimals=2
        )
        # value = -50.00, normalized = (-50+100)/200 = 0.25
        assert abs(summary.normalized_score - 0.25) < 0.001

    def test_normalized_score_clamped(self):
        summary = ReputationSummary(
            agent_id=1, count=1, value=50000, value_decimals=2
        )
        # value = 500 > 100 → clamped to 1.0
        assert summary.normalized_score == 1.0


# ============ EIP-712 Wallet Binding Tests ============

class TestBuildWalletBindingDigest:
    def test_produces_32_bytes(self):
        digest = build_wallet_binding_digest(
            agent_id=42,
            wallet_address=TEST_WALLET,
            deadline=1700000000,
            chain_id=8453,
        )
        assert len(digest) == 32

    def test_deterministic(self):
        d1 = build_wallet_binding_digest(42, TEST_WALLET, 1700000000, 8453)
        d2 = build_wallet_binding_digest(42, TEST_WALLET, 1700000000, 8453)
        assert d1 == d2

    def test_different_params_different_digest(self):
        d1 = build_wallet_binding_digest(42, TEST_WALLET, 1700000000, 8453)
        d2 = build_wallet_binding_digest(43, TEST_WALLET, 1700000000, 8453)
        d3 = build_wallet_binding_digest(42, TEST_WALLET, 1700000001, 8453)
        d4 = build_wallet_binding_digest(42, TEST_WALLET, 1700000000, 1)
        assert d1 != d2
        assert d1 != d3
        assert d1 != d4

    def test_custom_registry(self):
        d1 = build_wallet_binding_digest(
            42, TEST_WALLET, 1700000000, 8453,
        )
        d2 = build_wallet_binding_digest(
            42, TEST_WALLET, 1700000000, 8453,
            identity_registry="0x1111111111111111111111111111111111111111",
        )
        assert d1 != d2


# ============ Namespace Tests ============

class TestBuildAgentNamespace:
    def test_default_registry(self):
        ns = build_agent_namespace(8453)
        assert ns == f"erc8004:8453:{ERC8004_ADDRESSES['identity_registry']}"

    def test_custom_registry(self):
        custom = "0x1111111111111111111111111111111111111111"
        ns = build_agent_namespace(1, identity_registry=custom)
        assert ns == f"erc8004:1:{custom}"


class TestBuildAgentGlobalId:
    def test_format(self):
        gid = build_agent_global_id(42, 8453)
        assert gid.startswith("erc8004:8453:")
        assert gid.endswith(":42")

    def test_different_chains(self):
        g1 = build_agent_global_id(42, 8453)
        g2 = build_agent_global_id(42, 1)
        assert g1 != g2


# ============ Constants Tests ============

class TestConstants:
    def test_registry_addresses(self):
        assert ERC8004_ADDRESSES["identity_registry"].startswith("0x8004")
        assert ERC8004_ADDRESSES["reputation_registry"].startswith("0x8004")

    def test_function_selectors_length(self):
        assert len(REGISTER_SELECTOR) == 4
        assert len(SET_AGENT_URI_SELECTOR) == 4
        assert len(SET_AGENT_WALLET_SELECTOR) == 4
        assert len(GIVE_FEEDBACK_SELECTOR) == 4


# ============ Legacy Backward Compatibility Tests ============

class TestLegacyTypes:
    """Ensure existing types still work."""

    def test_agent_metadata(self):
        meta = AgentMetadata(
            name="Test",
            description="A test agent",
            version="1.0",
            model_type="claude-3-opus",
        )
        d = meta.to_dict()
        assert d["name"] == "Test"
        parsed = AgentMetadata.from_dict(d)
        assert parsed.model_type == "claude-3-opus"

    def test_agent_identity_did(self):
        identity = AgentIdentity(
            agent_id="42",
            owner_address=TEST_AGENT_ADDR,
            agent_uri="ipfs://test",
            metadata={},
            created_at=0,
            chain_id=8453,
        )
        assert identity.did == "did:erc8004:8453:42"

    @pytest.mark.asyncio
    async def test_in_memory_registry(self):
        registry = InMemoryERC8004Registry(chain_id=8453)
        meta = AgentMetadata(
            name="TestAgent",
            description="Test",
            version="1.0",
            model_type="gpt-4",
        )
        identity = await registry.register_agent(TEST_AGENT_ADDR, meta)
        assert identity.agent_id == "1"

        fetched = await registry.get_agent("1")
        assert fetched is not None
        assert fetched.owner_address == TEST_AGENT_ADDR


# ============ Module Export Tests ============

class TestModuleExports:
    def test_new_types_importable(self):
        from sardis_v2_core.erc8004 import (
            AgentRegistrationFile,
            AgentService,
            ReputationFeedback,
            ReputationSummary,
            build_sardis_agent_registration,
        )
        assert all([
            AgentRegistrationFile,
            AgentService,
            ReputationFeedback,
            ReputationSummary,
            build_sardis_agent_registration,
        ])

    def test_calldata_builders_importable(self):
        from sardis_v2_core.erc8004 import (
            build_register_calldata,
            build_set_agent_wallet_calldata,
            build_give_feedback_calldata,
            build_wallet_binding_digest,
        )
        assert all([
            build_register_calldata,
            build_set_agent_wallet_calldata,
            build_give_feedback_calldata,
            build_wallet_binding_digest,
        ])
