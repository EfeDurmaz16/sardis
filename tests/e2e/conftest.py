"""
Pytest configuration for E2E tests.
"""
import os
import pytest


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--api-url",
        action="store",
        default="http://localhost:8000",
        help="Sardis API URL for E2E tests",
    )
    parser.addoption(
        "--api-key",
        action="store",
        default="sk_test_sardis_e2e",
        help="API key for E2E tests",
    )


@pytest.fixture(scope="session")
def api_url(request):
    """Get API URL from command line or environment."""
    return os.getenv("SARDIS_API_URL", request.config.getoption("--api-url"))


@pytest.fixture(scope="session")
def api_key(request):
    """Get API key from command line or environment."""
    return os.getenv("SARDIS_TEST_API_KEY", request.config.getoption("--api-key"))
