"""Unified auth helpers for demo + production wiring.

Sardis supports:
- JWT (dashboard/admin UX)
- API keys (server-to-server / agent integrations)

For demo readiness, we allow either auth mechanism for most v2 endpoints.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Optional

from fastapi import Depends, HTTPException, status

from .middleware.auth import APIKey, get_api_key
from .routers.auth import UserInfo, get_current_user


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
    api_key: Optional[APIKey] = Depends(get_api_key),
    user: Optional[UserInfo] = Depends(get_current_user),
) -> Principal:
    """
    Require either API key or JWT.

    JWT-authenticated callers are mapped to a demo organization ID so that
    endpoints that require an organization context keep working.
    """
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

