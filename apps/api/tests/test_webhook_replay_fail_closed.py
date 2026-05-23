"""Webhook replay protection fail-closed behavior.

Pinned by ~/project-directions/sardis-sdk-security-model.md §4 (Webhook event_id):
the absence of a cache MUST NOT silently bypass replay protection, because a
captured webhook could otherwise be replayed indefinitely.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from server.webhook_replay import run_with_replay_protection


def _fake_request(cache_service=None):
    """Build the minimal Request-shaped object run_with_replay_protection needs."""
    app = SimpleNamespace(state=SimpleNamespace(cache_service=cache_service))
    return SimpleNamespace(app=app)


@pytest.mark.asyncio
async def test_missing_cache_rejects_by_default():
    """No cache_service on app.state -> 503, handler MUST NOT run."""
    called = False

    async def handler():
        nonlocal called
        called = True
        return "ok"

    with pytest.raises(HTTPException) as exc:
        await run_with_replay_protection(
            request=_fake_request(cache_service=None),
            provider="stripe",
            event_id="evt_123",
            fn=handler,
        )

    assert exc.value.status_code == 503
    assert exc.value.detail == "webhook_replay_cache_unavailable"
    assert called is False, "handler must not run when replay protection cannot be enforced"


@pytest.mark.asyncio
async def test_missing_cache_allowed_with_explicit_opt_out():
    """Explicit require_replay_protection=False is the only way past the gate."""
    async def handler():
        return "handled"

    result = await run_with_replay_protection(
        request=_fake_request(cache_service=None),
        provider="stripe",
        event_id="evt_123",
        require_replay_protection=False,
        fn=handler,
    )
    assert result == "handled"


@pytest.mark.asyncio
async def test_missing_event_id_rejected_when_protected():
    """Without a stable dedupe key, replay protection is impossible -> 400."""
    called = False

    async def handler():
        nonlocal called
        called = True
        return "ok"

    class _Cache:  # cache present, but event_id missing
        async def get(self, *a, **kw):
            return None

    with pytest.raises(HTTPException) as exc:
        await run_with_replay_protection(
            request=_fake_request(cache_service=_Cache()),
            provider="stripe",
            event_id="",
            fn=handler,
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "webhook_event_id_required"
    assert called is False
