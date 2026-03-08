"""End-to-end integration test for delegated payment pipeline.

Full pipeline: consent -> provision credential -> submit intent ->
router picks mode -> executor calls mock Stripe -> settlement created.
"""
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
from sardis_v2_core.delegation_consent import (
    ConsentType,
    DelegationConsent,
    InMemoryConsentStore,
)
from sardis_v2_core.delegated_adapters.stripe_spt import MockStripeSPTAdapter
from sardis_v2_core.delegated_executor import DelegatedPaymentRequest
from sardis_v2_core.execution_intent import ExecutionIntent, IntentSource
from sardis_v2_core.execution_mode import ExecutionMode, ExecutionModeRouter
from sardis_v2_core.merchant_capability import (
    InMemoryMerchantCapabilityStore,
    MerchantExecutionCapability,
)
from sardis_v2_core.settlement import (
    InMemorySettlementStore,
    SettlementMode,
    SettlementRecord,
    SettlementStatus,
)
from sardis_api.domains.delegated_executor import DelegatedExecutionAdapter
from sardis_api.domains.multi_modal_executor import MultiModalExecutionAdapter


def _fernet_key() -> bytes:
    from cryptography.fernet import Fernet
    return Fernet.generate_key()


class TestDelegatedPaymentE2E:

    @pytest.fixture
    def env(self):
        """Set up all stores and adapters for e2e testing."""
        encryption = CredentialEncryption(key=_fernet_key())
        cred_store = InMemoryCredentialStore(encryption=encryption)
        consent_store = InMemoryConsentStore()
        merchant_store = InMemoryMerchantCapabilityStore()
        settlement_store = InMemorySettlementStore()
        mock_stripe = MockStripeSPTAdapter()

        delegated_adapter = DelegatedExecutionAdapter(
            executor_port=mock_stripe,
            credential_store=cred_store,
        )

        mode_router = ExecutionModeRouter(
            credential_store=cred_store,
            merchant_capability_store=merchant_store,
        )

        multi_executor = MultiModalExecutionAdapter(
            crypto_executor=None,
            delegated_executor=delegated_adapter,
            mode_router=mode_router,
        )

        return {
            "encryption": encryption,
            "cred_store": cred_store,
            "consent_store": consent_store,
            "merchant_store": merchant_store,
            "settlement_store": settlement_store,
            "mock_stripe": mock_stripe,
            "delegated_adapter": delegated_adapter,
            "mode_router": mode_router,
            "multi_executor": multi_executor,
        }

    @pytest.mark.asyncio
    async def test_full_delegated_payment_pipeline(self, env):
        """consent -> provision -> intent -> router -> executor -> settlement"""
        cred_store = env["cred_store"]
        consent_store = env["consent_store"]
        merchant_store = env["merchant_store"]
        settlement_store = env["settlement_store"]
        mock_stripe = env["mock_stripe"]
        mode_router = env["mode_router"]
        encryption = env["encryption"]

        # 1. Record consent
        consent = DelegationConsent(
            org_id="org_1",
            user_id="user_1",
            agent_id="agent_1",
            consent_type=ConsentType.INITIAL_GRANT,
            source_surface="dashboard",
            approved_scopes_snapshot={"max_per_tx": "500", "daily_limit": "2000"},
        )
        consent_id = await consent_store.record_consent(consent)

        # 2. Provision credential
        scope = CredentialScope(max_per_tx=Decimal("500"), daily_limit=Decimal("2000"))
        cred = await mock_stripe.provision_credential(
            org_id="org_1",
            agent_id="agent_1",
            scope=scope,
            encryption=encryption,
        )
        cred.consent_id = consent_id
        await cred_store.store(cred)

        # 3. Register merchant capabilities
        merchant_cap = MerchantExecutionCapability(
            merchant_id="merch_amazon",
            domain="amazon.com",
            accepts_card=True,
            supports_delegated_card=True,
            supported_networks=["stripe_spt"],
            confidence=0.95,
        )
        await merchant_store.upsert(merchant_cap)

        # 4. Submit intent — router should pick delegated_card
        intent = ExecutionIntent(
            source=IntentSource.DELEGATED_CARD,
            org_id="org_1",
            agent_id="agent_1",
            amount=Decimal("49.99"),
            currency="USD",
            metadata={
                "merchant_id": "merch_amazon",
                "execution_mode": "delegated_card",
                "credential_id": cred.credential_id,
            },
            credential_id=cred.credential_id,
            execution_mode="delegated_card",
        )

        # 5. Router resolves mode
        selection = await mode_router.resolve(intent)
        assert selection.mode == ExecutionMode.DELEGATED_CARD
        assert selection.credential_id == cred.credential_id

        # 6. Execute via delegated adapter
        delegated_adapter = env["delegated_adapter"]
        result = await delegated_adapter.execute(intent)
        assert result["execution_mode"] == "delegated_card"
        assert result["tx_hash"].startswith("pi_mock_")

        # 7. Create settlement record
        settlement = SettlementRecord(
            intent_id=intent.intent_id,
            receipt_id="rcpt_test",
            mode=SettlementMode.DELEGATED_CARD,
            status=SettlementStatus.PENDING_CONFIRMATION,
            amount=intent.amount,
            currency=intent.currency,
            fee=Decimal(result.get("fee", "0")),
            network_reference=result["tx_hash"],
            credential_id=cred.credential_id,
            authorization_status="authorized",
            capture_status="pending_capture",
        )
        await settlement_store.create(settlement)

        # 8. Verify settlement
        stl = await settlement_store.get(settlement.settlement_id)
        assert stl.mode == SettlementMode.DELEGATED_CARD
        assert stl.network_reference == result["tx_hash"]
        assert stl.credential_id == cred.credential_id

    @pytest.mark.asyncio
    async def test_crypto_mode_regression(self, env):
        """Same pipeline for crypto mode still works."""

        class FakeCryptoExecutor:
            async def execute(self, intent):
                return {"tx_hash": "0xdeadbeef", "status": "submitted"}

        multi = MultiModalExecutionAdapter(
            crypto_executor=FakeCryptoExecutor(),
        )
        intent = ExecutionIntent(
            agent_id="agent_1",
            amount=Decimal("25"),
            currency="USDC",
            execution_mode="native_crypto",
            recipient_address="0xabc123",
        )
        result = await multi.execute(intent)
        assert result["execution_mode"] == "native_crypto"
        assert result["tx_hash"] == "0xdeadbeef"

    @pytest.mark.asyncio
    async def test_fail_closed_no_silent_fallback(self, env):
        """If delegated fails, NO silent fallback."""
        mode_router = env["mode_router"]

        intent = ExecutionIntent(
            agent_id="agent_no_cred",
            amount=Decimal("50"),
            currency="USD",
            metadata={
                "execution_mode": "delegated_card",
                "credential_id": "dcred_nonexistent",
                "fallback_policy": "fail_closed",
            },
        )
        with pytest.raises(ValueError, match="FAIL_CLOSED"):
            await mode_router.resolve(intent)

    @pytest.mark.asyncio
    async def test_policy_governed_fallback_with_evidence(self, env):
        """Fallback only when policy allows, recorded in evidence."""
        cred_store = env["cred_store"]
        merchant_store = env["merchant_store"]
        mode_router = env["mode_router"]

        # Merchant supports offramp but not delegated
        cap = MerchantExecutionCapability(
            merchant_id="merch_fallback",
            accepts_card=True,
            supports_delegated_card=False,
            confidence=0.9,
        )
        await merchant_store.upsert(cap)

        intent = ExecutionIntent(
            agent_id="agent_1",
            amount=Decimal("50"),
            currency="USD",
            metadata={
                "merchant_id": "merch_fallback",
                "execution_mode": "delegated_card",
                "fallback_policy": "policy_governed",
            },
        )
        selection = await mode_router.resolve(intent)
        assert selection.fallback_applied is True
        assert selection.original_mode == ExecutionMode.DELEGATED_CARD
        assert selection.mode != ExecutionMode.DELEGATED_CARD
        # Evidence: rejected_modes shows why delegated failed
        assert "delegated_card" in selection.rejected_modes
