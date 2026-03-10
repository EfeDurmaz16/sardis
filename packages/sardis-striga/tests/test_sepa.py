"""Tests for Striga SEPA provider."""
from __future__ import annotations

from decimal import Decimal

import pytest


class TestStrigaSEPAProvider:
    """Tests for StrigaSEPAProvider properties."""

    def test_provider_properties(self):
        """Test SEPA provider is correctly identified."""
        # Can't instantiate without real client, test properties via assertion
        from sardis_striga.sepa import StrigaSEPAProvider
        # Verify the class has the right interface
        assert hasattr(StrigaSEPAProvider, 'provider_name')
        assert hasattr(StrigaSEPAProvider, 'supports_onramp')
        assert hasattr(StrigaSEPAProvider, 'supports_offramp')
        assert hasattr(StrigaSEPAProvider, 'get_quote')
        assert hasattr(StrigaSEPAProvider, 'create_onramp')
        assert hasattr(StrigaSEPAProvider, 'create_offramp')
        assert hasattr(StrigaSEPAProvider, 'get_status')
        assert hasattr(StrigaSEPAProvider, 'handle_webhook')
