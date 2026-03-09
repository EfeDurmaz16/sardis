"""Tests for delegated executor and Stripe SPT adapter."""
from __future__ import annotations

from decimal import Decimal

import pytest

# Import API-layer adapters
from sardis_api.domains.delegated_executor import DelegatedExecutionAdapter
from sardis_api.domains.multi_modal_executor import MultiModalExecutionAdapter
from sardis_v2_core.credential_store import CredentialEncryption, InMemoryCredentialStore
from sardis_v2_core.delegated_adapters.stripe_spt import MockStripeSPTAdapter
from sardis_v2_core.delegated_credential import (
    CredentialNetwork,
    CredentialScope,
    CredentialStatus,
    DelegatedCredential,
)
from sardis_v2_core.delegated_executor import (
    DelegatedPaymentRequest,
)
from sardis_v2_core.execution_intent import ExecutionIntent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fernet_key() -> bytes:
    from cryptography.fernet import Fernet
    return Fernet.generate_key()


def _make_encryption() -> CredentialEncryption:
    return CredentialEncryption(key=_fernet_key())


def _make_active_credential(
    consent_id: str = "dcns_test",
    scope: CredentialScope | None = None,
) -> DelegatedCredential:
    return DelegatedCredential(
        org_id="org_1",
        agent_id="agent_1",
        network=CredentialNetwork.STRIPE_SPT,
        status=CredentialStatus.ACTIVE,
        token_reference="tok_ref_test",
        token_encrypted=b"enc_test_payload",
        scope=scope or CredentialScope(),
        consent_id=consent_id,
    )


def _make_request(amount: Decimal = Decimal("50")) -> DelegatedPaymentRequest:
    return DelegatedPaymentRequest(
        credential_reference="tok_ref_test",
        consent_reference="dcns_test",
        merchant_binding="merch_1",
        amount=amount,
        currency="USD",
    )


# ---------------------------------------------------------------------------
# MockStripeSPTAdapter tests
# ---------------------------------------------------------------------------

class TestMockStripeSPTAdapter:

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        adapter = MockStripeSPTAdapter()
        cred = _make_active_credential()
        request = _make_request()
        result = await adapter.execute(request, cred)
        assert result.success is True
        assert result.network == "stripe_spt"
        assert result.amount == Decimal("50")
        assert result.reference_id.startswith("pi_mock_")

    @pytest.mark.asyncio
    async def test_failure_on_inactive_credential(self):
        adapter = MockStripeSPTAdapter()
        cred = DelegatedCredential(
            status=CredentialStatus.REVOKED,
            token_reference="tok",
            token_encrypted=b"enc",
            consent_id="dcns_test",
        )
        request = _make_request()
        result = await adapter.execute(request, cred)
        assert result.success is False
        assert "not active" in result.error

    @pytest.mark.asyncio
    async def test_configured_failure(self):
        adapter = MockStripeSPTAdapter(should_fail=True)
        cred = _make_active_credential()
        request = _make_request()
        result = await adapter.execute(request, cred)
        assert result.success is False
        assert "Mock failure" in result.error

    @pytest.mark.asyncio
    async def test_check_health(self):
        adapter = MockStripeSPTAdapter()
        assert await adapter.check_health() is True

    @pytest.mark.asyncio
    async def test_estimate_fee(self):
        adapter = MockStripeSPTAdapter()
        fee = await adapter.estimate_fee(Decimal("100"), "USD")
        assert fee == Decimal("2.5")

    @pytest.mark.asyncio
    async def test_provision_credential(self):
        adapter = MockStripeSPTAdapter()
        enc = _make_encryption()
        cred = await adapter.provision_credential(
            org_id="org_1",
            agent_id="agent_1",
            scope=CredentialScope(max_per_tx=Decimal("200")),
            encryption=enc,
        )
        assert cred.network == CredentialNetwork.STRIPE_SPT
        assert cred.status == CredentialStatus.ACTIVE
        assert cred.scope.max_per_tx == Decimal("200")
        assert cred.token_encrypted != b"mock_encrypted"  # was actually encrypted


# ---------------------------------------------------------------------------
# DelegatedExecutionAdapter tests
# ---------------------------------------------------------------------------

class TestDelegatedExecutionAdapter:

    @pytest.fixture
    def setup(self):
        cred_store = InMemoryCredentialStore(encryption=_make_encryption())
        mock_port = MockStripeSPTAdapter()
        adapter = DelegatedExecutionAdapter(
            executor_port=mock_port,
            credential_store=cred_store,
        )
        return adapter, cred_store

    @pytest.mark.asyncio
    async def test_routes_correctly_from_intent(self, setup):
        adapter, cred_store = setup
        cred = _make_active_credential()
        await cred_store.store(cred)

        intent = ExecutionIntent(
            agent_id="agent_1",
            amount=Decimal("50"),
            currency="USD",
            credential_id=cred.credential_id,
        )
        result = await adapter.execute(intent)
        assert result["execution_mode"] == "delegated_card"
        assert result["tx_hash"].startswith("pi_mock_")

    @pytest.mark.asyncio
    async def test_missing_credential_raises(self, setup):
        adapter, _ = setup
        intent = ExecutionIntent(
            agent_id="agent_1",
            amount=Decimal("50"),
            credential_id="dcred_nonexistent",
        )
        with pytest.raises(RuntimeError, match="not found"):
            await adapter.execute(intent)

    @pytest.mark.asyncio
    async def test_expired_credential_raises(self, setup):
        adapter, cred_store = setup
        cred = DelegatedCredential(
            org_id="org_1",
            agent_id="agent_1",
            network=CredentialNetwork.STRIPE_SPT,
            status=CredentialStatus.EXPIRED,
            token_reference="tok",
            token_encrypted=b"enc",
            consent_id="dcns_test",
        )
        await cred_store.store(cred)
        intent = ExecutionIntent(
            amount=Decimal("50"),
            credential_id=cred.credential_id,
        )
        with pytest.raises(RuntimeError, match="not active"):
            await adapter.execute(intent)

    @pytest.mark.asyncio
    async def test_no_credential_id_raises(self, setup):
        adapter, _ = setup
        intent = ExecutionIntent(amount=Decimal("50"))
        with pytest.raises(RuntimeError, match="No credential_id"):
            await adapter.execute(intent)


# ---------------------------------------------------------------------------
# MultiModalExecutionAdapter tests
# ---------------------------------------------------------------------------

class TestMultiModalExecutionAdapter:

    @pytest.mark.asyncio
    async def test_routes_delegated_mode(self):
        cred_store = InMemoryCredentialStore(encryption=_make_encryption())
        cred = _make_active_credential()
        await cred_store.store(cred)

        delegated = DelegatedExecutionAdapter(
            executor_port=MockStripeSPTAdapter(),
            credential_store=cred_store,
        )
        multi = MultiModalExecutionAdapter(
            crypto_executor=None,
            delegated_executor=delegated,
        )
        intent = ExecutionIntent(
            agent_id="agent_1",
            amount=Decimal("50"),
            execution_mode="delegated_card",
            credential_id=cred.credential_id,
        )
        result = await multi.execute(intent)
        assert result["execution_mode"] == "delegated_card"

    @pytest.mark.asyncio
    async def test_routes_crypto_mode(self):
        class FakeCryptoExecutor:
            async def execute(self, intent):
                return {"tx_hash": "0xabc", "status": "submitted"}

        multi = MultiModalExecutionAdapter(
            crypto_executor=FakeCryptoExecutor(),
        )
        intent = ExecutionIntent(
            amount=Decimal("50"),
            execution_mode="native_crypto",
        )
        result = await multi.execute(intent)
        assert result["execution_mode"] == "native_crypto"
        assert result["tx_hash"] == "0xabc"

    @pytest.mark.asyncio
    async def test_no_delegated_executor_raises(self):
        multi = MultiModalExecutionAdapter()
        intent = ExecutionIntent(
            amount=Decimal("50"),
            execution_mode="delegated_card",
        )
        with pytest.raises(RuntimeError, match="Delegated executor not configured"):
            await multi.execute(intent)
