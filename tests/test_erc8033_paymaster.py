"""Tests for ERC-8033 Paymaster Protocol.

Covers issue #151. Tests gas session management, transaction processing,
sponsorship, gas estimation, calldata builders, and statistics.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sardis_protocol.erc8033 import (
    DEFAULT_GAS_LIMIT,
    DEFAULT_MAX_TX_COUNT,
    DEFAULT_SESSION_HOURS,
    ERC8033_VERSION,
    ETH_USD_ESTIMATE,
    GAS_PRICE_MAP,
    SPONSORSHIP_TIERS,
    GasEstimate,
    GasPolicy,
    GasSession,
    PaymasterConfig,
    PaymasterManager,
    PaymasterStats,
    PaymasterTransaction,
    PaymasterType,
    SessionStatus,
    SponsorshipRecord,
    SponsorshipTier,
    build_create_session_calldata,
    build_revoke_session_calldata,
    build_sponsor_calldata,
    create_paymaster_manager,
    estimate_tx_cost,
)


# ============ GasSession Tests ============


class TestGasSession:
    def test_creation(self):
        now = datetime.now(UTC)
        session = GasSession(
            session_id="sess001",
            agent_id="agent_1",
            paymaster="0xPaymaster",
            gas_limit=1_000_000,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        assert session.session_id == "sess001"
        assert session.agent_id == "agent_1"
        assert session.gas_used == 0
        assert session.tx_count == 0
        assert session.status == SessionStatus.ACTIVE

    def test_remaining_gas(self):
        now = datetime.now(UTC)
        session = GasSession(
            session_id="sess002",
            agent_id="agent_1",
            paymaster="0xPM",
            gas_limit=500_000,
            gas_used=200_000,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        assert session.remaining_gas == 300_000

    def test_remaining_gas_never_negative(self):
        now = datetime.now(UTC)
        session = GasSession(
            session_id="sess003",
            agent_id="agent_1",
            paymaster="0xPM",
            gas_limit=100,
            gas_used=200,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        assert session.remaining_gas == 0

    def test_is_active(self):
        now = datetime.now(UTC)
        session = GasSession(
            session_id="sess004",
            agent_id="agent_1",
            paymaster="0xPM",
            gas_limit=1_000_000,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        assert session.is_active is True

    def test_is_expired(self):
        now = datetime.now(UTC)
        session = GasSession(
            session_id="sess005",
            agent_id="agent_1",
            paymaster="0xPM",
            gas_limit=1_000_000,
            created_at=now - timedelta(hours=48),
            expires_at=now - timedelta(hours=1),
        )
        assert session.is_expired is True
        assert session.is_active is False

    def test_is_exhausted_by_gas(self):
        now = datetime.now(UTC)
        session = GasSession(
            session_id="sess006",
            agent_id="agent_1",
            paymaster="0xPM",
            gas_limit=1000,
            gas_used=1000,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        assert session.is_exhausted is True
        assert session.is_active is False

    def test_is_exhausted_by_tx_count(self):
        now = datetime.now(UTC)
        session = GasSession(
            session_id="sess007",
            agent_id="agent_1",
            paymaster="0xPM",
            gas_limit=1_000_000,
            tx_count=100,
            max_tx_count=100,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        assert session.is_exhausted is True
        assert session.is_active is False

    def test_utilization_pct(self):
        now = datetime.now(UTC)
        session = GasSession(
            session_id="sess008",
            agent_id="agent_1",
            paymaster="0xPM",
            gas_limit=1_000_000,
            gas_used=250_000,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        assert session.utilization_pct == 25.0

    def test_utilization_pct_zero_limit(self):
        now = datetime.now(UTC)
        session = GasSession(
            session_id="sess009",
            agent_id="agent_1",
            paymaster="0xPM",
            gas_limit=0,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        assert session.utilization_pct == 0.0


# ============ SponsorshipRecord Tests ============


class TestSponsorshipRecord:
    def test_creation(self):
        record = SponsorshipRecord(
            record_id="sp001",
            sponsor="0xSponsor",
            beneficiary="0xAgent",
            tier=SponsorshipTier.BASIC,
            gas_deposited=1_000_000,
        )
        assert record.sponsor == "0xSponsor"
        assert record.gas_consumed == 0
        assert record.tier == SponsorshipTier.BASIC

    def test_remaining_deposit(self):
        record = SponsorshipRecord(
            record_id="sp002",
            sponsor="0xSponsor",
            beneficiary="0xAgent",
            tier=SponsorshipTier.PREMIUM,
            gas_deposited=1_000_000,
            gas_consumed=400_000,
        )
        assert record.remaining_deposit == 600_000

    def test_is_active(self):
        record = SponsorshipRecord(
            record_id="sp003",
            sponsor="0xSponsor",
            beneficiary="0xAgent",
            tier=SponsorshipTier.FREE,
            gas_deposited=100_000,
        )
        assert record.is_active is True

    def test_is_active_exhausted(self):
        record = SponsorshipRecord(
            record_id="sp004",
            sponsor="0xSponsor",
            beneficiary="0xAgent",
            tier=SponsorshipTier.FREE,
            gas_deposited=100_000,
            gas_consumed=100_000,
        )
        assert record.is_active is False

    def test_is_active_expired(self):
        record = SponsorshipRecord(
            record_id="sp005",
            sponsor="0xSponsor",
            beneficiary="0xAgent",
            tier=SponsorshipTier.BASIC,
            gas_deposited=1_000_000,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert record.is_active is False


# ============ GasEstimate Tests ============


class TestGasEstimate:
    def test_creation(self):
        estimate = GasEstimate(
            chain="base",
            estimated_gas=100_000,
            gas_price_gwei=0.001,
            cost_usd=0.0003,
            paymaster_covers=True,
        )
        assert estimate.chain == "base"
        assert estimate.estimated_gas == 100_000
        assert estimate.gas_price_gwei == 0.001
        assert estimate.cost_usd == 0.0003
        assert estimate.paymaster_covers is True
        assert estimate.user_pays_usd == 0.0

    def test_user_pays(self):
        estimate = GasEstimate(
            chain="ethereum",
            estimated_gas=21_000,
            gas_price_gwei=30.0,
            cost_usd=1.89,
            paymaster_covers=False,
            user_pays_usd=1.89,
        )
        assert estimate.user_pays_usd == 1.89
        assert estimate.paymaster_covers is False


# ============ PaymasterTransaction Tests ============


class TestPaymasterTransaction:
    def test_creation(self):
        tx = PaymasterTransaction(
            tx_id="tx001",
            session_id="sess001",
            agent_id="agent_1",
            gas_used=21_000,
            gas_price_gwei=0.001,
            target="0xTarget",
        )
        assert tx.tx_id == "tx001"
        assert tx.gas_used == 21_000
        assert tx.sponsored is True
        assert tx.value == 0

    def test_sponsored_flag(self):
        tx = PaymasterTransaction(
            tx_id="tx002",
            session_id="sess001",
            agent_id="agent_1",
            gas_used=21_000,
            gas_price_gwei=30.0,
            target="0xTarget",
            sponsored=False,
        )
        assert tx.sponsored is False


# ============ PaymasterManager Tests ============


class TestPaymasterManager:
    # --- Session Tests ---

    def test_create_session(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1", gas_limit=500_000)
        assert session.agent_id == "agent_1"
        assert session.gas_limit == 500_000
        assert session.status == SessionStatus.ACTIVE
        assert session.is_active is True
        assert len(session.session_id) == 16

    def test_get_session(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1")
        retrieved = mgr.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_get_session_not_found(self):
        mgr = PaymasterManager()
        assert mgr.get_session("nonexistent") is None

    def test_get_sessions_for_agent(self):
        mgr = PaymasterManager()
        mgr.create_session("agent_1")
        mgr.create_session("agent_1")
        mgr.create_session("agent_2")
        sessions = mgr.get_sessions_for_agent("agent_1")
        assert len(sessions) == 2
        assert all(s.agent_id == "agent_1" for s in sessions)

    def test_revoke_session(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1")
        mgr.revoke_session(session.session_id)
        assert session.status == SessionStatus.REVOKED
        assert session.is_active is False

    def test_revoke_session_not_found(self):
        mgr = PaymasterManager()
        with pytest.raises(ValueError, match="not found"):
            mgr.revoke_session("nonexistent")

    def test_refresh_session_add_gas(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1", gas_limit=500_000)
        refreshed = mgr.refresh_session(session.session_id, additional_gas=200_000)
        assert refreshed.gas_limit == 700_000

    def test_refresh_session_extend_hours(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1", expires_in_hours=12)
        original_expiry = session.expires_at
        refreshed = mgr.refresh_session(session.session_id, extend_hours=12)
        assert refreshed.expires_at > original_expiry
        # Should be roughly 12 hours later
        delta = refreshed.expires_at - original_expiry
        assert abs(delta.total_seconds() - 12 * 3600) < 2

    def test_refresh_session_not_found(self):
        mgr = PaymasterManager()
        with pytest.raises(ValueError, match="not found"):
            mgr.refresh_session("nonexistent")

    def test_refresh_session_not_active(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1")
        mgr.revoke_session(session.session_id)
        with pytest.raises(ValueError, match="not active"):
            mgr.refresh_session(session.session_id, additional_gas=100)

    # --- Transaction Tests ---

    def test_process_transaction(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1", gas_limit=500_000)
        tx = mgr.process_transaction(
            session_id=session.session_id,
            gas_used=21_000,
            gas_price_gwei=0.001,
            target="0xTarget",
        )
        assert tx.gas_used == 21_000
        assert tx.agent_id == "agent_1"
        assert session.gas_used == 21_000
        assert session.tx_count == 1

    def test_process_transaction_deducts_gas(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1", gas_limit=100_000)
        mgr.process_transaction(session.session_id, 30_000, 0.001, "0xA")
        mgr.process_transaction(session.session_id, 20_000, 0.001, "0xB")
        assert session.gas_used == 50_000
        assert session.remaining_gas == 50_000
        assert session.tx_count == 2

    def test_session_exhausted_by_gas(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1", gas_limit=50_000)
        mgr.process_transaction(session.session_id, 50_000, 0.001, "0xTarget")
        assert session.status == SessionStatus.EXHAUSTED
        assert session.is_active is False

    def test_session_exhausted_by_tx_count(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1", gas_limit=10_000_000, max_tx_count=3)
        mgr.process_transaction(session.session_id, 100, 0.001, "0xA")
        mgr.process_transaction(session.session_id, 100, 0.001, "0xB")
        mgr.process_transaction(session.session_id, 100, 0.001, "0xC")
        assert session.tx_count == 3
        assert session.status == SessionStatus.EXHAUSTED

    def test_process_transaction_inactive_session(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1")
        mgr.revoke_session(session.session_id)
        with pytest.raises(ValueError, match="not active"):
            mgr.process_transaction(session.session_id, 100, 0.001, "0xA")

    def test_process_transaction_insufficient_gas(self):
        mgr = PaymasterManager()
        session = mgr.create_session("agent_1", gas_limit=1000)
        with pytest.raises(ValueError, match="Insufficient gas"):
            mgr.process_transaction(session.session_id, 5000, 0.001, "0xA")

    # --- Gas Estimation Tests ---

    def test_estimate_gas_base(self):
        mgr = PaymasterManager()
        estimate = mgr.estimate_gas("base", 100_000)
        assert estimate.chain == "base"
        assert estimate.gas_price_gwei == 0.001
        # cost = 100_000 * 0.001 * 1e-9 * 3000 = 0.0003
        assert abs(estimate.cost_usd - 0.0003) < 1e-10
        assert estimate.paymaster_covers is True
        assert estimate.user_pays_usd == 0.0

    def test_estimate_gas_ethereum(self):
        mgr = PaymasterManager()
        estimate = mgr.estimate_gas("ethereum", 21_000)
        assert estimate.gas_price_gwei == 30.0
        # cost = 21_000 * 30.0 * 1e-9 * 3000 = 1.89
        assert abs(estimate.cost_usd - 1.89) < 1e-10

    def test_estimate_gas_unknown_chain(self):
        mgr = PaymasterManager()
        estimate = mgr.estimate_gas("unknown_chain", 100_000)
        # Default gas price of 1.0 gwei
        assert estimate.gas_price_gwei == 1.0
        # cost = 100_000 * 1.0 * 1e-9 * 3000 = 0.3
        assert abs(estimate.cost_usd - 0.3) < 1e-10

    # --- Sponsorship Tests ---

    def test_create_sponsorship(self):
        mgr = PaymasterManager()
        record = mgr.create_sponsorship(
            sponsor="0xSponsor",
            beneficiary="0xAgent",
            tier=SponsorshipTier.BASIC,
            gas_amount=1_000_000,
        )
        assert record.sponsor == "0xSponsor"
        assert record.beneficiary == "0xAgent"
        assert record.gas_deposited == 1_000_000
        assert record.is_active is True

    def test_get_sponsorship(self):
        mgr = PaymasterManager()
        record = mgr.create_sponsorship(
            "0xSponsor", "0xAgent", SponsorshipTier.FREE, 100_000,
        )
        retrieved = mgr.get_sponsorship(record.record_id)
        assert retrieved is not None
        assert retrieved.record_id == record.record_id

    def test_get_sponsorship_not_found(self):
        mgr = PaymasterManager()
        assert mgr.get_sponsorship("nonexistent") is None

    def test_consume_sponsorship(self):
        mgr = PaymasterManager()
        record = mgr.create_sponsorship(
            "0xSponsor", "0xAgent", SponsorshipTier.BASIC, 1_000_000,
        )
        updated = mgr.consume_sponsorship(record.record_id, 300_000)
        assert updated.gas_consumed == 300_000
        assert updated.remaining_deposit == 700_000

    def test_consume_sponsorship_insufficient(self):
        mgr = PaymasterManager()
        record = mgr.create_sponsorship(
            "0xSponsor", "0xAgent", SponsorshipTier.FREE, 100_000,
        )
        with pytest.raises(ValueError, match="Insufficient sponsorship"):
            mgr.consume_sponsorship(record.record_id, 200_000)

    def test_consume_sponsorship_expired(self):
        mgr = PaymasterManager()
        record = mgr.create_sponsorship(
            "0xSponsor", "0xAgent", SponsorshipTier.BASIC, 1_000_000,
            expires_in_hours=0,
        )
        # Force expiry by setting expires_at in the past
        record.expires_at = datetime.now(UTC) - timedelta(hours=1)
        with pytest.raises(ValueError, match="not active"):
            mgr.consume_sponsorship(record.record_id, 100)

    # --- Stats Tests ---

    def test_get_stats(self):
        mgr = PaymasterManager()
        s1 = mgr.create_session("agent_1", gas_limit=100_000)
        s2 = mgr.create_session("agent_2", gas_limit=200_000)
        mgr.create_session("agent_1", gas_limit=50_000)

        mgr.process_transaction(s1.session_id, 10_000, 0.001, "0xA")
        mgr.process_transaction(s2.session_id, 20_000, 0.001, "0xB")

        stats = mgr.get_stats()
        assert isinstance(stats, PaymasterStats)
        assert stats.total_sessions == 3
        assert stats.active_sessions == 3
        assert stats.total_gas_sponsored == 30_000
        assert stats.total_transactions == 2
        assert stats.unique_agents == 2
        assert stats.gas_savings_usd > 0

    # --- Property Tests ---

    def test_total_sessions_property(self):
        mgr = PaymasterManager()
        assert mgr.total_sessions == 0
        mgr.create_session("agent_1")
        mgr.create_session("agent_2")
        assert mgr.total_sessions == 2

    def test_active_sessions_property(self):
        mgr = PaymasterManager()
        s1 = mgr.create_session("agent_1")
        mgr.create_session("agent_2")
        assert mgr.active_sessions == 2
        mgr.revoke_session(s1.session_id)
        assert mgr.active_sessions == 1

    def test_total_gas_sponsored_property(self):
        mgr = PaymasterManager()
        assert mgr.total_gas_sponsored == 0
        s = mgr.create_session("agent_1", gas_limit=500_000)
        mgr.process_transaction(s.session_id, 10_000, 0.001, "0xA")
        mgr.process_transaction(s.session_id, 15_000, 0.001, "0xB")
        assert mgr.total_gas_sponsored == 25_000


# ============ Calldata Tests ============


class TestCalldata:
    def test_create_session_calldata(self):
        cd = build_create_session_calldata("0xAgent", 1_000_000, 1700000000)
        assert len(cd) > 4
        assert cd[:4] == bytes.fromhex("a1b2c3d4")

    def test_sponsor_calldata(self):
        cd = build_sponsor_calldata("0xBeneficiary", 5_000_000)
        assert len(cd) > 4
        assert cd[:4] == bytes.fromhex("b2c3d4e5")

    def test_revoke_session_calldata(self):
        session_hash = b"\x01" * 32
        cd = build_revoke_session_calldata(session_hash)
        assert len(cd) == 36  # 4 selector + 32 bytes
        assert cd[:4] == bytes.fromhex("c3d4e5f6")


# ============ Enum Tests ============


class TestEnums:
    def test_paymaster_type(self):
        assert len(PaymasterType) == 4
        assert PaymasterType.VERIFYING.value == "verifying"
        assert PaymasterType.DEPOSITOR.value == "depositor"
        assert PaymasterType.TOKEN.value == "token"
        assert PaymasterType.SPONSORED.value == "sponsored"

    def test_session_status(self):
        assert len(SessionStatus) == 4
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.EXPIRED.value == "expired"
        assert SessionStatus.REVOKED.value == "revoked"
        assert SessionStatus.EXHAUSTED.value == "exhausted"

    def test_sponsorship_tier(self):
        assert len(SponsorshipTier) == 4
        assert SponsorshipTier.FREE.value == "free"
        assert SponsorshipTier.BASIC.value == "basic"
        assert SponsorshipTier.PREMIUM.value == "premium"
        assert SponsorshipTier.ENTERPRISE.value == "enterprise"

    def test_gas_policy(self):
        assert len(GasPolicy) == 4
        assert GasPolicy.SPONSOR_ALL.value == "sponsor_all"
        assert GasPolicy.USER_PAYS.value == "user_pays"
        assert GasPolicy.SPLIT.value == "split"
        assert GasPolicy.PREPAID.value == "prepaid"


# ============ Constants Tests ============


class TestConstants:
    def test_version(self):
        assert ERC8033_VERSION == "0.1.0"

    def test_default_session_hours(self):
        assert DEFAULT_SESSION_HOURS == 24

    def test_default_gas_limit(self):
        assert DEFAULT_GAS_LIMIT == 1_000_000

    def test_default_max_tx_count(self):
        assert DEFAULT_MAX_TX_COUNT == 100

    def test_gas_price_map(self):
        assert GAS_PRICE_MAP["base"] == 0.001
        assert GAS_PRICE_MAP["ethereum"] == 30.0
        assert GAS_PRICE_MAP["polygon"] == 30.0
        assert GAS_PRICE_MAP["arbitrum"] == 0.1
        assert GAS_PRICE_MAP["optimism"] == 0.001
        assert len(GAS_PRICE_MAP) == 5

    def test_eth_usd_estimate(self):
        assert ETH_USD_ESTIMATE == 3000.0

    def test_sponsorship_tiers(self):
        assert SPONSORSHIP_TIERS["free"] == 100_000
        assert SPONSORSHIP_TIERS["basic"] == 1_000_000
        assert SPONSORSHIP_TIERS["premium"] == 10_000_000
        assert SPONSORSHIP_TIERS["enterprise"] == 100_000_000
        assert len(SPONSORSHIP_TIERS) == 4


# ============ Factory Tests ============


class TestFactory:
    def test_create_paymaster_manager(self):
        mgr = create_paymaster_manager()
        assert isinstance(mgr, PaymasterManager)

    def test_create_with_args(self):
        mgr = create_paymaster_manager(
            paymaster_address="0xPaymaster",
            chain="polygon",
            gas_policy=GasPolicy.USER_PAYS,
        )
        assert isinstance(mgr, PaymasterManager)
        assert mgr._config.paymaster_address == "0xPaymaster"
        assert mgr._config.chain == "polygon"
        assert mgr._config.gas_policy == GasPolicy.USER_PAYS


# ============ estimate_tx_cost Tests ============


class TestEstimateTxCost:
    def test_base_chain(self):
        cost = estimate_tx_cost("base", 100_000)
        # 100_000 * 0.001 * 1e-9 * 3000 = 0.0003
        assert abs(cost - 0.0003) < 1e-10

    def test_ethereum_chain(self):
        cost = estimate_tx_cost("ethereum", 21_000)
        # 21_000 * 30.0 * 1e-9 * 3000 = 1.89
        assert abs(cost - 1.89) < 1e-10

    def test_unknown_chain(self):
        cost = estimate_tx_cost("unknown", 100_000)
        # 100_000 * 1.0 * 1e-9 * 3000 = 0.3
        assert abs(cost - 0.3) < 1e-10


# ============ Module Export Tests ============


class TestModuleExports:
    def test_imports_from_protocol(self):
        from sardis_protocol import (
            GasEstimate,
            GasPolicy,
            GasSession,
            PaymasterConfig,
            PaymasterManager,
            PaymasterStats,
            PaymasterTransaction,
            PaymasterType,
            SessionStatus,
            SponsorshipRecord,
            SponsorshipTier,
            create_paymaster_manager,
            estimate_tx_cost,
        )
        assert all([
            PaymasterManager, PaymasterConfig, GasSession,
            SessionStatus, PaymasterType, GasPolicy,
            SponsorshipTier, SponsorshipRecord, GasEstimate,
            PaymasterTransaction, PaymasterStats,
            create_paymaster_manager, estimate_tx_cost,
        ])
