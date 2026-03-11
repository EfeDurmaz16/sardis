"""Email templates and sending utilities for Sardis transactional notifications.

All email sending is fire-and-forget — callers should wrap in try/except and
never let email failures block API responses.

SMTP is configured via environment variables:
  SMTP_HOST         SMTP server hostname (required; no-op if missing)
  SMTP_PORT         SMTP port (default 587)
  SMTP_USER         SMTP username / login
  SMTP_PASSWORD     SMTP password
  SMTP_FROM_EMAIL   From address (default noreply@sardis.sh)
"""
from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_logger = logging.getLogger(__name__)

_DASHBOARD_URL = "https://app.sardis.sh"
_DOCS_URL = "https://sardis.sh/docs"

# ---------------------------------------------------------------------------
# Base layout
# ---------------------------------------------------------------------------

_BASE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f5f5;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
          <!-- Header -->
          <tr>
            <td style="background-color:#0a0a0a;padding:24px 40px;">
              <span style="color:#ffffff;font-size:22px;font-weight:700;letter-spacing:-0.5px;">Sardis</span>
              <span style="color:#888888;font-size:13px;margin-left:8px;">Payment OS for the Agent Economy</span>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:36px 40px 28px 40px;color:#1a1a1a;">
              {body}
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background-color:#f9f9f9;border-top:1px solid #eeeeee;padding:20px 40px;">
              <p style="margin:0;font-size:12px;color:#888888;line-height:1.6;">
                You received this email because you have a Sardis account.
                &nbsp;&middot;&nbsp;
                <a href="{dashboard_url}" style="color:#888888;">Dashboard</a>
                &nbsp;&middot;&nbsp;
                <a href="{docs_url}" style="color:#888888;">Docs</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

_BUTTON_HTML = (
    '<a href="{url}" style="display:inline-block;margin-top:24px;padding:12px 28px;'
    "background-color:#0a0a0a;color:#ffffff;text-decoration:none;border-radius:6px;"
    'font-size:14px;font-weight:600;">{label}</a>'
)


def _render(subject: str, body: str) -> str:
    return _BASE_HTML.format(
        subject=subject,
        body=body,
        dashboard_url=_DASHBOARD_URL,
        docs_url=_DOCS_URL,
    )


def _button(url: str, label: str) -> str:
    return _BUTTON_HTML.format(url=url, label=label)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def _welcome_html(api_key_prefix: str) -> str:
    body = f"""\
<h2 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:#0a0a0a;">Welcome to Sardis</h2>
<p style="margin:0 0 20px 0;font-size:15px;color:#444444;line-height:1.7;">
  Your account is ready. Here is your test API key prefix — save the full key you received
  on signup, as it is shown only once.
</p>
<div style="background:#f4f4f4;border-radius:6px;padding:14px 18px;font-family:monospace;font-size:15px;color:#0a0a0a;letter-spacing:0.5px;">
  {api_key_prefix}
</div>
<p style="margin:20px 0 0 0;font-size:14px;color:#555555;line-height:1.7;">
  Use this key in the <code style="background:#f4f4f4;padding:2px 6px;border-radius:3px;">Authorization: Bearer &lt;key&gt;</code>
  header when calling the Sardis API.
</p>
<p style="margin:12px 0 0 0;font-size:14px;color:#555555;line-height:1.7;">
  Test mode is active by default — no real money moves until you switch to live mode in the dashboard.
</p>
{_button(_DASHBOARD_URL, "Open Dashboard")}
<hr style="border:none;border-top:1px solid #eeeeee;margin:32px 0;" />
<p style="margin:0;font-size:13px;color:#888888;line-height:1.6;">
  Need help getting started?
  <a href="{_DOCS_URL}/quickstart" style="color:#0a0a0a;font-weight:600;">Read the quickstart guide</a>
  or reply to this email.
</p>
"""
    return _render("Welcome to Sardis", body)


def _payment_notification_html(
    agent_name: str,
    amount: float,
    merchant: str,
    tx_id: str,
) -> str:
    amount_str = f"${amount:,.2f}"
    tx_url = f"{_DASHBOARD_URL}/transactions/{tx_id}"
    body = f"""\
<h2 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:#0a0a0a;">Payment Executed</h2>
<p style="margin:0 0 24px 0;font-size:15px;color:#444444;line-height:1.7;">
  Your agent completed a payment. Review the details below.
</p>
<table cellpadding="0" cellspacing="0" style="width:100%;border:1px solid #eeeeee;border-radius:6px;overflow:hidden;">
  <tr style="background:#f9f9f9;">
    <td style="padding:12px 16px;font-size:13px;color:#888888;font-weight:600;width:38%;">AGENT</td>
    <td style="padding:12px 16px;font-size:14px;color:#1a1a1a;font-weight:600;">{agent_name}</td>
  </tr>
  <tr>
    <td style="padding:12px 16px;font-size:13px;color:#888888;font-weight:600;border-top:1px solid #eeeeee;">MERCHANT</td>
    <td style="padding:12px 16px;font-size:14px;color:#1a1a1a;border-top:1px solid #eeeeee;">{merchant}</td>
  </tr>
  <tr style="background:#f9f9f9;">
    <td style="padding:12px 16px;font-size:13px;color:#888888;font-weight:600;border-top:1px solid #eeeeee;">AMOUNT</td>
    <td style="padding:12px 16px;font-size:20px;color:#0a0a0a;font-weight:700;border-top:1px solid #eeeeee;">{amount_str}</td>
  </tr>
  <tr>
    <td style="padding:12px 16px;font-size:13px;color:#888888;font-weight:600;border-top:1px solid #eeeeee;">TRANSACTION ID</td>
    <td style="padding:12px 16px;font-size:13px;color:#555555;font-family:monospace;border-top:1px solid #eeeeee;">{tx_id}</td>
  </tr>
</table>
{_button(tx_url, "View Transaction")}
<p style="margin:20px 0 0 0;font-size:13px;color:#888888;line-height:1.6;">
  If this payment was not authorized, please review your agent spending policy in the
  <a href="{_DASHBOARD_URL}/policies" style="color:#0a0a0a;font-weight:600;">dashboard</a>
  and disable the agent immediately.
</p>
"""
    return _render("Payment Executed", body)


def _policy_block_html(agent_name: str, amount: float, reason: str) -> str:
    amount_str = f"${amount:,.2f}"
    body = f"""\
<h2 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:#c0392b;">Payment Blocked</h2>
<p style="margin:0 0 24px 0;font-size:15px;color:#444444;line-height:1.7;">
  A payment attempt by one of your agents was blocked by your spending policy.
</p>
<div style="border-left:4px solid #e74c3c;background:#fff5f5;border-radius:0 6px 6px 0;padding:16px 20px;margin-bottom:24px;">
  <p style="margin:0 0 6px 0;font-size:13px;color:#888888;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Block reason</p>
  <p style="margin:0;font-size:15px;color:#c0392b;font-weight:600;">{reason}</p>
</div>
<table cellpadding="0" cellspacing="0" style="width:100%;border:1px solid #eeeeee;border-radius:6px;overflow:hidden;">
  <tr style="background:#f9f9f9;">
    <td style="padding:12px 16px;font-size:13px;color:#888888;font-weight:600;width:38%;">AGENT</td>
    <td style="padding:12px 16px;font-size:14px;color:#1a1a1a;font-weight:600;">{agent_name}</td>
  </tr>
  <tr>
    <td style="padding:12px 16px;font-size:13px;color:#888888;font-weight:600;border-top:1px solid #eeeeee;">ATTEMPTED AMOUNT</td>
    <td style="padding:12px 16px;font-size:20px;color:#c0392b;font-weight:700;border-top:1px solid #eeeeee;">{amount_str}</td>
  </tr>
</table>
{_button(f"{_DASHBOARD_URL}/policies", "Review Spending Policy")}
<p style="margin:20px 0 0 0;font-size:13px;color:#888888;line-height:1.6;">
  Your policy is working as intended. Adjust limits anytime in the
  <a href="{_DASHBOARD_URL}/policies" style="color:#0a0a0a;font-weight:600;">Policies</a> section.
</p>
"""
    return _render("Payment Blocked by Policy", body)


def _kyc_status_html(status: str) -> str:
    status_lower = status.lower()
    if status_lower in ("approved", "verified", "complete", "completed"):
        color = "#27ae60"
        icon_char = "&#10003;"
        headline = "Identity Verification Approved"
        detail = (
            "Your identity has been verified. You now have access to higher transaction "
            "limits and live payment features."
        )
        cta_url = f"{_DASHBOARD_URL}/settings/kyc"
        cta_label = "View Account"
    elif status_lower in ("rejected", "failed", "declined"):
        color = "#c0392b"
        icon_char = "&#10007;"
        headline = "Identity Verification Failed"
        detail = (
            "We could not verify your identity with the documents provided. "
            "Please review the requirements and resubmit."
        )
        cta_url = f"{_DASHBOARD_URL}/settings/kyc"
        cta_label = "Resubmit Documents"
    else:
        color = "#f39c12"
        icon_char = "&#8987;"
        headline = "Identity Verification In Review"
        detail = (
            "We received your documents and are reviewing them. "
            "This usually takes 1-2 business days. We will email you when a decision is made."
        )
        cta_url = f"{_DASHBOARD_URL}/settings/kyc"
        cta_label = "Check Status"

    status_label = status.replace("_", " ").title()
    body = f"""\
<h2 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:#0a0a0a;">{headline}</h2>
<div style="display:inline-block;background:{color};color:#ffffff;border-radius:20px;padding:4px 14px;font-size:13px;font-weight:700;margin-bottom:20px;">
  {icon_char}&nbsp; {status_label}
</div>
<p style="margin:0 0 24px 0;font-size:15px;color:#444444;line-height:1.7;">
  {detail}
</p>
{_button(cta_url, cta_label)}
<p style="margin:20px 0 0 0;font-size:13px;color:#888888;line-height:1.6;">
  Questions about your KYC status? Contact us at
  <a href="mailto:support@sardis.sh" style="color:#0a0a0a;font-weight:600;">support@sardis.sh</a>.
</p>
"""
    return _render(f"KYC Status Update: {status_label}", body)


def _plan_upgrade_html(plan: str) -> str:
    plan_label = plan.replace("_", " ").title()
    body = f"""\
<h2 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:#0a0a0a;">Plan Upgraded</h2>
<p style="margin:0 0 24px 0;font-size:15px;color:#444444;line-height:1.7;">
  Your Sardis plan has been upgraded. Welcome to <strong>{plan_label}</strong>.
</p>
<div style="background:#f0faf4;border:1px solid #27ae60;border-radius:6px;padding:20px 24px;margin-bottom:24px;">
  <p style="margin:0 0 4px 0;font-size:13px;color:#27ae60;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Current Plan</p>
  <p style="margin:0;font-size:22px;font-weight:700;color:#0a0a0a;">{plan_label}</p>
</div>
<p style="margin:0 0 8px 0;font-size:15px;color:#444444;line-height:1.7;">
  Your new limits and features are active immediately. Visit the dashboard to explore what is available on your plan.
</p>
{_button(_DASHBOARD_URL, "Go to Dashboard")}
<p style="margin:20px 0 0 0;font-size:13px;color:#888888;line-height:1.6;">
  Billing questions?
  <a href="mailto:billing@sardis.sh" style="color:#0a0a0a;font-weight:600;">billing@sardis.sh</a>
</p>
"""
    return _render(f"Plan Upgraded: {plan_label}", body)


# ---------------------------------------------------------------------------
# Core send function
# ---------------------------------------------------------------------------

async def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send a transactional HTML email via SMTP.

    Returns True if sent, False if SMTP is not configured or an error occurs.
    This function is safe to fire-and-forget — it never raises.
    """
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    if not smtp_host:
        _logger.debug("send_email: SMTP_HOST not set, skipping email to %s", to)
        return False

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@sardis.sh").strip()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to

    # Plain-text fallback (strip obvious HTML tags)
    import re
    plain = re.sub(r"<[^>]+>", "", html_body).strip()
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    def _smtp_send() -> None:
        # Use STARTTLS for port 587 (default), SSL for port 465
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
        try:
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [to], msg.as_string())
        finally:
            server.quit()

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _smtp_send)
        _logger.info("send_email: sent '%s' to %s", subject, to)
        return True
    except Exception as exc:  # noqa: BLE001
        _logger.warning("send_email: failed to send '%s' to %s: %s", subject, to, exc)
        return False


# ---------------------------------------------------------------------------
# Event-specific helpers
# ---------------------------------------------------------------------------

async def send_welcome_email(email: str, api_key_prefix: str) -> None:
    """Send a welcome email after registration with the API key prefix."""
    await send_email(
        to=email,
        subject="Welcome to Sardis — your API key is ready",
        html_body=_welcome_html(api_key_prefix),
    )


async def send_payment_notification(
    email: str,
    agent_name: str,
    amount: float,
    merchant: str,
    tx_id: str,
) -> None:
    """Notify the account owner that an agent executed a payment."""
    await send_email(
        to=email,
        subject=f"Payment executed by {agent_name}: ${amount:,.2f} to {merchant}",
        html_body=_payment_notification_html(agent_name, amount, merchant, tx_id),
    )


async def send_policy_block_notification(
    email: str,
    agent_name: str,
    amount: float,
    reason: str,
) -> None:
    """Notify the account owner that a payment was blocked by spending policy."""
    await send_email(
        to=email,
        subject=f"Payment blocked by policy — {agent_name} attempted ${amount:,.2f}",
        html_body=_policy_block_html(agent_name, amount, reason),
    )


async def send_kyc_status_email(email: str, status: str) -> None:
    """Notify the user of a KYC status change (approved / rejected / pending)."""
    status_label = status.replace("_", " ").title()
    await send_email(
        to=email,
        subject=f"Sardis identity verification: {status_label}",
        html_body=_kyc_status_html(status),
    )


async def send_plan_upgrade_email(email: str, plan: str) -> None:
    """Confirm a successful plan upgrade to the user."""
    plan_label = plan.replace("_", " ").title()
    await send_email(
        to=email,
        subject=f"Your Sardis plan has been upgraded to {plan_label}",
        html_body=_plan_upgrade_html(plan),
    )
