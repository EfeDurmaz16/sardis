"""SSO middleware — SAML/OIDC authentication flows.

Supports per-organization SSO configuration:
- OIDC: Standard OpenID Connect with code flow
- SAML: SAML 2.0 SP-initiated SSO

When enforce_sso_only is True for an org, password login is blocked.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/sso", tags=["sso"])


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SSOConfig:
    """SSO configuration for an organization."""
    id: str
    org_id: str
    provider_type: str  # "saml" or "oidc"
    display_name: str
    enabled: bool

    # OIDC
    oidc_issuer_url: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_scopes: list[str] = None

    # SAML
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_certificate: Optional[str] = None

    # Behavior
    auto_provision_users: bool = True
    default_role: str = "member"
    enforce_sso_only: bool = False
    allowed_email_domains: list[str] = None


class OIDCCallbackRequest(BaseModel):
    code: str
    state: str


class SSOInitResponse(BaseModel):
    redirect_url: str
    state: str


class SSOUserInfo(BaseModel):
    email: str
    name: Optional[str] = None
    subject_id: str
    provider_id: str


# ---------------------------------------------------------------------------
# SSO configuration store
# ---------------------------------------------------------------------------

class SSOConfigStore:
    """Load SSO configurations from database."""

    def __init__(self, pool: Any) -> None:
        self._pool = pool

    async def get_by_org(self, org_id: str) -> Optional[SSOConfig]:
        """Get the enabled SSO config for an org."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM sso_configurations WHERE org_id = $1 AND enabled = TRUE",
                org_id,
            )
            if not row:
                return None
            return SSOConfig(
                id=row["id"],
                org_id=row["org_id"],
                provider_type=row["provider_type"],
                display_name=row["display_name"],
                enabled=row["enabled"],
                oidc_issuer_url=row.get("oidc_issuer_url"),
                oidc_client_id=row.get("oidc_client_id"),
                oidc_client_secret=row.get("oidc_client_secret"),
                oidc_scopes=row.get("oidc_scopes") or ["openid", "profile", "email"],
                saml_entity_id=row.get("saml_entity_id"),
                saml_sso_url=row.get("saml_sso_url"),
                saml_certificate=row.get("saml_certificate"),
                auto_provision_users=row.get("auto_provision_users", True),
                default_role=row.get("default_role", "member"),
                enforce_sso_only=row.get("enforce_sso_only", False),
                allowed_email_domains=row.get("allowed_email_domains") or [],
            )

    async def is_sso_enforced(self, org_id: str) -> bool:
        """Check if SSO-only is enforced for an org (blocks password login)."""
        config = await self.get_by_org(org_id)
        return config is not None and config.enforce_sso_only


# ---------------------------------------------------------------------------
# OIDC handler
# ---------------------------------------------------------------------------

class OIDCHandler:
    """OpenID Connect authentication handler."""

    def __init__(self, config: SSOConfig) -> None:
        self._config = config
        self._base_url = os.getenv("SARDIS_API_BASE_URL", "http://localhost:8000")

    def get_authorization_url(self, state: str) -> str:
        """Build the OIDC authorization URL."""
        import urllib.parse

        params = {
            "response_type": "code",
            "client_id": self._config.oidc_client_id,
            "redirect_uri": f"{self._base_url}/api/v2/auth/sso/oidc/callback",
            "scope": " ".join(self._config.oidc_scopes or ["openid", "profile", "email"]),
            "state": state,
        }
        issuer = self._config.oidc_issuer_url.rstrip("/")
        return f"{issuer}/authorize?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> SSOUserInfo:
        """Exchange authorization code for user info."""
        import httpx

        issuer = self._config.oidc_issuer_url.rstrip("/")
        token_url = f"{issuer}/token"
        userinfo_url = f"{issuer}/userinfo"

        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_resp = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": f"{self._base_url}/api/v2/auth/sso/oidc/callback",
                    "client_id": self._config.oidc_client_id,
                    "client_secret": self._config.oidc_client_secret,
                },
            )
            if token_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="OIDC token exchange failed",
                )

            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No access token in OIDC response",
                )

            # Fetch user info
            userinfo_resp = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="OIDC userinfo fetch failed",
                )

            userinfo = userinfo_resp.json()
            email = userinfo.get("email")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No email in OIDC userinfo",
                )

            # Validate email domain if restricted
            if self._config.allowed_email_domains:
                domain = email.split("@")[-1].lower()
                if domain not in [d.lower() for d in self._config.allowed_email_domains]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Email domain {domain} not allowed for this SSO config",
                    )

            return SSOUserInfo(
                email=email,
                name=userinfo.get("name"),
                subject_id=userinfo.get("sub", email),
                provider_id=self._config.id,
            )


# ---------------------------------------------------------------------------
# SAML handler (basic SP-initiated flow)
# ---------------------------------------------------------------------------

class SAMLHandler:
    """SAML 2.0 SP-initiated SSO handler."""

    def __init__(self, config: SSOConfig) -> None:
        self._config = config
        self._base_url = os.getenv("SARDIS_API_BASE_URL", "http://localhost:8000")

    def get_authorization_url(self, state: str) -> str:
        """Build a SAML AuthnRequest redirect URL.

        In production, this would build a proper SAML AuthnRequest XML.
        For now, we use a simplified redirect-based approach.
        """
        import urllib.parse

        params = {
            "SAMLRequest": self._build_authn_request(),
            "RelayState": state,
        }
        return f"{self._config.saml_sso_url}?{urllib.parse.urlencode(params)}"

    def _build_authn_request(self) -> str:
        """Build a base64-encoded SAML AuthnRequest."""
        import base64

        acs_url = f"{self._base_url}/api/v2/auth/sso/saml/acs"
        request_xml = (
            f'<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
            f'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" '
            f'ID="_sardis_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]}" '
            f'Version="2.0" IssueInstant="{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}" '
            f'AssertionConsumerServiceURL="{acs_url}">'
            f'<saml:Issuer>{self._base_url}</saml:Issuer>'
            f'</samlp:AuthnRequest>'
        )
        return base64.b64encode(request_xml.encode()).decode()

    async def validate_response(self, saml_response: str) -> SSOUserInfo:
        """Validate a SAML Response and extract user info.

        In production, this would verify the XML signature against the IdP certificate.
        """
        import base64
        import xml.etree.ElementTree as ET

        try:
            decoded = base64.b64decode(saml_response)
            root = ET.fromstring(decoded)

            # Extract NameID (email)
            ns = {
                "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
                "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
            }
            name_id_elem = root.find(".//saml:NameID", ns)
            if name_id_elem is None or not name_id_elem.text:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No NameID in SAML response",
                )

            email = name_id_elem.text

            # Validate email domain
            if self._config.allowed_email_domains:
                domain = email.split("@")[-1].lower()
                if domain not in [d.lower() for d in self._config.allowed_email_domains]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Email domain {domain} not allowed",
                    )

            return SSOUserInfo(
                email=email,
                name=None,
                subject_id=email,
                provider_id=self._config.id,
            )

        except ET.ParseError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid SAML response",
            ) from e


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

class SSOInitRequest(BaseModel):
    org_id: str


@router.post("/init", response_model=SSOInitResponse)
async def sso_init(req: SSOInitRequest, request: Request):
    """Initiate SSO login for an organization."""
    pool = getattr(request.app.state, "db_pool", None)
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")

    store = SSOConfigStore(pool)
    config = await store.get_by_org(req.org_id)
    if not config:
        raise HTTPException(status_code=404, detail="No SSO configured for this organization")

    # Generate state token
    state = hashlib.sha256(f"{req.org_id}:{time.time()}:{os.urandom(16).hex()}".encode()).hexdigest()

    if config.provider_type == "oidc":
        handler = OIDCHandler(config)
        redirect_url = handler.get_authorization_url(state)
    elif config.provider_type == "saml":
        handler = SAMLHandler(config)
        redirect_url = handler.get_authorization_url(state)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported SSO provider: {config.provider_type}")

    return SSOInitResponse(redirect_url=redirect_url, state=state)


@router.post("/oidc/callback")
async def oidc_callback(req: OIDCCallbackRequest, request: Request):
    """Handle OIDC callback with authorization code."""
    pool = getattr(request.app.state, "db_pool", None)
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")

    # In production, validate state against a session/cache
    # For now, extract org_id from state (would be stored in session)
    store = SSOConfigStore(pool)

    # Find OIDC configs to try (in production, state maps to specific org)
    async with pool.acquire() as conn:
        configs = await conn.fetch(
            "SELECT org_id FROM sso_configurations WHERE provider_type = 'oidc' AND enabled = TRUE"
        )

    for row in configs:
        config = await store.get_by_org(row["org_id"])
        if config and config.provider_type == "oidc":
            handler = OIDCHandler(config)
            try:
                user_info = await handler.exchange_code(req.code)
                return await _provision_sso_user(pool, config, user_info)
            except HTTPException:
                continue

    raise HTTPException(status_code=401, detail="OIDC authentication failed")


async def _provision_sso_user(
    pool: Any, config: SSOConfig, user_info: SSOUserInfo
) -> dict[str, Any]:
    """Provision or update a user from SSO, return session info."""
    async with pool.acquire() as conn:
        # Check if user exists
        existing = await conn.fetchrow(
            "SELECT id, email FROM users WHERE email = $1",
            user_info.email,
        )

        if existing:
            # Update SSO linkage
            await conn.execute(
                "UPDATE users SET sso_provider_id = $1, sso_subject_id = $2, updated_at = NOW() "
                "WHERE id = $3",
                user_info.provider_id, user_info.subject_id, existing["id"],
            )
            user_id = existing["id"]
        elif config.auto_provision_users:
            # Create new user
            user_id = await conn.fetchval(
                "INSERT INTO users (email, display_name, email_verified, sso_provider_id, sso_subject_id) "
                "VALUES ($1, $2, TRUE, $3, $4) RETURNING id",
                user_info.email, user_info.name, user_info.provider_id, user_info.subject_id,
            )
            # Add org membership
            await conn.execute(
                "INSERT INTO user_org_memberships (user_id, org_id, role) "
                "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                user_id, config.org_id, config.default_role,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Auto-provisioning disabled. Contact your admin.",
            )

        logger.info("SSO login: user=%s org=%s provider=%s", user_id, config.org_id, config.provider_type)

        return {
            "user_id": user_id,
            "email": user_info.email,
            "org_id": config.org_id,
            "sso_provider": config.provider_type,
        }
