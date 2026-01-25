"""
Pytest configuration for sardis-chain tests.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Add package source to path
package_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(package_src))

# Add cross-package imports
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists() and str(pkg_path) not in sys.path:
        sys.path.insert(0, str(pkg_path))

# Set test environment
os.environ.setdefault("SARDIS_ENVIRONMENT", "dev")
os.environ.setdefault("SARDIS_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("SARDIS_CHAIN_MODE", "simulated")


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"


@pytest.fixture
def sample_eth_address():
    """Valid Ethereum address for testing."""
    return "0x1234567890123456789012345678901234567890"


@pytest.fixture
def sample_tx_hash():
    """Valid transaction hash for testing."""
    return "0x" + "a" * 64
