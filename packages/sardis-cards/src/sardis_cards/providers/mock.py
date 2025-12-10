"""Mock card provider for testing and development."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import secrets
import uuid

from .base import CardProvider
from ..models import Card, CardTransaction, CardType, CardStatus, TransactionStatus, FundingSource


class MockProvider(CardProvider):
    """Mock provider that simulates card operations in memory."""
    
    def __init__(self) -> None:
        self._cards: dict[str, Card] = {}
        self._transactions: dict[str, CardTransaction] = {}
    
    @property
    def name(self) -> str:
        return "mock"
    
    def _generate_card_number_last4(self) -> str:
        return f"{secrets.randbelow(10000):04d}"
    
    def _generate_expiry(self) -> tuple[int, int]:
        now = datetime.now(timezone.utc)
        return now.month, now.year + 3
    
    async def create_card(
        self,
        wallet_id: str,
        card_type: CardType,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        locked_merchant_id: Optional[str] = None,
    ) -> Card:
        provider_card_id = f"mock_card_{uuid.uuid4().hex[:12]}"
        exp_month, exp_year = self._generate_expiry()
        
        card = Card(
            card_id=f"card_{uuid.uuid4().hex[:16]}",
            wallet_id=wallet_id,
            provider=self.name,
            provider_card_id=provider_card_id,
            card_number_last4=self._generate_card_number_last4(),
            expiry_month=exp_month,
            expiry_year=exp_year,
            card_type=card_type,
            status=CardStatus.PENDING,
            locked_merchant_id=locked_merchant_id,
            funding_source=FundingSource.STABLECOIN,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
        )
        
        self._cards[provider_card_id] = card
        return card
    
    async def get_card(self, provider_card_id: str) -> Optional[Card]:
        return self._cards.get(provider_card_id)
    
    async def activate_card(self, provider_card_id: str) -> Card:
        card = self._cards.get(provider_card_id)
        if not card:
            raise ValueError(f"Card not found: {provider_card_id}")
        
        card.status = CardStatus.ACTIVE
        card.activated_at = datetime.now(timezone.utc)
        return card
    
    async def freeze_card(self, provider_card_id: str) -> Card:
        card = self._cards.get(provider_card_id)
        if not card:
            raise ValueError(f"Card not found: {provider_card_id}")
        
        card.status = CardStatus.FROZEN
        card.frozen_at = datetime.now(timezone.utc)
        return card
    
    async def unfreeze_card(self, provider_card_id: str) -> Card:
        card = self._cards.get(provider_card_id)
        if not card:
            raise ValueError(f"Card not found: {provider_card_id}")
        
        card.status = CardStatus.ACTIVE
        card.frozen_at = None
        return card
    
    async def cancel_card(self, provider_card_id: str) -> Card:
        card = self._cards.get(provider_card_id)
        if not card:
            raise ValueError(f"Card not found: {provider_card_id}")
        
        card.status = CardStatus.CANCELLED
        card.cancelled_at = datetime.now(timezone.utc)
        return card
    
    async def update_limits(
        self,
        provider_card_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_daily: Optional[Decimal] = None,
        limit_monthly: Optional[Decimal] = None,
    ) -> Card:
        card = self._cards.get(provider_card_id)
        if not card:
            raise ValueError(f"Card not found: {provider_card_id}")
        
        if limit_per_tx is not None:
            card.limit_per_tx = limit_per_tx
        if limit_daily is not None:
            card.limit_daily = limit_daily
        if limit_monthly is not None:
            card.limit_monthly = limit_monthly
        
        return card
    
    async def fund_card(
        self,
        provider_card_id: str,
        amount: Decimal,
    ) -> Card:
        card = self._cards.get(provider_card_id)
        if not card:
            raise ValueError(f"Card not found: {provider_card_id}")
        
        card.funded_amount += amount
        return card
    
    async def list_transactions(
        self,
        provider_card_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CardTransaction]:
        card_txs = [
            tx for tx in self._transactions.values()
            if tx.card_id == provider_card_id
        ]
        card_txs.sort(key=lambda x: x.created_at, reverse=True)
        return card_txs[offset:offset + limit]
    
    async def get_transaction(
        self,
        provider_tx_id: str,
    ) -> Optional[CardTransaction]:
        return self._transactions.get(provider_tx_id)
    
    # Test helper methods
    
    async def simulate_transaction(
        self,
        provider_card_id: str,
        amount: Decimal,
        merchant_name: str = "Test Merchant",
        merchant_category: str = "5411",
        status: TransactionStatus = TransactionStatus.APPROVED,
    ) -> CardTransaction:
        """Simulate a card transaction for testing."""
        card = self._cards.get(provider_card_id)
        if not card:
            raise ValueError(f"Card not found: {provider_card_id}")
        
        provider_tx_id = f"mock_tx_{uuid.uuid4().hex[:12]}"
        
        tx = CardTransaction(
            transaction_id=f"ctx_{uuid.uuid4().hex[:16]}",
            card_id=provider_card_id,
            provider_tx_id=provider_tx_id,
            amount=amount,
            currency="USD",
            merchant_name=merchant_name,
            merchant_category=merchant_category,
            status=status,
        )
        
        self._transactions[provider_tx_id] = tx
        
        # Update card spending if approved
        if status == TransactionStatus.APPROVED:
            card.spent_today += amount
            card.spent_this_month += amount
            card.total_spent += amount
            card.funded_amount -= amount
            card.last_used_at = datetime.now(timezone.utc)
        
        return tx
