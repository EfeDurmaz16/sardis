"""Tests for Tempo token registry entries."""
from sardis_v2_core.tokens import TOKEN_REGISTRY, TokenType, get_tokens_for_chain


class TestTempoTokenRegistry:
    def test_usdc_has_tempo_testnet_address(self):
        usdc = TOKEN_REGISTRY[TokenType.USDC]
        assert "tempo_testnet" in usdc.contract_addresses
        assert usdc.contract_addresses["tempo_testnet"].startswith("0x")

    def test_get_tokens_for_tempo_testnet(self):
        tokens = get_tokens_for_chain("tempo_testnet")
        assert TokenType.USDC in tokens
