from __future__ import annotations


def test_preferred_namespace_resolves_existing_submodules() -> None:
    from sardis.core.budget_allocator import BudgetAllocator
    from sardis.core.circuit_breaker import CircuitBreakerConfig

    assert BudgetAllocator is not None
    assert CircuitBreakerConfig is not None


def test_public_core_symbols_exist() -> None:
    import sardis.core

    assert hasattr(sardis.core, "Wallet")
    assert hasattr(sardis.core, "Transaction")
    assert hasattr(sardis.core, "get_logger")
