from fastapi import FastAPI

from sardis_server.routing.providers import register_mastercard_webhook_routes


def test_register_mastercard_webhook_routes_mounts_public_route():
    app = FastAPI()

    register_mastercard_webhook_routes(app)

    paths = {route.path for route in app.routes}
    assert "/mastercard/webhooks" in paths
