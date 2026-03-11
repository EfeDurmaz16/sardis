"""Tests for Tempo chain RPC integration."""
from sardis_chain.executor import CHAIN_CONFIGS


class TestTempoRPCRouting:
    def test_tempo_is_not_solana(self):
        """Tempo should NOT be routed to SolanaClient."""
        config = CHAIN_CONFIGS["tempo_testnet"]
        assert config.get("is_solana") is not True

    def test_tempo_is_evm_compatible(self):
        """Tempo should be routed through standard EVM RPC client."""
        config = CHAIN_CONFIGS["tempo_testnet"]
        # No is_solana flag = EVM path
        assert "is_solana" not in config or config["is_solana"] is False

    def test_tempo_has_no_native_gas_token(self):
        """Tempo has no native gas token — fees deducted from TIP-20."""
        config = CHAIN_CONFIGS["tempo_testnet"]
        assert config["native_token"] == "NONE"

    def test_tempo_has_is_tempo_flag(self):
        """Tempo chains should have is_tempo flag for special fee handling."""
        config = CHAIN_CONFIGS["tempo_testnet"]
        assert config.get("is_tempo") is True
