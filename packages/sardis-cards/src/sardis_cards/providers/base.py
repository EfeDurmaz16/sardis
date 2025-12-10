"""Abstract base class for card providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

from ..models import Card, CardTransaction, CardType


class CardProvider(ABC):
    """Abstract base class for virtual card providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'lithic', 'marqeta', 'mock')."""
        ...
    
    @abstractmethod
    async def create_card(
        self,
        wallet_id: str,
        card_type: CardType,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        locked_merchant_id: Optional[str] = None,
    ) -> Card:
        """
        Create a new virtual card.
        
        Args:
            wallet_id: The wallet ID to link the card to
            card_type: Type of card (single_use, multi_use, merchant_locked)
            limit_per_tx: Maximum amount per transaction
            limit_daily: Maximum daily spend
            limit_monthly: Maximum monthly spend
            locked_merchant_id: Merchant ID for merchant-locked cards
            
        Returns:
            The created Card object
        """
        ...
    
    @abstractmethod
    async def get_card(self, provider_card_id: str) -> Optional[Card]:
        """
        Get card details from provider.
        
        Args:
            provider_card_id: The provider's card ID
            
        Returns:
            Card object if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def activate_card(self, provider_card_id: str) -> Card:
        """
        Activate a pending card.
        
        Args:
            provider_card_id: The provider's card ID
            
        Returns:
            Updated Card object
        """
        ...
    
    @abstractmethod
    async def freeze_card(self, provider_card_id: str) -> Card:
        """
        Freeze a card to prevent transactions.
        
        Args:
            provider_card_id: The provider's card ID
            
        Returns:
            Updated Card object
        """
        ...
    
    @abstractmethod
    async def unfreeze_card(self, provider_card_id: str) -> Card:
        """
        Unfreeze a previously frozen card.
        
        Args:
            provider_card_id: The provider's card ID
            
        Returns:
            Updated Card object
        """
        ...
    
    @abstractmethod
    async def cancel_card(self, provider_card_id: str) -> Card:
        """
        Cancel a card permanently.
        
        Args:
            provider_card_id: The provider's card ID
            
        Returns:
            Updated Card object
        """
        ...
    
    @abstractmethod
    async def update_limits(
        self,
        provider_card_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_daily: Optional[Decimal] = None,
        limit_monthly: Optional[Decimal] = None,
    ) -> Card:
        """
        Update card spending limits.
        
        Args:
            provider_card_id: The provider's card ID
            limit_per_tx: New per-transaction limit
            limit_daily: New daily limit
            limit_monthly: New monthly limit
            
        Returns:
            Updated Card object
        """
        ...
    
    @abstractmethod
    async def fund_card(
        self,
        provider_card_id: str,
        amount: Decimal,
    ) -> Card:
        """
        Add funds to a card.
        
        Args:
            provider_card_id: The provider's card ID
            amount: Amount to add
            
        Returns:
            Updated Card object
        """
        ...
    
    @abstractmethod
    async def list_transactions(
        self,
        provider_card_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CardTransaction]:
        """
        List transactions for a card.
        
        Args:
            provider_card_id: The provider's card ID
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip
            
        Returns:
            List of CardTransaction objects
        """
        ...
    
    @abstractmethod
    async def get_transaction(
        self,
        provider_tx_id: str,
    ) -> Optional[CardTransaction]:
        """
        Get a specific transaction.
        
        Args:
            provider_tx_id: The provider's transaction ID
            
        Returns:
            CardTransaction object if found, None otherwise
        """
        ...
