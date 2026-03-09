"""Tests for merchant execution capability registry."""
from __future__ import annotations

import pytest
from sardis_v2_core.merchant_capability import (
    InMemoryMerchantCapabilityStore,
    MerchantExecutionCapability,
)


def _make_cap(**kwargs) -> MerchantExecutionCapability:
    defaults = {
        "merchant_id": "merch_test_001",
        "domain": "example.com",
        "accepts_native_crypto": False,
        "accepts_card": True,
        "supports_delegated_card": True,
        "supported_networks": ["stripe_spt"],
        "confidence": 0.8,
    }
    defaults.update(kwargs)
    return MerchantExecutionCapability(**defaults)


class TestMerchantExecutionCapability:

    def test_create(self):
        cap = _make_cap()
        assert cap.merchant_id == "merch_test_001"
        assert cap.domain == "example.com"
        assert cap.supports_delegated_card is True

    def test_supports_mode_native_crypto(self):
        cap = _make_cap(accepts_native_crypto=True)
        assert cap.supports_mode("native_crypto") is True

    def test_supports_mode_native_crypto_false(self):
        cap = _make_cap(accepts_native_crypto=False)
        assert cap.supports_mode("native_crypto") is False

    def test_supports_mode_offramp(self):
        cap = _make_cap(accepts_card=True)
        assert cap.supports_mode("offramp_settlement") is True

    def test_supports_mode_delegated_card(self):
        cap = _make_cap(supports_delegated_card=True)
        assert cap.supports_mode("delegated_card") is True

    def test_supports_mode_delegated_card_false(self):
        cap = _make_cap(supports_delegated_card=False)
        assert cap.supports_mode("delegated_card") is False

    def test_supports_mode_unknown(self):
        cap = _make_cap()
        assert cap.supports_mode("unknown_mode") is False

    def test_to_dict(self):
        cap = _make_cap()
        d = cap.to_dict()
        assert d["merchant_id"] == "merch_test_001"
        assert d["supported_networks"] == ["stripe_spt"]
        assert d["confidence"] == 0.8

    def test_default_merchant_has_sensible_defaults(self):
        cap = MerchantExecutionCapability()
        assert cap.accepts_card is True
        assert cap.supports_delegated_card is False
        assert cap.verification_status == "unverified"
        assert cap.confidence == 0.5


class TestInMemoryMerchantCapabilityStore:

    @pytest.fixture
    def store(self):
        return InMemoryMerchantCapabilityStore()

    @pytest.mark.asyncio
    async def test_upsert_and_get(self, store):
        cap = _make_cap()
        await store.upsert(cap)
        result = await store.get("merch_test_001")
        assert result is not None
        assert result.domain == "example.com"

    @pytest.mark.asyncio
    async def test_get_not_found(self, store):
        result = await store.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_domain(self, store):
        cap = _make_cap(domain="shop.example.com")
        await store.upsert(cap)
        result = await store.get_by_domain("shop.example.com")
        assert result is not None
        assert result.merchant_id == "merch_test_001"

    @pytest.mark.asyncio
    async def test_get_by_domain_not_found(self, store):
        result = await store.get_by_domain("nope.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_supports_mode(self, store):
        cap = _make_cap(supports_delegated_card=True, accepts_native_crypto=False)
        await store.upsert(cap)
        assert await store.supports_mode("merch_test_001", "delegated_card") is True
        assert await store.supports_mode("merch_test_001", "native_crypto") is False

    @pytest.mark.asyncio
    async def test_supports_mode_unknown_merchant(self, store):
        assert await store.supports_mode("unknown_merchant", "delegated_card") is False

    @pytest.mark.asyncio
    async def test_upsert_overwrites(self, store):
        cap1 = _make_cap(confidence=0.5)
        await store.upsert(cap1)
        cap2 = _make_cap(confidence=0.9)
        await store.upsert(cap2)
        result = await store.get("merch_test_001")
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_confidence_based_decisions(self, store):
        low = _make_cap(merchant_id="m_low", confidence=0.3, supports_delegated_card=True)
        high = _make_cap(merchant_id="m_high", confidence=0.9, supports_delegated_card=True)
        await store.upsert(low)
        await store.upsert(high)

        low_cap = await store.get("m_low")
        high_cap = await store.get("m_high")
        assert low_cap.confidence < 0.7  # below auto-route threshold
        assert high_cap.confidence >= 0.7  # above auto-route threshold
