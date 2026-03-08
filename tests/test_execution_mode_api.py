"""Tests for execution mode API endpoints."""
from __future__ import annotations

from decimal import Decimal

import pytest

from sardis_v2_core.credential_store import CredentialEncryption, InMemoryCredentialStore
from sardis_v2_core.delegated_credential import (
    CredentialNetwork,
    CredentialScope,
    CredentialStatus,
    DelegatedCredential,
)
from sardis_v2_core.execution_mode import ExecutionMode, ExecutionModeRouter
from sardis_v2_core.merchant_capability import (
    InMemoryMerchantCapabilityStore,
    MerchantExecutionCapability,
)


def _fernet_key() -> bytes:
    from cryptography.fernet import Fernet
    return Fernet.generate_key()


class TestExecutionModeAPI:
    """Tests for execution mode discovery and simulation."""

    @pytest.fixture
    def router(self):
        cred_store = InMemoryCredentialStore(
            encryption=CredentialEncryption(key=_fernet_key()),
        )
        merchant_store = InMemoryMerchantCapabilityStore()
        return ExecutionModeRouter(
            credential_store=cred_store,
            merchant_capability_store=merchant_store,
        ), cred_store, merchant_store

    @pytest.mark.asyncio
    async def test_available_modes_returns_all(self, router):
        mode_router, cred_store, merchant_store = router

        # Seed merchant and credential
        cap = MerchantExecutionCapability(
            merchant_id="merch_1",
            accepts_native_crypto=True,
            accepts_card=True,
            supports_delegated_card=True,
            confidence=0.9,
        )
        await merchant_store.upsert(cap)

        cred = DelegatedCredential(
            org_id="org_1", agent_id="agent_1",
            network=CredentialNetwork.STRIPE_SPT,
            status=CredentialStatus.ACTIVE,
            token_reference="tok", token_encrypted=b"enc",
            consent_id="dcns_test",
        )
        await cred_store.store(cred)

        modes = await mode_router.get_available_modes(
            agent_id="agent_1",
            amount=Decimal("50"),
            currency="USDC",
            merchant_id="merch_1",
        )
        assert len(modes) == 3  # all three modes
        mode_names = [m.mode.value for m in modes]
        assert "native_crypto" in mode_names
        assert "offramp_settlement" in mode_names
        assert "delegated_card" in mode_names

    @pytest.mark.asyncio
    async def test_simulate_returns_fee_estimate(self, router):
        mode_router, cred_store, merchant_store = router

        cap = MerchantExecutionCapability(
            merchant_id="merch_1",
            accepts_native_crypto=True,
            confidence=0.9,
        )
        await merchant_store.upsert(cap)

        from sardis_v2_core.execution_intent import ExecutionIntent
        intent = ExecutionIntent(
            agent_id="agent_1",
            amount=Decimal("100"),
            currency="USDC",
            recipient_address="0xabc",
            metadata={"merchant_id": "merch_1"},
        )
        selection = await mode_router.resolve(intent)
        assert selection.estimated_fee > Decimal("0")
        assert selection.settlement_time_seconds > 0
