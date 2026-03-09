"""Tests for settlement tracking and reconciliation."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sardis_v2_core.settlement import (
    InMemorySettlementStore,
    SettlementMode,
    SettlementReconciler,
    SettlementRecord,
    SettlementStatus,
)


def _make_record(
    mode: SettlementMode = SettlementMode.NATIVE_CRYPTO,
    status: SettlementStatus = SettlementStatus.INITIATED,
    **kwargs,
) -> SettlementRecord:
    defaults = {
        "intent_id": "int_test123",
        "receipt_id": "rcpt_test",
        "mode": mode,
        "status": status,
        "amount": Decimal("100"),
        "currency": "USDC",
        "fee": Decimal("0.50"),
        "network_reference": "0xabc123",
    }
    defaults.update(kwargs)
    return SettlementRecord(**defaults)


class TestSettlementRecord:

    def test_create_crypto_settlement(self):
        rec = _make_record(mode=SettlementMode.NATIVE_CRYPTO)
        assert rec.settlement_id.startswith("stl_")
        assert rec.mode == SettlementMode.NATIVE_CRYPTO
        assert rec.status == SettlementStatus.INITIATED

    def test_create_delegated_card_settlement(self):
        rec = _make_record(
            mode=SettlementMode.DELEGATED_CARD,
            credential_id="dcred_test",
            authorization_status="authorized",
        )
        assert rec.mode == SettlementMode.DELEGATED_CARD
        assert rec.credential_id == "dcred_test"
        assert rec.authorization_status == "authorized"

    def test_create_offramp_settlement(self):
        rec = _make_record(mode=SettlementMode.OFFRAMP)
        assert rec.mode == SettlementMode.OFFRAMP

    def test_to_dict(self):
        rec = _make_record()
        d = rec.to_dict()
        assert d["mode"] == "native_crypto"
        assert d["amount"] == "100"
        assert d["fee"] == "0.50"

    def test_dispute_status_tracking(self):
        rec = _make_record(
            mode=SettlementMode.DELEGATED_CARD,
            dispute_status="opened",
            reversal_reference="rev_123",
            liability_party="merchant",
        )
        assert rec.dispute_status == "opened"
        assert rec.reversal_reference == "rev_123"
        assert rec.liability_party == "merchant"


class TestInMemorySettlementStore:

    @pytest.fixture
    def store(self):
        return InMemorySettlementStore()

    @pytest.mark.asyncio
    async def test_create_and_get(self, store):
        rec = _make_record()
        sid = await store.create(rec)
        retrieved = await store.get(sid)
        assert retrieved is not None
        assert retrieved.intent_id == "int_test123"

    @pytest.mark.asyncio
    async def test_get_by_intent(self, store):
        rec = _make_record(intent_id="int_xyz")
        await store.create(rec)
        result = await store.get_by_intent("int_xyz")
        assert result is not None
        assert result.settlement_id == rec.settlement_id

    @pytest.mark.asyncio
    async def test_status_transitions(self, store):
        """initiated -> pending_confirmation -> confirmed -> settled"""
        rec = _make_record()
        await store.create(rec)

        await store.update_status(rec.settlement_id, SettlementStatus.PENDING_CONFIRMATION)
        r = await store.get(rec.settlement_id)
        assert r.status == SettlementStatus.PENDING_CONFIRMATION

        await store.update_status(rec.settlement_id, SettlementStatus.CONFIRMED)
        r = await store.get(rec.settlement_id)
        assert r.status == SettlementStatus.CONFIRMED
        assert r.confirmed_at is not None

        await store.update_status(rec.settlement_id, SettlementStatus.SETTLED)
        r = await store.get(rec.settlement_id)
        assert r.status == SettlementStatus.SETTLED
        assert r.settled_at is not None

    @pytest.mark.asyncio
    async def test_failed_settlement_retry(self, store):
        rec = _make_record()
        await store.create(rec)

        await store.update_status(
            rec.settlement_id, SettlementStatus.FAILED,
            error="network timeout",
        )
        r = await store.get(rec.settlement_id)
        assert r.status == SettlementStatus.FAILED
        assert r.failed_at is not None
        assert r.last_error == "network timeout"
        assert r.retry_count == 1

        # Retry: reset to initiated
        await store.update_status(rec.settlement_id, SettlementStatus.INITIATED)
        r = await store.get(rec.settlement_id)
        assert r.status == SettlementStatus.INITIATED

    @pytest.mark.asyncio
    async def test_authorization_capture_lifecycle(self, store):
        """Card-aware: authorization -> capture -> settlement."""
        rec = _make_record(
            mode=SettlementMode.DELEGATED_CARD,
            authorization_status="authorized",
            capture_status="pending_capture",
        )
        await store.create(rec)

        # Simulate capture
        await store.update_status(
            rec.settlement_id, SettlementStatus.CONFIRMED,
            capture_status="captured",
            authorization_status="captured",
        )
        r = await store.get(rec.settlement_id)
        assert r.capture_status == "captured"
        assert r.authorization_status == "captured"

    @pytest.mark.asyncio
    async def test_get_pending(self, store):
        r1 = _make_record(status=SettlementStatus.INITIATED)
        r2 = _make_record(status=SettlementStatus.SETTLED)
        r3 = _make_record(status=SettlementStatus.PENDING_CONFIRMATION)
        await store.create(r1)
        await store.create(r2)
        await store.create(r3)
        pending = await store.get_pending()
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_summary(self, store):
        r1 = _make_record(mode=SettlementMode.NATIVE_CRYPTO, amount=Decimal("100"), fee=Decimal("0.50"))
        r2 = _make_record(mode=SettlementMode.NATIVE_CRYPTO, amount=Decimal("200"), fee=Decimal("1.00"))
        r3 = _make_record(mode=SettlementMode.DELEGATED_CARD, amount=Decimal("50"), fee=Decimal("1.25"))
        await store.create(r1)
        await store.create(r2)
        await store.create(r3)
        summary = await store.get_summary()
        assert summary["native_crypto"]["count"] == 2
        assert summary["native_crypto"]["total_amount"] == "300"
        assert summary["delegated_card"]["count"] == 1


class TestSettlementReconciler:

    @pytest.mark.asyncio
    async def test_reconcile_crypto(self):
        store = InMemorySettlementStore()
        rec = _make_record(
            mode=SettlementMode.NATIVE_CRYPTO,
            status=SettlementStatus.PENDING_CONFIRMATION,
        )
        await store.create(rec)
        reconciler = SettlementReconciler(store)
        await reconciler.reconcile_crypto(rec.settlement_id)
        r = await store.get(rec.settlement_id)
        assert r.status == SettlementStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_reconcile_delegated(self):
        store = InMemorySettlementStore()
        rec = _make_record(
            mode=SettlementMode.DELEGATED_CARD,
            status=SettlementStatus.PENDING_CONFIRMATION,
        )
        await store.create(rec)
        reconciler = SettlementReconciler(store)
        await reconciler.reconcile_delegated(rec.settlement_id)
        r = await store.get(rec.settlement_id)
        assert r.status == SettlementStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_reconcile_all_pending(self):
        store = InMemorySettlementStore()
        r1 = _make_record(
            mode=SettlementMode.NATIVE_CRYPTO,
            status=SettlementStatus.PENDING_CONFIRMATION,
        )
        r2 = _make_record(
            mode=SettlementMode.DELEGATED_CARD,
            status=SettlementStatus.PENDING_CONFIRMATION,
        )
        r3 = _make_record(
            mode=SettlementMode.NATIVE_CRYPTO,
            status=SettlementStatus.SETTLED,
        )
        await store.create(r1)
        await store.create(r2)
        await store.create(r3)
        reconciler = SettlementReconciler(store)
        count = await reconciler.reconcile_all_pending()
        assert count == 2
