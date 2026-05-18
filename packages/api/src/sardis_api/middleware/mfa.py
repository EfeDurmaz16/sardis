"""MFA enforcement for admin endpoints.

Verifies TOTP codes via X-MFA-Code header when users have MFA enabled.
In production, admin endpoints with sensitive operations require MFA.
"""
from __future__ import annotations

import logging
import os

from fastapi import Depends, HTTPException, Request, status

from sardis_api.authz import Principal, require_admin_principal

logger = logging.getLogger("sardis.api.mfa")


async def _get_user_mfa_status(user_id: str) -> dict:
    """Check if a user has MFA enabled and retrieve their secret."""
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT mfa_enabled, mfa_secret FROM users WHERE id = $1",
                user_id,
            )
            if not row:
                return {"enabled": False, "secret": None}
            return {
                "enabled": bool(row["mfa_enabled"]),
                "secret": row["mfa_secret"],
            }
    except Exception as e:
        logger.warning("Could not check MFA status for user=%s: %s", user_id, e)
        return {"enabled": False, "secret": None}


async def require_mfa_if_enabled(
    request: Request,
    principal: Principal = Depends(require_admin_principal),
) -> None:
    """FastAPI dependency that enforces MFA for admin users who have it enabled.

    Checks for X-MFA-Code header and verifies against the user's TOTP secret.
    Skips verification if MFA is not enabled for the user or in dev/test environments
    (unless SARDIS_REQUIRE_ADMIN_MFA=1 is set).
    """
    env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
    force_mfa = os.getenv("SARDIS_REQUIRE_ADMIN_MFA", "").strip().lower() in (
        "1", "true", "yes", "on",
    )

    # In dev/test, skip MFA unless explicitly forced
    if env not in ("prod", "production") and not force_mfa:
        return

    # Only enforce MFA for JWT-authenticated users (not API keys)
    if principal.kind != "jwt":
        return

    user = principal.user
    if user is None:
        return

    user_id = getattr(user, "username", None) or getattr(user, "id", None)
    if not user_id:
        return

    mfa_status = await _get_user_mfa_status(user_id)
    if not mfa_status["enabled"]:
        if env in ("prod", "production"):
            logger.warning(
                "Admin user %s has no MFA enabled — consider enforcing MFA setup",
                user_id,
            )
        return

    # MFA is enabled — require the code
    mfa_code = request.headers.get("X-MFA-Code", "").strip()
    if not mfa_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA code required. Provide X-MFA-Code header.",
        )

    # Verify TOTP code
    try:
        import pyotp

        totp = pyotp.TOTP(mfa_status["secret"])
        if not totp.verify(mfa_code, valid_window=1):
            logger.warning("Invalid MFA code for admin user %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid MFA code",
            )
    except ImportError:
        logger.error("pyotp not installed — MFA verification unavailable")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA verification unavailable",
        )

    logger.info("MFA verified for admin user %s", user_id)
