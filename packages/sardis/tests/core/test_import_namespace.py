from __future__ import annotations


def test_preferred_namespace_reexports_public_core_symbols() -> None:
    import sardis.core
    import sardis.core

    assert sardis_core.Wallet is sardis.core.Wallet
    assert sardis_core.Transaction is sardis.core.Transaction
    assert sardis_core.get_logger is sardis.core.get_logger


def test_preferred_namespace_resolves_existing_submodules() -> None:
    from sardis.core.budget_allocator import BudgetAllocator
    from sardis.core.circuit_breaker import CircuitBreakerConfig

    from sardis.core.budget_allocator import BudgetAllocator as LegacyBudgetAllocator
    from sardis.core.circuit_breaker import CircuitBreakerConfig as LegacyConfig

    assert CircuitBreakerConfig is LegacyConfig
    assert BudgetAllocator is LegacyBudgetAllocator
