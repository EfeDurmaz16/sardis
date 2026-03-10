"""Tests for card lifecycle manager."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sardis_cards.card_lifecycle import CardLifecycleManager, CardReplacement


class TestCardLifecycleManager:
    """Tests for CardLifecycleManager."""

    def test_expired_card(self):
        mgr = CardLifecycleManager(expiry_warning_days=30)
        result = mgr.check_expiration(1, 2020)
        assert result["is_expired"] is True
        assert result["is_expiring_soon"] is False
        assert result["days_until_expiry"] == 0

    def test_far_future_card(self):
        mgr = CardLifecycleManager(expiry_warning_days=30)
        result = mgr.check_expiration(12, 2099)
        assert result["is_expired"] is False
        assert result["is_expiring_soon"] is False
        assert result["days_until_expiry"] > 30

    def test_find_expiring_cards(self):
        mgr = CardLifecycleManager(expiry_warning_days=30)
        cards = [
            {"card_id": "c1", "expiry_month": 1, "expiry_year": 2020},
            {"card_id": "c2", "expiry_month": 12, "expiry_year": 2099},
        ]
        expiring = mgr.find_expiring_cards(cards)
        assert len(expiring) == 1
        assert expiring[0]["card_id"] == "c1"

    def test_record_replacement(self):
        mgr = CardLifecycleManager()
        replacement = mgr.record_replacement("old_1", "new_1", "expired")
        assert isinstance(replacement, CardReplacement)
        assert replacement.old_card_id == "old_1"
        assert replacement.new_card_id == "new_1"
        assert replacement.reason == "expired"

    def test_replacement_chain(self):
        mgr = CardLifecycleManager()
        mgr.record_replacement("c1", "c2", "expired")
        mgr.record_replacement("c2", "c3", "expired")
        chain = mgr.get_replacement_chain("c1")
        assert chain == ["c1", "c2", "c3"]

    def test_get_current_card(self):
        mgr = CardLifecycleManager()
        mgr.record_replacement("c1", "c2", "expired")
        mgr.record_replacement("c2", "c3", "upgrade")
        assert mgr.get_current_card("c1") == "c3"

    def test_get_current_card_no_replacements(self):
        mgr = CardLifecycleManager()
        assert mgr.get_current_card("c1") == "c1"
