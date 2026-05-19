import pytest
from fastapi import FastAPI

from server.route_registry.commerce import (
    register_checkout_routes,
    register_merchant_checkout_routes,
    register_merchant_routes,
    register_secure_checkout_routes,
)
from server.routes.commerce import checkout, merchant_checkout, merchants, secure_checkout


def test_register_checkout_routes_mounts_private_and_public_paths_with_dependencies() -> None:
    app = FastAPI()
    orchestrator = object()

    register_checkout_routes(
        app,
        database_url="memory://",
        use_postgres=False,
        orchestrator=orchestrator,
    )

    paths = {route.path for route in app.routes}
    assert "/api/v2/checkout" in paths
    assert "/api/v2/checkout/{checkout_id}" in paths
    assert "/api/v2/checkout/webhooks/{psp}" in paths
    assert "/api/v2/checkout/checkout/payment-methods" in paths

    deps = app.dependency_overrides[checkout.get_deps]()
    assert deps.orchestrator is orchestrator
    assert deps.wallet_repo is not None


def test_register_secure_checkout_routes_mounts_routes_and_dependencies(monkeypatch) -> None:
    monkeypatch.delenv("SARDIS_ENABLE_SECURE_CHECKOUT_EXECUTOR", raising=False)
    app = FastAPI()
    wallet_repo = object()
    agent_repo = object()
    card_repo = object()
    card_provider = object()
    policy_store = object()
    approval_service = object()
    audit_store = object()
    cache_service = object()

    register_secure_checkout_routes(
        app,
        database_url="memory://",
        use_postgres=False,
        is_production=False,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        card_repo=card_repo,
        card_provider=card_provider,
        policy_store=policy_store,
        approval_service=approval_service,
        audit_store=audit_store,
        cache_service=cache_service,
    )

    paths = {route.path for route in app.routes}
    assert "/api/v2/checkout/secure/security-policy" in paths
    assert "/api/v2/checkout/secure/jobs" in paths

    deps = app.dependency_overrides[secure_checkout.get_deps]()
    assert deps.wallet_repo is wallet_repo
    assert deps.agent_repo is agent_repo
    assert deps.card_repo is card_repo
    assert deps.card_provider is card_provider
    assert deps.policy_store is policy_store
    assert deps.approval_service is approval_service
    assert deps.audit_sink is audit_store
    assert deps.cache_service is cache_service
    assert isinstance(deps.store, secure_checkout.InMemorySecureCheckoutStore)


def test_register_secure_checkout_routes_respects_disabled_executor(monkeypatch) -> None:
    monkeypatch.setenv("SARDIS_ENABLE_SECURE_CHECKOUT_EXECUTOR", "0")
    app = FastAPI()

    register_secure_checkout_routes(
        app,
        database_url="memory://",
        use_postgres=False,
        is_production=False,
        wallet_repo=object(),
        agent_repo=object(),
        card_repo=object(),
        card_provider=object(),
        policy_store=object(),
        approval_service=object(),
        audit_store=object(),
        cache_service=object(),
    )

    paths = {route.path for route in app.routes}
    assert "/api/v2/checkout/secure/jobs" not in paths
    assert secure_checkout.get_deps in app.dependency_overrides


def test_register_secure_checkout_routes_requires_postgres_in_production(monkeypatch) -> None:
    monkeypatch.delenv("SARDIS_ENABLE_SECURE_CHECKOUT_EXECUTOR", raising=False)
    app = FastAPI()

    with pytest.raises(RuntimeError, match="secure_checkout_executor requires PostgreSQL"):
        register_secure_checkout_routes(
            app,
            database_url="memory://",
            use_postgres=False,
            is_production=True,
            wallet_repo=object(),
            agent_repo=object(),
            card_repo=object(),
            card_provider=object(),
            policy_store=object(),
            approval_service=object(),
            audit_store=object(),
            cache_service=object(),
        )


def test_register_merchant_routes_mounts_paths_and_dependencies() -> None:
    app = FastAPI()
    merchant_repo = object()
    wallet_manager = object()
    settlement_service = object()

    register_merchant_routes(
        app,
        merchant_repo=merchant_repo,
        wallet_manager=wallet_manager,
        settlement_service=settlement_service,
        checkout_base_url="https://checkout.test.sardis",
    )

    paths = {route.path for route in app.routes}
    assert "/api/v2/merchants" in paths
    assert "/api/v2/merchants/{merchant_id}" in paths
    assert "/api/v2/merchants/{merchant_id}/links" in paths
    assert "/api/v2/merchants/{merchant_id}/settlements" in paths

    deps = app.dependency_overrides[merchants.get_deps]()
    assert deps.merchant_repo is merchant_repo
    assert deps.wallet_manager is wallet_manager
    assert deps.settlement_service is settlement_service
    assert deps.checkout_base_url == "https://checkout.test.sardis"


def test_register_merchant_checkout_routes_mounts_private_and_public_paths_with_dependencies() -> None:
    app = FastAPI()
    merchant_repo = object()
    sardis_connector = object()
    wallet_manager = object()

    register_merchant_checkout_routes(
        app,
        merchant_repo=merchant_repo,
        sardis_connector=sardis_connector,
        wallet_manager=wallet_manager,
        checkout_base_url="https://checkout.test.sardis",
    )

    paths = {route.path for route in app.routes}
    assert "/api/v2/merchant-checkout/sessions" in paths
    assert "/api/v2/merchant-checkout/sessions/{session_id}" in paths
    assert "/api/v2/merchant-checkout/sessions/client/{client_secret}/details" in paths
    assert "/api/v2/merchant-checkout/sessions/client/{client_secret}/pay" in paths
    assert "/api/v2/merchant-checkout/links/{slug}" in paths

    deps = app.dependency_overrides[merchant_checkout.get_deps]()
    assert deps.merchant_repo is merchant_repo
    assert deps.sardis_connector is sardis_connector
    assert deps.wallet_manager is wallet_manager
    assert deps.checkout_base_url == "https://checkout.test.sardis"
