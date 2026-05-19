from fastapi import FastAPI

from server.route_registry.authority import register_spending_mandate_routes


def test_register_spending_mandate_routes_mounts_crud_and_lifecycle_paths() -> None:
    app = FastAPI()

    register_spending_mandate_routes(app)

    paths = {route.path for route in app.routes}
    assert "/api/v2/spending-mandates" in paths
    assert "/api/v2/spending-mandates/{mandate_id}" in paths
    assert "/api/v2/spending-mandates/{mandate_id}/revoke" in paths
    assert "/api/v2/spending-mandates/{mandate_id}/transitions" in paths
