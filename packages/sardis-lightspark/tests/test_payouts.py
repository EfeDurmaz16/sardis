"""Tests for Grid payout provider."""
from __future__ import annotations

import pytest

from sardis_lightspark.payouts import GridPayoutProvider
from sardis_lightspark.models import GridPaymentRail


class TestGridPayoutProvider:
    """Tests for GridPayoutProvider interface."""

    def test_implements_ramp_interface(self):
        """Test that GridPayoutProvider implements RampProvider ABC."""
        assert hasattr(GridPayoutProvider, 'provider_name')
        assert hasattr(GridPayoutProvider, 'supports_onramp')
        assert hasattr(GridPayoutProvider, 'supports_offramp')
        assert hasattr(GridPayoutProvider, 'get_quote')
        assert hasattr(GridPayoutProvider, 'create_offramp')
        assert hasattr(GridPayoutProvider, 'get_status')
        assert hasattr(GridPayoutProvider, 'handle_webhook')

    def test_rail_fees(self):
        """Test fee schedule for different rails."""
        fees = GridPayoutProvider.RAIL_FEES_BPS
        assert fees[GridPaymentRail.ACH] == 25
        assert fees[GridPaymentRail.RTP] == 75
        assert fees[GridPaymentRail.WIRE] == 100
        assert fees[GridPaymentRail.FEDNOW] == 75
