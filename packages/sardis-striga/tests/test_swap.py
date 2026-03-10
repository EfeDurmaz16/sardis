"""Tests for Striga EURC→EUR swap provider."""
from __future__ import annotations

import pytest

from sardis_striga.swap import StrigaSwapProvider


class TestStrigaSwapProvider:
    """Tests for StrigaSwapProvider interface."""

    def test_implements_offramp_interface(self):
        """Test that StrigaSwapProvider implements OfframpProviderBase."""
        assert hasattr(StrigaSwapProvider, 'get_quote')
        assert hasattr(StrigaSwapProvider, 'execute_offramp')
        assert hasattr(StrigaSwapProvider, 'get_transaction_status')
        assert hasattr(StrigaSwapProvider, 'get_deposit_address')
