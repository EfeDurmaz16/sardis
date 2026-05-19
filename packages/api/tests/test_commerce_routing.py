from fastapi import FastAPI

from sardis_server.routes.commerce import checkout
from sardis_server.routing.commerce import register_checkout_routes


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
