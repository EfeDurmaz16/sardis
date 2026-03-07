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

# In-memory state store for OIDC CSRF protection.
# In production, replace with Redis or DB-backed store.
_SSO_STATE_STORE: dict[str, dict[str, Any]] = {}
_SSO_STATE_TTL = 600  # 10 minutes


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
# Secret encryption helpers for OIDC client_secret (I5)
# ---------------------------------------------------------------------------

def _get_encryption_key() -> bytes:
    """Get or derive the encryption key for SSO secrets."""
    import base64
    raw_key = os.getenv("SARDIS_SSO_ENCRYPTION_KEY", "")
    if not raw_key:
        env = os.getenv("SARDIS_ENVIRONMENT", "dev")
        if env in ("prod", "production", "staging"):
            raise RuntimeError(
                "SARDIS_SSO_ENCRYPTION_KEY must be set in production/staging. "
                "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        # Dev fallback — deterministic key for local testing only
        raw_key = base64.urlsafe_b64encode(b"sardis-dev-sso-key-00000000000000").decode()
    return raw_key.encode()


def _encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret using Fernet symmetric encryption."""
    try:
        from cryptography.fernet import Fernet
        f = Fernet(_get_encryption_key())
        return f.encrypt(plaintext.encode()).decode()
    except ImportError:
        logger.warning("cryptography package not installed; storing SSO secret in plaintext")
        return plaintext


def _decrypt_secret(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted secret."""
    try:
        from cryptography.fernet import Fernet
        f = Fernet(_get_encryption_key())
        return f.decrypt(ciphertext.encode()).decode()
    except ImportError:
        return ciphertext
    except Exception:
        # If decryption fails, assume it's stored in plaintext (migration period)
        return ciphertext


# ---------------------------------------------------------------------------
# SSO state management (C4 fix)
# ---------------------------------------------------------------------------

def _store_sso_state(state: str, org_id: str, provider_type: str) -> None:
    """Store SSO state for CSRF validation."""
    # Prune expired entries
    now = time.time()
    expired = [k for k, v in _SSO_STATE_STORE.items() if v["expires_at"] < now]
    for k in expired:
        del _SSO_STATE_STORE[k]

    _SSO_STATE_STORE[state] = {
        "org_id": org_id,
        "provider_type": provider_type,
        "expires_at": now + _SSO_STATE_TTL,
    }


def _validate_sso_state(state: str) -> Optional[dict[str, Any]]:
    """Validate and consume a SSO state token. Returns state data or None."""
    data = _SSO_STATE_STORE.pop(state, None)
    if data is None:
        return None
    if data["expires_at"] < time.time():
        return None
    return data


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

            # Decrypt client_secret if present (I5)
            oidc_client_secret = row.get("oidc_client_secret")
            if oidc_client_secret:
                oidc_client_secret = _decrypt_secret(oidc_client_secret)

            return SSOConfig(
                id=row["id"],
                org_id=row["org_id"],
                provider_type=row["provider_type"],
                display_name=row["display_name"],
                enabled=row["enabled"],
                oidc_issuer_url=row.get("oidc_issuer_url"),
                oidc_client_id=row.get("oidc_client_id"),
                oidc_client_secret=oidc_client_secret,
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

        SECURITY: SAML XML signature verification is NOT yet implemented.
        This method raises NotImplementedError to prevent deployment without
        proper signature verification, which would allow SAML response forgery.
        """
        raise NotImplementedError(
            "SAML response signature verification is not yet implemented. "
            "Integrate a library such as python3-saml or signxml to verify "
            "the XML signature against the IdP certificate before enabling "
            "SAML SSO in production."
        )


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

    # Store state → org mapping for CSRF validation (C4 fix)
    _store_sso_state(state, req.org_id, config.provider_type)

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
    """Handle OIDC callback with authorization code.

    Validates the state token against the stored org_id to prevent CSRF
    and ensure the code is exchanged with the correct org's IdP config.
    """
    pool = getattr(request.app.state, "db_pool", None)
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")

    # Validate state token (C4 fix — prevents CSRF and org mismatch)
    state_data = _validate_sso_state(req.state)
    if state_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired SSO state token",
        )

    org_id = state_data["org_id"]
    store = SSOConfigStore(pool)
    config = await store.get_by_org(org_id)
    if not config or config.provider_type != "oidc":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OIDC not configured for this organization",
        )

    handler = OIDCHandler(config)
    user_info = await handler.exchange_code(req.code)
    return await _provision_sso_user(pool, config, user_info)


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
