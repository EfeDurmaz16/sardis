"""Tests for Tempo settlement routing."""
from sardis_checkout.config import CHECKOUT_CHAIN_CONFIG, get_checkout_chain_config
from sardis_checkout.settlement import _TEMPO_CHAINS


class TestTempoSettlementConfig:
    """Verify settlement configuration supports Tempo."""

    def test_tempo_in_checkout_chain_config(self):
        assert "tempo" in CHECKOUT_CHAIN_CONFIG

    def test_tempo_testnet_in_checkout_chain_config(self):
        assert "tempo_testnet" in CHECKOUT_CHAIN_CONFIG

    def test_tempo_chain_id(self):
        assert CHECKOUT_CHAIN_CONFIG["tempo"]["chain_id"] == 4217

    def test_tempo_fee_model_is_tip20(self):
        assert CHECKOUT_CHAIN_CONFIG["tempo"]["fee_model"] == "tip20"

    def test_tempo_has_usdc_address(self):
        assert CHECKOUT_CHAIN_CONFIG["tempo"]["usdc_address"] == "0x20c0000000000000000000000000000000000000"

    def test_tempo_has_usdc_e_address(self):
        assert CHECKOUT_CHAIN_CONFIG["tempo"]["usdc_e_address"] == "0x20C000000000000000000000b9537d11c60E8b50"

    def test_base_fee_model_is_native(self):
        assert CHECKOUT_CHAIN_CONFIG["base"]["fee_model"] == "native"


class TestTempoChainIdentifiers:
    """Verify Tempo chain identifiers for settlement routing."""

    def test_tempo_chains_includes_tempo(self):
        assert "tempo" in _TEMPO_CHAINS

    def test_tempo_chains_includes_testnet(self):
        assert "tempo_testnet" in _TEMPO_CHAINS

    def test_tempo_chains_does_not_include_base(self):
        assert "base" not in _TEMPO_CHAINS
