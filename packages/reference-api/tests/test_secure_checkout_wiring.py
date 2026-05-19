from __future__ import annotations

from fastapi import FastAPI

from server.routes.commerce import secure_checkout
from server.route_registry.commerce import register_secure_checkout_routes


def test_secure_checkout_registrar_wires_router_with_flag(monkeypatch):
    monkeypatch.delenv("SARDIS_ENABLE_SECURE_CHECKOUT_EXECUTOR", raising=False)
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
    assert "/api/v2/checkout/secure/jobs" in paths
    assert secure_checkout.get_deps in app.dependency_overrides
