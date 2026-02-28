"""Shared fixtures for sardis-protocol tests."""
import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
