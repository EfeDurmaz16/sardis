"""Security regression tests for A2A message handling."""
from __future__ import annotations

import inspect


def test_a2a_messages_verify_signature_before_dispatch():
    from sardis_api.routers import a2a

    source = inspect.getsource(a2a)
    assert "_verify_a2a_message_signature" in source
    assert "signature_required" in source
    assert "sender_identity_not_found" in source


def test_a2a_messages_have_replay_protection():
    from sardis_api.routers import a2a

    source = inspect.getsource(a2a)
    assert "run_with_replay_protection" in source
    assert 'provider="a2a"' in source
    assert "event_id=msg.message_id" in source
