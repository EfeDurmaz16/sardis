"""Tests for ERC-8001 Agent Coordination Framework.

Covers issue #144. Tests intent lifecycle, acceptance attestations,
execution, cancellation, bounded policies, and calldata builders.
"""
from __future__ import annotations

import time

import pytest

from sardis_protocol.erc8001 import (
    AGENT_INTENT_TYPEHASH,
    CHAIN_IDS,
    DEFAULT_INTENT_EXPIRY_HOURS,
    AcceptanceAttestation,
    AgentCoordinationManager,
    AgentIntent,
    BoundedPolicy,
    CoordinationPayload,
    CoordinationStatus,
    CoordinationType,
    ExecutionResult,
    build_accept_calldata,
    build_cancel_calldata,
    build_domain_separator,
    build_execute_calldata,
    build_propose_calldata,
    compute_acceptance_hash,
    compute_intent_hash,
    create_coordination_manager,
)


# ============ Coordination Payload Tests ============


class TestCoordinationPayload:
    def test_create_payload(self):
        payload = CoordinationPayload(
            coordination_type=CoordinationType.PAYMENT,
            coordination_data=b"test",
        )
        assert payload.version == 1
        assert payload.timestamp > 0

    def test_payload_hash(self):
        payload = CoordinationPayload(
            coordination_type=CoordinationType.PAYMENT,
            coordination_data=b"test",
        )
        h = payload.payload_hash
        assert len(h) == 32  # SHA-256

    def test_different_payloads_different_hashes(self):
        p1 = CoordinationPayload(coordination_data=b"data1", timestamp=100)
        p2 = CoordinationPayload(coordination_data=b"data2", timestamp=100)
        assert p1.payload_hash != p2.payload_hash


# ============ Agent Intent Tests ============


class TestAgentIntent:
    def test_create_intent(self):
        intent = AgentIntent(
            intent_id="test_1",
            payload_hash=b"\x00" * 32,
            expiry=int(time.time()) + 3600,
            nonce=1,
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2", "agent_3"],
        )
        assert intent.status == CoordinationStatus.PROPOSED
        assert intent.is_expired is False
        assert intent.required_acceptances == 2
        assert intent.acceptance_count == 0

    def test_expired_intent(self):
        intent = AgentIntent(
            intent_id="test_2",
            payload_hash=b"\x00" * 32,
            expiry=int(time.time()) - 100,
            nonce=1,
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2"],
        )
        assert intent.is_expired is True
        assert intent.is_ready is False

    def test_pending_participants(self):
        intent = AgentIntent(
            intent_id="test_3",
            payload_hash=b"\x00" * 32,
            expiry=int(time.time()) + 3600,
            nonce=1,
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2", "agent_3"],
        )
        assert intent.pending_participants == ["agent_2", "agent_3"]

    def test_intent_hash(self):
        intent = AgentIntent(
            intent_id="test_4",
            payload_hash=b"\x01" * 32,
            expiry=1000000,
            nonce=42,
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
        )
        h = intent.intent_hash
        assert len(h) == 32


# ============ Acceptance Tests ============


class TestAcceptanceAttestation:
    def test_create_attestation(self):
        att = AcceptanceAttestation(
            intent_hash=b"\x00" * 32,
            participant="agent_2",
            nonce=1,
            expiry=int(time.time()) + 3600,
        )
        assert att.is_expired is False

    def test_expired_attestation(self):
        att = AcceptanceAttestation(
            intent_hash=b"\x00" * 32,
            participant="agent_2",
            nonce=1,
            expiry=int(time.time()) - 100,
        )
        assert att.is_expired is True

    def test_attestation_hash(self):
        att = AcceptanceAttestation(
            intent_hash=b"\x01" * 32,
            participant="agent_2",
            nonce=42,
            expiry=1000000,
        )
        h = att.attestation_hash
        assert len(h) == 32


# ============ Coordination Manager Tests ============


class TestCoordinationManager:
    def test_propose(self):
        mgr = AgentCoordinationManager()
        intent = mgr.propose(
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2", "agent_3"],
        )
        assert intent.status == CoordinationStatus.PROPOSED
        assert intent.agent_id == "agent_1"
        assert len(intent.participants) == 2

    def test_accept_single(self):
        mgr = AgentCoordinationManager()
        intent = mgr.propose(
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2"],
        )
        att = mgr.accept(intent.intent_id, "agent_2")
        assert isinstance(att, AcceptanceAttestation)
        assert intent.status == CoordinationStatus.READY

    def test_accept_multiple(self):
        mgr = AgentCoordinationManager()
        intent = mgr.propose(
            agent_id="agent_1",
            coordination_type=CoordinationType.JOB_CREATE,
            participants=["agent_2", "agent_3"],
        )
        mgr.accept(intent.intent_id, "agent_2")
        assert intent.status == CoordinationStatus.PROPOSED
        mgr.accept(intent.intent_id, "agent_3")
        assert intent.status == CoordinationStatus.READY

    def test_accept_not_found(self):
        mgr = AgentCoordinationManager()
        with pytest.raises(ValueError, match="not found"):
            mgr.accept("fake", "agent_2")

    def test_accept_not_participant(self):
        mgr = AgentCoordinationManager()
        intent = mgr.propose(
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2"],
        )
        with pytest.raises(ValueError, match="not in intent"):
            mgr.accept(intent.intent_id, "agent_99")

    def test_accept_duplicate(self):
        mgr = AgentCoordinationManager()
        intent = mgr.propose(
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2"],
        )
        mgr.accept(intent.intent_id, "agent_2")
        with pytest.raises(ValueError, match="already accepted"):
            mgr.accept(intent.intent_id, "agent_2")

    def test_execute(self):
        mgr = AgentCoordinationManager()
        intent = mgr.propose(
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2"],
        )
        mgr.accept(intent.intent_id, "agent_2")
        result = mgr.execute(intent.intent_id)
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert intent.status == CoordinationStatus.EXECUTED

    def test_execute_not_ready(self):
        mgr = AgentCoordinationManager()
        intent = mgr.propose(
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2"],
        )
        with pytest.raises(ValueError, match="not ready"):
            mgr.execute(intent.intent_id)

    def test_cancel_by_proposer(self):
        mgr = AgentCoordinationManager()
        intent = mgr.propose(
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2"],
        )
        result = mgr.cancel(intent.intent_id, "agent_1")
        assert result.status == CoordinationStatus.CANCELLED

    def test_cancel_not_proposer(self):
        mgr = AgentCoordinationManager()
        intent = mgr.propose(
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2"],
        )
        with pytest.raises(ValueError, match="Only proposer"):
            mgr.cancel(intent.intent_id, "agent_2")

    def test_cancel_executed_fails(self):
        mgr = AgentCoordinationManager()
        intent = mgr.propose(
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2"],
        )
        mgr.accept(intent.intent_id, "agent_2")
        mgr.execute(intent.intent_id)
        with pytest.raises(ValueError, match="already executed"):
            mgr.cancel(intent.intent_id, "agent_1")

    def test_get_intent(self):
        mgr = AgentCoordinationManager()
        intent = mgr.propose(
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
            participants=["agent_2"],
        )
        found = mgr.get_intent(intent.intent_id)
        assert found is intent

    def test_list_pending(self):
        mgr = AgentCoordinationManager()
        mgr.propose("a1", CoordinationType.PAYMENT, ["a2"])
        mgr.propose("a3", CoordinationType.JOB_CREATE, ["a4"])
        pending = mgr.list_pending()
        assert len(pending) == 2

    def test_list_pending_for_participant(self):
        mgr = AgentCoordinationManager()
        mgr.propose("a1", CoordinationType.PAYMENT, ["a2"])
        mgr.propose("a3", CoordinationType.JOB_CREATE, ["a4"])
        pending = mgr.list_pending(participant="a2")
        assert len(pending) == 1


# ============ Bounded Policy Tests ============


class TestBoundedPolicy:
    def test_allows_counterparty(self):
        policy = BoundedPolicy(
            agent_id="agent_1",
            approved_counterparties=["agent_2", "agent_3"],
        )
        assert policy.allows_counterparty("agent_2") is True
        assert policy.allows_counterparty("agent_99") is False

    def test_no_counterparty_restriction(self):
        policy = BoundedPolicy(agent_id="agent_1")
        assert policy.allows_counterparty("anyone") is True

    def test_allows_coordination_type(self):
        policy = BoundedPolicy(
            agent_id="agent_1",
            approved_coordination_types=[CoordinationType.PAYMENT],
        )
        assert policy.allows_coordination_type(CoordinationType.PAYMENT) is True
        assert policy.allows_coordination_type(CoordinationType.JOB_CREATE) is False

    def test_allows_amount(self):
        policy = BoundedPolicy(
            agent_id="agent_1",
            per_tx_limit_usd=1000,
        )
        assert policy.allows_amount(500) is True
        assert policy.allows_amount(1500) is False

    def test_no_amount_restriction(self):
        policy = BoundedPolicy(agent_id="agent_1")
        assert policy.allows_amount(999999) is True

    def test_validity(self):
        policy = BoundedPolicy(
            agent_id="agent_1",
            valid_until=int(time.time()) + 3600,
        )
        assert policy.is_valid is True

    def test_expired_policy(self):
        policy = BoundedPolicy(
            agent_id="agent_1",
            valid_until=int(time.time()) - 100,
        )
        assert policy.is_valid is False


# ============ EIP-712 Tests ============


class TestEIP712:
    def test_domain_separator(self):
        sep = build_domain_separator()
        assert len(sep) == 32

    def test_domain_separator_different_chains(self):
        s1 = build_domain_separator(chain_id=1)
        s2 = build_domain_separator(chain_id=8453)
        assert s1 != s2

    def test_compute_intent_hash(self):
        intent = AgentIntent(
            intent_id="test",
            payload_hash=b"\x01" * 32,
            expiry=999999,
            nonce=1,
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
        )
        h = compute_intent_hash(intent)
        assert len(h) == 32

    def test_compute_acceptance_hash(self):
        att = AcceptanceAttestation(
            intent_hash=b"\x01" * 32,
            participant="agent_2",
            nonce=1,
            expiry=999999,
        )
        h = compute_acceptance_hash(att)
        assert len(h) == 32


# ============ Calldata Tests ============


class TestCalldata:
    def test_propose_calldata(self):
        intent = AgentIntent(
            intent_id="test",
            payload_hash=b"\x01" * 32,
            expiry=999999,
            nonce=1,
            agent_id="agent_1",
            coordination_type=CoordinationType.PAYMENT,
        )
        cd = build_propose_calldata(intent)
        assert len(cd) > 4
        assert cd[:4] == bytes.fromhex("a1b2c3d4")

    def test_accept_calldata(self):
        att = AcceptanceAttestation(
            intent_hash=b"\x01" * 32,
            participant="agent_2",
            nonce=1,
            expiry=999999,
        )
        cd = build_accept_calldata(att)
        assert len(cd) > 4
        assert cd[:4] == bytes.fromhex("b2c3d4e5")

    def test_execute_calldata(self):
        cd = build_execute_calldata(b"\x01" * 32)
        assert len(cd) == 36
        assert cd[:4] == bytes.fromhex("c3d4e5f6")

    def test_cancel_calldata(self):
        cd = build_cancel_calldata(b"\x01" * 32)
        assert len(cd) == 36
        assert cd[:4] == bytes.fromhex("d4e5f6a7")


# ============ Enum Tests ============


class TestEnums:
    def test_coordination_status(self):
        assert len(CoordinationStatus) == 6

    def test_coordination_types(self):
        assert len(CoordinationType) == 7
        assert CoordinationType.PAYMENT.value == "sardis.payment"

    def test_status_values(self):
        assert CoordinationStatus.READY.value == "ready"
        assert CoordinationStatus.EXECUTED.value == "executed"


# ============ Constants Tests ============


class TestConstants:
    def test_chain_ids(self):
        assert CHAIN_IDS["base"] == 8453
        assert CHAIN_IDS["ethereum"] == 1

    def test_typehash(self):
        assert len(AGENT_INTENT_TYPEHASH) == 32

    def test_default_expiry(self):
        assert DEFAULT_INTENT_EXPIRY_HOURS == 24


# ============ Factory Tests ============


class TestFactory:
    def test_create_manager(self):
        mgr = create_coordination_manager()
        assert isinstance(mgr, AgentCoordinationManager)

    def test_create_custom(self):
        mgr = create_coordination_manager(chain="polygon")
        assert mgr._chain == "polygon"


# ============ Module Export Tests ============


class TestModuleExports:
    def test_imports_from_protocol(self):
        from sardis_protocol import (
            AgentCoordinationManager,
            AgentIntent,
            CoordinationStatus,
            CoordinationType,
            create_coordination_manager,
        )
        assert all([
            AgentCoordinationManager, AgentIntent,
            CoordinationStatus, CoordinationType,
            create_coordination_manager,
        ])
