from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.route_registry.protocol import register_a2a_discovery_routes


def test_register_a2a_discovery_routes_mounts_well_known_agent_card() -> None:
    app = FastAPI()

    register_a2a_discovery_routes(app)

    paths = {route.path for route in app.routes}
    assert "/.well-known/agent-card.json" in paths


def test_well_known_agent_card_delegates_to_a2a_agent_card() -> None:
    app = FastAPI()
    register_a2a_discovery_routes(app)

    response = TestClient(app).get("/.well-known/agent-card.json")

    assert response.status_code == 200
    assert response.json()["agent_id"] == "sardis-platform"
