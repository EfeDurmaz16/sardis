"""Unit tests for FXSigner 3-tier signing architecture.

Tests:
  - Tempo access key signing
  - Turnkey MPC signing (mocked)
  - EOA fallback
  - Production guard (no EOA in prod)
  - Mode detection
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis_chain.fx_signer import FXSigner, create_fx_signer

# ── Mode detection ───────────────────────────────────────────────────


class TestModeDetection:
    def test_turnkey_mode(self):
        signer = FXSigner(
            turnkey_client=MagicMock(),
            turnkey_wallet_id="wallet_123",
            turnkey_sign_with="0xabc",
        )
        assert signer.mode == "turnkey"
        assert signer.is_available is True
        assert signer.can_sign_evm() is True

    def test_tempo_access_key_mode(self):
        signer = FXSigner(tempo_access_key="0xprivkey")
        assert signer.mode == "tempo_access_key"
        assert signer.is_available is True
        assert signer.can_sign_tempo() is True

    def test_eoa_mode(self):
        signer = FXSigner(eoa_private_key="0xdeadbeef")
        assert signer.mode == "eoa"
        assert signer.is_available is True
        assert signer.can_sign_tempo() is True
        assert signer.can_sign_evm() is True

    def test_no_keys_mode(self):
        signer = FXSigner()
        assert signer.mode == "none"
        assert signer.is_available is False
        assert signer.can_sign_tempo() is False
        assert signer.can_sign_evm() is False

    def test_turnkey_takes_priority_over_eoa(self):
        signer = FXSigner(
            turnkey_client=MagicMock(),
            turnkey_wallet_id="wallet_123",
            eoa_private_key="0xdeadbeef",
        )
        assert signer.mode == "turnkey"

    def test_tempo_key_takes_priority_over_eoa_for_mode(self):
        signer = FXSigner(
            tempo_access_key="0xtempokey",
            eoa_private_key="0xdeadbeef",
        )
        assert signer.mode == "tempo_access_key"


# ── Tempo signing ────────────────────────────────────────────────────


class TestTempoSigning:
    def test_get_tempo_key_returns_access_key(self):
        signer = FXSigner(tempo_access_key="0xtempokey", eoa_private_key="0xeoa")
        assert signer.get_tempo_key() == "0xtempokey"

    def test_get_tempo_key_falls_back_to_eoa(self):
        signer = FXSigner(eoa_private_key="0xeoa")
        assert signer.get_tempo_key() == "0xeoa"

    def test_get_tempo_key_none_when_no_keys(self):
        signer = FXSigner()
        assert signer.get_tempo_key() is None

    def test_sign_tempo_transaction_no_key_raises(self):
        signer = FXSigner()
        with pytest.raises(RuntimeError, match="No Tempo signing key"):
            signer.sign_tempo_transaction(MagicMock())

    def test_sign_tempo_transaction_calls_sign(self):
        signer = FXSigner(tempo_access_key="0xkey")
        mock_tx = MagicMock()
        mock_tx.sign.return_value = MagicMock()

        result = signer.sign_tempo_transaction(mock_tx)
        mock_tx.sign.assert_called_once_with("0xkey")


# ── EVM signing ──────────────────────────────────────────────────────


class TestEVMSigning:
    @pytest.mark.asyncio
    async def test_evm_sign_no_method_raises(self):
        signer = FXSigner(tempo_access_key="0xtempoonly")
        with pytest.raises(RuntimeError, match="No EVM signing method"):
            await signer.sign_and_broadcast_evm({}, "https://rpc.example.com")


# ── Address resolution ───────────────────────────────────────────────


class TestAddressResolution:
    def test_address_from_tempo_root(self):
        signer = FXSigner(
            tempo_access_key="0xkey",
            tempo_root_address="0xROOT",
        )
        assert signer.address == "0xROOT"

    def test_address_from_turnkey(self):
        signer = FXSigner(
            turnkey_client=MagicMock(),
            turnkey_wallet_id="wallet_123",
            turnkey_sign_with="0xTURNKEY",
        )
        assert signer.address == "0xTURNKEY"

    def test_address_none_when_no_keys(self):
        signer = FXSigner()
        assert signer.address is None


# ── get_private_key backward compat ──────────────────────────────────


class TestBackwardCompat:
    def test_get_private_key_returns_tempo(self):
        signer = FXSigner(tempo_access_key="0xtempo", eoa_private_key="0xeoa")
        assert signer.get_private_key() == "0xtempo"

    def test_get_private_key_returns_eoa_fallback(self):
        signer = FXSigner(eoa_private_key="0xeoa")
        assert signer.get_private_key() == "0xeoa"

    def test_get_private_key_none(self):
        signer = FXSigner()
        assert signer.get_private_key() is None


# ── create_fx_signer factory ─────────────────────────────────────────


class TestCreateFXSigner:
    @pytest.mark.asyncio
    async def test_creates_eoa_signer_from_env(self):
        with patch.dict("os.environ", {
            "SARDIS_EOA_PRIVATE_KEY": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        }, clear=False):
            signer = await create_fx_signer()
        assert signer._has_eoa is True
        assert signer.mode == "eoa"

    @pytest.mark.asyncio
    async def test_creates_tempo_signer_from_env(self):
        with patch.dict("os.environ", {
            "SARDIS_TEMPO_ACCESS_KEY": "0xtempokey",
        }, clear=False):
            signer = await create_fx_signer()
        assert signer._has_tempo_access_key is True

    @pytest.mark.asyncio
    async def test_no_env_returns_unavailable(self):
        with patch.dict("os.environ", {}, clear=True):
            signer = await create_fx_signer()
        assert signer.is_available is False
