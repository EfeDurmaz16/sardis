"""Test F16: Configurable confirmation counts per chain.

Tests CHAIN_CONFIRMATIONS class-level dict on ChainExecutor without instantiation.
"""
from sardis_chain.executor import ChainExecutor


def test_confirmation_counts_configured():
    """All major chains have explicit confirmation counts."""
    for chain in ("ethereum", "base", "polygon", "arbitrum", "optimism"):
        assert chain in ChainExecutor.CHAIN_CONFIRMATIONS, (
            f"Chain '{chain}' missing from CHAIN_CONFIRMATIONS"
        )


def test_ethereum_requires_most_confirmations():
    """Ethereum requires 12 confirmations for finality."""
    assert ChainExecutor.get_confirmations_required("ethereum") == 12


def test_base_requires_fewer_confirmations():
    """Base requires 3 confirmations due to faster finality."""
    assert ChainExecutor.get_confirmations_required("base") == 3


def test_polygon_requires_many_confirmations():
    """Polygon requires 10 confirmations due to reorg risk."""
    assert ChainExecutor.get_confirmations_required("polygon") == 10


def test_l2_chains_require_fewer_confirmations():
    """L2 chains (Arbitrum, Optimism) require fewer confirmations."""
    assert ChainExecutor.get_confirmations_required("arbitrum") == 3
    assert ChainExecutor.get_confirmations_required("optimism") == 3


def test_unknown_chain_gets_safe_default():
    """Unknown chains default to 12 confirmations (safest)."""
    assert ChainExecutor.get_confirmations_required("unknown_chain") == 12


def test_case_insensitive_chain_lookup():
    """Chain name lookup is case-insensitive."""
    assert ChainExecutor.get_confirmations_required("ETHEREUM") == 12
    assert ChainExecutor.get_confirmations_required("Ethereum") == 12
    assert ChainExecutor.get_confirmations_required("ethereum") == 12


def test_testnet_chains_configured():
    """Testnet chains are also configured."""
    assert "base_sepolia" in ChainExecutor.CHAIN_CONFIRMATIONS
    assert "polygon_amoy" in ChainExecutor.CHAIN_CONFIRMATIONS


def test_no_chain_has_zero_confirmations():
    """No chain is configured with 0 confirmations (unsafe)."""
    for chain, count in ChainExecutor.CHAIN_CONFIRMATIONS.items():
        assert count > 0, f"Chain {chain} must require at least 1 confirmation"


def test_ethereum_has_highest_or_equal_confirmations():
    """Ethereum has the highest or equal confirmation requirement."""
    eth_confs = ChainExecutor.CHAIN_CONFIRMATIONS["ethereum"]
    for chain, count in ChainExecutor.CHAIN_CONFIRMATIONS.items():
        assert count <= eth_confs, (
            f"Chain {chain} should not require more confirmations than Ethereum"
        )


def test_confirmation_counts_are_reasonable():
    """All confirmation counts are in a reasonable range (1-15)."""
    for chain, count in ChainExecutor.CHAIN_CONFIRMATIONS.items():
        assert 1 <= count <= 15, (
            f"Chain {chain} has unreasonable confirmation count: {count}"
        )
