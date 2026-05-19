from types import SimpleNamespace

from fastapi import FastAPI

from server.route_registry.health import register_health_routes


def test_register_health_routes_mounts_liveness_readiness_and_discovery_paths() -> None:
    app = FastAPI()
    shutdown_state = SimpleNamespace(is_shutting_down=False)
    settings = SimpleNamespace(chain_mode="simulated")

    register_health_routes(
        app,
        shutdown_state=shutdown_state,
        use_postgres=False,
        database_url="memory://",
        redis_url="",
        settings=settings,
    )

    paths = {route.path for route in app.routes}
    assert "/" in paths
    assert "/health/live" in paths
    assert "/ready" in paths
    assert "/health" in paths
    assert "/api/v2/health" in paths
