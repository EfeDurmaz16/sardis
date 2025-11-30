"""Wallet service for managing agent wallets and limits."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import threading

from sardis_core.config import settings
from sardis_core.models import Agent, Wallet, VirtualCard, Merchant
from sardis_core.ledger import InMemoryLedger


class WalletService:
    """
    Service for managing wallets, agents, and merchants.
    
    Handles wallet creation, limit enforcement, and balance tracking.
    """
    
    def __init__(self, ledger: InMemoryLedger):
        """
        Initialize the wallet service.
        
        Args:
            ledger: The ledger implementation to use
        """
        self._ledger = ledger
        self._agents: dict[str, Agent] = {}
        self._merchants: dict[str, Merchant] = {}
        self._lock = threading.RLock()
    
    def register_agent(
        self,
        name: str,
        owner_id: str,
        initial_balance: Decimal = Decimal("0.00"),
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
        description: Optional[str] = None
    ) -> tuple[Agent, Wallet]:
        """
        Register a new agent and create their wallet.
        
        Args:
            name: Agent display name
            owner_id: ID of the developer/company owning this agent
            initial_balance: Starting USDC balance
            limit_per_tx: Max per-transaction limit
            limit_total: Max total spending limit
            description: Optional agent description
            
        Returns:
            Tuple of (agent, wallet)
        """
        with self._lock:
            # Create the agent
            agent = Agent(
                name=name,
                owner_id=owner_id,
                description=description
            )
            
            # Create wallet with limits
            wallet = Wallet(
                agent_id=agent.agent_id,
                currency=settings.default_currency,
                limit_per_tx=limit_per_tx or settings.default_limit_per_tx,
                limit_total=limit_total or settings.default_limit_total,
            )
            
            # Create virtual card for the wallet
            virtual_card = VirtualCard(wallet_id=wallet.wallet_id)
            wallet.virtual_card = virtual_card
            
            # Register on ledger
            self._ledger.create_wallet(wallet)
            
            # Fund wallet if initial balance > 0
            if initial_balance > Decimal("0"):
                self._ledger.fund_wallet(wallet.wallet_id, initial_balance)
                # Refresh wallet to get updated balance
                wallet = self._ledger.get_wallet(wallet.wallet_id)
            
            # Store agent with wallet reference
            agent.wallet_id = wallet.wallet_id
            self._agents[agent.agent_id] = agent
            
            return agent, wallet
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        with self._lock:
            return self._agents.get(agent_id)
    
    def get_agent_wallet(self, agent_id: str) -> Optional[Wallet]:
        """Get the wallet for an agent."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent or not agent.wallet_id:
                return None
            return self._ledger.get_wallet(agent.wallet_id)
    
    def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Get wallet by ID."""
        return self._ledger.get_wallet(wallet_id)
    
    def list_agents(self, owner_id: Optional[str] = None) -> list[Agent]:
        """List all agents, optionally filtered by owner."""
        with self._lock:
            if owner_id:
                return [a for a in self._agents.values() if a.owner_id == owner_id]
            return list(self._agents.values())
    
    def check_spending_limit(
        self,
        agent_id: str,
        amount: Decimal,
        fee: Decimal = Decimal("0.00")
    ) -> tuple[bool, str]:
        """
        Check if an agent can spend the given amount.
        
        Args:
            agent_id: The agent attempting to spend
            amount: Amount to spend (excluding fee)
            fee: Transaction fee
            
        Returns:
            Tuple of (allowed, reason)
        """
        wallet = self.get_agent_wallet(agent_id)
        if not wallet:
            return False, f"Wallet not found for agent {agent_id}"
        
        return wallet.can_spend(amount, fee)
    
    def register_merchant(
        self,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None
    ) -> tuple[Merchant, Wallet]:
        """
        Register a new merchant that can receive payments.
        
        Args:
            name: Merchant display name
            description: Optional description
            category: Optional category (e.g., "retail", "api_service")
            
        Returns:
            Tuple of (merchant, wallet)
        """
        with self._lock:
            # Create merchant
            merchant = Merchant(
                name=name,
                description=description,
                category=category
            )
            
            # Create merchant wallet
            wallet = Wallet(
                wallet_id=f"merchant_wallet_{merchant.merchant_id}",
                agent_id=merchant.merchant_id,
                currency=settings.default_currency,
                # Merchants have high limits for receiving
                limit_per_tx=Decimal("999999999.00"),
                limit_total=Decimal("999999999.00"),
            )
            
            # Register on ledger
            self._ledger.create_wallet(wallet)
            
            # Store merchant with wallet reference
            merchant.wallet_id = wallet.wallet_id
            self._merchants[merchant.merchant_id] = merchant
            
            return merchant, wallet
    
    def get_merchant(self, merchant_id: str) -> Optional[Merchant]:
        """Get merchant by ID."""
        with self._lock:
            return self._merchants.get(merchant_id)
    
    def get_merchant_wallet(self, merchant_id: str) -> Optional[Wallet]:
        """Get the wallet for a merchant."""
        with self._lock:
            merchant = self._merchants.get(merchant_id)
            if not merchant or not merchant.wallet_id:
                return None
            return self._ledger.get_wallet(merchant.wallet_id)
    
    def list_merchants(self) -> list[Merchant]:
        """List all merchants."""
        with self._lock:
            return list(self._merchants.values())

