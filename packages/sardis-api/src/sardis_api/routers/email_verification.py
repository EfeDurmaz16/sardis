"""Email verification flow — send and confirm endpoints."""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import smtplib
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from sardis_api.routers.auth import UserInfo, require_auth

_logger = logging.getLogger(__name__)

router = APIRouter()

# TODO: use DB (email_verification_tokens table from migration 066)
# Keyed by token_hash -> {"user_id": str, "expires_at": datetime, "used_at": datetime | None}
_token_store: dict[str, dict] = {}

_TOKEN_TTL_HOURS = 24


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _send_verification_email(to_email: str, verification_link: str) -> None:
    """Send a verification email via SMTP.

    No-op if SMTP_HOST is not configured.
    """
    smtp_host = os.getenv("SMTP_HOST", "")
    if not smtp_host:
        _logger.info(
            "SMTP_HOST not configured — skipping verification email to %s (link: %s)",
            to_email,
            verification_link,
        )
        return

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user or "noreply@sardis.sh")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() not in ("0", "false", "no")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your Sardis email address"
    msg["From"] = from_email
    msg["To"] = to_email

    text_body = (
        f"Please verify your email address by clicking the link below:\n\n"
        f"{verification_link}\n\n"
        f"This link expires in {_TOKEN_TTL_HOURS} hours.\n\n"
        f"If you did not request this, you can safely ignore this email."
    )
    html_body = (
        f"<html><body>"
        f"<p>Please verify your email address by clicking the link below:</p>"
        f'<p><a href="{verification_link}">{verification_link}</a></p>'
        f"<p>This link expires in {_TOKEN_TTL_HOURS} hours.</p>"
        f"<p>If you did not request this, you can safely ignore this email.</p>"
        f"</body></html>"
    )

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)

        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)

        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        _logger.info("Verification email sent to %s", to_email)
    except Exception as exc:
        _logger.error("Failed to send verification email to %s: %s", to_email, exc)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SendVerificationResponse(BaseModel):
    sent: bool
    message: str


class ConfirmVerificationRequest(BaseModel):
    token: str


class ConfirmVerificationResponse(BaseModel):
    email_verified: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/verify-email/send",
    response_model=SendVerificationResponse,
    summary="Send a verification email to the authenticated user",
)
async def send_verification_email(
    request: Request,
    user: UserInfo = Depends(require_auth),
) -> SendVerificationResponse:
    """Generate a verification token and email a confirmation link.

    Requires a valid bearer token. Returns 200 regardless of whether SMTP is
    configured so callers can always treat the response as success.
    """
    user_id = user.username

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(hours=_TOKEN_TTL_HOURS)

    # TODO: use DB — INSERT INTO email_verification_tokens
    _token_store[token_hash] = {
        "user_id": user_id,
        "expires_at": expires_at,
        "used_at": None,
    }

    base_url = os.getenv("SARDIS_API_BASE_URL", "https://api.sardis.sh")
    verification_link = f"{base_url}/api/v2/auth/verify-email/confirm?token={raw_token}"

    # Derive email from user_id (may be an email address itself) or fall back
    to_email = user_id if "@" in user_id else os.getenv("SARDIS_VERIFICATION_FALLBACK_EMAIL", user_id)

    _send_verification_email(to_email=to_email, verification_link=verification_link)

    return SendVerificationResponse(sent=True, message="Verification email sent")


@router.post(
    "/verify-email/confirm",
    response_model=ConfirmVerificationResponse,
    summary="Confirm an email address using a verification token",
)
async def confirm_verification_email(
    request: Request,
    body: ConfirmVerificationRequest,
) -> ConfirmVerificationResponse:
    """Validate a verification token and mark the user's email as verified.

    Public endpoint — no authentication required.
    Returns 400 if the token is expired, already used, or not found.
    """
    token_hash = _hash_token(body.token)

    # TODO: use DB — SELECT ... FROM email_verification_tokens WHERE token_hash = $1
    record = _token_store.get(token_hash)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unknown verification token",
        )

    if record["used_at"] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has already been used",
        )

    now = datetime.now(UTC)
    if now > record["expires_at"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired",
        )

    # Mark token as used
    # TODO: use DB — UPDATE email_verification_tokens SET used_at = NOW() WHERE token_hash = $1
    record["used_at"] = now

    # Mark user email as verified
    # TODO: use DB — UPDATE users SET email_verified = TRUE WHERE id = $1
    user_id = record["user_id"]
    database_url = getattr(getattr(request.app, "state", None), "database_url", None)
    if database_url and (database_url.startswith("postgresql://") or database_url.startswith("postgres://")):
        try:
            from sardis_api.services.auth_service import AuthService
            auth_svc = AuthService(dsn=database_url)
            await auth_svc.mark_email_verified(user_id=user_id)
        except Exception as exc:
            _logger.error("Failed to persist email_verified for user %s: %s", user_id, exc)

    _logger.info("Email verified for user %s", user_id)
    return ConfirmVerificationResponse(email_verified=True)
