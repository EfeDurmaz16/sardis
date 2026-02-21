"""RBAC middleware for organization-based access control.

This middleware enforces role-based access control for multi-tenant organizations.
It extracts organization context from requests and validates user permissions.

Usage:
    app.add_middleware(RBACMiddleware)

The middleware:
  1. Extracts org_id from path parameters or headers
  2. Loads the user's membership in that organization
  3. Attaches org_member to request.state for downstream use
  4. Route handlers can then use require_permission() decorator
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Callable

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from sardis_v2_core.organizations import OrganizationManager, OrgMember
from sardis_v2_core.rbac import Permission, RBACEngine

logger = logging.getLogger("sardis.api.rbac")


class RBACMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce RBAC for organization routes.

    This middleware runs before route handlers and:
      1. Extracts org_id from the request path or headers
      2. Identifies the authenticated user (from existing auth middleware)
      3. Loads the user's organization membership
      4. Attaches org_member to request.state for RBAC checks
    """

    def __init__(self, app, org_manager: Optional[OrganizationManager] = None):
        """
        Initialize RBAC middleware.

        Args:
            app: FastAPI application
            org_manager: OrganizationManager instance (optional, created if not provided)
        """
        super().__init__(app)
        self._org_manager = org_manager

    async def _get_org_manager(self) -> OrganizationManager:
        """Lazy initialization of OrganizationManager."""
        if self._org_manager is None:
            dsn = os.getenv("DATABASE_URL", "postgresql://localhost/sardis")
            self._org_manager = OrganizationManager(dsn=dsn)
        return self._org_manager

    def _extract_org_id(self, request: Request) -> Optional[str]:
        """
        Extract org_id from request path parameters or headers.

        Checks in order:
          1. Path parameter: /api/v2/orgs/{org_id}/...
          2. Header: X-Organization-ID
          3. Query parameter: ?org_id=...

        Args:
            request: FastAPI request object

        Returns:
            Organization ID if found, None otherwise
        """
        # Try path parameters first
        path_params = request.path_params
        if "org_id" in path_params:
            return path_params["org_id"]

        # Try custom header
        org_id_header = request.headers.get("X-Organization-ID")
        if org_id_header:
            return org_id_header

        # Try query parameter
        org_id_query = request.query_params.get("org_id")
        if org_id_query:
            return org_id_query

        return None

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """
        Extract authenticated user ID from request.

        Assumes upstream auth middleware has set request.state.principal
        or request.state.user_id.

        Args:
            request: FastAPI request object

        Returns:
            User ID if authenticated, None otherwise
        """
        # Check for principal (from authz.py)
        principal = getattr(request.state, "principal", None)
        if principal and hasattr(principal, "user_id"):
            return principal.user_id

        # Fallback: check for user_id directly
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return user_id

        # Check JWT claims if available
        jwt_claims = getattr(request.state, "jwt_claims", None)
        if jwt_claims and "sub" in jwt_claims:
            return jwt_claims["sub"]

        return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and enforce RBAC if org_id is present.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response from downstream handler
        """
        # Extract org_id from request
        org_id = self._extract_org_id(request)

        # If no org_id, skip RBAC (non-org routes)
        if not org_id:
            return await call_next(request)

        # Extract authenticated user
        user_id = self._extract_user_id(request)
        if not user_id:
            # Organization routes require authentication
            # Let the require_principal dependency handle this
            return await call_next(request)

        # Load user's membership in this organization
        try:
            org_manager = await self._get_org_manager()
            member = await org_manager.get_user_membership(org_id, user_id)

            if member:
                # Attach member to request state for route handlers
                request.state.org_member = member
                request.state.org_id = org_id
                logger.debug(
                    f"RBAC: user={user_id} org={org_id} role={member.role}"
                )
            else:
                # User is not a member of this organization
                logger.warning(
                    f"RBAC: user={user_id} not a member of org={org_id}"
                )
                request.state.org_member = None
                request.state.org_id = org_id

        except Exception as e:
            logger.error(f"RBAC middleware error: {e}", exc_info=True)
            # Don't block the request on middleware errors
            # Let the route handler deal with missing org_member
            request.state.org_member = None
            request.state.org_id = org_id

        # Continue to route handler
        return await call_next(request)


# ========== FastAPI Dependencies ==========

async def require_org_member(request: Request) -> OrgMember:
    """
    FastAPI dependency to require organization membership.

    This should be used in route dependencies to ensure the user
    is a member of the organization in the request path.

    Usage:
        @router.get("/api/v2/orgs/{org_id}/agents")
        async def list_agents(
            org_id: str,
            member: OrgMember = Depends(require_org_member),
        ):
            # member is guaranteed to be set and match org_id
            ...

    Raises:
        HTTPException: 401 if not authenticated, 403 if not a member
    """
    org_member = getattr(request.state, "org_member", None)
    if not org_member:
        # Check if this is an auth issue or membership issue
        user_id = getattr(request.state, "user_id", None) or getattr(
            getattr(request.state, "principal", None), "user_id", None
        )

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization"
            )

    return org_member


async def require_permission(permission: Permission):
    """
    FastAPI dependency factory to require a specific permission.

    Usage:
        @router.post("/api/v2/orgs/{org_id}/agents")
        async def create_agent(
            org_id: str,
            member: OrgMember = Depends(require_org_member),
            _perm: None = Depends(require_permission(Permission.CREATE_AGENT)),
        ):
            # Permission check passed
            ...

    Args:
        permission: Required permission

    Returns:
        Dependency function that checks permission

    Raises:
        HTTPException: 403 if permission denied
    """
    async def check_permission(request: Request):
        org_member = getattr(request.state, "org_member", None)
        if not org_member:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        if not RBACEngine.check_permission(org_member.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires {permission.value}"
            )

    return check_permission


async def require_role(role: str):
    """
    FastAPI dependency factory to require a specific role.

    Similar to require_permission but checks role directly.

    Usage:
        @router.delete("/api/v2/orgs/{org_id}")
        async def delete_org(
            org_id: str,
            member: OrgMember = Depends(require_org_member),
            _role: None = Depends(require_role("org_admin")),
        ):
            ...

    Args:
        role: Required role (e.g., "org_admin")

    Returns:
        Dependency function that checks role

    Raises:
        HTTPException: 403 if role doesn't match
    """
    async def check_role(request: Request):
        org_member = getattr(request.state, "org_member", None)
        if not org_member:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # org_admin can bypass role checks
        if org_member.role != role and org_member.role != "org_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role denied: requires {role}"
            )

    return check_role


# ========== Helper: Get organization context from request ==========

def get_org_context(request: Request) -> tuple[Optional[str], Optional[OrgMember]]:
    """
    Extract organization context from request state.

    This is a convenience helper for route handlers that need
    both org_id and org_member.

    Args:
        request: FastAPI request

    Returns:
        Tuple of (org_id, org_member) - either may be None
    """
    org_id = getattr(request.state, "org_id", None)
    org_member = getattr(request.state, "org_member", None)
    return org_id, org_member


def get_user_id(request: Request) -> Optional[str]:
    """
    Extract authenticated user ID from request state.

    Checks multiple possible locations where user_id might be stored.

    Args:
        request: FastAPI request

    Returns:
        User ID if found, None otherwise
    """
    # Check principal
    principal = getattr(request.state, "principal", None)
    if principal and hasattr(principal, "user_id"):
        return principal.user_id

    # Check direct user_id
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return user_id

    # Check org_member
    org_member = getattr(request.state, "org_member", None)
    if org_member and hasattr(org_member, "user_id"):
        return org_member.user_id

    # Check JWT claims
    jwt_claims = getattr(request.state, "jwt_claims", None)
    if jwt_claims and "sub" in jwt_claims:
        return jwt_claims["sub"]

    return None
