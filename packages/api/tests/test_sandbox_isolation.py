"""Tests for per-developer sandbox isolation (GitHub issue #106)."""
from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _namespace_for(token: str) -> str:
    return f"ns_{hashlib.sha256(token.encode()).hexdigest()[:16]}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_sandbox_manager():
    """Reset the global SandboxStoreManager before every test for isolation."""
    from sardis_api.routers import sandbox as sandbox_mod
    sandbox_mod._manager = sandbox_mod.SandboxStoreManager()
    yield
    # No teardown needed; next test resets again.


@pytest.fixture
def app():
    from sardis_api.main import create_app
    return create_app()


@pytest.fixture
async def anon_client(app) -> AsyncClient:
    """Client with no Authorization header."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def dev_a_client(app) -> AsyncClient:
    """Client authenticated as developer A."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=_auth_header("token_developer_a"),
    ) as ac:
        yield ac


@pytest.fixture
async def dev_b_client(app) -> AsyncClient:
    """Client authenticated as developer B."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=_auth_header("token_developer_b"),
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Isolation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_different_auth_tokens_get_different_stores(dev_a_client, dev_b_client):
    """Two different Bearer tokens must see completely independent sandbox stores."""
    # Both start with seed data — ledger entries are identical in count.
    # Create a wallet in dev_a's namespace.
    resp_a = await dev_a_client.post(
        "/api/v2/sandbox/create-wallet",
        json={"agent_name": "Agent A Only", "initial_balance": "777.00"},
    )
    assert resp_a.status_code == 200
    wallet_a_agent_id = resp_a.json()["agent_id"]

    # dev_b must not see dev_a's wallet / agent in its demo-data.
    data_b = await dev_b_client.get("/api/v2/sandbox/demo-data")
    assert data_b.status_code == 200
    agent_ids_in_b = {a["agent_id"] for a in data_b.json()["agents"]}
    assert wallet_a_agent_id not in agent_ids_in_b


@pytest.mark.asyncio
async def test_unauthenticated_requests_share_demo_namespace(anon_client, app):
    """Two unauthenticated clients (different instances) share the __demo__ namespace."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as second_anon:
        resp1 = await anon_client.post(
            "/api/v2/sandbox/create-wallet",
            json={"agent_name": "Shared Anon Wallet"},
        )
        assert resp1.status_code == 200
        new_agent_id = resp1.json()["agent_id"]

        # The same agent should appear in the second unauthenticated client's view.
        data2 = await second_anon.get("/api/v2/sandbox/demo-data")
        assert data2.status_code == 200
        agent_ids = {a["agent_id"] for a in data2.json()["agents"]}
        assert new_agent_id in agent_ids


@pytest.mark.asyncio
async def test_post_reset_only_resets_caller_namespace(dev_a_client, dev_b_client):
    """POST /sandbox/reset only resets the caller's namespace, not others."""
    # Create distinct wallets in each namespace.
    resp_a = await dev_a_client.post(
        "/api/v2/sandbox/create-wallet",
        json={"agent_name": "A Before Reset"},
    )
    assert resp_a.status_code == 200
    agent_a_id = resp_a.json()["agent_id"]

    resp_b = await dev_b_client.post(
        "/api/v2/sandbox/create-wallet",
        json={"agent_name": "B Before Reset"},
    )
    assert resp_b.status_code == 200
    agent_b_id = resp_b.json()["agent_id"]

    # Reset dev_a's namespace only.
    reset_resp = await dev_a_client.post("/api/v2/sandbox/reset")
    assert reset_resp.status_code == 200

    # dev_a should no longer see its created agent (store was re-seeded).
    data_a = await dev_a_client.get("/api/v2/sandbox/demo-data")
    agent_ids_a = {a["agent_id"] for a in data_a.json()["agents"]}
    assert agent_a_id not in agent_ids_a

    # dev_b's data must be untouched.
    data_b = await dev_b_client.get("/api/v2/sandbox/demo-data")
    agent_ids_b = {a["agent_id"] for a in data_b.json()["agents"]}
    assert agent_b_id in agent_ids_b


@pytest.mark.asyncio
async def test_delete_reset_only_resets_caller_namespace(dev_a_client, dev_b_client):
    """DELETE /sandbox/reset (legacy method) behaves the same as POST."""
    resp_b = await dev_b_client.post(
        "/api/v2/sandbox/create-wallet",
        json={"agent_name": "B Delete Reset Test"},
    )
    assert resp_b.status_code == 200
    agent_b_id = resp_b.json()["agent_id"]

    # dev_a deletes its own namespace.
    reset_resp = await dev_a_client.delete("/api/v2/sandbox/reset")
    assert reset_resp.status_code == 200

    # dev_b data must still be present.
    data_b = await dev_b_client.get("/api/v2/sandbox/demo-data")
    agent_ids_b = {a["agent_id"] for a in data_b.json()["agents"]}
    assert agent_b_id in agent_ids_b


# ---------------------------------------------------------------------------
# Rate limiting tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_returns_429_after_60_requests(app):
    """After 60 requests within the rate-limit window the 61st must return 429."""
    from sardis_api.routers.sandbox import RATE_LIMIT_WINDOW_SECONDS, _manager

    token = "token_rate_limit_test"
    namespace = _namespace_for(token)

    # Pre-fill the rate limit bucket to just below the threshold.
    now = time.monotonic()
    _manager._rate_limits[namespace] = [now] * 59

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=_auth_header(token),
    ) as client:
        # 60th request — should still succeed.
        resp60 = await client.get("/api/v2/sandbox/demo-data")
        assert resp60.status_code == 200

        # 61st request — must be rate-limited.
        resp61 = await client.get("/api/v2/sandbox/demo-data")
        assert resp61.status_code == 429
        assert "rate limit" in resp61.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rate_limit_resets_after_window(app):
    """Requests outside the window are not counted toward the limit."""
    from sardis_api.routers.sandbox import RATE_LIMIT_WINDOW_SECONDS, _manager

    token = "token_window_expiry_test"
    namespace = _namespace_for(token)

    # Simulate 60 timestamps that are just outside the window (already expired).
    old_time = time.monotonic() - RATE_LIMIT_WINDOW_SECONDS - 1
    _manager._rate_limits[namespace] = [old_time] * 60

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=_auth_header(token),
    ) as client:
        # First request after window expiry — should be allowed.
        resp = await client.get("/api/v2/sandbox/demo-data")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TTL / expiry tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stores_expire_after_24h_inactivity(app):
    """A store whose last_accessed is >24h ago is evicted on next access."""
    from sardis_api.routers.sandbox import _manager

    token = "token_ttl_expiry_test"
    namespace = _namespace_for(token)

    # Manually create a store and backdate its last_accessed by more than 24h.
    from sardis_api.routers.sandbox import SandboxStore
    stale_store = SandboxStore()
    stale_store.last_accessed = datetime.now(UTC) - timedelta(hours=25)
    _manager._stores[namespace] = stale_store
    _manager._rate_limits[namespace] = []

    # Record identity of the stale store.
    stale_id = id(stale_store)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=_auth_header(token),
    ) as client:
        # Accessing the endpoint triggers eviction + fresh store creation.
        resp = await client.get("/api/v2/sandbox/demo-data")
        assert resp.status_code == 200

    # The manager should now hold a different (new) store for that namespace.
    current_store = _manager._stores.get(namespace)
    assert current_store is not None
    assert id(current_store) != stale_id
