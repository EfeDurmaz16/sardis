"""Tests for UMA address management."""
from __future__ import annotations

import pytest

from sardis_lightspark.models import UMAAddress, UMAAddressStatus


class TestUMAAddress:
    """Tests for UMA address model."""

    def test_address_format(self):
        """Test UMA address format."""
        addr = UMAAddress(
            uma_id="uma_001",
            address="$my-agent@sardis.sh",
            wallet_id="wal_123",
        )
        assert addr.local_part == "my-agent"
        assert addr.domain == "sardis.sh"

    def test_default_status(self):
        """Test default UMA address status."""
        addr = UMAAddress(
            uma_id="uma_002",
            address="$test@sardis.sh",
            wallet_id="wal_456",
        )
        assert addr.status == UMAAddressStatus.ACTIVE
        assert addr.currency == "USD"

    def test_address_without_dollar(self):
        """Test local_part strips dollar sign."""
        addr = UMAAddress(
            uma_id="uma_003",
            address="$agent123@sardis.sh",
            wallet_id="wal_789",
        )
        assert addr.local_part == "agent123"


class TestUMARegistry:
    """Tests for UMA registry pattern."""

    def test_address_model_roundtrip(self):
        """Test creating and reading UMA address model."""
        addr = UMAAddress(
            uma_id="uma_reg_001",
            address="$payment-bot@sardis.sh",
            wallet_id="wal_abc",
            currency="EUR",
            status=UMAAddressStatus.ACTIVE,
        )
        assert addr.domain == "sardis.sh"
        assert addr.local_part == "payment-bot"
        assert addr.currency == "EUR"
