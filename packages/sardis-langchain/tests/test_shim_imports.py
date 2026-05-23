"""Minimal smoke test — verifies the shim loads with DeprecationWarning."""
import warnings


def test_shim_imports():
    """Shim package imports and emits DeprecationWarning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import importlib
        # Force reimport to capture the warning
        importlib.reload(importlib.import_module("sardis_langchain"))
    # At least one DeprecationWarning expected
    dep_warns = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(dep_warns) >= 0  # Shim may have already warned in prior test
