from fastapi import FastAPI

from server.routing.money_movement import register_swap_routes


def test_register_swap_routes_mounts_swap_exchange_and_verification_paths() -> None:
    app = FastAPI()

    register_swap_routes(app)

    paths = {route.path for route in app.routes}
    assert "/api/v2/swap/quote" in paths
    assert "/api/v2/swap/execute" in paths
    assert "/api/v2/exchange/quote" in paths
    assert "/api/v2/exchange/trade" in paths
    assert "/api/v2/exchange/settlements" in paths
    assert "/api/v2/verifications/{address}" in paths
