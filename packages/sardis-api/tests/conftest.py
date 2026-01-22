"""Pytest configuration and fixtures for Sardis API tests."""
from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient

# Set test environment before importing app
os.environ["SARDIS_ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "memory://"
os.environ["SARDIS_CHAIN_MODE"] = "simulated"

from sardis_api.main import create_app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app()


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "sk_test_demo123"},
    ) as ac:
        yield ac


@pytest.fixture
def test_wallet_id() -> str:
    """Test wallet ID."""
    return "wallet_test_001"


@pytest.fixture
def test_agent_id() -> str:
    """Test agent ID."""
    return "agent_test_001"
