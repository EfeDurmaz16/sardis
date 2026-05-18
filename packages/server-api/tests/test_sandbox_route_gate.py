"""Ensure sandbox routes are not implicitly exposed in production."""
from __future__ import annotations

import inspect


def test_main_has_explicit_sandbox_enable_flag():
    from sardis_server import main

    source = inspect.getsource(main)
    assert "SARDIS_ENABLE_SANDBOX" in source
    assert "sandbox_env in (\"prod\", \"production\")" in source
    assert "Sandbox/Playground routes disabled" in source
