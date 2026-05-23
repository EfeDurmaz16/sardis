"""Tests for MPC signer fail-closed behavior.

Verifies:
1. Unknown MPC provider name raises ValueError (not silent SimulatedMPCSigner fallback)
2. Production environment blocks SimulatedMPCSigner entirely
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from sardis_chain.executor import ChainExecutor, SimulatedMPCSigner


def _make_settings(
    *,
    mpc_name: str = "simulated",
    chain_mode: str = "simulated",
    environment: str = "dev",
) -> MagicMock:
    """Create a minimal mock SardisSettings for _init_mpc_signer tests."""
    settings = MagicMock()
    settings.mpc = MagicMock()
    settings.mpc.name = mpc_name
    settings.mpc.credential_id = ""
    settings.mpc.api_base = ""
    settings.chain_mode = chain_mode
    settings.environment = environment
    settings.is_production = environment == "prod"
    settings.chain = MagicMock()
    settings.chain.name = "base_sepolia"
    settings.chain.rpc_url = "https://sepolia.base.org"
    settings.chain.chain_id = 84532
    return settings


def _make_executor(settings: MagicMock) -> ChainExecutor:
    """Create a ChainExecutor with mocked internals, skipping full init."""
    executor = object.__new__(ChainExecutor)
    executor._settings = settings
    executor._mpc_signer = None
    executor._turnkey_client = None
    executor._circle_client = None
    return executor


class TestUnknownProviderRaisesValueError:
    """An unrecognized MPC provider name must raise ValueError, not silently use SimulatedMPCSigner."""

    def test_unknown_provider_raises(self):
        settings = _make_settings(mpc_name="typo_turnkee")
        executor = _make_executor(settings)

        with pytest.raises(ValueError, match="Unknown MPC provider: typo_turnkee"):
            executor._init_mpc_signer()

    def test_unknown_provider_error_lists_supported(self):
        settings = _make_settings(mpc_name="aws_kms")
        executor = _make_executor(settings)

        with pytest.raises(ValueError, match="Supported providers"):
            executor._init_mpc_signer()

    @pytest.mark.parametrize("provider", ["TURNKEY", "Turnkey", "CIRCLE", "Fireblocks"])
    def test_case_sensitive_provider_rejects_wrong_case(self, provider: str):
        """Provider names are case-sensitive; wrong case should raise."""
        settings = _make_settings(mpc_name=provider)
        executor = _make_executor(settings)

        with pytest.raises(ValueError, match="Unknown MPC provider"):
            executor._init_mpc_signer()

    def test_empty_string_provider_raises(self):
        settings = _make_settings(mpc_name="")
        executor = _make_executor(settings)

        with pytest.raises(ValueError, match="Unknown MPC provider"):
            executor._init_mpc_signer()


class TestProductionBlocksSimulatedMPCSigner:
    """In production (SARDIS_ENVIRONMENT=prod), SimulatedMPCSigner must NEVER be active."""

    def test_production_circle_nonlive_raises(self):
        """Circle in non-live mode falls back to SimulatedMPCSigner, which must be blocked in prod."""
        settings = _make_settings(
            mpc_name="circle",
            chain_mode="simulated",
            environment="prod",
        )
        executor = _make_executor(settings)

        # Mock the Circle imports to succeed but trigger non-live path
        mock_circle_client = MagicMock()
        with patch.dict(os.environ, {
            "SARDIS_CIRCLE_WALLET_API_KEY": "test-key",
            "SARDIS_CIRCLE_ENTITY_SECRET": "test-secret",
        }):
            with patch(
                "sardis_chain.executor.CircleWalletSigner",
                create=True,
            ), patch(
                "sardis_wallet.circle_client.CircleWalletClient",
                return_value=mock_circle_client,
                create=True,
            ):
                with pytest.raises(RuntimeError, match="SimulatedMPCSigner is active but SARDIS_ENVIRONMENT=prod"):
                    executor._init_mpc_signer()

    def test_production_import_error_fallback_raises(self):
        """ImportError fallback to SimulatedMPCSigner must be blocked in production even if chain_mode != live."""
        settings = _make_settings(
            mpc_name="circle",
            chain_mode="simulated",
            environment="prod",
        )
        executor = _make_executor(settings)

        # Trigger ImportError on circle imports
        with patch.dict(os.environ, {
            "SARDIS_CIRCLE_WALLET_API_KEY": "test-key",
        }):
            with patch.dict("sys.modules", {"sardis_wallet.circle_client": None}):
                with pytest.raises(RuntimeError, match="SimulatedMPCSigner is active but SARDIS_ENVIRONMENT=prod"):
                    executor._init_mpc_signer()

    def test_dev_environment_allows_simulated(self):
        """Dev environment must allow SimulatedMPCSigner without error (for local development)."""
        settings = _make_settings(
            mpc_name="circle",
            chain_mode="simulated",
            environment="dev",
        )
        executor = _make_executor(settings)

        # Trigger ImportError so it falls back to SimulatedMPCSigner
        with patch.dict(os.environ, {
            "SARDIS_CIRCLE_WALLET_API_KEY": "test-key",
        }):
            with patch.dict("sys.modules", {"sardis_wallet.circle_client": None}):
                executor._init_mpc_signer()

        assert isinstance(executor._mpc_signer, SimulatedMPCSigner)


class TestSimulatedMPCSignerBehavior:
    """SimulatedMPCSigner must still work in dev for legitimate dev use."""

    @pytest.mark.asyncio
    async def test_simulated_signer_returns_mock_hash(self):
        signer = SimulatedMPCSigner()
        tx = MagicMock()
        result = await signer.sign_transaction("wal_test", tx)
        assert result.startswith("0x")
        assert len(result) == 66  # 0x + 64 hex chars

    @pytest.mark.asyncio
    async def test_simulated_signer_returns_address(self):
        signer = SimulatedMPCSigner()
        addr = await signer.get_address("wal_test", "base")
        assert addr.startswith("0x")
        assert len(addr) == 42  # 0x + 40 hex chars
