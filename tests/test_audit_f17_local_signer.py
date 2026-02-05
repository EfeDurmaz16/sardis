"""
Test F17: LocalAccountSigner dev-only warning.

Ensures that LocalAccountSigner warns when used in production,
since it stores private keys in memory (insecure).
"""
import pytest
import logging
from unittest.mock import patch
from sardis_chain.executor import LocalAccountSigner


@pytest.fixture
def test_private_key():
    """A test private key (never use in production)."""
    return "0x1234567890123456789012345678901234567890123456789012345678901234"


def test_local_signer_warns_in_production(test_private_key, caplog):
    """Test that LocalAccountSigner logs a warning when SARDIS_ENV=production."""
    with patch.dict("os.environ", {"SARDIS_ENV": "production"}):
        with caplog.at_level(logging.WARNING):
            signer = LocalAccountSigner(test_private_key)

            # Verify warning was logged
            assert any(
                "LocalAccountSigner stores private keys in memory" in record.message
                for record in caplog.records
            ), "Should warn about storing private keys in memory"

            assert any(
                "Use TurnkeySigner for production" in record.message
                for record in caplog.records
            ), "Should recommend TurnkeySigner for production"


def test_local_signer_no_warning_in_dev(test_private_key, caplog):
    """Test that LocalAccountSigner does NOT warn when SARDIS_ENV is not production."""
    with patch.dict("os.environ", {"SARDIS_ENV": "development"}, clear=True):
        with caplog.at_level(logging.WARNING):
            signer = LocalAccountSigner(test_private_key)

            # Verify no warning was logged
            assert not any(
                "LocalAccountSigner stores private keys in memory" in record.message
                for record in caplog.records
            ), "Should NOT warn in development environment"


def test_local_signer_no_warning_when_env_not_set(test_private_key, caplog):
    """Test that LocalAccountSigner does NOT warn when SARDIS_ENV is not set."""
    with patch.dict("os.environ", {}, clear=True):
        # Ensure SARDIS_ENV is not set
        import os
        if "SARDIS_ENV" in os.environ:
            del os.environ["SARDIS_ENV"]

        with caplog.at_level(logging.WARNING):
            signer = LocalAccountSigner(test_private_key)

            # Verify no warning was logged
            assert not any(
                "LocalAccountSigner stores private keys in memory" in record.message
                for record in caplog.records
            ), "Should NOT warn when SARDIS_ENV is not set"


def test_local_signer_still_works_in_production(test_private_key):
    """Test that LocalAccountSigner still functions despite the warning."""
    with patch.dict("os.environ", {"SARDIS_ENV": "production"}):
        signer = LocalAccountSigner(test_private_key)

        # Verify it still works
        assert signer._address is not None
        assert isinstance(signer._address, str)
        assert signer._address.startswith("0x")


def test_local_signer_requires_private_key():
    """Test that LocalAccountSigner raises error without private key."""
    with pytest.raises(ValueError, match="SARDIS_EOA_PRIVATE_KEY is required"):
        LocalAccountSigner("")


def test_local_signer_accepts_custom_address(test_private_key):
    """Test that LocalAccountSigner accepts a custom address."""
    custom_address = "0xCustomAddress1234567890123456789012345678"
    signer = LocalAccountSigner(test_private_key, address=custom_address)

    assert signer._address == custom_address


def test_local_signer_derives_address_from_key(test_private_key):
    """Test that LocalAccountSigner derives address from private key if not provided."""
    signer = LocalAccountSigner(test_private_key)

    # Verify address was derived (should be a valid Ethereum address)
    assert signer._address is not None
    assert isinstance(signer._address, str)
    assert len(signer._address) == 42  # 0x + 40 hex chars
    assert signer._address.startswith("0x")
