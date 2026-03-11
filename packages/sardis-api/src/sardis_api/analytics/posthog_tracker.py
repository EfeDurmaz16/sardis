"""PostHog product analytics — tracks user behavior events. No-op when not configured."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_client = None
_POSTHOG_KEY = os.getenv("POSTHOG_API_KEY", "")
_POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")

if _POSTHOG_KEY:
    try:
        import posthog
        posthog.project_api_key = _POSTHOG_KEY
        posthog.host = _POSTHOG_HOST
        _client = posthog
        logger.info("PostHog analytics initialized")
    except ImportError:
        logger.warning("posthog package not installed, analytics disabled")


def track_event(user_id: str, event: str, properties: dict | None = None) -> None:
    if not _client:
        return
    try:
        _client.capture(user_id, event, properties or {})
    except Exception as e:
        logger.warning(f"PostHog tracking failed: {e}")


def identify_user(user_id: str, properties: dict | None = None) -> None:
    if not _client:
        return
    try:
        _client.identify(user_id, properties or {})
    except Exception as e:
        logger.warning(f"PostHog identify failed: {e}")


# Standard event names
SIGNUP_COMPLETED = "signup_completed"
FIRST_AGENT_CREATED = "first_agent_created"
FIRST_POLICY_CREATED = "first_policy_created"
FIRST_PAYMENT = "first_payment"
API_KEY_CREATED = "api_key_created"
PLAN_UPGRADED = "plan_upgraded"
DASHBOARD_LOGIN = "dashboard_login"
