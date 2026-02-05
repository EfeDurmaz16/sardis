"""Test that InMemoryReconciliationQueue warns in production."""
import logging
import os
import pytest
from unittest.mock import patch
from sardis_v2_core.orchestrator import InMemoryReconciliationQueue


def test_production_warning_logged(caplog):
    """Test that critical warning is logged when SARDIS_ENV=production."""
    with patch.dict(os.environ, {"SARDIS_ENV": "production"}):
        with caplog.at_level(logging.CRITICAL):
            queue = InMemoryReconciliationQueue()

        # Verify critical log was emitted
        assert any(
            "InMemoryReconciliationQueue is NOT suitable for production" in record.message
            for record in caplog.records
        )
        assert any(
            "WILL BE LOST on restart" in record.message
            for record in caplog.records
        )


def test_development_no_warning(caplog):
    """Test that no warning is logged in development mode."""
    with patch.dict(os.environ, {"SARDIS_ENV": "development"}):
        with caplog.at_level(logging.CRITICAL):
            queue = InMemoryReconciliationQueue()

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
            queue = InMemoryReconciliationQueue()

        # Verify no critical logs
        assert not any(
            "InMemoryReconciliationQueue is NOT suitable for production" in record.message
            for record in caplog.records
        )


def test_staging_no_warning(caplog):
    """Test that no warning is logged in staging (only production triggers it)."""
    with patch.dict(os.environ, {"SARDIS_ENV": "staging"}):
        with caplog.at_level(logging.CRITICAL):
            queue = InMemoryReconciliationQueue()

        # Verify no critical logs
        assert not any(
            "InMemoryReconciliationQueue is NOT suitable for production" in record.message
            for record in caplog.records
        )
