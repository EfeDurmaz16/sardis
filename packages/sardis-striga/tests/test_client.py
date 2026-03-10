"""Tests for Striga HTTP client."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from sardis_striga.client import StrigaClient
from sardis_striga.config import StrigaConfig
from sardis_striga.exceptions import StrigaAuthError, StrigaRateLimitError, StrigaValidationError


@pytest.fixture
def config():
    return StrigaConfig(
        api_key="test_key",
        api_secret="test_secret",
        base_url="https://api.striga.test",
    )


@pytest.fixture
def client(config):
    return StrigaClient(config)


class TestStrigaClient:
    """Tests for StrigaClient."""

    def test_sign_request(self, client):
        """Test HMAC-SHA256 request signing."""
        timestamp = "1234567890"
        method = "POST"
        path = "/v1/test"
        body = '{"key":"value"}'

        sig = client._sign_request(timestamp, method, path, body)

        # Verify manually
        message = f"{timestamp}{method}{path}{body}"
        expected = hmac.new(
            b"test_secret",
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        assert sig == expected

    def test_sign_request_empty_body(self, client):
        """Test signing with empty body."""
        sig = client._sign_request("123", "GET", "/test", "")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex digest

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test client cleanup."""
        # Create client first
        await client._get_client()
        assert client._http_client is not None

        await client.close()
        assert client._http_client is None

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """Test async context manager."""
        async with StrigaClient(config) as client:
            assert client is not None


class TestStrigaConfig:
    """Tests for StrigaConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = StrigaConfig()
        assert config.api_key == ""
        assert config.enabled is False
        assert config.cards_enabled is True
        assert config.viban_enabled is True
        assert config.environment == "sandbox"

    def test_custom_config(self):
        """Test custom configuration."""
        config = StrigaConfig(
            api_key="sk_test",
            enabled=True,
            environment="production",
        )
        assert config.api_key == "sk_test"
        assert config.enabled is True
        assert config.environment == "production"
