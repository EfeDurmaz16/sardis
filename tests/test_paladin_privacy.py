"""Tests for Paladin Privacy integration.

Covers issue #147. Tests UTXO lifecycle, private transfers with notary
validation, privacy group management, calldata builders, and factory functions.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sardis_protocol.paladin_privacy import (
    DEFAULT_ENDORSEMENT_POLICY,
    MAX_UTXO_INPUTS,
    PALADIN_VERSION,
    SUPPORTED_PRIVACY_TOKENS,
    NotaryDecision,
    NotaryValidation,
    PaladinPrivacyManager,
    PrivacyConfig,
    PrivacyDomain,
    PrivacyGroup,
    PrivacyGroupStatus,
    PrivacyLevel,
    PrivateTransfer,
    UTXO,
    UTXOState,
    ZKProofRequest,
    build_create_privacy_group_calldata,
    build_notarized_transfer_calldata,
    create_privacy_manager,
)


# ============ UTXO Tests ============


class TestUTXO:
    def test_creation(self):
        utxo = UTXO(
            utxo_id="utxo_1",
            owner="0xAlice",
            amount=1000,
            token="USDC",
        )
        assert utxo.utxo_id == "utxo_1"
        assert utxo.owner == "0xAlice"
        assert utxo.amount == 1000
        assert utxo.token == "USDC"
        assert utxo.state == UTXOState.UNSPENT
        assert utxo.spent_at is None
        assert isinstance(utxo.created_at, datetime)

    def test_is_spendable_unspent(self):
        utxo = UTXO(utxo_id="u1", owner="alice", amount=100)
        assert utxo.is_spendable is True

    def test_is_spendable_spent(self):
        utxo = UTXO(utxo_id="u1", owner="alice", amount=100, state=UTXOState.SPENT)
        assert utxo.is_spendable is False

    def test_is_spendable_locked(self):
        utxo = UTXO(utxo_id="u1", owner="alice", amount=100, state=UTXOState.LOCKED)
        assert utxo.is_spendable is False

    def test_default_token(self):
        utxo = UTXO(utxo_id="u1", owner="alice", amount=100)
        assert utxo.token == "USDC"


# ============ Privacy Group Tests ============


class TestPrivacyGroup:
    def test_creation(self):
        group = PrivacyGroup(
            group_id="grp_1",
            name="Test Group",
            members=["alice", "bob"],
        )
        assert group.group_id == "grp_1"
        assert group.name == "Test Group"
        assert group.member_count == 2
        assert group.status == PrivacyGroupStatus.ACTIVE
        assert group.endorsement_policy == DEFAULT_ENDORSEMENT_POLICY

    def test_is_active(self):
        group = PrivacyGroup(group_id="g1", name="G")
        assert group.is_active is True
        group.status = PrivacyGroupStatus.SUSPENDED
        assert group.is_active is False
        group.status = PrivacyGroupStatus.DISSOLVED
        assert group.is_active is False

    def test_is_member(self):
        group = PrivacyGroup(
            group_id="g1", name="G", members=["alice", "bob"],
        )
        assert group.is_member("alice") is True
        assert group.is_member("charlie") is False

    def test_add_member(self):
        group = PrivacyGroup(group_id="g1", name="G", members=["alice"])
        group.add_member("bob")
        assert group.is_member("bob") is True
        assert group.member_count == 2

    def test_add_member_idempotent(self):
        group = PrivacyGroup(group_id="g1", name="G", members=["alice"])
        group.add_member("alice")
        assert group.member_count == 1

    def test_remove_member(self):
        group = PrivacyGroup(
            group_id="g1", name="G", members=["alice", "bob"],
        )
        group.remove_member("bob")
        assert group.is_member("bob") is False
        assert group.member_count == 1

    def test_remove_member_not_present(self):
        group = PrivacyGroup(group_id="g1", name="G", members=["alice"])
        group.remove_member("charlie")  # Should not raise
        assert group.member_count == 1

    def test_member_count(self):
        group = PrivacyGroup(
            group_id="g1", name="G", members=["a", "b", "c"],
        )
        assert group.member_count == 3


# ============ Private Transfer Tests ============


class TestPrivateTransfer:
    def test_creation(self):
        transfer = PrivateTransfer(
            transfer_id="txfr_1",
            domain=PrivacyDomain.NOTO,
            sender="alice",
            receiver="bob",
            amount=500,
        )
        assert transfer.transfer_id == "txfr_1"
        assert transfer.domain == PrivacyDomain.NOTO
        assert transfer.sender == "alice"
        assert transfer.receiver == "bob"
        assert transfer.amount == 500
        assert transfer.token == "USDC"
        assert transfer.privacy_level == PrivacyLevel.PRIVATE
        assert transfer.notary_decision == NotaryDecision.PENDING

    def test_is_approved(self):
        transfer = PrivateTransfer(
            transfer_id="t1", domain=PrivacyDomain.NOTO,
            sender="a", receiver="b", amount=100,
            notary_decision=NotaryDecision.APPROVE,
        )
        assert transfer.is_approved is True
        assert transfer.is_pending is False

    def test_is_pending(self):
        transfer = PrivateTransfer(
            transfer_id="t1", domain=PrivacyDomain.NOTO,
            sender="a", receiver="b", amount=100,
        )
        assert transfer.is_pending is True
        assert transfer.is_approved is False

    def test_rejected_transfer(self):
        transfer = PrivateTransfer(
            transfer_id="t1", domain=PrivacyDomain.NOTO,
            sender="a", receiver="b", amount=100,
            notary_decision=NotaryDecision.REJECT,
        )
        assert transfer.is_approved is False
        assert transfer.is_pending is False


# ============ Paladin Privacy Manager Tests ============


class TestPaladinPrivacyManager:
    # ---- UTXO management ----

    def test_create_utxo(self):
        mgr = PaladinPrivacyManager()
        utxo = mgr.create_utxo("alice", 1000)
        assert utxo.owner == "alice"
        assert utxo.amount == 1000
        assert utxo.state == UTXOState.UNSPENT
        assert utxo.utxo_id.startswith("utxo_")

    def test_create_utxo_custom_token(self):
        mgr = PaladinPrivacyManager()
        utxo = mgr.create_utxo("alice", 500, "EURC")
        assert utxo.token == "EURC"

    def test_get_utxo(self):
        mgr = PaladinPrivacyManager()
        utxo = mgr.create_utxo("alice", 1000)
        found = mgr.get_utxo(utxo.utxo_id)
        assert found is utxo

    def test_get_utxo_not_found(self):
        mgr = PaladinPrivacyManager()
        assert mgr.get_utxo("nonexistent") is None

    def test_get_utxos_for_owner(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 100)
        mgr.create_utxo("alice", 200)
        mgr.create_utxo("bob", 300)
        alice_utxos = mgr.get_utxos_for_owner("alice")
        assert len(alice_utxos) == 2
        assert all(u.owner == "alice" for u in alice_utxos)

    def test_get_utxos_for_owner_excludes_spent(self):
        mgr = PaladinPrivacyManager()
        u1 = mgr.create_utxo("alice", 100)
        mgr.create_utxo("alice", 200)
        u1.state = UTXOState.SPENT
        alice_utxos = mgr.get_utxos_for_owner("alice")
        assert len(alice_utxos) == 1

    def test_get_balance(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 100)
        mgr.create_utxo("alice", 250)
        mgr.create_utxo("alice", 50, "EURC")
        assert mgr.get_balance("alice", "USDC") == 350
        assert mgr.get_balance("alice", "EURC") == 50

    def test_get_balance_empty(self):
        mgr = PaladinPrivacyManager()
        assert mgr.get_balance("nobody") == 0

    # ---- Transfer operations ----

    def test_create_private_transfer(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 1000)
        transfer = mgr.create_private_transfer("alice", "bob", 500)
        assert transfer.sender == "alice"
        assert transfer.receiver == "bob"
        assert transfer.amount == 500
        assert transfer.is_pending is True
        assert len(transfer.inputs) >= 1
        assert len(transfer.outputs) >= 1

    def test_create_transfer_with_change(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 1000)
        transfer = mgr.create_private_transfer("alice", "bob", 300)
        # Should have 2 outputs: 300 to bob + 700 change to alice
        assert len(transfer.outputs) == 2

    def test_create_transfer_exact_amount(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 500)
        transfer = mgr.create_private_transfer("alice", "bob", 500)
        # No change needed
        assert len(transfer.outputs) == 1

    def test_create_transfer_multiple_inputs(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 100)
        mgr.create_utxo("alice", 200)
        mgr.create_utxo("alice", 300)
        transfer = mgr.create_private_transfer("alice", "bob", 500)
        # Should select enough UTXOs to cover 500
        assert len(transfer.inputs) >= 2

    def test_create_transfer_insufficient_balance(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 100)
        with pytest.raises(ValueError, match="Insufficient balance"):
            mgr.create_private_transfer("alice", "bob", 500)

    def test_create_transfer_custom_privacy_level(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 1000)
        transfer = mgr.create_private_transfer(
            "alice", "bob", 500,
            privacy_level=PrivacyLevel.CONFIDENTIAL,
        )
        assert transfer.privacy_level == PrivacyLevel.CONFIDENTIAL

    def test_validate_transfer_approve(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 1000)
        transfer = mgr.create_private_transfer("alice", "bob", 500)

        validation = mgr.validate_transfer(
            transfer.transfer_id, "notary_1", NotaryDecision.APPROVE,
        )

        assert isinstance(validation, NotaryValidation)
        assert validation.decision == NotaryDecision.APPROVE
        assert transfer.is_approved is True

        # Inputs should be SPENT
        for utxo_id in transfer.inputs:
            utxo = mgr.get_utxo(utxo_id)
            assert utxo.state == UTXOState.SPENT
            assert utxo.spent_at is not None

        # Outputs should be UNSPENT (available)
        for utxo_id in transfer.outputs:
            utxo = mgr.get_utxo(utxo_id)
            assert utxo.state == UTXOState.UNSPENT

    def test_validate_transfer_approve_updates_balance(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 1000)
        transfer = mgr.create_private_transfer("alice", "bob", 400)
        mgr.validate_transfer(
            transfer.transfer_id, "notary_1", NotaryDecision.APPROVE,
        )
        assert mgr.get_balance("bob", "USDC") == 400
        assert mgr.get_balance("alice", "USDC") == 600  # change

    def test_validate_transfer_reject(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 1000)
        transfer = mgr.create_private_transfer("alice", "bob", 500)

        validation = mgr.validate_transfer(
            transfer.transfer_id, "notary_1", NotaryDecision.REJECT, "Policy violation",
        )

        assert validation.decision == NotaryDecision.REJECT
        assert validation.reason == "Policy violation"
        assert transfer.is_approved is False
        assert transfer.is_pending is False

        # Inputs should be restored to UNSPENT
        for utxo_id in transfer.inputs:
            utxo = mgr.get_utxo(utxo_id)
            assert utxo.state == UTXOState.UNSPENT

        # Outputs should be SPENT (invalidated)
        for utxo_id in transfer.outputs:
            utxo = mgr.get_utxo(utxo_id)
            assert utxo.state == UTXOState.SPENT

    def test_validate_transfer_reject_restores_balance(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 1000)
        transfer = mgr.create_private_transfer("alice", "bob", 500)
        mgr.validate_transfer(
            transfer.transfer_id, "notary_1", NotaryDecision.REJECT,
        )
        # Alice's balance should be fully restored
        assert mgr.get_balance("alice", "USDC") == 1000
        assert mgr.get_balance("bob", "USDC") == 0

    def test_validate_transfer_not_found(self):
        mgr = PaladinPrivacyManager()
        with pytest.raises(ValueError, match="Transfer not found"):
            mgr.validate_transfer("fake", "notary", NotaryDecision.APPROVE)

    def test_validate_transfer_already_decided(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 1000)
        transfer = mgr.create_private_transfer("alice", "bob", 500)
        mgr.validate_transfer(
            transfer.transfer_id, "notary_1", NotaryDecision.APPROVE,
        )
        with pytest.raises(ValueError, match="already decided"):
            mgr.validate_transfer(
                transfer.transfer_id, "notary_1", NotaryDecision.REJECT,
            )

    def test_get_transfer(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 1000)
        transfer = mgr.create_private_transfer("alice", "bob", 500)
        found = mgr.get_transfer(transfer.transfer_id)
        assert found is transfer

    def test_get_transfer_not_found(self):
        mgr = PaladinPrivacyManager()
        assert mgr.get_transfer("nonexistent") is None

    # ---- Privacy groups ----

    def test_create_privacy_group(self):
        mgr = PaladinPrivacyManager()
        group = mgr.create_privacy_group("Agents", ["alice", "bob"])
        assert group.name == "Agents"
        assert group.member_count == 2
        assert group.is_active is True
        assert group.group_id.startswith("grp_")

    def test_create_privacy_group_custom_policy(self):
        mgr = PaladinPrivacyManager()
        group = mgr.create_privacy_group(
            "Custom", ["alice"], endorsement_policy="majority",
        )
        assert group.endorsement_policy == "majority"

    def test_get_privacy_group(self):
        mgr = PaladinPrivacyManager()
        group = mgr.create_privacy_group("Test", ["alice"])
        found = mgr.get_privacy_group(group.group_id)
        assert found is group

    def test_get_privacy_group_not_found(self):
        mgr = PaladinPrivacyManager()
        assert mgr.get_privacy_group("nonexistent") is None

    def test_dissolve_privacy_group(self):
        mgr = PaladinPrivacyManager()
        group = mgr.create_privacy_group("Test", ["alice"])
        mgr.dissolve_privacy_group(group.group_id)
        assert group.status == PrivacyGroupStatus.DISSOLVED
        assert group.is_active is False

    def test_dissolve_privacy_group_not_found(self):
        mgr = PaladinPrivacyManager()
        with pytest.raises(ValueError, match="not found"):
            mgr.dissolve_privacy_group("fake")

    # ---- Properties ----

    def test_total_utxos(self):
        mgr = PaladinPrivacyManager()
        assert mgr.total_utxos == 0
        mgr.create_utxo("alice", 100)
        mgr.create_utxo("bob", 200)
        assert mgr.total_utxos == 2

    def test_total_transfers(self):
        mgr = PaladinPrivacyManager()
        assert mgr.total_transfers == 0
        mgr.create_utxo("alice", 1000)
        mgr.create_private_transfer("alice", "bob", 100)
        assert mgr.total_transfers == 1

    def test_total_utxos_includes_outputs(self):
        mgr = PaladinPrivacyManager()
        mgr.create_utxo("alice", 1000)
        mgr.create_private_transfer("alice", "bob", 300)
        # 1 input + 2 outputs (receiver + change)
        assert mgr.total_utxos == 3

    def test_active_groups(self):
        mgr = PaladinPrivacyManager()
        assert mgr.active_groups == 0
        mgr.create_privacy_group("G1", ["alice"])
        mgr.create_privacy_group("G2", ["bob"])
        assert mgr.active_groups == 2
        mgr.dissolve_privacy_group(
            list(mgr._groups.keys())[0],
        )
        assert mgr.active_groups == 1


# ============ Notary Validation Tests ============


class TestNotaryValidation:
    def test_creation(self):
        validation = NotaryValidation(
            transfer_id="txfr_1",
            notary="notary_1",
            decision=NotaryDecision.APPROVE,
            reason="All checks passed",
        )
        assert validation.transfer_id == "txfr_1"
        assert validation.notary == "notary_1"
        assert validation.decision == NotaryDecision.APPROVE
        assert validation.reason == "All checks passed"
        assert isinstance(validation.validated_at, datetime)

    def test_default_reason(self):
        validation = NotaryValidation(
            transfer_id="t1",
            notary="n1",
            decision=NotaryDecision.REJECT,
        )
        assert validation.reason == ""


# ============ ZK Proof Request Tests ============


class TestZKProofRequest:
    def test_creation(self):
        req = ZKProofRequest(
            proof_id="proof_1",
            prover="alice",
            statement="balance >= 1000",
        )
        assert req.proof_id == "proof_1"
        assert req.prover == "alice"
        assert req.statement == "balance >= 1000"
        assert req.domain == PrivacyDomain.ZETO


# ============ Calldata Tests ============


class TestCalldata:
    def test_notarized_transfer_calldata(self):
        calldata = build_notarized_transfer_calldata(
            sender="0xAlice",
            receiver="0xBob",
            amount=1000,
            notary_signature=b"\x01" * 65,
        )
        assert len(calldata) > 4
        assert calldata[:4] == bytes.fromhex("a1b2c3d4")

    def test_notarized_transfer_calldata_structure(self):
        calldata = build_notarized_transfer_calldata(
            sender="0xAlice",
            receiver="0xBob",
            amount=500,
            notary_signature=b"\xab" * 32,
        )
        # selector(4) + sender(32) + receiver(32) + amount(32) + sig_len(32) + sig(32)
        assert len(calldata) == 4 + 32 + 32 + 32 + 32 + 32

    def test_create_privacy_group_calldata(self):
        calldata = build_create_privacy_group_calldata(
            group_id="grp_1",
            members=["alice", "bob", "charlie"],
        )
        assert len(calldata) > 4
        assert calldata[:4] == bytes.fromhex("b2c3d4e5")

    def test_create_privacy_group_calldata_structure(self):
        calldata = build_create_privacy_group_calldata(
            group_id="grp_1",
            members=["alice", "bob"],
        )
        # selector(4) + group_id(32) + count(32) + 2*member(32)
        assert len(calldata) == 4 + 32 + 32 + 2 * 32


# ============ Enum Tests ============


class TestEnums:
    def test_privacy_domain_values(self):
        assert PrivacyDomain.NOTO.value == "noto"
        assert PrivacyDomain.ZETO.value == "zeto"
        assert PrivacyDomain.PENTE.value == "pente"
        assert PrivacyDomain.CUSTOM.value == "custom"
        assert len(PrivacyDomain) == 4

    def test_privacy_level_values(self):
        assert PrivacyLevel.PUBLIC.value == "public"
        assert PrivacyLevel.PRIVATE.value == "private"
        assert PrivacyLevel.CONFIDENTIAL.value == "confidential"
        assert PrivacyLevel.ANONYMOUS.value == "anonymous"
        assert len(PrivacyLevel) == 4

    def test_notary_decision_values(self):
        assert NotaryDecision.APPROVE.value == "approve"
        assert NotaryDecision.REJECT.value == "reject"
        assert NotaryDecision.PENDING.value == "pending"
        assert len(NotaryDecision) == 3

    def test_utxo_state_values(self):
        assert UTXOState.UNSPENT.value == "unspent"
        assert UTXOState.SPENT.value == "spent"
        assert UTXOState.LOCKED.value == "locked"
        assert len(UTXOState) == 3

    def test_privacy_group_status_values(self):
        assert PrivacyGroupStatus.ACTIVE.value == "active"
        assert PrivacyGroupStatus.SUSPENDED.value == "suspended"
        assert PrivacyGroupStatus.DISSOLVED.value == "dissolved"
        assert len(PrivacyGroupStatus) == 3


# ============ Constants Tests ============


class TestConstants:
    def test_paladin_version(self):
        assert PALADIN_VERSION == "0.1.0"

    def test_default_endorsement_policy(self):
        assert DEFAULT_ENDORSEMENT_POLICY == "all"

    def test_supported_tokens(self):
        assert SUPPORTED_PRIVACY_TOKENS == frozenset({"USDC", "EURC", "USDT"})
        assert "USDC" in SUPPORTED_PRIVACY_TOKENS
        assert "EURC" in SUPPORTED_PRIVACY_TOKENS
        assert "USDT" in SUPPORTED_PRIVACY_TOKENS

    def test_max_utxo_inputs(self):
        assert MAX_UTXO_INPUTS == 10


# ============ Factory Tests ============


class TestFactory:
    def test_create_privacy_manager(self):
        mgr = create_privacy_manager()
        assert isinstance(mgr, PaladinPrivacyManager)
        assert mgr._config.domain == PrivacyDomain.NOTO

    def test_create_privacy_manager_custom(self):
        mgr = create_privacy_manager(
            domain=PrivacyDomain.ZETO,
            notary_address="0xNotary",
            privacy_level=PrivacyLevel.ANONYMOUS,
        )
        assert mgr._config.domain == PrivacyDomain.ZETO
        assert mgr._config.notary_address == "0xNotary"
        assert mgr._config.privacy_level == PrivacyLevel.ANONYMOUS

    def test_create_privacy_manager_default_config(self):
        mgr = create_privacy_manager()
        assert mgr._config.require_endorsement is True
        assert mgr._config.privacy_level == PrivacyLevel.PRIVATE


# ============ Privacy Config Tests ============


class TestPrivacyConfig:
    def test_defaults(self):
        config = PrivacyConfig()
        assert config.domain == PrivacyDomain.NOTO
        assert config.notary_address == ""
        assert config.privacy_level == PrivacyLevel.PRIVATE
        assert config.require_endorsement is True

    def test_custom(self):
        config = PrivacyConfig(
            domain=PrivacyDomain.PENTE,
            notary_address="0xNotary",
            privacy_level=PrivacyLevel.CONFIDENTIAL,
            require_endorsement=False,
        )
        assert config.domain == PrivacyDomain.PENTE
        assert config.require_endorsement is False


# ============ Module Export Tests ============


class TestModuleExports:
    def test_imports_from_protocol(self):
        from sardis_protocol import (
            NotaryDecision,
            NotaryValidation,
            PaladinPrivacyManager,
            PrivacyConfig,
            PrivacyDomain,
            PrivacyGroup,
            PrivacyLevel,
            PrivateTransfer,
            UTXO,
            UTXOState,
            create_privacy_manager,
        )
        assert all([
            PaladinPrivacyManager, PrivacyDomain, PrivacyLevel,
            PrivacyGroup, PrivateTransfer, UTXO, UTXOState,
            NotaryDecision, NotaryValidation, PrivacyConfig,
            create_privacy_manager,
        ])
