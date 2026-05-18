"""Tests for RBAC middleware — organization-based access control.

Covers:
- User with valid org membership → request proceeds with org_member set
- User without org membership → 403 from require_org_member
- Database failure in non-dev → 503
- Database failure in dev → continues with None
- Org ID extraction from path, header, and query parameter
- require_permission dependency
- require_role dependency
- get_org_context and get_user_id helpers
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI, Request
from httpx import ASGITransport, AsyncClient
from starlette.responses import JSONResponse

# Ensure package sources are on sys.path
_root = Path(__file__).parent.parent
_pkgs = _root / "packages"
for _pkg in ("sardis-core", "server-api"):
    _p = _pkgs / _pkg / "src"
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sardis_server.middleware.rbac import (
    RBACMiddleware,
    get_org_context,
    get_user_id,
    require_org_member,
    require_permission,
    require_role,
)
from sardis_v2_core.organizations import OrgMember

# ---------------------------------------------------------------------------
# Fake OrganizationManager
# ---------------------------------------------------------------------------


class _FakeOrgManager:
    """In-memory organization manager for tests."""

    def __init__(self, members: dict[tuple[str, str], OrgMember] | None = None):
        self._members = members or {}
        self.should_fail = False

    async def get_user_membership(self, org_id: str, user_id: str) -> OrgMember | None:
        if self.should_fail:
            raise RuntimeError("Database connection failed")
        return self._members.get((org_id, user_id))


# ---------------------------------------------------------------------------
# Fake principal for setting request.state
# ---------------------------------------------------------------------------


@dataclass
class _FakePrincipal:
    user_id: str
    role: str = "user"


# ---------------------------------------------------------------------------
# App builders
# ---------------------------------------------------------------------------


def _build_rbac_app(
    org_manager: _FakeOrgManager | None = None,
    *,
    env: str = "dev",
) -> FastAPI:
    """Build a test app with RBAC middleware and a simple test route."""
    app = FastAPI()

    mgr = org_manager or _FakeOrgManager()
    app.add_middleware(RBACMiddleware, org_manager=mgr)

    @app.get("/api/v2/orgs/{org_id}/test")
    async def test_route(request: Request, org_id: str):
        org_member = getattr(request.state, "org_member", None)
        org_id_from_state = getattr(request.state, "org_id", None)
        return {
            "org_id": org_id_from_state,
            "has_member": org_member is not None,
            "member_role": org_member.role if org_member else None,
        }

    @app.get("/api/v2/public/test")
    async def public_route(request: Request):
        """Route without org_id — RBAC should skip."""
        return {"public": True}

    @app.get("/api/v2/header-org/test")
    async def header_org_route(request: Request):
        """Route that gets org_id from header."""
        org_member = getattr(request.state, "org_member", None)
        org_id_from_state = getattr(request.state, "org_id", None)
        return {
            "org_id": org_id_from_state,
            "has_member": org_member is not None,
        }

    return app


def _add_principal_middleware(app: FastAPI, user_id: str | None):
    """Add a middleware that sets request.state.principal before RBAC runs.

    Starlette middlewares run in reverse order of addition. Since RBAC is
    already added, we add the principal setter AFTER so it runs FIRST (outer).
    """
    from starlette.middleware.base import BaseHTTPMiddleware

    class _PrincipalSetter(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if user_id:
                request.state.principal = _FakePrincipal(user_id=user_id)
            return await call_next(request)

    app.add_middleware(_PrincipalSetter)


# ---------------------------------------------------------------------------
# Tests: Middleware dispatch
# ---------------------------------------------------------------------------


class TestRBACMiddlewareDispatch:
    """Test the RBAC middleware dispatch logic."""

    @pytest.mark.asyncio
    async def test_no_org_id_skips_rbac(self):
        """Routes without org_id pass through without RBAC."""
        app = _build_rbac_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v2/public/test")
        assert resp.status_code == 200
        assert resp.json()["public"] is True

    @pytest.mark.asyncio
    async def test_authenticated_user_with_membership_via_header(self):
        """User with valid membership (org_id via header) → org_member is set."""
        member = OrgMember(
            id="mem_1",
            org_id="org_123",
            user_id="user_456",
            role="org_admin",
        )
        mgr = _FakeOrgManager(members={("org_123", "user_456"): member})
        app = _build_rbac_app(org_manager=mgr)
        _add_principal_middleware(app, user_id="user_456")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v2/header-org/test",
                headers={"X-Organization-ID": "org_123"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["has_member"] is True
        assert body["org_id"] == "org_123"

    @pytest.mark.asyncio
    async def test_authenticated_user_without_membership_via_header(self):
        """User not a member (org_id via header) → org_member is None, request proceeds."""
        mgr = _FakeOrgManager(members={})
        app = _build_rbac_app(org_manager=mgr)
        _add_principal_middleware(app, user_id="user_789")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v2/header-org/test",
                headers={"X-Organization-ID": "org_123"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["has_member"] is False
        assert body["org_id"] == "org_123"

    @pytest.mark.asyncio
    async def test_unauthenticated_user_passes_through(self):
        """No principal set → RBAC skips (lets route handler deal with auth)."""
        mgr = _FakeOrgManager()
        app = _build_rbac_app(org_manager=mgr)
        # No principal middleware added

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v2/orgs/org_123/test")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_org_id_from_query_param(self):
        """org_id query parameter is used as fallback."""
        member = OrgMember(
            id="mem_1",
            org_id="org_from_query",
            user_id="user_111",
            role="developer",
        )
        mgr = _FakeOrgManager(members={("org_from_query", "user_111"): member})
        app = _build_rbac_app(org_manager=mgr)
        _add_principal_middleware(app, user_id="user_111")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v2/header-org/test?org_id=org_from_query",
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["org_id"] == "org_from_query"
        assert body["has_member"] is True


# ---------------------------------------------------------------------------
# Tests: Database failure behavior
# ---------------------------------------------------------------------------


class TestRBACDatabaseFailure:
    """Test middleware behavior when database lookup fails."""

    @pytest.mark.asyncio
    async def test_db_failure_in_non_dev_returns_503(self):
        """Database error in sandbox/staging/prod → 503."""
        mgr = _FakeOrgManager()
        mgr.should_fail = True

        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "sandbox"}):
            app = _build_rbac_app(org_manager=mgr, env="sandbox")
            _add_principal_middleware(app, user_id="user_1")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v2/header-org/test",
                    headers={"X-Organization-ID": "org_123"},
                )

        assert resp.status_code == 503
        assert "authorization service" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_db_failure_in_dev_continues(self):
        """Database error in dev → continues with org_member=None."""
        mgr = _FakeOrgManager()
        mgr.should_fail = True

        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "dev"}):
            app = _build_rbac_app(org_manager=mgr, env="dev")
            _add_principal_middleware(app, user_id="user_1")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v2/header-org/test",
                    headers={"X-Organization-ID": "org_123"},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["has_member"] is False  # None because DB failed
        assert body["org_id"] == "org_123"

    @pytest.mark.asyncio
    async def test_db_failure_in_staging_returns_503(self):
        """Staging is non-dev → 503."""
        mgr = _FakeOrgManager()
        mgr.should_fail = True

        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "staging"}):
            app = _build_rbac_app(org_manager=mgr)
            _add_principal_middleware(app, user_id="user_1")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v2/header-org/test",
                    headers={"X-Organization-ID": "org_123"},
                )

        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Tests: require_org_member dependency
# ---------------------------------------------------------------------------


class TestRequireOrgMember:
    """Test the require_org_member FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_with_member_returns_member(self):
        member = OrgMember(
            id="mem_1", org_id="org_1", user_id="user_1", role="developer"
        )
        request = MagicMock()
        request.state.org_member = member

        result = await require_org_member(request)
        assert result.role == "developer"
        assert result.user_id == "user_1"

    @pytest.mark.asyncio
    async def test_without_member_and_no_user_raises_401(self):
        request = MagicMock()
        request.state.org_member = None
        request.state.user_id = None
        request.state.principal = None

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await require_org_member(request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_without_member_but_with_user_raises_403(self):
        request = MagicMock()
        request.state.org_member = None
        request.state.user_id = "user_1"
        request.state.principal = None

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await require_org_member(request)
        assert exc_info.value.status_code == 403
        assert "not a member" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Tests: require_permission / require_role
# ---------------------------------------------------------------------------


class TestRequirePermission:
    """Test permission enforcement dependency."""

    @pytest.mark.asyncio
    async def test_no_member_raises_401(self):
        from sardis_v2_core.rbac import Permission
        check_fn = await require_permission(Permission.CREATE_AGENT)

        request = MagicMock()
        request.state.org_member = None

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(request)
        assert exc_info.value.status_code == 401


class TestRequireRole:
    """Test role enforcement dependency."""

    @pytest.mark.asyncio
    async def test_no_member_raises_401(self):
        check_fn = await require_role("org_admin")

        request = MagicMock()
        request.state.org_member = None

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_role_raises_403(self):
        check_fn = await require_role("org_admin")

        member = OrgMember(
            id="mem_1", org_id="org_1", user_id="user_1", role="viewer"
        )
        request = MagicMock()
        request.state.org_member = member

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(request)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_matching_role_passes(self):
        check_fn = await require_role("developer")

        member = OrgMember(
            id="mem_1", org_id="org_1", user_id="user_1", role="developer"
        )
        request = MagicMock()
        request.state.org_member = member

        # Should not raise
        await check_fn(request)

    @pytest.mark.asyncio
    async def test_org_admin_bypasses_role_check(self):
        check_fn = await require_role("developer")

        member = OrgMember(
            id="mem_1", org_id="org_1", user_id="user_1", role="org_admin"
        )
        request = MagicMock()
        request.state.org_member = member

        # org_admin should bypass any role check
        await check_fn(request)


# ---------------------------------------------------------------------------
# Tests: Helper functions
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """Test get_org_context and get_user_id helpers."""

    def test_get_org_context_with_state(self):
        request = MagicMock()
        member = OrgMember(
            id="mem_1", org_id="org_1", user_id="user_1", role="developer"
        )
        request.state.org_id = "org_1"
        request.state.org_member = member

        org_id, org_member = get_org_context(request)
        assert org_id == "org_1"
        assert org_member is member

    def test_get_org_context_without_state(self):
        request = MagicMock(spec=[])
        request.state = MagicMock(spec=[])

        org_id, org_member = get_org_context(request)
        assert org_id is None
        assert org_member is None

    def test_get_user_id_from_principal(self):
        request = MagicMock()
        request.state.principal = _FakePrincipal(user_id="user_from_principal")
        request.state.user_id = None
        request.state.org_member = None
        request.state.jwt_claims = None

        assert get_user_id(request) == "user_from_principal"

    def test_get_user_id_from_state(self):
        request = MagicMock()
        request.state.principal = None
        request.state.user_id = "user_from_state"
        request.state.org_member = None
        request.state.jwt_claims = None

        assert get_user_id(request) == "user_from_state"

    def test_get_user_id_from_jwt_claims(self):
        request = MagicMock()
        request.state.principal = None
        request.state.user_id = None
        request.state.org_member = None
        request.state.jwt_claims = {"sub": "user_from_jwt"}

        assert get_user_id(request) == "user_from_jwt"

    def test_get_user_id_returns_none_when_nothing_set(self):
        request = MagicMock(spec=[])
        request.state = MagicMock(spec=[])

        assert get_user_id(request) is None
