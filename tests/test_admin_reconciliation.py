"""Tests for admin reconciliation endpoint.

Covers:
- Non-admin user → 403
- Admin user creates reconciliation job → success
- Missing reconciliation engine → 503
- Missing ledger repo → 503
- Empty entries → success with zero counts
- Specific entry lookup (by entry_id, wallet_id, chain)
- Discrepancy reporting
"""
from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

# Ensure package sources are on sys.path
_root = Path(__file__).parent.parent
_pkgs = _root / "packages"
for _pkg in ("sardis-core", "api"):
    _p = _pkgs / _pkg / "src"
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


# ---------------------------------------------------------------------------
# Fakes / Stubs
# ---------------------------------------------------------------------------


@dataclass
class _FakeReconciliationStatus:
    value: str = "matched"


@dataclass
class _FakeReconciliationRecord:
    ledger_entry_id: str = "entry_1"
    chain: str = "base"
    chain_tx_hash: str = "0xabc"
    ledger_amount: int = 100_000
    chain_amount: int | None = 100_000
    discrepancy_amount: int | None = None
    discrepancy_reason: str | None = None
    status: _FakeReconciliationStatus = field(default_factory=_FakeReconciliationStatus)


@dataclass
class _FakeLedgerEntry:
    entry_id: str = "entry_1"
    wallet_id: str = "wal_1"
    chain: str = "base"
    amount: int = 100_000


class _FakeLedgerRepo:
    def __init__(self, entries: list[_FakeLedgerEntry] | None = None):
        self._entries = entries or []

    async def get_entry(self, entry_id: str):
        for e in self._entries:
            if e.entry_id == entry_id:
                return e
        return None

    async def list_entries(self, wallet_id=None, chain=None, limit=50):
        results = self._entries
        if wallet_id:
            results = [e for e in results if e.wallet_id == wallet_id]
        if chain:
            results = [e for e in results if e.chain == chain]
        return results[:limit]


class _FakeReconciliationEngine:
    def __init__(self, records: list[_FakeReconciliationRecord] | None = None):
        self._records = records or []
        self._stats: dict[str, Any] = {"total_runs": 1}
        self._discrepancies: list = []

    async def reconcile_batch(self, entries, actor_id: str = ""):
        return self._records


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------


def _build_app(
    is_admin: bool = True,
    reconciliation_engine=None,
    ledger_repo=None,
):
    """Build a test FastAPI app with admin_reconciliation router.

    The admin_reconciliation router has a dependency on require_mfa_if_enabled
    which in turn depends on require_admin_principal. We override those
    dependencies to control admin vs non-admin access.
    """
    with patch.dict(os.environ, {
        "JWT_SECRET_KEY": "a" * 64,
        "SARDIS_ENVIRONMENT": "dev",
        "BETTER_AUTH_JWKS_URL": "",
    }):
        import server.routes.accounts.auth as _auth_mod
        importlib.reload(_auth_mod)

        from server.authz import Principal
        from server.middleware.mfa import require_mfa_if_enabled
        from server.routes.admin.control import require_admin_rate_limit
        from server.routes.admin.reconciliation import router as recon_router
        from server.routes.accounts.auth import UserInfo

        app = FastAPI()

        # Override MFA dependency (which includes admin check)
        if is_admin:
            async def _fake_mfa():
                return None
        else:
            async def _fake_mfa():
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin privileges required",
                )

        app.dependency_overrides[require_mfa_if_enabled] = _fake_mfa

        # Override rate limit dependency
        def _fake_rate_limit(is_sensitive=False):
            async def _noop(request):
                return None
            return _noop

        # We need to override the actual dependency function used in the router.
        # The router uses Depends(require_admin_rate_limit(is_sensitive=True)).
        # Since require_admin_rate_limit is a factory, we patch it at module level.
        with patch(
            "server.routes.admin.reconciliation.require_admin_rate_limit",
            _fake_rate_limit,
        ):
            # Re-import to pick up the patch (router is created at import time,
            # but dependencies are evaluated at request time, so patching the
            # module-level function works for the Depends(factory()) pattern
            # only if we rebuild the router).
            pass

        app.include_router(recon_router, prefix="/api/v2/admin/reconciliation")

        # Set app.state attributes
        app.state.reconciliation_engine = reconciliation_engine
        app.state.ledger_repo = ledger_repo

        return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAdminReconciliationAccess:
    """Access control tests."""

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self):
        app = _build_app(is_admin=False)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v2/admin/reconciliation/check",
                json={"limit": 10},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_without_engine_gets_503(self):
        app = _build_app(is_admin=True, reconciliation_engine=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v2/admin/reconciliation/check",
                json={"limit": 10},
            )
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"].lower()


class TestAdminReconciliationCheck:
    """Functional tests for the /check endpoint."""

    @pytest.mark.asyncio
    async def test_empty_entries_returns_zero_counts(self):
        engine = _FakeReconciliationEngine()
        ledger = _FakeLedgerRepo(entries=[])
        app = _build_app(
            is_admin=True,
            reconciliation_engine=engine,
            ledger_repo=ledger,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v2/admin/reconciliation/check",
                json={"limit": 10},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_checked"] == 0

    @pytest.mark.asyncio
    async def test_matched_entries_reported_correctly(self):
        entries = [_FakeLedgerEntry(entry_id="e1"), _FakeLedgerEntry(entry_id="e2")]
        records = [
            _FakeReconciliationRecord(ledger_entry_id="e1"),
            _FakeReconciliationRecord(ledger_entry_id="e2"),
        ]
        engine = _FakeReconciliationEngine(records=records)
        ledger = _FakeLedgerRepo(entries=entries)

        app = _build_app(
            is_admin=True,
            reconciliation_engine=engine,
            ledger_repo=ledger,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v2/admin/reconciliation/check",
                json={"limit": 50},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_checked"] == 2
        assert body["matched"] == 2
        assert body["unmatched"] == 0
        assert body["discrepancies"] == []

    @pytest.mark.asyncio
    async def test_discrepancy_reported(self):
        entries = [_FakeLedgerEntry(entry_id="e1")]
        records = [
            _FakeReconciliationRecord(
                ledger_entry_id="e1",
                ledger_amount=100_000,
                chain_amount=99_000,
                discrepancy_amount=1_000,
                discrepancy_reason="amount mismatch",
                status=_FakeReconciliationStatus(value="unmatched"),
            ),
        ]
        engine = _FakeReconciliationEngine(records=records)
        ledger = _FakeLedgerRepo(entries=entries)

        app = _build_app(
            is_admin=True,
            reconciliation_engine=engine,
            ledger_repo=ledger,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v2/admin/reconciliation/check",
                json={"limit": 50},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["unmatched"] == 1
        assert len(body["discrepancies"]) == 1
        disc = body["discrepancies"][0]
        assert disc["entry_id"] == "e1"
        assert disc["reason"] == "amount mismatch"

    @pytest.mark.asyncio
    async def test_entry_not_found_returns_404(self):
        engine = _FakeReconciliationEngine()
        ledger = _FakeLedgerRepo(entries=[])

        app = _build_app(
            is_admin=True,
            reconciliation_engine=engine,
            ledger_repo=ledger,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v2/admin/reconciliation/check",
                json={"entry_id": "nonexistent_entry"},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_missing_ledger_repo_returns_503(self):
        engine = _FakeReconciliationEngine()
        app = _build_app(
            is_admin=True,
            reconciliation_engine=engine,
            ledger_repo=None,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v2/admin/reconciliation/check",
                json={"limit": 10},
            )
        assert resp.status_code == 503
        assert "ledger" in resp.json()["detail"].lower()


class TestAdminReconciliationStats:
    """Tests for the /stats endpoint."""

    @pytest.mark.asyncio
    async def test_stats_without_engine(self):
        app = _build_app(is_admin=True, reconciliation_engine=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v2/admin/reconciliation/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["configured"] is False

    @pytest.mark.asyncio
    async def test_stats_with_engine(self):
        engine = _FakeReconciliationEngine()
        engine._stats = {"total_runs": 5, "last_run": "2026-04-04"}
        engine._discrepancies = ["d1", "d2"]
        app = _build_app(
            is_admin=True,
            reconciliation_engine=engine,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v2/admin/reconciliation/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["configured"] is True
        assert body["stats"]["total_runs"] == 5
        assert body["discrepancy_count"] == 2
