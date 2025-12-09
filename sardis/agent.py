"""
Agent identity and wallet management.

Agents are autonomous entities that can hold wallets and make payments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from .wallet import Wallet
from .policy import Policy
from .transaction import Transaction, TransactionResult


@dataclass
class Agent:
    """
    An AI agent with payment capabilities.
    
    Agents can:
    - Hold one or more wallets
    - Make payments to other agents or merchants
    - Enforce spending policies
    
    Example:
        >>> agent = Agent(name="Shopping Assistant")
        >>> agent.create_wallet(initial_balance=100)
        >>> result = agent.pay("openai:api", 5, purpose="API call")
        >>> print(result.success)  # True
    """
    
    agent_id: str = field(default_factory=lambda: f"agent_{uuid4().hex[:12]}")
    name: str = "Unnamed Agent"
    description: Optional[str] = None
    wallets: List[Wallet] = field(default_factory=list)
    default_policy: Policy = field(default_factory=Policy)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __init__(
        self,
        name: str = "Unnamed Agent",
        *,
        description: Optional[str] = None,
        agent_id: Optional[str] = None,
        policy: Optional[Policy] = None,
    ):
        """
        Create a new agent.
        
        Args:
            name: Human-readable name
            description: Optional description
            agent_id: Optional ID (auto-generated if not provided)
            policy: Default spending policy
        """
        self.agent_id = agent_id or f"agent_{uuid4().hex[:12]}"
        self.name = name
        self.description = description
        self.wallets = []
        self.default_policy = policy or Policy()
        self.is_active = True
        self.created_at = datetime.now(timezone.utc)
    
    def create_wallet(
        self,
        initial_balance: float = 0,
        *,
        currency: str = "USDC",
        limit_per_tx: float = 100,
        limit_total: float = 1000,
    ) -> Wallet:
        """
        Create a new wallet for this agent.
        
        Args:
            initial_balance: Starting balance
            currency: Token type (default: USDC)
            limit_per_tx: Maximum per transaction
            limit_total: Maximum total spending
            
        Returns:
            The created wallet
        """
        wallet = Wallet(
            initial_balance=initial_balance,
            currency=currency,
            limit_per_tx=limit_per_tx,
            limit_total=limit_total,
            agent_id=self.agent_id,
        )
        self.wallets.append(wallet)
        return wallet
    
    @property
    def primary_wallet(self) -> Optional[Wallet]:
        """Get the agent's primary (first) wallet."""
        return self.wallets[0] if self.wallets else None
    
    @property
    def total_balance(self) -> float:
        """Get total balance across all wallets."""
        return float(sum(w.balance for w in self.wallets))
    
    def pay(
        self,
        to: str,
        amount: float,
        *,
        purpose: Optional[str] = None,
        wallet: Optional[Wallet] = None,
        policy: Optional[Policy] = None,
    ) -> TransactionResult:
        """
        Make a payment from this agent.
        
        Args:
            to: Destination (address, agent ID, or merchant)
            amount: Amount to pay
            purpose: Optional payment purpose
            wallet: Specific wallet to use (default: primary wallet)
            policy: Policy to enforce (default: agent's default policy)
            
        Returns:
            TransactionResult with success status
        """
        source_wallet = wallet or self.primary_wallet
        
        if not source_wallet:
            from .transaction import TransactionResult, TransactionStatus
            return TransactionResult(
                tx_id=f"tx_{uuid4().hex[:16]}",
                status=TransactionStatus.FAILED,
                amount=amount,
                from_wallet="none",
                to=to,
                currency="USDC",
                timestamp=datetime.now(timezone.utc),
                message="No wallet available",
            )
        
        tx = Transaction(
            from_wallet=source_wallet,
            to=to,
            amount=amount,
            purpose=purpose,
            policy=policy or self.default_policy,
        )
        
        return tx.execute()
    
    def __repr__(self) -> str:
        wallet_count = len(self.wallets)
        balance = self.total_balance
        return f"Agent({self.name}, {wallet_count} wallets, balance={balance})"
