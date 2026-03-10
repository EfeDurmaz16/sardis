"""Card selection engine for multi-currency card routing."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CardRoutingStrategy(str, Enum):
    """Card selection strategies."""
    MERCHANT_LOCKED_FIRST = "merchant_locked_first"
    CURRENCY_MATCH = "currency_match"
    LOWEST_SPEND = "lowest_spend"
    USER_PREFERRED = "user_preferred"


@dataclass
class CardSelectionResult:
    """Result of card selection."""
    card_id: str
    provider: str
    currency: str
    strategy_used: CardRoutingStrategy
    reason: str


class CardRouter:
    """
    Card selection engine for multi-currency, multi-provider setups.

    Strategies (in priority order):
    1. MERCHANT_LOCKED_FIRST — Use merchant-locked card if available
    2. CURRENCY_MATCH — Match card currency to merchant currency
    3. USER_PREFERRED — Use preferred card if set
    4. LOWEST_SPEND — Use card with lowest spend this period
    """

    def __init__(self):
        self._merchant_preferences: dict[str, dict[str, str]] = {}  # wallet -> {pattern: card_id}

    def set_merchant_preference(
        self,
        wallet_id: str,
        merchant_pattern: str,
        preferred_card_id: str,
    ) -> None:
        """Set a preferred card for a merchant pattern."""
        if wallet_id not in self._merchant_preferences:
            self._merchant_preferences[wallet_id] = {}
        self._merchant_preferences[wallet_id][merchant_pattern] = preferred_card_id

    def select_card_for_merchant(
        self,
        wallet_id: str,
        merchant: str,
        mcc: str,
        currency: str,
        available_cards: list[dict[str, Any]],
    ) -> CardSelectionResult | None:
        """
        Select the best card for a merchant payment.

        Args:
            wallet_id: Agent wallet ID
            merchant: Merchant name/descriptor
            mcc: Merchant category code
            currency: Transaction currency
            available_cards: List of card dicts with id, provider, currency, status, etc.

        Returns:
            CardSelectionResult or None if no suitable card found
        """
        if not available_cards:
            return None

        active_cards = [c for c in available_cards if c.get("status") == "active"]
        if not active_cards:
            return None

        # Strategy 1: Merchant-locked card
        for card in active_cards:
            if card.get("locked_merchant_id") and merchant.upper() in card["locked_merchant_id"].upper():
                return CardSelectionResult(
                    card_id=card["card_id"],
                    provider=card.get("provider", ""),
                    currency=card.get("currency", "USD"),
                    strategy_used=CardRoutingStrategy.MERCHANT_LOCKED_FIRST,
                    reason=f"Merchant-locked card for {merchant}",
                )

        # Strategy 2: Merchant preference
        prefs = self._merchant_preferences.get(wallet_id, {})
        for pattern, card_id in prefs.items():
            if pattern.upper() in merchant.upper():
                matching = next((c for c in active_cards if c["card_id"] == card_id), None)
                if matching:
                    return CardSelectionResult(
                        card_id=card_id,
                        provider=matching.get("provider", ""),
                        currency=matching.get("currency", "USD"),
                        strategy_used=CardRoutingStrategy.USER_PREFERRED,
                        reason=f"User preferred card for pattern {pattern}",
                    )

        # Strategy 3: Currency match
        currency_cards = [c for c in active_cards if c.get("currency", "USD") == currency]
        if currency_cards:
            # Pick the one with lowest spend
            best = min(currency_cards, key=lambda c: c.get("spent_this_month", 0))
            return CardSelectionResult(
                card_id=best["card_id"],
                provider=best.get("provider", ""),
                currency=best.get("currency", "USD"),
                strategy_used=CardRoutingStrategy.CURRENCY_MATCH,
                reason=f"Currency match ({currency}), lowest spend",
            )

        # Strategy 4: Lowest spend across all cards
        best = min(active_cards, key=lambda c: c.get("spent_this_month", 0))
        return CardSelectionResult(
            card_id=best["card_id"],
            provider=best.get("provider", ""),
            currency=best.get("currency", "USD"),
            strategy_used=CardRoutingStrategy.LOWEST_SPEND,
            reason="Lowest spend card (cross-currency)",
        )
