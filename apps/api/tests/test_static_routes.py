from fastapi import FastAPI

from server.route_registry.static_routes import register_static_public_routes


def test_register_static_public_routes_mounts_late_public_surface() -> None:
    app = FastAPI()

    register_static_public_routes(app)

    paths = {route.path for route in app.routes}
    assert "/api/v2/directory" in paths
    assert "/api/v2/compliance/export" in paths
    assert "/api/v2/agents/registry" in paths
    assert "/api/v2/settlements" in paths
    assert "/api/v2/evidence/transactions/{tx_id}" in paths
    assert "/api/v2/receipts/{receipt_id}" in paths
    assert "/api/v2/policies/simulate" in paths
    assert "/api/v2/templates" in paths
    assert "/api/v2/funding/commit" in paths
    assert "/api/v2/fx/quote" in paths
    assert "/api/v2/payments/batch" in paths
    assert "/api/v2/payments/stream/open" in paths
    assert "/api/v2/acp/checkout_sessions" in paths
    assert "/api/v2/onramp/session" in paths
    assert "/.well-known/agent-card.json" in paths
