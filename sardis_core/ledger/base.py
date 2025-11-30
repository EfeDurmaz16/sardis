"""Abstract base class for ledger implementations."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

from sardis_core.models import Transaction, Wallet


class BaseLedger(ABC):
    """
    Abstract base class for ledger implementations.
    
    This interface allows swapping between different backends:
    - InMemoryLedger for MVP/testing
    - BlockchainLedger for real chain integration (future)
    """
    
    @abstractmethod
    def create_wallet(self, wallet: Wallet) -> Wallet:
        """
        Register a new wallet on the ledger.
        
        Args:
            wallet: The wallet to create
            
        Returns:
            The created wallet with any ledger-assigned fields
        """
        pass
    
    @abstractmethod
    def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """
        Retrieve a wallet by ID.
        
        Args:
            wallet_id: The wallet identifier
            
        Returns:
            The wallet if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_wallet(self, wallet: Wallet) -> Wallet:
        """
        Update a wallet's state.
        
        Args:
            wallet: The wallet with updated values
            
        Returns:
            The updated wallet
        """
        pass
    
    @abstractmethod
    def transfer(
        self,
        from_wallet_id: str,
        to_wallet_id: str,
        amount: Decimal,
        fee: Decimal,
        currency: str,
        purpose: Optional[str] = None
    ) -> Transaction:
        """
        Execute a transfer between wallets.
        
        This is the core operation that:
        1. Validates sufficient balance
        2. Deducts amount + fee from source
        3. Credits amount to destination
        4. Credits fee to fee pool
        5. Records the transaction
        
        Args:
            from_wallet_id: Source wallet
            to_wallet_id: Destination wallet
            amount: Transfer amount
            fee: Transaction fee
            currency: Currency code (e.g., "USDC")
            purpose: Optional memo/purpose
            
        Returns:
            The completed transaction record
            
        Raises:
            ValueError: If transfer cannot be completed
        """
        pass
    
    @abstractmethod
    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """
        Retrieve a transaction by ID.
        
        Args:
            tx_id: The transaction identifier
            
        Returns:
            The transaction if found, None otherwise
        """
        pass
    
    @abstractmethod
    def list_transactions(
        self,
        wallet_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list[Transaction]:
        """
        List transactions for a wallet.
        
        Args:
            wallet_id: The wallet to list transactions for
            limit: Maximum number to return
            offset: Number to skip for pagination
            
        Returns:
            List of transactions involving this wallet
        """
        pass
    
    @abstractmethod
    def get_balance(self, wallet_id: str) -> Decimal:
        """
        Get the current balance of a wallet.
        
        Args:
            wallet_id: The wallet identifier
            
        Returns:
            Current balance
            
        Raises:
            ValueError: If wallet not found
        """
        pass

