"""In-memory ledger implementation for MVP."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import asyncio

from sardis_core.config import settings
from sardis_core.models import Transaction, TransactionStatus, Wallet
from sardis_core.models.agent import Agent
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
        self._lock = asyncio.Lock()
        
        # Create system wallet
        system_wallet = Wallet(
            wallet_id=settings.system_wallet_id,
            agent_id="system",
            balance=Decimal("1000000000.00"),  # Initial treasury
            is_active=True
        )
        self._wallets[system_wallet.wallet_id] = system_wallet
        
        # Create fee pool wallet
        fee_wallet = Wallet(
            wallet_id=settings.fee_pool_wallet_id,
            agent_id="system_fees",
            balance=Decimal("0.00"),
            is_active=True
        )
        self._wallets[fee_wallet.wallet_id] = fee_wallet
        
        # Create settlement wallet
        settlement_wallet = Wallet(
            wallet_id=settings.settlement_wallet_id,
            agent_id="system_settlement",
            balance=Decimal("0.00"),
            is_active=True
        )
        self._wallets[settlement_wallet.wallet_id] = settlement_wallet
    
    async def create_agent(self, agent: "Agent") -> "Agent":
        """Register a new agent on the ledger."""
        # In memory ledger doesn't track agents separately in this implementation,
        # but we implement the interface for consistency.
        return agent

    async def create_wallet(self, wallet: Wallet) -> Wallet:
        """Register a new wallet on the ledger."""
        async with self._lock:
            if wallet.wallet_id in self._wallets:
                raise ValueError(f"Wallet {wallet.wallet_id} already exists")
            
            self._wallets[wallet.wallet_id] = wallet
            return wallet
    
    async def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Retrieve a wallet by ID."""
        async with self._lock:
            return self._wallets.get(wallet_id)
    
    async def update_wallet(self, wallet: Wallet) -> Wallet:
        """Update a wallet's state."""
        async with self._lock:
            if wallet.wallet_id not in self._wallets:
                raise ValueError(f"Wallet {wallet.wallet_id} not found")
            
            wallet.updated_at = datetime.utcnow()
            self._wallets[wallet.wallet_id] = wallet
            return wallet
    
    async def transfer(
        self,
        from_wallet_id: str,
        to_wallet_id: str,
        amount: Decimal,
        fee: Decimal,
        currency: str,
        purpose: Optional[str] = None
    ) -> Transaction:
        """Execute a transfer between wallets."""
        async with self._lock:
            # 1. Validate
            sender = self._wallets.get(from_wallet_id)
            recipient = self._wallets.get(to_wallet_id)
            
            if not sender:
                raise ValueError(f"Sender wallet {from_wallet_id} not found")
            if not recipient:
                raise ValueError(f"Recipient wallet {to_wallet_id} not found")
            
            total_deduction = amount + fee
            
            # Check balance
            sender_balance = sender.get_balance(currency)
            if sender_balance < total_deduction:
                raise ValueError(f"Insufficient balance: have {sender_balance}, need {total_deduction}")
            
            # 2. Execute Transfer
            # Deduct from sender
            from sardis_core.models.wallet import TokenType
            token_type = TokenType(currency)
            sender.set_token_balance(token_type, sender_balance - total_deduction)
            sender.spent_total += total_deduction
            sender.updated_at = datetime.utcnow()
            
            # Credit to recipient
            recipient_balance = recipient.get_balance(currency)
            recipient.set_token_balance(token_type, recipient_balance + amount)
            recipient.updated_at = datetime.utcnow()
            
            # Credit fee to system (if not system itself)
            if fee > 0 and to_wallet_id != settings.system_wallet_id:
                system = self._wallets.get(settings.system_wallet_id)
                if system:
                    system_balance = system.get_balance(currency)
                    system.set_token_balance(token_type, system_balance + fee)
            
            # 3. Record Transaction
            tx = Transaction(
                from_wallet=from_wallet_id,
                to_wallet=to_wallet_id,
                amount=amount,
                fee=fee,
                currency=currency,
                purpose=purpose,
                status=TransactionStatus.COMPLETED,
                completed_at=datetime.utcnow()
            )
            
            self._transactions[tx.tx_id] = tx
            
            return tx
            
    async def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """Retrieve a transaction by ID."""
        async with self._lock:
            return self._transactions.get(tx_id)
    
    async def list_transactions(
        self,
        wallet_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list[Transaction]:
        """List transactions for a wallet."""
        async with self._lock:
            # Filter transactions involving this wallet
            wallet_txs = [
                tx for tx in self._transactions.values()
                if tx.from_wallet == wallet_id or tx.to_wallet == wallet_id
            ]
            
            # Sort by date desc
            wallet_txs.sort(key=lambda x: x.created_at, reverse=True)
            
            # Apply pagination
            return wallet_txs[offset:offset + limit]
    
    async def get_balance(self, wallet_id: str, currency: str = settings.default_currency) -> Decimal:
        """Get the current balance of a wallet for a specific currency."""
        async with self._lock:
            wallet = self._wallets.get(wallet_id)
            if not wallet:
                raise ValueError(f"Wallet {wallet_id} not found")
            return wallet.get_balance(currency)
    
    async def fund_wallet(self, wallet_id: str, amount: Decimal) -> Transaction:
        """
        Fund a wallet from the system treasury.
        
        Used for testing and initial setup. In production, this would be
        replaced by actual fiat/crypto on-ramps.
        """
        # No lock needed here as it calls transfer which locks
        return await self.transfer(
            from_wallet_id=settings.system_wallet_id,
            to_wallet_id=wallet_id,
            amount=amount,
            fee=Decimal("0.00"),  # No fee for funding
            currency=settings.default_currency,
            purpose="Initial funding"
        )

