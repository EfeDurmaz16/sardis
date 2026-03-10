"""Tests for UsageMeteringMiddleware (issue #76)."""
from __future__ import annotations

import importlib

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from sardis_api.billing.config import BillingConfig, PLAN_LIMITS
from sardis_api.middleware.usage_metering import (
    EXEMPT_PREFIXES,
    UsageMeteringMiddleware,
    _usage_counters,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(
    *,
    billing_enabled: bool = True,
    org_id: str | None = "org_test",
) -> FastAPI:
    """Build a minimal FastAPI app wrapped with UsageMeteringMiddleware."""
    inner = FastAPI()

    @inner.get("/api/v2/agents")
    async def metered_endpoint():
        return {"ok": True}

    @inner.get("/api/v2/billing/plans")
    async def billing_endpoint():
        return {"plans": []}

    @inner.get("/health")
    async def health():
        return {"status": "ok"}

    @inner.get("/api/v2/docs")
    async def docs():
        return {}

    @inner.get("/sandbox/demo")
    async def sandbox():
        return {}

    billing_cfg = BillingConfig(billing_enabled=billing_enabled)
    inner.add_middleware(UsageMeteringMiddleware, billing_config=billing_cfg)

    # Inject org_id into request.state the same way RBAC/auth middleware would.
    if org_id is not None:
        @inner.middleware("http")
        async def inject_org(request: Request, call_next):
            request.state.org_id = org_id
            return await call_next(request)

    return inner


@pytest.fixture(autouse=True)
def reset_counters():
    """Clear in-memory counters before every test."""
    _usage_counters.clear()
    yield
    _usage_counters.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exempt_billing_path_bypasses_metering():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/billing/plans")
    assert resp.status_code == 200
    assert "X-RateLimit-Limit" not in resp.headers


@pytest.mark.asyncio
async def test_exempt_health_path_bypasses_metering():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert "X-RateLimit-Limit" not in resp.headers


@pytest.mark.asyncio
async def test_exempt_docs_path_bypasses_metering():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/docs")
    assert resp.status_code == 200
    assert "X-RateLimit-Limit" not in resp.headers


@pytest.mark.asyncio
async def test_exempt_sandbox_path_bypasses_metering():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/sandbox/demo")
    assert resp.status_code == 200
    assert "X-RateLimit-Limit" not in resp.headers


@pytest.mark.asyncio
async def test_rate_limit_headers_added_for_metered_request():
    app = _make_app(org_id="org_header_test")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/agents")
    assert resp.status_code == 200
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers
    assert "X-RateLimit-Reset" in resp.headers

    plan_limit = PLAN_LIMITS["free"]["api_calls_per_month"]
    assert resp.headers["X-RateLimit-Limit"] == str(plan_limit)
    # After 1 call, remaining = limit - 1
    assert resp.headers["X-RateLimit-Remaining"] == str(plan_limit - 1)


@pytest.mark.asyncio
async def test_counter_increments_across_requests():
    org = "org_incr"
    app = _make_app(org_id=org)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(3):
            await client.get("/api/v2/agents")

    assert _usage_counters[org] == 3


@pytest.mark.asyncio
async def test_429_when_over_limit():
    org = "org_over_limit"
    # Artificially set counter to the limit.
    plan_limit = PLAN_LIMITS["free"]["api_calls_per_month"]
    _usage_counters[org] = plan_limit

    app = _make_app(org_id=org)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/agents")

    assert resp.status_code == 429
    body = resp.json()
    assert body["plan"] == "free"
    assert body["limit"] == plan_limit
    assert "sardis.sh/pricing" in body["detail"]


@pytest.mark.asyncio
async def test_no_metering_when_no_org_id():
    """Unauthenticated requests (no org_id on state) pass through without metering."""
    app = _make_app(org_id=None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/agents")
    assert resp.status_code == 200
    assert "X-RateLimit-Limit" not in resp.headers
    assert _usage_counters == {}


@pytest.mark.asyncio
async def test_no_op_when_billing_disabled():
    """Middleware is a complete no-op when billing_enabled=False."""
    org = "org_billing_off"
    app = _make_app(billing_enabled=False, org_id=org)
    # Pre-seed counter beyond limit — should still be let through.
    plan_limit = PLAN_LIMITS["free"]["api_calls_per_month"]
    _usage_counters[org] = plan_limit + 9999

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/agents")

    assert resp.status_code == 200
    assert "X-RateLimit-Limit" not in resp.headers


@pytest.mark.asyncio
async def test_remaining_header_clamps_to_zero():
    """X-RateLimit-Remaining must not go negative."""
    org = "org_clamp"
    plan_limit = PLAN_LIMITS["free"]["api_calls_per_month"]
    # Set to limit-1 so after increment it equals limit, remaining = 0.
    _usage_counters[org] = plan_limit - 1

    app = _make_app(org_id=org)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/agents")

    assert resp.status_code == 200
    assert resp.headers["X-RateLimit-Remaining"] == "0"


@pytest.mark.parametrize("prefix", list(EXEMPT_PREFIXES))
@pytest.mark.asyncio
async def test_all_exempt_prefixes_constant(prefix: str):
    """Verify the EXEMPT_PREFIXES tuple contains expected values."""
    assert isinstance(prefix, str)
    assert prefix.startswith("/")
