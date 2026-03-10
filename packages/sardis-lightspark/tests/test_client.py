"""Tests for Lightspark Grid HTTP client."""
from __future__ import annotations

import pytest

from sardis_lightspark.client import GridClient
from sardis_lightspark.config import LightsparkConfig


@pytest.fixture
def config():
    return LightsparkConfig(
        api_key="test_grid_key",
        api_secret="test_grid_secret",
        base_url="https://api.grid.test",
        uma_domain="sardis.sh",
    )


@pytest.fixture
def client(config):
    return GridClient(config)


class TestGridClient:
    """Tests for GridClient."""

    def test_auth_headers(self, client):
        """Test authentication header generation."""
        headers = client._auth_headers()
        assert headers["Authorization"] == "Bearer test_grid_key"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test client cleanup."""
        await client._get_client()
        assert client._http_client is not None

        await client.close()
        assert client._http_client is None

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """Test async context manager."""
        async with GridClient(config) as client:
            assert client is not None


class TestLightsparkConfig:
    """Tests for LightsparkConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LightsparkConfig()
        assert config.api_key == ""
        assert config.enabled is False
        assert config.uma_domain == "sardis.sh"
        assert config.fx_enabled is True
        assert config.environment == "sandbox"

    def test_custom_config(self):
        """Test custom configuration."""
        config = LightsparkConfig(
            api_key="sk_grid",
            enabled=True,
            uma_domain="custom.sh",
        )
        assert config.api_key == "sk_grid"
        assert config.enabled is True
        assert config.uma_domain == "custom.sh"
