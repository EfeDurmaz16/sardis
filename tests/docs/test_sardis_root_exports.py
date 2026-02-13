"""Contracts for root `sardis` package exports used in docs/examples."""

from __future__ import annotations

import importlib.util


def test_root_exports_cover_documented_symbols() -> None:
    import sardis

    documented = {
        "SardisClient",
        "Wallet",
        "Transaction",
        "TransactionResult",
        "TransactionStatus",
        "Policy",
        "PolicyResult",
        "Agent",
        "AgentGroup",
    }

    exported = set(sardis.__all__)
    assert documented.issubset(exported)
    for symbol in documented:
        assert hasattr(sardis, symbol)


def test_sdk_reexports_are_conditional_and_consistent() -> None:
    import sardis

    sdk_symbols = {"AsyncSardisClient", "RetryConfig", "TimeoutConfig"}
    sdk_installed = importlib.util.find_spec("sardis_sdk") is not None

    if sdk_installed:
        assert sdk_symbols.issubset(set(sardis.__all__))
        for symbol in sdk_symbols:
            assert hasattr(sardis, symbol)
    else:
        assert sdk_symbols.isdisjoint(set(sardis.__all__))
