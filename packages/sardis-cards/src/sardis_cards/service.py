"""Card service for managing virtual cards."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from .models import Card, CardTransaction, CardType
from .providers.base import CardProvider


class CardService:
    """
    High-level service for virtual card operations.
    
    Provides business logic on top of card providers.
    """
    
    def __init__(self, provider: CardProvider) -> None:
        self._provider = provider
    
    @property
    def provider_name(self) -> str:
        """Get the name of the current provider."""
        return self._provider.name
    
    async def issue_card(
        self,
        wallet_id: str,
        card_type: CardType = CardType.MULTI_USE,
        limit_per_tx: Decimal = Decimal("500.00"),
        limit_daily: Decimal = Decimal("2000.00"),
        limit_monthly: Decimal = Decimal("10000.00"),
        locked_merchant_id: Optional[str] = None,
        auto_activate: bool = True,
    ) -> Card:
        """
        Issue a new virtual card for a wallet.
        
        Args:
            wallet_id: The wallet ID to link the card to
            card_type: Type of card (single_use, multi_use, merchant_locked)
            limit_per_tx: Maximum amount per transaction
            limit_daily: Maximum daily spend
            limit_monthly: Maximum monthly spend
            locked_merchant_id: Merchant ID for merchant-locked cards
            auto_activate: Automatically activate the card after creation
            
        Returns:
            The created Card object
        """
        # Validate merchant_locked cards have a merchant ID
        if card_type == CardType.MERCHANT_LOCKED and not locked_merchant_id:
            raise ValueError("Merchant-locked cards require a locked_merchant_id")
        
        card = await self._provider.create_card(
            wallet_id=wallet_id,
            card_type=card_type,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
            locked_merchant_id=locked_merchant_id,
        )
        
        if auto_activate:
            card = await self._provider.activate_card(card.provider_card_id)
        
        return card
    
    async def get_card(self, card_id: str) -> Optional[Card]:
        """
        Get card details.
        
        Args:
            card_id: The card ID (provider_card_id)
            
        Returns:
            Card object if found, None otherwise
        """
        return await self._provider.get_card(card_id)
    
    async def fund_card(
        self,
        card_id: str,
        amount: Decimal,
        source: str = "stablecoin",
    ) -> Card:
        """
        Add funds to a card.
        
        Args:
            card_id: The card ID (provider_card_id)
            amount: Amount to add
            source: Funding source (stablecoin, bank_transfer, crypto)
            
        Returns:
            Updated Card object
        """
        if amount <= 0:
            raise ValueError("Funding amount must be positive")
        
        card = await self._provider.get_card(card_id)
        if not card:
            raise ValueError(f"Card not found: {card_id}")
        
        return await self._provider.fund_card(card_id, amount)
    
    async def freeze_card(self, card_id: str) -> Card:
        """
        Freeze a card to prevent transactions.
        
        Args:
            card_id: The card ID (provider_card_id)
            
        Returns:
            Updated Card object
        """
        return await self._provider.freeze_card(card_id)
    
    async def unfreeze_card(self, card_id: str) -> Card:
        """
        Unfreeze a previously frozen card.
        
        Args:
            card_id: The card ID (provider_card_id)
            
        Returns:
            Updated Card object
        """
        return await self._provider.unfreeze_card(card_id)
    
    async def cancel_card(self, card_id: str) -> Card:
        """
        Cancel a card permanently.
        
        Args:
            card_id: The card ID (provider_card_id)
            
        Returns:
            Updated Card object
        """
        return await self._provider.cancel_card(card_id)
    
    async def update_limits(
        self,
        card_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_daily: Optional[Decimal] = None,
        limit_monthly: Optional[Decimal] = None,
    ) -> Card:
        """
        Update card spending limits.
        
        Args:
            card_id: The card ID (provider_card_id)
            limit_per_tx: New per-transaction limit
            limit_daily: New daily limit
            limit_monthly: New monthly limit
            
        Returns:
            Updated Card object
        """
        return await self._provider.update_limits(
            card_id,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
        )
    
    async def list_transactions(
        self,
        card_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CardTransaction]:
        """
        List transactions for a card.
        
        Args:
            card_id: The card ID (provider_card_id)
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip
            
        Returns:
            List of CardTransaction objects
        """
        return await self._provider.list_transactions(card_id, limit, offset)
    
    async def get_transaction(self, transaction_id: str) -> Optional[CardTransaction]:
        """
        Get a specific transaction.
        
        Args:
            transaction_id: The transaction ID (provider_tx_id)
            
        Returns:
            CardTransaction object if found, None otherwise
        """
        return await self._provider.get_transaction(transaction_id)
