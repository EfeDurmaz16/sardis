"""Tests for Striga card provider."""
from __future__ import annotations

from decimal import Decimal

import pytest

from sardis_striga.models import StrigaCard, StrigaCardStatus, StrigaCardType


class TestStrigaCardModels:
    """Tests for Striga card models."""

    def test_card_defaults(self):
        """Test default card values."""
        card = StrigaCard(
            card_id="card_001",
            user_id="user_001",
            wallet_id="wal_001",
        )
        assert card.currency == "EUR"
        assert card.card_type == StrigaCardType.VIRTUAL
        assert card.status == StrigaCardStatus.CREATED

    def test_card_with_limits(self):
        """Test card with spending limits."""
        card = StrigaCard(
            card_id="card_002",
            user_id="user_001",
            wallet_id="wal_001",
            spending_limit_cents=50000,
            daily_limit_cents=200000,
            monthly_limit_cents=1000000,
        )
        assert card.spending_limit_cents == 50000
        assert card.daily_limit_cents == 200000
        assert card.monthly_limit_cents == 1000000

    def test_card_apple_pay_eligibility(self):
        """Test Apple Pay / Google Pay eligibility."""
        card = StrigaCard(
            card_id="card_003",
            user_id="user_001",
            wallet_id="wal_001",
            apple_pay_eligible=True,
            google_pay_eligible=True,
        )
        assert card.apple_pay_eligible is True
        assert card.google_pay_eligible is True
