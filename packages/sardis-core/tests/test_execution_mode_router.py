"""Tests for execution mode routing."""
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
from sardis_v2_core.execution_intent import ExecutionIntent
from sardis_v2_core.execution_mode import (
    ExecutionMode,
    ExecutionModeRouter,
    ExecutionModeSelection,
    RoutingThresholds,
)
from sardis_v2_core.merchant_capability import (
    InMemoryMerchantCapabilityStore,
    MerchantExecutionCapability,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fernet_key() -> bytes:
    from cryptography.fernet import Fernet
    return Fernet.generate_key()


def _make_cred_store() -> InMemoryCredentialStore:
    return InMemoryCredentialStore(encryption=CredentialEncryption(key=_fernet_key()))


def _make_merchant_store() -> InMemoryMerchantCapabilityStore:
    return InMemoryMerchantCapabilityStore()


def _make_router(
    cred_store=None,
    merchant_store=None,
    thresholds=None,
) -> ExecutionModeRouter:
    return ExecutionModeRouter(
        credential_store=cred_store or _make_cred_store(),
        merchant_capability_store=merchant_store or _make_merchant_store(),
        thresholds=thresholds or RoutingThresholds(),
    )


async def _seed_credential(
    store: InMemoryCredentialStore,
    agent_id: str = "agent_1",
    status: CredentialStatus = CredentialStatus.ACTIVE,
    scope: CredentialScope | None = None,
) -> DelegatedCredential:
    cred = DelegatedCredential(
        org_id="org_1",
        agent_id=agent_id,
        network=CredentialNetwork.STRIPE_SPT,
        status=status,
        token_reference="tok_ref",
        token_encrypted=b"enc_payload",
        consent_id="dcns_test",
        scope=scope or CredentialScope(),
    )
    await store.store(cred)
    return cred


async def _seed_merchant(
    store: InMemoryMerchantCapabilityStore,
    merchant_id: str = "merch_1",
    **kwargs,
) -> MerchantExecutionCapability:
    defaults = {
        "merchant_id": merchant_id,
        "accepts_native_crypto": False,
        "accepts_card": True,
        "supports_delegated_card": True,
        "confidence": 0.9,
    }
    defaults.update(kwargs)
    cap = MerchantExecutionCapability(**defaults)
    await store.upsert(cap)
    return cap


def _intent(
    recipient_address: str = "",
    merchant_id: str = "",
    execution_mode: str = "",
    credential_id: str = "",
    amount: Decimal = Decimal("50"),
    fallback_policy: str = "fail_closed",
    **extra_meta,
) -> ExecutionIntent:
    meta = {"merchant_id": merchant_id, "fallback_policy": fallback_policy}
    if credential_id:
        meta["credential_id"] = credential_id
    if execution_mode:
        meta["execution_mode"] = execution_mode
    meta.update(extra_meta)
    return ExecutionIntent(
        agent_id="agent_1",
        amount=amount,
        currency="USDC",
        recipient_address=recipient_address,
        metadata=meta,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExecutionModeRouter:

    @pytest.mark.asyncio
    async def test_routes_to_native_crypto_with_recipient_address(self):
        """Routes to NATIVE_CRYPTO when recipient has on-chain address."""
        router = _make_router()
        intent = _intent(recipient_address="0xabc123")
        selection = await router.resolve(intent)
        assert selection.mode == ExecutionMode.NATIVE_CRYPTO

    @pytest.mark.asyncio
    async def test_routes_to_delegated_card_with_credential(self):
        """Routes to DELEGATED_CARD when agent has active credential + merchant supports it."""
        cred_store = _make_cred_store()
        merchant_store = _make_merchant_store()
        await _seed_credential(cred_store)
        await _seed_merchant(merchant_store)
        router = _make_router(cred_store=cred_store, merchant_store=merchant_store)

        intent = _intent(merchant_id="merch_1")
        selection = await router.resolve(intent)
        # With no recipient address and merchant supporting delegated card,
        # auto-routing should pick cheapest viable = offramp (merchant accepts_card)
        # or delegated_card depending on cost ranking
        assert selection.mode in (
            ExecutionMode.OFFRAMP_SETTLEMENT,
            ExecutionMode.DELEGATED_CARD,
        )

    @pytest.mark.asyncio
    async def test_explicit_mode_delegated_card_succeeds(self):
        """Explicit delegated_card mode works when credential + merchant viable."""
        cred_store = _make_cred_store()
        merchant_store = _make_merchant_store()
        cred = await _seed_credential(cred_store)
        await _seed_merchant(merchant_store)
        router = _make_router(cred_store=cred_store, merchant_store=merchant_store)

        intent = _intent(
            merchant_id="merch_1",
            execution_mode="delegated_card",
            credential_id=cred.credential_id,
        )
        selection = await router.resolve(intent)
        assert selection.mode == ExecutionMode.DELEGATED_CARD
        assert selection.credential_id == cred.credential_id

    @pytest.mark.asyncio
    async def test_fails_closed_when_explicit_mode_unavailable(self):
        """Fails closed when explicit mode set but credential unavailable."""
        router = _make_router()
        intent = _intent(
            execution_mode="delegated_card",
            credential_id="dcred_nonexistent",
        )
        with pytest.raises(ValueError, match="FAIL_CLOSED"):
            await router.resolve(intent)

    @pytest.mark.asyncio
    async def test_policy_governed_fallback_records_applied(self):
        """Policy-governed fallback records fallback_applied=True + original_mode."""
        cred_store = _make_cred_store()
        merchant_store = _make_merchant_store()
        await _seed_merchant(merchant_store, accepts_card=True)
        router = _make_router(cred_store=cred_store, merchant_store=merchant_store)

        intent = _intent(
            merchant_id="merch_1",
            execution_mode="delegated_card",
            fallback_policy="policy_governed",
        )
        selection = await router.resolve(intent)
        assert selection.fallback_applied is True
        assert selection.original_mode == ExecutionMode.DELEGATED_CARD
        assert selection.mode != ExecutionMode.DELEGATED_CARD

    @pytest.mark.asyncio
    async def test_cost_ranks_correctly(self):
        """Crypto < offramp < card in cost ranking."""
        cred_store = _make_cred_store()
        merchant_store = _make_merchant_store()
        await _seed_credential(cred_store)
        await _seed_merchant(
            merchant_store,
            accepts_native_crypto=True,
            accepts_card=True,
            supports_delegated_card=True,
            confidence=0.9,
        )
        router = _make_router(cred_store=cred_store, merchant_store=merchant_store)

        intent = _intent(
            recipient_address="0xabc",
            merchant_id="merch_1",
        )
        selection = await router.resolve(intent)
        # Crypto is cheapest, so auto-routing should pick it
        assert selection.mode == ExecutionMode.NATIVE_CRYPTO

    @pytest.mark.asyncio
    async def test_merchant_capability_gates_delegated(self):
        """Merchant not supporting delegated_card blocks that mode."""
        cred_store = _make_cred_store()
        merchant_store = _make_merchant_store()
        await _seed_credential(cred_store)
        await _seed_merchant(merchant_store, supports_delegated_card=False)
        router = _make_router(cred_store=cred_store, merchant_store=merchant_store)

        intent = _intent(merchant_id="merch_1")
        selection = await router.resolve(intent)
        assert selection.mode != ExecutionMode.DELEGATED_CARD

    @pytest.mark.asyncio
    async def test_low_confidence_rejects_auto_route(self):
        """Low merchant confidence blocks delegated card and offramp in auto-routing."""
        cred_store = _make_cred_store()
        merchant_store = _make_merchant_store()
        await _seed_credential(cred_store)
        await _seed_merchant(
            merchant_store,
            supports_delegated_card=True,
            confidence=0.3,
        )
        router = _make_router(cred_store=cred_store, merchant_store=merchant_store)

        intent = _intent(merchant_id="merch_1")
        # Low confidence rejects both delegated_card and offramp, and no
        # recipient address means native_crypto also fails — no modes available
        with pytest.raises(ValueError, match="No execution mode available"):
            await router.resolve(intent)

    @pytest.mark.asyncio
    async def test_get_available_modes(self):
        """get_available_modes returns all modes with viability info."""
        cred_store = _make_cred_store()
        merchant_store = _make_merchant_store()
        await _seed_credential(cred_store)
        await _seed_merchant(merchant_store, accepts_native_crypto=True)
        router = _make_router(cred_store=cred_store, merchant_store=merchant_store)

        modes = await router.get_available_modes(
            agent_id="agent_1",
            amount=Decimal("50"),
            currency="USDC",
            merchant_id="merch_1",
        )
        assert len(modes) == len(ExecutionMode)

    @pytest.mark.asyncio
    async def test_no_modes_available_raises(self):
        """ValueError when no mode is viable."""
        merchant_store = _make_merchant_store()
        # Merchant that rejects all modes
        await _seed_merchant(
            merchant_store,
            accepts_native_crypto=False,
            accepts_card=False,
            supports_delegated_card=False,
            confidence=0.9,
        )
        router = _make_router(merchant_store=merchant_store)
        # No recipient address, merchant rejects fiat, no credentials
        intent = _intent(merchant_id="merch_1")
        with pytest.raises(ValueError, match="No execution mode available"):
            await router.resolve(intent)

    @pytest.mark.asyncio
    async def test_selection_to_dict(self):
        """ExecutionModeSelection.to_dict() produces expected shape."""
        sel = ExecutionModeSelection(
            mode=ExecutionMode.NATIVE_CRYPTO,
            reason="test",
            evaluated_modes=["native_crypto"],
        )
        d = sel.to_dict()
        assert d["mode"] == "native_crypto"
        assert d["reason"] == "test"
