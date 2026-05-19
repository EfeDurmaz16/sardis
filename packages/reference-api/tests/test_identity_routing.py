from fastapi import FastAPI

from server.routing.identity import register_agent_auth_routes, register_sso_routes


def test_register_agent_auth_routes_mounts_discovery_and_management_routes():
    app = FastAPI()

    register_agent_auth_routes(app)

    paths = {route.path for route in app.routes}
    assert "/.well-known/agent-configuration" in paths
    assert "/api/v2/capability/list" in paths
    assert "/api/v2/capability/execute" in paths
    assert "/api/v2/agent/register" in paths


def test_register_sso_routes_mounts_enterprise_auth_routes():
    app = FastAPI()

    register_sso_routes(app)

    paths = {route.path for route in app.routes}
    assert "/api/v2/auth/sso/init" in paths
    assert "/api/v2/auth/sso/oidc/callback" in paths
    assert "/api/v2/auth/sso/saml/acs" in paths
