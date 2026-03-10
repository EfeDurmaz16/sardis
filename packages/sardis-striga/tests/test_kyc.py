"""Tests for Striga KYC provider."""
from __future__ import annotations

import hashlib
import hmac

import pytest

from sardis_striga.kyc import StrigaKYCProvider


class TestStrigaKYCProvider:
    """Tests for StrigaKYCProvider interface."""

    def test_implements_kyc_interface(self):
        """Test that StrigaKYCProvider implements KYCProvider ABC."""
        assert hasattr(StrigaKYCProvider, 'create_inquiry')
        assert hasattr(StrigaKYCProvider, 'get_inquiry_status')
        assert hasattr(StrigaKYCProvider, 'cancel_inquiry')
        assert hasattr(StrigaKYCProvider, 'verify_webhook')
