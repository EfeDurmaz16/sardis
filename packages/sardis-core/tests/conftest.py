"""
Pytest configuration for sardis-core tests.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Add package source to path
package_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(package_src))

# Also add root packages directory for cross-package imports
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists() and str(pkg_path) not in sys.path:
        sys.path.insert(0, str(pkg_path))

# Set test environment
os.environ.setdefault("SARDIS_ENVIRONMENT", "dev")
os.environ.setdefault("SARDIS_SECRET_KEY", "test-secret-key-for-testing-only")


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"


@pytest.fixture
def sample_wallet_id():
    """Valid wallet ID for testing."""
    return "wallet_1234567890abcdef"


@pytest.fixture
def sample_agent_id():
    """Valid agent ID for testing."""
    return "agent_1234567890abcdef"


@pytest.fixture
def sample_eth_address():
    """Valid Ethereum address for testing."""
    return "0x1234567890123456789012345678901234567890"


@pytest.fixture
def sample_solana_address():
    """Valid Solana address for testing."""
    return "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV"
