"""Unified auth helpers for demo + production wiring.

Sardis supports:
- JWT (dashboard/admin UX)
- API keys (server-to-server / agent integrations)

For demo readiness, we allow either auth mechanism for most v2 endpoints.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal, Optional

from fastapi import Depends, HTTPException, Request, status

from .middleware.auth import APIKey, get_api_key
from .routers.auth import UserInfo, get_current_user

_logger = logging.getLogger("sardis.api.authz")


@dataclass(frozen=True)
class Principal:
    kind: Literal["api_key", "jwt"]
    organization_id: str
    scopes: list[str]
    user: Optional[UserInfo] = None
    api_key: Optional[APIKey] = None

    @property
    def is_admin(self) -> bool:
        if self.kind == "api_key":
            return "admin" in self.scopes or "*" in self.scopes
        return bool(self.user and self.user.role == "admin")


async def require_principal(
    request: Request,
    api_key: Optional[APIKey] = Depends(get_api_key),
    user: Optional[UserInfo] = Depends(get_current_user),
) -> Principal:
    """
    Require either API key or JWT.

    JWT-authenticated callers are mapped to a demo organization ID so that
    endpoints that require an organization context keep working.
    """
    env = os.getenv("SARDIS_ENVIRONMENT", "").strip().lower()
    allow_anon = os.getenv("SARDIS_ALLOW_ANON", "").strip().lower() in {"1", "true", "yes", "on"}
    if allow_anon and env in {"dev", "test", "local"}:
        # SECURITY: Only allow anonymous access from loopback addresses.
        # Without this restriction, a network-accessible staging/dev deployment
        # would allow any caller full wildcard-scope access without credentials.
        client_ip = request.client.host if request.client else ""
        loopback = {"127.0.0.1", "::1", "localhost"}
        if client_ip not in loopback:
            _logger.warning(
                "SARDIS_ALLOW_ANON rejected non-loopback request from %s on %s",
                client_ip,
                request.url.path,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Anonymous access is only allowed from localhost",
                headers={"WWW-Authenticate": "ApiKey, Bearer"},
            )
        _logger.debug("Anonymous access granted from %s (dev/test mode)", client_ip)
        org_id = os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")
        return Principal(
            kind="api_key",
            organization_id=org_id,
            scopes=["*"],
            api_key=None,
        )

    if api_key is not None:
        return Principal(
            kind="api_key",
            organization_id=api_key.organization_id,
            scopes=list(api_key.scopes),
            api_key=api_key,
        )

    if user is not None:
        org_id = os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")
        scopes = ["*"] if user.role == "admin" else ["read"]
        return Principal(
            kind="jwt",
            organization_id=org_id,
            scopes=scopes,
            user=user,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "ApiKey, Bearer"},
    )


async def require_admin_principal(
    principal: Principal = Depends(require_principal),
) -> Principal:
    if principal.is_admin:
        return principal
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin privileges required",
    )


def metrics_auth_required() -> bool:
    """
    Whether the /metrics endpoint should require auth.

    Default: require auth (production-grade). Set SARDIS_PUBLIC_METRICS=1 to expose.
    """
    return os.getenv("SARDIS_PUBLIC_METRICS", "").strip() not in {"1", "true", "yes", "on"}
