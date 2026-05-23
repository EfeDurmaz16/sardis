from __future__ import annotations


def test_preferred_namespace_reexports_public_core_symbols() -> None:
    import sardis_core
    import sardis_v2_core

    assert sardis_core.Wallet is sardis_v2_core.Wallet
    assert sardis_core.Transaction is sardis_v2_core.Transaction
    assert sardis_core.get_logger is sardis_v2_core.get_logger


def test_preferred_namespace_resolves_existing_submodules() -> None:
    from sardis_core.budget_allocator import BudgetAllocator
    from sardis_core.circuit_breaker import CircuitBreakerConfig
    from sardis_v2_core.budget_allocator import BudgetAllocator as LegacyBudgetAllocator
    from sardis_v2_core.circuit_breaker import CircuitBreakerConfig as LegacyConfig

    assert CircuitBreakerConfig is LegacyConfig
    assert BudgetAllocator is LegacyBudgetAllocator
