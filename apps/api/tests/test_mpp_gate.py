"""Tests for the MPP-conformant pay-per-request gate (middleware/mpp_gate.py).

Focus: the money-path correctness fix — a paid gate must NEVER serve free data
when it cannot verify payment (pympp missing or MPP_SECRET_KEY unset), and the
replay store must be atomic + fail-closed.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

mpp_gate_mod = importlib.import_module("server.middleware.mpp_gate")
from server.middleware.mpp_gate import (  # noqa: E402
    _Mpp402,
    _mpp_402_handler,
    mpp_gate,
    reset_mpp_server,
)
from server.middleware.mpp_replay_store import CacheBackedReplayStore  # noqa: E402


def _make_gated_app(price: str = "0.01") -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(_Mpp402, _mpp_402_handler)

    @app.get("/paid", dependencies=[Depends(mpp_gate(price=price))])
    async def paid():
        return {"data": "secret-intelligence"}

    return app


@pytest.fixture(autouse=True)
def _reset_server():
    reset_mpp_server()
    yield
    reset_mpp_server()


# ---------------------------------------------------------------------------
# S1/S2 — fail-closed when payment cannot be verified
# ---------------------------------------------------------------------------


class TestGateFailsClosed:
    def test_no_pympp_no_auth_is_not_free(self, monkeypatch):
        """pympp absent + unauthenticated => 503, NEVER 200-free."""
        monkeypatch.setattr(mpp_gate_mod, "_HAS_MPP", False)
        app = _make_gated_app()
        with TestClient(app) as c:
            r = c.get("/paid")
        assert r.status_code == 503
        assert r.json()["error"] == "payment_verification_unavailable"
        assert "secret-intelligence" not in r.text

    def test_no_pympp_with_payment_credential_is_not_free(self, monkeypatch):
        """pympp absent + a 'Payment ...' credential => 503, never serves data."""
        monkeypatch.setattr(mpp_gate_mod, "_HAS_MPP", False)
        app = _make_gated_app()
        with TestClient(app) as c:
            r = c.get("/paid", headers={"Authorization": "Payment deadbeef"})
        assert r.status_code == 503
        assert "secret-intelligence" not in r.text

    def test_pympp_present_but_secret_unset_is_not_free(self, monkeypatch):
        """pympp present but MPP_SECRET_KEY unset => still 503, never free."""
        monkeypatch.setattr(mpp_gate_mod, "_HAS_MPP", True)
        monkeypatch.delenv("MPP_SECRET_KEY", raising=False)
        app = _make_gated_app()
        with TestClient(app) as c:
            r = c.get("/paid")
        assert r.status_code == 503
        assert "secret-intelligence" not in r.text

    def test_blank_secret_is_treated_as_unset(self, monkeypatch):
        monkeypatch.setattr(mpp_gate_mod, "_HAS_MPP", True)
        monkeypatch.setenv("MPP_SECRET_KEY", "   ")
        app = _make_gated_app()
        with TestClient(app) as c:
            r = c.get("/paid")
        assert r.status_code == 503

    def test_authenticated_user_passes_through_free(self, monkeypatch):
        """A non-'Payment ' Authorization header => free passthrough (auth handled
        by the endpoint's own dependency). Independent of pympp state."""
        monkeypatch.setattr(mpp_gate_mod, "_HAS_MPP", False)
        app = _make_gated_app()
        with TestClient(app) as c:
            r = c.get("/paid", headers={"Authorization": "Bearer dummy-api-token"})
        assert r.status_code == 200
        assert r.json()["data"] == "secret-intelligence"


# ---------------------------------------------------------------------------
# Secret resolution helper
# ---------------------------------------------------------------------------


class TestSecretResolution:
    def test_unset_returns_none(self, monkeypatch):
        monkeypatch.delenv("MPP_SECRET_KEY", raising=False)
        assert mpp_gate_mod._resolve_secret_key() is None

    def test_blank_returns_none(self, monkeypatch):
        monkeypatch.setenv("MPP_SECRET_KEY", "  ")
        assert mpp_gate_mod._resolve_secret_key() is None

    def test_set_returns_value(self, monkeypatch):
        monkeypatch.setenv("MPP_SECRET_KEY", "s3cr3t")
        assert mpp_gate_mod._resolve_secret_key() == "s3cr3t"


# ---------------------------------------------------------------------------
# S3 — replay store: atomic first-writer-wins, fail-closed on error
# ---------------------------------------------------------------------------


class _FakeBackend:
    """Mimics CacheBackend.acquire_lock (atomic SETNX) + get/set/delete."""

    def __init__(self, *, raise_on_lock: bool = False):
        self._data: dict[str, str] = {}
        self._locks: set[str] = set()
        self._raise = raise_on_lock

    async def get(self, key):
        return self._data.get(key)

    async def set(self, key, value, ttl=None):
        self._data[key] = value
        return True

    async def delete(self, key):
        self._data.pop(key, None)
        self._locks.discard(key)
        return True

    async def acquire_lock(self, key, ttl, owner):
        if self._raise:
            raise RuntimeError("redis down")
        if key in self._locks:
            return False
        self._locks.add(key)
        return True


@pytest.mark.asyncio
class TestReplayStore:
    async def test_put_if_absent_first_writer_wins(self):
        store = CacheBackedReplayStore(_FakeBackend())
        assert await store.put_if_absent("mpp:charge:0xabc", "1") is True
        # Replay of the same tx hash is rejected.
        assert await store.put_if_absent("mpp:charge:0xabc", "1") is False

    async def test_distinct_keys_independent(self):
        store = CacheBackedReplayStore(_FakeBackend())
        assert await store.put_if_absent("k1", "1") is True
        assert await store.put_if_absent("k2", "1") is True

    async def test_backend_error_is_fail_closed(self):
        """A backend error => put_if_absent False => pympp treats as duplicate =>
        credential rejected. Never accidentally 'new' (which would re-grant)."""
        store = CacheBackedReplayStore(_FakeBackend(raise_on_lock=True))
        assert await store.put_if_absent("k", "1") is False

    async def test_get_set_delete_roundtrip(self):
        store = CacheBackedReplayStore(_FakeBackend())
        await store.put("k", "v")
        assert await store.get("k") == "v"
        await store.delete("k")
        assert await store.get("k") is None
