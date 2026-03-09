"""Health check endpoint tests."""
from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_root_endpoint(test_client):
    """Test root endpoint returns service info."""
    response = await test_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Sardis API"
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.anyio
async def test_health_endpoint(test_client):
    """Test health endpoint returns component status."""
    response = await test_client.get("/health")

    # In test environment without full infrastructure, may return 503 (degraded)
    assert response.status_code in (200, 503)
    data = response.json()
    # In test environment without full infrastructure, status may vary
    assert data["status"] in ("healthy", "degraded", "partial")
    assert "components" in data
    assert "database" in data["components"]
    assert "execution_mode" in data
    assert data["execution_mode"] in ("simulated", "staging_live", "production_live")
    assert "critical_failures" in data
    assert "non_critical_failures" in data
    assert isinstance(data["critical_failures"], list)
    assert isinstance(data["non_critical_failures"], list)
    assert data["components"]["chain_executor"]["execution_mode"] == data["execution_mode"]
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], int)


@pytest.mark.anyio
async def test_health_components_have_standardized_status(test_client):
    """All health components use healthy/degraded/unhealthy status vocabulary."""
    response = await test_client.get("/health")
    assert response.status_code in (200, 503)

    data = response.json()
    allowed_statuses = {
        "healthy", "degraded", "unhealthy",
        # Acceptable contextual statuses
        "unconfigured", "check_required", "disabled_dev_mode",
        "active", "clear", "error",
        # Custody-specific
        "simulated_or_sandbox", "non_custodial_mpc",
        "custodial_local_signer", "misconfigured",
        # TAP JWKS dev-mode
        "not_required_in_dev",
    }
    for name, comp in data["components"].items():
        status = comp.get("status")
        assert status is not None, f"Component {name} missing status"
        assert status in allowed_statuses, (
            f"Component {name} has unexpected status '{status}', "
            f"expected one of {allowed_statuses}"
        )


@pytest.mark.anyio
async def test_health_tap_jwks_component(test_client):
    """Health endpoint should include tap_jwks component."""
    response = await test_client.get("/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "tap_jwks" in data["components"]
    tap = data["components"]["tap_jwks"]
    assert "status" in tap


@pytest.mark.anyio
async def test_health_failure_entries_are_structured(test_client):
    """Health failures should include machine-readable component and reason code."""
    response = await test_client.get("/health")
    assert response.status_code in (200, 503)

    data = response.json()
    failures = data.get("critical_failures", []) + data.get("non_critical_failures", [])
    for failure in failures:
        assert "component" in failure
        assert "reason_code" in failure
        assert "detail" in failure

    assert "rpc" in data["components"]
    assert "contracts" in data["components"]


@pytest.mark.anyio
async def test_health_live_endpoint(test_client):
    """Test /health/live liveness probe returns alive."""
    response = await test_client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.anyio
async def test_live_endpoint_legacy(test_client):
    """Test /live legacy alias also returns alive."""
    response = await test_client.get("/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.anyio
async def test_ready_endpoint(test_client):
    """Test /ready endpoint returns ready when app.state.ready is True."""
    response = await test_client.get("/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


@pytest.mark.anyio
async def test_ready_endpoint_not_ready():
    """Test /ready returns 503 when app.state.ready is not set."""
    from httpx import ASGITransport, AsyncClient
    from sardis_api.main import create_app

    app = create_app()
    # Do NOT set app.state.ready — simulates pre-startup

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"


@pytest.mark.anyio
async def test_health_returns_503_when_not_ready():
    """Test /health returns 503 with not_ready when startup incomplete."""
    from httpx import ASGITransport, AsyncClient
    from sardis_api.main import create_app

    app = create_app()
    # Do NOT set app.state.ready

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"


@pytest.mark.anyio
async def test_api_v2_health(test_client):
    """Test API v2 health endpoint."""
    response = await test_client.get("/api/v2/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"


@pytest.mark.anyio
async def test_api_root_discovery(test_client):
    """Test API root discovery endpoint."""
    response = await test_client.get("/api")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["latest"] == "/api/v2"
    assert data["docs"] == "/api/v2/docs"


@pytest.mark.anyio
async def test_api_v2_root_discovery(test_client):
    """Test API v2 root discovery endpoint."""
    response = await test_client.get("/api/v2")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["docs"] == "/api/v2/docs"
    assert data["openapi"] == "/api/v2/openapi.json"


@pytest.mark.anyio
async def test_metrics_health_returns_uptime(test_client):
    """Test /metrics/health returns uptime and ready flag."""
    response = await test_client.get("/metrics/health")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "sardis-api"
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], int)
    assert data["ready"] is True
    assert data["status"] == "healthy"
