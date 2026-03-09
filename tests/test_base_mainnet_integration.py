"""Integration tests for Base mainnet deployment flow.

Tests the full payment pipeline on Base with Circle Paymaster,
EAS attestations, Tenderly simulation, and production config.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sardis_v2_core.config import SardisSettings
from sardis_v2_core.spending_policy import (
    TrustLevel,
    create_default_policy,
)
from sardis_v2_core.tokens import TokenType
from sardis_v2_core.wallets import Wallet

# ── Config validation ────────────────────────────────────────────────────


class TestBaseMainnetConfig:
    def test_base_in_default_chains(self):
        settings = SardisSettings()
        chain_names = [c.name for c in settings.chains]
        assert "base" in chain_names
        assert "base_sepolia" in chain_names

    def test_base_chain_config(self):
        settings = SardisSettings()
        base_config = next(c for c in settings.chains if c.name == "base")
        assert base_config.chain_id == 8453
        assert "USDC" in base_config.stablecoins

    def test_base_in_erc4337_allowlist(self):
        settings = SardisSettings()
        assert "base" in settings.erc4337_chain_allowlist_set
        assert "base_sepolia" in settings.erc4337_chain_allowlist_set

    def test_tenderly_config_fields_exist(self):
        settings = SardisSettings()
        assert hasattr(settings, "tenderly_api_key")
        assert hasattr(settings, "tenderly_account_slug")
        assert hasattr(settings, "tenderly_project_slug")

    def test_circle_wallet_config_fields_exist(self):
        settings = SardisSettings()
        assert hasattr(settings, "circle_wallet_api_key")
        assert hasattr(settings, "circle_entity_secret")
        assert hasattr(settings, "circle_wallet_set_id")
        assert hasattr(settings, "circle_account_type")
        assert settings.circle_account_type == "SCA"

    def test_mpc_provider_supports_circle(self):
        from sardis_v2_core.config import MPCProvider
        provider = MPCProvider(name="circle")
        assert provider.name == "circle"


# ── Circle Paymaster wiring ──────────────────────────────────────────────


class TestCirclePaymasterWiring:
    def test_paymaster_addresses_include_base(self):
        from sardis_chain.erc4337.paymaster_client import (
            CIRCLE_PAYMASTER_ADDRESSES,
            USDC_FOR_PAYMASTER,
        )
        assert "base" in CIRCLE_PAYMASTER_ADDRESSES
        assert "base" in USDC_FOR_PAYMASTER

    def test_chain_aware_bundler_url_mainnet(self):
        from sardis_chain.erc4337.paymaster_client import CirclePaymasterClient

        client = CirclePaymasterClient(
            bundler_url="https://api.pimlico.io/v2/base-sepolia/rpc?apikey=test"
        )
        url = client.get_bundler_url("base")
        assert "base-sepolia" not in url
        assert "/base/" in url

    def test_chain_aware_bundler_url_testnet_unchanged(self):
        from sardis_chain.erc4337.paymaster_client import CirclePaymasterClient

        client = CirclePaymasterClient(
            bundler_url="https://api.pimlico.io/v2/base-sepolia/rpc?apikey=test"
        )
        url = client.get_bundler_url("base_sepolia")
        assert "base-sepolia" in url

    @pytest.mark.asyncio
    async def test_circle_paymaster_sponsor_base(self):
        from sardis_chain.erc4337.paymaster_client import CirclePaymasterClient
        from sardis_chain.erc4337.user_operation import UserOperation

        client = CirclePaymasterClient(bundler_url="https://example.com/bundler")
        user_op = UserOperation(
            sender="0x" + "11" * 20,
            nonce="0x0",
            init_code="0x",
            call_data="0x",
            call_gas_limit="0x5208",
            verification_gas_limit="0x5208",
            pre_verification_gas="0x5208",
            max_fee_per_gas="0x3b9aca00",
            max_priority_fee_per_gas="0x3b9aca00",
            paymaster_and_data="0x",
            signature="0x",
        )

        result = await client.sponsor_user_operation(
            user_op=user_op,
            entrypoint="0x0000000071727De22E5E9d8BAf0edAc6f37da032",
            chain="base",
        )
        assert result.paymaster != ""
        assert result.paymaster_and_data.startswith("0x0578")


# ── Contract addresses ───────────────────────────────────────────────────


class TestContractAddresses:
    def test_sardis_contracts_has_base_key(self):
        from sardis_chain.executor import SARDIS_CONTRACTS
        assert "base" in SARDIS_CONTRACTS
        assert "policy_module" in SARDIS_CONTRACTS["base"]
        assert "ledger_anchor" in SARDIS_CONTRACTS["base"]

    def test_sardis_contracts_has_base_sepolia(self):
        from sardis_chain.executor import SARDIS_CONTRACTS
        assert "base_sepolia" in SARDIS_CONTRACTS


# ── EAS + Policy pipeline ───────────────────────────────────────────────


class TestEASPolicyPipeline:
    @pytest.mark.asyncio
    async def test_kya_check_passes_with_valid_attestation(self):
        from sardis_protocol.eas_kya import KYAAttestation

        wallet = Wallet.new("agent_test", mpc_provider="circle")
        wallet.kya_attestation_uid = "0x" + "ab" * 32
        wallet.set_address("base", "0x" + "11" * 20)

        policy = create_default_policy("agent_test", TrustLevel.MEDIUM)

        kya_client = AsyncMock()
        kya_client.verify_attestation = AsyncMock(return_value=KYAAttestation(
            agent_id="agent_test",
            trust_level="MEDIUM",
            policy_hash="0x" + "00" * 32,
            attestation_uid=bytes.fromhex("ab" * 32),
        ))

        ok, reason = await policy.evaluate(
            wallet, Decimal("10"), Decimal("0.01"),
            chain="base", token=TokenType.USDC,
            kya_client=kya_client,
        )
        assert ok is True
        assert reason == "OK"

    @pytest.mark.asyncio
    async def test_kya_check_fails_without_attestation(self):
        wallet = Wallet.new("agent_test", mpc_provider="circle")
        wallet.set_address("base", "0x" + "11" * 20)
        # No kya_attestation_uid set

        policy = create_default_policy("agent_test", TrustLevel.MEDIUM)

        kya_client = AsyncMock()

        ok, reason = await policy.evaluate(
            wallet, Decimal("10"), Decimal("0.01"),
            chain="base", token=TokenType.USDC,
            kya_client=kya_client,
        )
        assert ok is False
        assert reason == "kya_attestation_required"

    @pytest.mark.asyncio
    async def test_kya_check_fails_when_revoked(self):
        from sardis_protocol.eas_kya import KYAAttestation

        wallet = Wallet.new("agent_test", mpc_provider="circle")
        wallet.kya_attestation_uid = "0x" + "ab" * 32
        wallet.set_address("base", "0x" + "11" * 20)

        policy = create_default_policy("agent_test", TrustLevel.HIGH)

        kya_client = AsyncMock()
        kya_client.verify_attestation = AsyncMock(return_value=KYAAttestation(
            agent_id="agent_test",
            trust_level="HIGH",
            policy_hash="0x" + "00" * 32,
            attestation_uid=bytes.fromhex("ab" * 32),
            revoked=True,
        ))

        ok, reason = await policy.evaluate(
            wallet, Decimal("10"), Decimal("0.01"),
            chain="base", token=TokenType.USDC,
            kya_client=kya_client,
        )
        assert ok is False
        assert reason == "kya_attestation_revoked"

    @pytest.mark.asyncio
    async def test_kya_check_skipped_for_low_trust(self):
        """LOW trust agents don't need KYA attestation."""
        wallet = Wallet.new("agent_test", mpc_provider="circle")
        wallet.set_address("base", "0x" + "11" * 20)

        policy = create_default_policy("agent_test", TrustLevel.LOW)

        kya_client = AsyncMock()

        ok, reason = await policy.evaluate(
            wallet, Decimal("10"), Decimal("0.01"),
            chain="base", token=TokenType.USDC,
            kya_client=kya_client,
        )
        assert ok is True
        assert reason == "OK"


# ── Simulation router ───────────────────────────────────────────────────


class TestSimulationIntegration:
    def test_simulation_router_creation_from_settings(self):
        from sardis_chain.simulation import SimulationRouter

        settings = SardisSettings()
        router = SimulationRouter.from_settings(settings)
        # Without Tenderly creds, should fall back to local
        assert router.has_tenderly is False

    def test_simulation_router_with_tenderly_creds(self):
        from sardis_chain.simulation import SimulationRouter

        settings = MagicMock()
        settings.tenderly_api_key = "test-key"
        settings.tenderly_account_slug = "sardis"
        settings.tenderly_project_slug = "prod"

        router = SimulationRouter.from_settings(settings)
        assert router.has_tenderly is True


# ── Wallet model ─────────────────────────────────────────────────────────


class TestWalletModel:
    def test_wallet_has_circle_wallet_id(self):
        wallet = Wallet.new("agent_1")
        assert wallet.circle_wallet_id is None
        wallet.circle_wallet_id = "circle_w_123"
        assert wallet.circle_wallet_id == "circle_w_123"

    def test_wallet_has_kya_attestation_uid(self):
        wallet = Wallet.new("agent_1")
        assert wallet.kya_attestation_uid is None
        wallet.kya_attestation_uid = "0x" + "ab" * 32
        assert wallet.kya_attestation_uid.startswith("0x")
