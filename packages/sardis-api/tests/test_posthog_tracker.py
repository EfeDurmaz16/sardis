"""Tests for PostHog analytics tracker — verifies no-op behavior without POSTHOG_API_KEY."""
from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch


def _reload_tracker_without_key():
    """Reload the tracker module with POSTHOG_API_KEY unset."""
    # Remove cached module so environment changes take effect
    for mod_name in list(sys.modules):
        if "posthog_tracker" in mod_name:
            del sys.modules[mod_name]
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("POSTHOG_API_KEY", None)
        from sardis_api.analytics import posthog_tracker
        return posthog_tracker


def test_track_event_noop_without_key():
    """track_event is a no-op when POSTHOG_API_KEY is not set."""
    tracker = _reload_tracker_without_key()
    # Should not raise and should do nothing
    tracker.track_event("user_123", "some_event", {"foo": "bar"})


def test_identify_user_noop_without_key():
    """identify_user is a no-op when POSTHOG_API_KEY is not set."""
    tracker = _reload_tracker_without_key()
    # Should not raise and should do nothing
    tracker.identify_user("user_123", {"email": "test@example.com"})


def test_track_event_does_not_raise_on_error():
    """track_event swallows exceptions and never raises."""
    tracker = _reload_tracker_without_key()

    # Inject a fake client that raises on capture
    mock_client = MagicMock()
    mock_client.capture.side_effect = RuntimeError("network error")
    tracker._client = mock_client

    try:
        tracker.track_event("user_123", "test_event")
    except Exception as exc:
        raise AssertionError(f"track_event raised unexpectedly: {exc}") from exc
    finally:
        # Reset client so other tests stay isolated
        tracker._client = None


def test_identify_user_does_not_raise_on_error():
    """identify_user swallows exceptions and never raises."""
    tracker = _reload_tracker_without_key()

    mock_client = MagicMock()
    mock_client.identify.side_effect = RuntimeError("network error")
    tracker._client = mock_client

    try:
        tracker.identify_user("user_123", {"plan": "free"})
    except Exception as exc:
        raise AssertionError(f"identify_user raised unexpectedly: {exc}") from exc
    finally:
        tracker._client = None


def test_event_name_constants_defined():
    """All standard event name constants are non-empty strings."""
    tracker = _reload_tracker_without_key()
    constants = [
        tracker.SIGNUP_COMPLETED,
        tracker.FIRST_AGENT_CREATED,
        tracker.FIRST_POLICY_CREATED,
        tracker.FIRST_PAYMENT,
        tracker.API_KEY_CREATED,
        tracker.PLAN_UPGRADED,
        tracker.DASHBOARD_LOGIN,
    ]
    for constant in constants:
        assert isinstance(constant, str) and constant, f"Expected non-empty string, got {constant!r}"
