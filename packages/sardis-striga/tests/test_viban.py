"""Tests for Striga vIBAN management."""
from __future__ import annotations

import pytest

from sardis_striga.models import StrigaVIBAN, StrigaVIBANStatus


class TestStrigaVIBAN:
    """Tests for StrigaVIBAN model."""

    def test_viban_creation(self):
        """Test vIBAN model creation."""
        viban = StrigaVIBAN(
            viban_id="viban_001",
            wallet_id="wal_001",
            user_id="user_001",
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
            currency="EUR",
        )
        assert viban.iban == "DE89370400440532013000"
        assert viban.bic == "COBADEFFXXX"
        assert viban.currency == "EUR"
        assert viban.status == StrigaVIBANStatus.ACTIVE

    def test_viban_default_status(self):
        """Test vIBAN default status is ACTIVE."""
        viban = StrigaVIBAN(
            viban_id="viban_002",
            wallet_id="wal_002",
            user_id="user_002",
            iban="FR7630006000011234567890189",
        )
        assert viban.status == StrigaVIBANStatus.ACTIVE
