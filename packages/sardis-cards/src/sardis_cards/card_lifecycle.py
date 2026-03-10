"""Card lifecycle manager — expiration tracking, auto-renewal, replacement linking."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CardReplacement:
    """Record of a card replacement."""
    old_card_id: str
    new_card_id: str
    reason: str  # expired, compromised, upgrade
    created_at: datetime


class CardLifecycleManager:
    """
    Manages card lifecycle: expiration tracking, auto-renewal, replacement linking.

    Checks for cards expiring within a configurable window and triggers
    replacement flows.
    """

    def __init__(self, expiry_warning_days: int = 30):
        self._expiry_warning_days = expiry_warning_days
        self._replacements: list[CardReplacement] = []

    def check_expiration(
        self,
        expiry_month: int,
        expiry_year: int,
    ) -> dict:
        """
        Check card expiration status.

        Args:
            expiry_month: Card expiry month (1-12)
            expiry_year: Card expiry year (4-digit)

        Returns:
            Dict with is_expired, is_expiring_soon, days_until_expiry
        """
        now = datetime.now(UTC)

        # Card expires at end of expiry month
        if expiry_month == 12:
            expiry_date = datetime(expiry_year + 1, 1, 1, tzinfo=UTC)
        else:
            expiry_date = datetime(expiry_year, expiry_month + 1, 1, tzinfo=UTC)

        days_until = (expiry_date - now).days
        is_expired = days_until <= 0
        is_expiring_soon = 0 < days_until <= self._expiry_warning_days

        return {
            "is_expired": is_expired,
            "is_expiring_soon": is_expiring_soon,
            "days_until_expiry": max(0, days_until),
            "expiry_date": expiry_date.isoformat(),
        }

    def find_expiring_cards(
        self,
        cards: list[dict],
    ) -> list[dict]:
        """
        Find cards expiring within the warning window.

        Args:
            cards: List of card dicts with expiry_month, expiry_year

        Returns:
            List of cards that are expiring soon
        """
        expiring = []
        for card in cards:
            status = self.check_expiration(
                card.get("expiry_month", 0),
                card.get("expiry_year", 0),
            )
            if status["is_expiring_soon"] or status["is_expired"]:
                card["expiration_status"] = status
                expiring.append(card)
        return expiring

    def record_replacement(
        self,
        old_card_id: str,
        new_card_id: str,
        reason: str = "expired",
    ) -> CardReplacement:
        """Record a card replacement."""
        replacement = CardReplacement(
            old_card_id=old_card_id,
            new_card_id=new_card_id,
            reason=reason,
            created_at=datetime.now(UTC),
        )
        self._replacements.append(replacement)
        logger.info(f"Card replacement: {old_card_id} -> {new_card_id} ({reason})")
        return replacement

    def get_replacement_chain(self, card_id: str) -> list[str]:
        """Get the chain of replacements for a card."""
        chain = [card_id]
        current = card_id
        for replacement in self._replacements:
            if replacement.old_card_id == current:
                chain.append(replacement.new_card_id)
                current = replacement.new_card_id
        return chain

    def get_current_card(self, original_card_id: str) -> str:
        """Get the current (most recent) card in a replacement chain."""
        chain = self.get_replacement_chain(original_card_id)
        return chain[-1]
