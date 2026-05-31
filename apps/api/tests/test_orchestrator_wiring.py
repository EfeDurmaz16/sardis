"""The prod orchestrator must have the moat ports wired, not inert.

Audit finding: the DI container and ``configure_payment_runtime`` built the
``PaymentOrchestrator`` WITHOUT the optional moat ports, so revocation (spending
mandate lookup), KYA, sanctions, durable dedup, and the settlement lock never
ran in production. These tests pin the wiring so the moat cannot silently go
inert again.
"""
from __future__ import annotations

import os

from sardis.core import load_settings

from server.dependencies import (
    DependencyConfig,
    DependencyContainer,
    build_moat_ports,
    configure_payment_runtime,
)


def _build_container() -> DependencyContainer:
    """Build the container the same way the app factory initialises it."""
    settings = load_settings()
    config = DependencyConfig.from_environment()
    return DependencyContainer(settings=settings, config=config)


def test_container_orchestrator_has_moat_ports_wired() -> None:
    """DependencyContainer.payment_orchestrator must inject the moat ports."""
    orch = _build_container().payment_orchestrator

    assert orch._spending_mandate_lookup is not None, (
        "mandate lookup not injected — revocation is inert"
    )
    assert orch._kya_service is not None, "KYA service not injected"
    assert orch._sanctions_service is not None, "sanctions service not injected"
    assert orch._dedup_store is not None
    assert orch._group_policy is not None


def test_payment_runtime_orchestrator_has_moat_ports_wired() -> None:
    """configure_payment_runtime (the production path used by create_app)
    must inject the moat ports too."""
    from unittest.mock import MagicMock

    settings = load_settings()
    runtime = configure_payment_runtime(
        settings=settings,
        database_url="memory://",
        use_postgres=False,
        identity_registry=MagicMock(name="identity_registry"),
        wallet_manager=MagicMock(name="wallet_manager"),
        compliance_engine=MagicMock(name="compliance_engine"),
        chain_executor=MagicMock(name="chain_executor"),
        ledger_store=MagicMock(name="ledger_store"),
        kya_service=MagicMock(name="kya_service"),
        sanctions_service=MagicMock(name="sanctions_service"),
    )
    orch = runtime.orchestrator

    assert orch._spending_mandate_lookup is not None, (
        "mandate lookup not injected — revocation is inert"
    )
    assert orch._kya_service is not None, "KYA service not injected"
    assert orch._sanctions_service is not None, "sanctions service not injected"
    assert orch._dedup_store is not None


def test_dedup_store_durable_and_settlement_lock_in_production() -> None:
    """In production/staging the dedup store must be durable (not in-memory)
    and a settlement lock must be present."""
    from sardis.core.dedup_store import InMemoryDedupStore

    env = os.getenv("SARDIS_ENVIRONMENT", "dev").lower()
    if env not in ("production", "prod", "staging"):
        import pytest

        pytest.skip("Production durability assertions only run in prod/staging env")

    orch = _build_container().payment_orchestrator
    assert not isinstance(orch._dedup_store, InMemoryDedupStore)
    assert orch._settlement_lock is not None


def test_build_moat_ports_fails_closed_without_redis_in_production() -> None:
    """In production, a missing/unbuildable Redis dedup store must raise rather
    than silently fall back to in-memory (non-durable) duplicate protection."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    import pytest

    prod_settings = SimpleNamespace(is_production=True)
    with pytest.raises(RuntimeError, match="durable Redis dedup store required"):
        build_moat_ports(
            prod_settings,
            database_url="postgresql://localhost/sardis",
            use_postgres=True,
            kya_service=MagicMock(),
            sanctions_service=MagicMock(),
            redis_url=None,
            environ={},  # no SARDIS_REDIS_URL/REDIS_URL/UPSTASH_REDIS_URL
        )


def test_build_moat_ports_allows_inmemory_dedup_outside_production() -> None:
    """Dev/test keep the in-memory dedup fallback (no raise)."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from sardis.core.dedup_store import InMemoryDedupStore

    dev_settings = SimpleNamespace(is_production=False)
    moat = build_moat_ports(
        dev_settings,
        database_url="memory://",
        use_postgres=False,
        kya_service=MagicMock(),
        sanctions_service=MagicMock(),
        redis_url=None,
        environ={},
    )
    assert isinstance(moat.dedup_store, InMemoryDedupStore)
