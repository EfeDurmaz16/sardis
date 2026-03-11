"""Tests for card routing engine."""
from __future__ import annotations

import pytest
from sardis_cards.card_routing import CardRouter, CardRoutingStrategy, CardSelectionResult


class TestCardRouter:
    """Tests for CardRouter selection logic."""

    def _make_card(self, card_id, currency="USD", provider="stripe", status="active", **kw):
        return {"card_id": card_id, "currency": currency, "provider": provider, "status": status, **kw}

    def test_returns_none_for_empty_cards(self):
        router = CardRouter()
        result = router.select_card_for_merchant("wal_1", "Amazon", "5411", "USD", [])
        assert result is None

    def test_returns_none_for_no_active_cards(self):
        router = CardRouter()
        cards = [self._make_card("c1", status="closed")]
        result = router.select_card_for_merchant("wal_1", "Amazon", "5411", "USD", cards)
        assert result is None

    def test_merchant_locked_card_takes_priority(self):
        router = CardRouter()
        cards = [
            self._make_card("c1"),
            self._make_card("c2", locked_merchant_id="AMAZON"),
        ]
        result = router.select_card_for_merchant("wal_1", "Amazon", "5411", "USD", cards)
        assert result is not None
        assert result.card_id == "c2"
        assert result.strategy_used == CardRoutingStrategy.MERCHANT_LOCKED_FIRST

    def test_user_preference_overrides_currency(self):
        router = CardRouter()
        router.set_merchant_preference("wal_1", "Netflix", "c_eur")
        cards = [
            self._make_card("c_usd", currency="USD"),
            self._make_card("c_eur", currency="EUR"),
        ]
        result = router.select_card_for_merchant("wal_1", "Netflix EU", "5815", "USD", cards)
        assert result is not None
        assert result.card_id == "c_eur"
        assert result.strategy_used == CardRoutingStrategy.USER_PREFERRED

    def test_currency_match_selects_matching_card(self):
        router = CardRouter()
        cards = [
            self._make_card("c_usd", currency="USD"),
            self._make_card("c_eur", currency="EUR"),
        ]
        result = router.select_card_for_merchant("wal_1", "Zalando", "5699", "EUR", cards)
        assert result is not None
        assert result.card_id == "c_eur"
        assert result.strategy_used == CardRoutingStrategy.CURRENCY_MATCH

    def test_lowest_spend_fallback(self):
        router = CardRouter()
        cards = [
            self._make_card("c1", currency="USD", spent_this_month=500),
            self._make_card("c2", currency="USD", spent_this_month=100),
        ]
        result = router.select_card_for_merchant("wal_1", "Merchant", "5411", "EUR", cards)
        assert result is not None
        assert result.card_id == "c2"
        assert result.strategy_used == CardRoutingStrategy.LOWEST_SPEND

    def test_currency_match_picks_lowest_spend(self):
        router = CardRouter()
        cards = [
            self._make_card("c1", currency="EUR", spent_this_month=300),
            self._make_card("c2", currency="EUR", spent_this_month=50),
        ]
        result = router.select_card_for_merchant("wal_1", "Merchant", "5411", "EUR", cards)
        assert result is not None
        assert result.card_id == "c2"
        assert result.strategy_used == CardRoutingStrategy.CURRENCY_MATCH

    def test_selection_result_fields(self):
        result = CardSelectionResult(
            card_id="c1",
            provider="stripe",
            currency="USD",
            strategy_used=CardRoutingStrategy.CURRENCY_MATCH,
            reason="test",
        )
        assert result.card_id == "c1"
        assert result.provider == "stripe"
        assert result.currency == "USD"
