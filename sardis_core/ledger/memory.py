"""In-memory ledger implementation for MVP."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import threading

from sardis_core.config import settings
from sardis_core.models import Transaction, TransactionStatus, Wallet
from .base import BaseLedger


class InMemoryLedger(BaseLedger):
    """
    In-memory implementation of the ledger.
    
    This provides a simple, thread-safe ledger for the MVP.
    Data is lost on restart, but the interface is designed
    to be swappable with a real blockchain backend.
    """
    
    def __init__(self):
        self._wallets: dict[str, Wallet] = {}
        self._transactions: dict[str, Transaction] = {}
        self._lock = threading.RLock()
        
        # Initialize system wallets
        self._init_system_wallets()
    
    def _init_system_wallets(self) -> None:
        """Create system wallets for fees and treasury."""
        # Fee pool wallet - collects transaction fees
        fee_pool = Wallet(
            wallet_id=settings.fee_pool_wallet_id,
            agent_id="system",
            balance=Decimal("0.00"),
            currency=settings.default_currency,
            limit_per_tx=Decimal("999999999.00"),
            limit_total=Decimal("999999999.00"),
        )
        self._wallets[fee_pool.wallet_id] = fee_pool
        
        # System wallet - for minting/burning (treasury)
        system_wallet = Wallet(
            wallet_id=settings.system_wallet_id,
            agent_id="system",
            balance=Decimal("999999999.00"),  # Unlimited for minting
            currency=settings.default_currency,
            limit_per_tx=Decimal("999999999.00"),
            limit_total=Decimal("999999999.00"),
        )
        self._wallets[system_wallet.wallet_id] = system_wallet
    
    def create_wallet(self, wallet: Wallet) -> Wallet:
        """Register a new wallet on the ledger."""
        with self._lock:
            if wallet.wallet_id in self._wallets:
                raise ValueError(f"Wallet {wallet.wallet_id} already exists")
            
            self._wallets[wallet.wallet_id] = wallet
            return wallet
    
    def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Retrieve a wallet by ID."""
        with self._lock:
            return self._wallets.get(wallet_id)
    
    def update_wallet(self, wallet: Wallet) -> Wallet:
        """Update a wallet's state."""
        with self._lock:
            if wallet.wallet_id not in self._wallets:
                raise ValueError(f"Wallet {wallet.wallet_id} not found")
            
            wallet.updated_at = datetime.utcnow()
            self._wallets[wallet.wallet_id] = wallet
            return wallet
    
    def transfer(
        self,
        from_wallet_id: str,
        to_wallet_id: str,
        amount: Decimal,
        fee: Decimal,
        currency: str,
        purpose: Optional[str] = None
    ) -> Transaction:
        """Execute a transfer between wallets."""
        with self._lock:
            # Get wallets
            from_wallet = self._wallets.get(from_wallet_id)
            to_wallet = self._wallets.get(to_wallet_id)
            fee_pool = self._wallets.get(settings.fee_pool_wallet_id)
            
            if not from_wallet:
                raise ValueError(f"Source wallet {from_wallet_id} not found")
            if not to_wallet:
                raise ValueError(f"Destination wallet {to_wallet_id} not found")
            if not fee_pool:
                raise ValueError("Fee pool wallet not initialized")
            
            # Create transaction record
            tx = Transaction(
                from_wallet=from_wallet_id,
                to_wallet=to_wallet_id,
                amount=amount,
                fee=fee,
                currency=currency,
                purpose=purpose,
                status=TransactionStatus.PENDING
            )
            
            # Validate transfer
            total_cost = amount + fee
            if from_wallet.balance < total_cost:
                tx.mark_failed(f"Insufficient balance: have {from_wallet.balance}, need {total_cost}")
                self._transactions[tx.tx_id] = tx
                raise ValueError(tx.error_message)
            
            # Execute the transfer atomically
            try:
                # Deduct from source
                from_wallet.balance -= total_cost
                from_wallet.spent_total += amount
                from_wallet.updated_at = datetime.utcnow()
                
                # Credit to destination
                to_wallet.balance += amount
                to_wallet.updated_at = datetime.utcnow()
                
                # Credit fee to fee pool
                if fee > Decimal("0"):
                    fee_pool.balance += fee
                    fee_pool.updated_at = datetime.utcnow()
                
                # Mark transaction complete
                tx.mark_completed()
                
                # Store updated state
                self._wallets[from_wallet_id] = from_wallet
                self._wallets[to_wallet_id] = to_wallet
                self._wallets[settings.fee_pool_wallet_id] = fee_pool
                self._transactions[tx.tx_id] = tx
                
                return tx
                
            except Exception as e:
                tx.mark_failed(str(e))
                self._transactions[tx.tx_id] = tx
                raise
    
    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """Retrieve a transaction by ID."""
        with self._lock:
            return self._transactions.get(tx_id)
    
    def list_transactions(
        self,
        wallet_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list[Transaction]:
        """List transactions for a wallet."""
        with self._lock:
            # Get all transactions involving this wallet
            wallet_txs = [
                tx for tx in self._transactions.values()
                if tx.from_wallet == wallet_id or tx.to_wallet == wallet_id
            ]
            
            # Sort by created_at descending
            wallet_txs.sort(key=lambda x: x.created_at, reverse=True)
            
            # Apply pagination
            return wallet_txs[offset:offset + limit]
    
    def get_balance(self, wallet_id: str) -> Decimal:
        """Get the current balance of a wallet."""
        with self._lock:
            wallet = self._wallets.get(wallet_id)
            if not wallet:
                raise ValueError(f"Wallet {wallet_id} not found")
            return wallet.balance
    
    def fund_wallet(self, wallet_id: str, amount: Decimal) -> Transaction:
        """
        Fund a wallet from the system treasury.
        
        This is a convenience method for the MVP to add
        initial balance to agent wallets.
        """
        return self.transfer(
            from_wallet_id=settings.system_wallet_id,
            to_wallet_id=wallet_id,
            amount=amount,
            fee=Decimal("0.00"),  # No fee for funding
            currency=settings.default_currency,
            purpose="Initial funding"
        )

