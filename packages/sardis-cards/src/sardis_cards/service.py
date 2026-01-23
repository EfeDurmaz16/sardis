"""Card service for managing virtual cards."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional, Protocol

from .models import Card, CardTransaction, CardType
from .providers.base import CardProvider

logger = logging.getLogger(__name__)


class InsufficientBalanceError(Exception):
    """Raised when wallet balance is insufficient for card issuance."""

    def __init__(
        self,
        wallet_id: str,
        required_balance: Decimal,
        actual_balance: Decimal,
        currency: str = "USD",
    ):
        self.wallet_id = wallet_id
        self.required_balance = required_balance
        self.actual_balance = actual_balance
        self.currency = currency
        super().__init__(
            f"Insufficient balance in wallet {wallet_id}: "
            f"required {required_balance} {currency}, "
            f"available {actual_balance} {currency}"
        )


class WalletBalanceChecker(Protocol):
    """Protocol for checking wallet balances before card issuance."""

    async def get_balance(self, wallet_id: str, currency: str = "USD") -> Decimal:
        """
        Get the current balance of a wallet.

        Args:
            wallet_id: The wallet ID to check
            currency: The currency to check balance for

        Returns:
            The wallet balance as a Decimal
        """
        ...


class CardService:
    """
    High-level service for virtual card operations.

    Provides business logic on top of card providers.
    """

    def __init__(
        self,
        provider: CardProvider,
        balance_checker: Optional[WalletBalanceChecker] = None,
    ) -> None:
        """
        Initialize the card service.

        Args:
            provider: Card provider for card operations
            balance_checker: Optional wallet balance checker for pre-issuance validation
        """
        self._provider = provider
        self._balance_checker = balance_checker
    
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
        require_minimum_balance: Optional[Decimal] = None,
        balance_currency: str = "USD",
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
            require_minimum_balance: Minimum wallet balance required before issuing.
                If specified and wallet balance is below this amount, card issuance
                will be rejected. Requires balance_checker to be configured.
            balance_currency: Currency for balance check (default: USD)

        Returns:
            The created Card object

        Raises:
            InsufficientBalanceError: If wallet balance is below require_minimum_balance
            ValueError: If merchant-locked card without merchant ID, or balance check
                requested without balance_checker configured
        """
        # Validate merchant_locked cards have a merchant ID
        if card_type == CardType.MERCHANT_LOCKED and not locked_merchant_id:
            raise ValueError("Merchant-locked cards require a locked_merchant_id")

        # Check wallet balance if minimum balance is required
        if require_minimum_balance is not None:
            if self._balance_checker is None:
                raise ValueError(
                    "Cannot enforce minimum balance: balance_checker not configured. "
                    "Initialize CardService with a WalletBalanceChecker to enable balance checks."
                )

            logger.info(
                f"Checking wallet balance before card issuance: "
                f"wallet_id={wallet_id}, required={require_minimum_balance} {balance_currency}"
            )

            actual_balance = await self._balance_checker.get_balance(
                wallet_id, balance_currency
            )

            if actual_balance < require_minimum_balance:
                logger.warning(
                    f"Card issuance rejected due to insufficient balance: "
                    f"wallet_id={wallet_id}, required={require_minimum_balance}, "
                    f"actual={actual_balance} {balance_currency}"
                )
                raise InsufficientBalanceError(
                    wallet_id=wallet_id,
                    required_balance=require_minimum_balance,
                    actual_balance=actual_balance,
                    currency=balance_currency,
                )

            logger.info(
                f"Wallet balance check passed: wallet_id={wallet_id}, "
                f"balance={actual_balance} {balance_currency}"
            )

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
