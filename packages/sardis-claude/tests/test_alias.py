"""Smoke tests for the sardis-claude thin alias package."""

import warnings


def test_imports_resolve_to_agent_sdk():
    import sardis_agent_sdk
    import sardis_claude

    assert sardis_claude.SardisToolkit is sardis_agent_sdk.SardisToolkit
    assert sardis_claude.SardisToolHandler is sardis_agent_sdk.SardisToolHandler
    assert sardis_claude.ALL_TOOLS is sardis_agent_sdk.ALL_TOOLS


def test_version_present():
    import sardis_claude

    assert isinstance(sardis_claude.__version__, str)
    assert sardis_claude.__version__


def test_import_suppresses_upstream_deprecation_warning():
    """Importing the alias should not surface the agent-sdk rename warning."""
    import importlib

    import sardis_claude

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(sardis_claude)

    rename_warnings = [
        w
        for w in caught
        if issubclass(w.category, DeprecationWarning)
        and "sardis-agent-sdk" in str(w.message)
    ]
    assert rename_warnings == []
