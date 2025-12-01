from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import json

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sardis_core.models import Wallet, Transaction, TransactionStatus, TokenType
from sardis_core.models.agent import Agent
from sardis_core.database.models import DBWallet, DBTransaction, DBAgent
from sardis_core.database.session import async_session_factory
from sardis_core.config import settings
from .base import BaseLedger


class PostgresLedger(BaseLedger):
    """
    PostgreSQL implementation of the ledger.
    Uses SQLAlchemy for persistence.
    """
    
    def __init__(self):
        # We don't hold state in memory, but we need to ensure system wallets exist
        pass

    async def _get_session(self) -> AsyncSession:
        """Get a new async session."""
        return async_session_factory()

    async def create_agent(self, agent: "Agent") -> "Agent":
        """Register a new agent on the ledger."""
        async with async_session_factory() as session:
            async with session.begin():
                # Check if exists
                stmt = select(DBAgent).where(DBAgent.agent_id == agent.agent_id)
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    # If exists, just return (idempotent for merchants)
                    return agent
                
                # Create DB model
                db_agent = DBAgent(
                    agent_id=agent.agent_id,
                    name=agent.name,
                    owner_id=agent.owner_id,
                    description=agent.description,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                session.add(db_agent)
            
            return agent

    async def create_wallet(self, wallet: Wallet) -> Wallet:
        """Register a new wallet on the ledger."""
        async with async_session_factory() as session:
            async with session.begin():
                # Check if exists
                stmt = select(DBWallet).where(DBWallet.wallet_id == wallet.wallet_id)
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    raise ValueError(f"Wallet {wallet.wallet_id} already exists")
                
                # Create DB model
                # Convert virtual_card to dict with JSON-serializable values
                virtual_card_data = None
                if wallet.virtual_card:
                    vc_dict = wallet.virtual_card.model_dump()
                    # Convert any Decimal and datetime values to strings
                    for key, value in vc_dict.items():
                        if isinstance(value, Decimal):
                            vc_dict[key] = str(value)
                        elif isinstance(value, datetime):
                            vc_dict[key] = value.isoformat()
                        elif isinstance(value, dict):
                            # Handle nested dicts (like balances)
                            for k, v in value.items():
                                if isinstance(v, Decimal):
                                    value[k] = str(v)
                                elif isinstance(v, datetime):
                                    value[k] = v.isoformat()
                    virtual_card_data = vc_dict
                
                db_wallet = DBWallet(
                    wallet_id=wallet.wallet_id,
                    agent_id=wallet.agent_id,
                    balances={wallet.currency: str(wallet.balance)},
                    currency=wallet.currency,
                    limit_per_tx=wallet.limit_per_tx,
                    limit_total=wallet.limit_total,
                    spent_total=wallet.spent_total,
                    virtual_card=virtual_card_data,
                    is_active=wallet.is_active,
                    created_at=wallet.created_at,
                    updated_at=wallet.updated_at
                )
                session.add(db_wallet)
            
            return wallet

    async def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Retrieve a wallet by ID."""
        async with async_session_factory() as session:
            stmt = select(DBWallet).where(DBWallet.wallet_id == wallet_id)
            result = await session.execute(stmt)
            db_wallet = result.scalar_one_or_none()
            
            if not db_wallet:
                return None
            
            # Map back to Pydantic
            wallet = Wallet(
                wallet_id=db_wallet.wallet_id,
                agent_id=db_wallet.agent_id,
                balance=Decimal(db_wallet.balances.get(db_wallet.currency, "0.00")),
                currency=db_wallet.currency,
                limit_per_tx=db_wallet.limit_per_tx,
                limit_total=db_wallet.limit_total,
                spent_total=db_wallet.spent_total,
                is_active=db_wallet.is_active,
                created_at=db_wallet.created_at,
                updated_at=db_wallet.updated_at
            )
            
            # Restore virtual card
            if db_wallet.virtual_card:
                from sardis_core.models.virtual_card import VirtualCard
                wallet.virtual_card = VirtualCard(**db_wallet.virtual_card)
                
            # Restore multi-token balances
            for token, balance in db_wallet.balances.items():
                if token != db_wallet.currency:
                    wallet.set_token_balance(TokenType(token), Decimal(balance))
            
            return wallet

    async def update_wallet(self, wallet: Wallet) -> Wallet:
        """Update a wallet's state."""
        async with async_session_factory() as session:
            async with session.begin():
                stmt = select(DBWallet).where(DBWallet.wallet_id == wallet.wallet_id)
                result = await session.execute(stmt)
                db_wallet = result.scalar_one_or_none()
                
                if not db_wallet:
                    raise ValueError(f"Wallet {wallet.wallet_id} not found")
                
                # Update fields
                balances = {str(k.value): str(v) for k, v in wallet.get_all_balances().items()}
                db_wallet.balances = balances
                db_wallet.spent_total = wallet.spent_total
                db_wallet.updated_at = datetime.utcnow()
                
                if wallet.virtual_card:
                    db_wallet.virtual_card = wallet.virtual_card.model_dump()
                
                session.add(db_wallet)
            
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
        async with async_session_factory() as session:
            async with session.begin():
                # Lock rows for update
                stmt_from = select(DBWallet).where(DBWallet.wallet_id == from_wallet_id).with_for_update()
                stmt_to = select(DBWallet).where(DBWallet.wallet_id == to_wallet_id).with_for_update()
                
                res_from = await session.execute(stmt_from)
                res_to = await session.execute(stmt_to)
                
                from_wallet = res_from.scalar_one_or_none()
                to_wallet = res_to.scalar_one_or_none()
                
                if not from_wallet:
                    raise ValueError(f"Source wallet {from_wallet_id} not found")
                if not to_wallet:
                    raise ValueError(f"Destination wallet {to_wallet_id} not found")
                
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
                
                db_tx = DBTransaction(
                    tx_id=tx.tx_id,
                    from_wallet=from_wallet_id,
                    to_wallet=to_wallet_id,
                    amount=amount,
                    fee=fee,
                    currency=currency,
                    purpose=purpose,
                    status=TransactionStatus.PENDING.value,
                    created_at=tx.created_at
                )
                session.add(db_tx)
                
                # Validate balance
                current_balance = Decimal(from_wallet.balances.get(currency, "0.00"))
                total_cost = amount + fee
                
                if current_balance < total_cost:
                    tx.mark_failed(f"Insufficient balance: have {current_balance}, need {total_cost}")
                    db_tx.status = TransactionStatus.FAILED.value
                    db_tx.error_message = tx.error_message
                    raise ValueError(tx.error_message)
                
                # Execute transfer
                try:
                    # Deduct from source
                    new_from_balance = current_balance - total_cost
                    # Create new dict to ensure SQLAlchemy detects change
                    new_balances_from = dict(from_wallet.balances)
                    new_balances_from[currency] = str(new_from_balance)
                    from_wallet.balances = new_balances_from
                    
                    from_wallet.spent_total = Decimal(from_wallet.spent_total) + amount
                    from_wallet.updated_at = datetime.utcnow()
                    
                    # Credit to destination
                    current_to_balance = Decimal(to_wallet.balances.get(currency, "0.00"))
                    new_to_balance = current_to_balance + amount
                    
                    new_balances_to = dict(to_wallet.balances)
                    new_balances_to[currency] = str(new_to_balance)
                    to_wallet.balances = new_balances_to
                    
                    to_wallet.updated_at = datetime.utcnow()
                    
                    # Handle Fee (if > 0)
                    if fee > Decimal("0"):
                        stmt_fee = select(DBWallet).where(DBWallet.wallet_id == settings.fee_pool_wallet_id).with_for_update()
                        res_fee = await session.execute(stmt_fee)
                        fee_wallet = res_fee.scalar_one_or_none()
                        
                        if fee_wallet:
                            current_fee_balance = Decimal(fee_wallet.balances.get(currency, "0.00"))
                            new_balances_fee = dict(fee_wallet.balances)
                            new_balances_fee[currency] = str(current_fee_balance + fee)
                            fee_wallet.balances = new_balances_fee
                            fee_wallet.updated_at = datetime.utcnow()
                    
                    # Mark complete
                    tx.mark_completed()
                    db_tx.status = TransactionStatus.COMPLETED.value
                    db_tx.completed_at = tx.completed_at
                    
                    return tx
                    
                except Exception as e:
                    tx.mark_failed(str(e))
                    db_tx.status = TransactionStatus.FAILED.value
                    db_tx.error_message = str(e)
                    raise

    async def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """Retrieve a transaction by ID."""
        async with async_session_factory() as session:
            stmt = select(DBTransaction).where(DBTransaction.tx_id == tx_id)
            result = await session.execute(stmt)
            db_tx = result.scalar_one_or_none()
            
            if not db_tx:
                return None
            
            return Transaction(
                tx_id=db_tx.tx_id,
                from_wallet=db_tx.from_wallet,
                to_wallet=db_tx.to_wallet,
                amount=db_tx.amount,
                fee=db_tx.fee,
                currency=db_tx.currency,
                purpose=db_tx.purpose,
                status=TransactionStatus(db_tx.status),
                error_message=db_tx.error_message,
                created_at=db_tx.created_at,
                completed_at=db_tx.completed_at
            )

    async def list_transactions(
        self,
        wallet_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Transaction]:
        """List transactions for a wallet."""
        async with async_session_factory() as session:
            stmt = select(DBTransaction).where(
                (DBTransaction.from_wallet == wallet_id) | 
                (DBTransaction.to_wallet == wallet_id)
            ).order_by(DBTransaction.created_at.desc()).limit(limit).offset(offset)
            
            result = await session.execute(stmt)
            db_txs = result.scalars().all()
            
            return [
                Transaction(
                    tx_id=tx.tx_id,
                    from_wallet=tx.from_wallet,
                    to_wallet=tx.to_wallet,
                    amount=tx.amount,
                    fee=tx.fee,
                    currency=tx.currency,
                    purpose=tx.purpose,
                    status=TransactionStatus(tx.status),
                    error_message=tx.error_message,
                    created_at=tx.created_at,
                    completed_at=tx.completed_at
                )
                for tx in db_txs
            ]

    async def get_balance(self, wallet_id: str) -> Decimal:
        """Get the current balance of a wallet."""
        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet {wallet_id} not found")
        return wallet.balance

    async def fund_wallet(self, wallet_id: str, amount: Decimal) -> Transaction:
        """Fund a wallet from the system treasury."""
        return await self.transfer(
            from_wallet_id=settings.system_wallet_id,
            to_wallet_id=wallet_id,
            amount=amount,
            fee=Decimal("0.00"),
            currency=settings.default_currency,
            purpose="Initial funding"
        )
