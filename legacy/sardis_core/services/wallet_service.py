"""Wallet service for managing agent wallets and limits."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import asyncio

from sardis_core.config import settings
from sardis_core.ledger import BaseLedger
from sardis_core.models.agent import Agent
from sardis_core.models.merchant import Merchant
from sardis_core.models.wallet import Wallet
from sardis_core.models.virtual_card import VirtualCard


class WalletService:
    """
    Service for managing agents, merchants, and their wallets.
    """
    
    def __init__(self, ledger: BaseLedger):
        """
        Initialize the wallet service.
        
        Args:
            ledger: The ledger implementation to use
        """
        self._ledger = ledger
        self._agents: dict[str, Agent] = {}
        self._merchants: dict[str, Merchant] = {}
        self._lock = asyncio.Lock()
    
    async def register_agent(
        self,
        name: str,
        owner_id: str,
        initial_balance: Decimal = Decimal("0.00"),
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
        description: Optional[str] = None
    ) -> tuple[Agent, Wallet]:
        """
        Register a new AI agent and create a wallet for it.
        
        Args:
            name: Agent display name
            owner_id: ID of the user/system owning the agent
            initial_balance: Starting balance (funded from system treasury)
            limit_per_tx: Optional per-transaction spending limit
            limit_total: Optional total spending limit
            description: Optional description
            
        Returns:
            Tuple of (Agent, Wallet)
        """
        async with self._lock:
            # Create agent
            agent = Agent(
                name=name,
                owner_id=owner_id,
                description=description
            )
            
            # Prepare wallet data
            wallet_data = {"agent_id": agent.agent_id}
            if limit_per_tx is not None:
                wallet_data["limit_per_tx"] = limit_per_tx
            if limit_total is not None:
                wallet_data["limit_total"] = limit_total
            
            # Create wallet
            wallet = Wallet(**wallet_data)
            
            # Create virtual card if needed (mock implementation)
            virtual_card = VirtualCard(wallet_id=wallet.wallet_id)
            wallet.virtual_card = virtual_card
            
            # Register on ledger
            await self._ledger.create_agent(agent)
            await self._ledger.create_wallet(wallet)
            
            # Fund wallet if initial balance > 0
            if initial_balance > Decimal("0"):
                await self._ledger.fund_wallet(wallet.wallet_id, initial_balance)
                # Refresh wallet to get updated balance
                wallet = await self._ledger.get_wallet(wallet.wallet_id)
            
            # Store agent with wallet reference
            agent.wallet_id = wallet.wallet_id
            self._agents[agent.agent_id] = agent
            
            return agent, wallet
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent details."""
        # No lock needed for simple read from dict
        return self._agents.get(agent_id)
    
    async def get_agent_wallet(self, agent_id: str) -> Optional[Wallet]:
        """Get the wallet for an agent."""
        # No lock needed for reading agent from dict, but ledger call is async
        agent = self._agents.get(agent_id)
        if not agent or not agent.wallet_id:
            return None
        return await self._ledger.get_wallet(agent.wallet_id)
    
    async def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Get wallet by ID."""
        return await self._ledger.get_wallet(wallet_id)
    
    def list_agents(self, owner_id: Optional[str] = None) -> list[Agent]:
        """List all agents, optionally filtered by owner."""
        # No lock needed for simple read
        if owner_id:
            return [a for a in self._agents.values() if a.owner_id == owner_id]
        return list(self._agents.values())
    
    async def check_spending_limit(
        self,
        agent_id: str,
        amount: Decimal,
        fee: Decimal = Decimal("0.00")
    ) -> tuple[bool, str]:
        """
        Check if an agent can spend the specified amount.
        
        Args:
            agent_id: The agent to check
            amount: The amount to spend
            fee: The fee amount
            
        Returns:
            Tuple of (allowed, reason)
        """
        wallet = await self.get_agent_wallet(agent_id)
        if not wallet:
            return False, f"Wallet not found for agent {agent_id}"
        
        return wallet.can_spend(amount, fee)
    
    async def register_merchant(
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
            Tuple of (Merchant, Wallet)
        """
        async with self._lock:
            # Create merchant
            merchant = Merchant(
                name=name,
                description=description,
                category=category
            )
            
            # Create a pseudo-agent for the merchant to satisfy FK constraints
            merchant_agent_id = f"merchant_{merchant.merchant_id}"
            merchant_agent = Agent(
                agent_id=merchant_agent_id,
                name=f"Merchant: {name}",
                owner_id="system_merchants",
                description=f"System agent for merchant {name}"
            )
            
            # Register agent on ledger (if using PostgresLedger this might be needed)
            await self._ledger.create_agent(merchant_agent)
            
            # Create wallet for merchant
            wallet = Wallet(
                agent_id=merchant_agent_id,
                limit_per_tx=Decimal("999999999.00"),
                limit_total=Decimal("999999999.00")
            )
            
            # Register on ledger
            await self._ledger.create_wallet(wallet)
            
            # Store merchant with wallet reference
            merchant.wallet_id = wallet.wallet_id
            self._merchants[merchant.merchant_id] = merchant
            
            return merchant, wallet
    
    def get_merchant(self, merchant_id: str) -> Optional[Merchant]:
        """Get merchant details."""
        return self._merchants.get(merchant_id)
    
    async def get_merchant_wallet(self, merchant_id: str) -> Optional[Wallet]:
        """Get the wallet for a merchant."""
        merchant = self._merchants.get(merchant_id)
        if not merchant or not merchant.wallet_id:
            return None
        return await self._ledger.get_wallet(merchant.wallet_id)
    
    def list_merchants(self) -> list[Merchant]:
        """List all merchants."""
        return list(self._merchants.values())
