"""Tests for Plaid Link integration."""
from __future__ import annotations

import pytest

from sardis_lightspark.plaid import PlaidService


class TestPlaidService:
    """Tests for PlaidService interface."""

    def test_has_required_methods(self):
        """Test PlaidService has all required methods."""
        assert hasattr(PlaidService, 'create_link_token')
        assert hasattr(PlaidService, 'exchange_public_token')
        assert hasattr(PlaidService, 'get_bank_account')
