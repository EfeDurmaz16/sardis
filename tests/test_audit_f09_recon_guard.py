"""Test that InMemoryReconciliationQueue is blocked in production."""
import logging
import os
from unittest.mock import patch

import pytest
from sardis.core.orchestrator import InMemoryReconciliationQueue


def test_production_raises_runtime_error():
    """Test that RuntimeError is raised when SARDIS_ENVIRONMENT=production."""
    env = {"SARDIS_ENVIRONMENT": "production"}
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("SARDIS_ENV", None)  # ensure fallback doesn't interfere
        with pytest.raises(RuntimeError, match="InMemoryReconciliationQueue"):
            InMemoryReconciliationQueue()


def test_development_no_warning(caplog):
    """Test that no warning is logged in development mode."""
    with patch.dict(os.environ, {"SARDIS_ENV": "development"}):
        with caplog.at_level(logging.CRITICAL):
            InMemoryReconciliationQueue()

        # Verify no critical logs
        assert not any(
            "InMemoryReconciliationQueue is NOT suitable for production" in record.message
            for record in caplog.records
        )


def test_default_env_no_warning(caplog):
    """Test that no warning is logged when SARDIS_ENV is not set (defaults to development)."""
    with patch.dict(os.environ, {}, clear=True):
        # Remove SARDIS_ENV if it exists
        os.environ.pop("SARDIS_ENV", None)

        with caplog.at_level(logging.CRITICAL):
            InMemoryReconciliationQueue()

        # Verify no critical logs
        assert not any(
            "InMemoryReconciliationQueue is NOT suitable for production" in record.message
            for record in caplog.records
        )


def test_staging_raises_runtime_error():
    """Test that RuntimeError is raised in staging too."""
    env = {"SARDIS_ENVIRONMENT": "staging"}
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("SARDIS_ENV", None)
        with pytest.raises(RuntimeError, match="InMemoryReconciliationQueue"):
            InMemoryReconciliationQueue()
