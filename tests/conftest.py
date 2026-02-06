"""Pytest configuration for Sardis V2 API tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest
from typing import AsyncGenerator
from unittest.mock import patch

# Add package paths for testing FIRST
root_dir = Path(__file__).parent.parent
packages_dir = root_dir / "packages"
for pkg in ["sardis-core", "sardis-api", "sardis-wallet", "sardis-protocol",
            "sardis-chain", "sardis-ledger", "sardis-compliance", "sardis-checkout",
            "sardis-cards", "sardis-ramp", "sardis-sdk-python", "sardis-ucp"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

# Also add the root sardis package
sys.path.insert(0, str(root_dir))

# Clear any cached settings and set clean test environment
# Remove problematic env vars that might be read from .env
for key in list(os.environ.keys()):
    if key.startswith("SARDIS_") and key not in {"SARDIS_ENVIRONMENT", "SARDIS_ALLOW_ANON"}:
        del os.environ[key]

os.environ["SARDIS_ENVIRONMENT"] = "dev"
os.environ["SARDIS_ALLOW_ANON"] = os.environ.get("SARDIS_ALLOW_ANON", "1")
os.environ["SARDIS_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["SARDIS_CHAIN_MODE"] = "simulated"

# Clear the settings cache so tests get fresh settings
from sardis_v2_core.config import load_settings
load_settings.cache_clear()

_BASE_SARDIS_ENV: dict[str, str] = {
    "SARDIS_ENVIRONMENT": os.environ["SARDIS_ENVIRONMENT"],
    "SARDIS_ALLOW_ANON": os.environ["SARDIS_ALLOW_ANON"],
    "SARDIS_SECRET_KEY": os.environ["SARDIS_SECRET_KEY"],
    "SARDIS_CHAIN_MODE": os.environ["SARDIS_CHAIN_MODE"],
}

_BASE_OTHER_ENV: dict[str, str | None] = {
    "DATABASE_URL": os.environ.get("DATABASE_URL"),
    "REDIS_URL": os.environ.get("REDIS_URL"),
    "UPSTASH_REDIS_URL": os.environ.get("UPSTASH_REDIS_URL"),
    "SARDIS_REDIS_URL": os.environ.get("SARDIS_REDIS_URL"),
}


@pytest.fixture(autouse=True)
def _reset_sardis_env_between_tests():
    """
    Prevent cross-test leakage via environment variables and cached settings.

    Many components use env vars + cached settings at import/runtime. Without
    resetting between tests, auth/anon mode and backends can drift and cause
    flaky failures.
    """
    # Reset before test
    for key in list(os.environ.keys()):
        if key.startswith("SARDIS_"):
            del os.environ[key]
    os.environ.update(_BASE_SARDIS_ENV)
    for key, value in _BASE_OTHER_ENV.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    load_settings.cache_clear()

    yield

    # Reset after test
    for key in list(os.environ.keys()):
        if key.startswith("SARDIS_"):
            del os.environ[key]
    os.environ.update(_BASE_SARDIS_ENV)
    for key, value in _BASE_OTHER_ENV.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    load_settings.cache_clear()


# Check if PostgreSQL database is available
def has_postgres_db():
    """Check if PostgreSQL database is available for testing."""
    db_url = os.environ.get("DATABASE_URL", "")
    return db_url.startswith("postgresql://") or db_url.startswith("postgres://")


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"


def pytest_configure(config):
    """Register custom markers for protocol conformance testing."""
    config.addinivalue_line("markers", "protocol_conformance: Protocol conformance test")
    config.addinivalue_line("markers", "tap: TAP (Trusted Agent Protocol) test")
    config.addinivalue_line("markers", "ap2: AP2 (Agent Payment Protocol) test")
    config.addinivalue_line("markers", "ucp: UCP (Universal Commerce Protocol) test")
    config.addinivalue_line("markers", "x402: x402 (HTTP 402 Micropayments) test")
    config.addinivalue_line("markers", "security: Security invariant test")
    config.addinivalue_line("markers", "sdk: SDK conformance test")
    config.addinivalue_line("markers", "integration: Integration test")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-mark tests under tests/e2e as e2e."""
    for item in items:
        try:
            path = str(item.fspath)
        except Exception:
            continue
        if "/tests/e2e/" in path.replace("\\", "/"):
            item.add_marker(pytest.mark.e2e)


@pytest.fixture
def test_settings():
    """Get test settings."""
    from sardis_v2_core import load_settings
    return load_settings()


@pytest.fixture
async def test_client():
    """Create a test client for the API."""
    from httpx import AsyncClient, ASGITransport
    from sardis_api.main import create_app
    
    app = create_app()
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def sample_mandate():
    """Create a sample payment mandate for testing."""
    import time
    from sardis_v2_core.mandates import PaymentMandate
    
    return PaymentMandate(
        mandate_id="test_mandate_001",
        issuer="test_issuer",
        subject="test_wallet",
        destination="0x1234567890123456789012345678901234567890",
        amount_minor=10000,  # $100.00
        token="USDC",
        chain="base_sepolia",
        expires_at=int(time.time()) + 300,
    )


@pytest.fixture
def sample_hold_request():
    """Create a sample hold request for testing."""
    return {
        "wallet_id": "test_wallet_001",
        "amount": "1000",
        "token": "USDC",
        "merchant_id": "test_merchant",
        "purpose": "Test hold",
        "expiration_hours": 24,
    }


@pytest.fixture
def sample_webhook_request():
    """Create a sample webhook subscription request."""
    return {
        "url": "https://example.com/webhook",
        "events": ["payment.completed", "hold.created"],
    }


@pytest.fixture
def sample_service_request():
    """Create a sample marketplace service request."""
    return {
        "name": "Test AI Service",
        "description": "A test AI service for automated tasks",
        "category": "ai",
        "tags": ["ai", "automation", "test"],
        "price_amount": "100.00",
        "price_token": "USDC",
        "price_type": "fixed",
    }
