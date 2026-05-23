"""Tests for Solana payment dispatch chain detection."""
from sardis_chain.executor import CHAIN_CONFIGS


class TestSolanaChainDetection:
    def test_solana_devnet_has_is_solana_flag(self):
        assert CHAIN_CONFIGS["solana_devnet"].get("is_solana") is True

    def test_solana_mainnet_has_is_solana_flag(self):
        assert CHAIN_CONFIGS["solana"].get("is_solana") is True

    def test_tempo_does_not_have_is_solana_flag(self):
        assert CHAIN_CONFIGS["tempo_testnet"].get("is_solana") is not True

    def test_base_does_not_have_is_solana_flag(self):
        assert CHAIN_CONFIGS["base"].get("is_solana") is not True

    def test_ethereum_does_not_have_is_solana_flag(self):
        assert CHAIN_CONFIGS["ethereum"].get("is_solana") is not True
