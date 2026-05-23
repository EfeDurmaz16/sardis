"""Tests for Tempo + Solana chain config entries."""
import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core", "sardis-ledger"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_chain.config import (
    CHAIN_ID_MAP,
    ChainNetwork,
    build_default_config,
)


class TestChainNetworkEnum:
    def test_tempo_testnet_in_enum(self):
        assert ChainNetwork.TEMPO_TESTNET.value == "tempo_testnet"

    def test_tempo_in_enum(self):
        assert ChainNetwork.TEMPO.value == "tempo"

    def test_solana_devnet_in_enum(self):
        assert ChainNetwork.SOLANA_DEVNET.value == "solana_devnet"

    def test_solana_in_enum(self):
        assert ChainNetwork.SOLANA.value == "solana"


class TestChainIdMap:
    def test_tempo_testnet_chain_id(self):
        assert CHAIN_ID_MAP["tempo_testnet"] == 42431

    def test_tempo_mainnet_chain_id(self):
        assert CHAIN_ID_MAP["tempo"] == 4217

    def test_solana_devnet_chain_id(self):
        assert CHAIN_ID_MAP["solana_devnet"] == 0

    def test_solana_mainnet_chain_id(self):
        assert CHAIN_ID_MAP["solana"] == 0


class TestBuildDefaultConfig:
    def test_tempo_testnet_in_default_config(self):
        config = build_default_config()
        assert "tempo_testnet" in config.chains
        chain = config.chains["tempo_testnet"]
        assert chain.chain_id == 42431
        assert chain.is_testnet is True
        assert chain.native_token == "NONE"

    def test_tempo_mainnet_in_default_config(self):
        config = build_default_config()
        assert "tempo" in config.chains
        chain = config.chains["tempo"]
        assert chain.chain_id == 4217
        assert chain.is_testnet is False
        assert chain.native_token == "NONE"
        assert "rpc.tempo.xyz" in chain.get_primary_rpc_url()

    def test_solana_devnet_in_default_config(self):
        config = build_default_config()
        assert "solana_devnet" in config.chains
        chain = config.chains["solana_devnet"]
        assert chain.is_testnet is True
        assert chain.native_token == "SOL"
