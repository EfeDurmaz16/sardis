"""
Card Issuer Service

Abstract interface for virtual card issuance and management.
Supports multiple providers (Stripe Issuing, Marqeta, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid


class CardStatus(str, Enum):
    """Card status values."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELED = "canceled"
    FROZEN = "frozen"


class CardType(str, Enum):
    """Card type values."""
    VIRTUAL = "virtual"
    PHYSICAL = "physical"


class TransactionStatus(str, Enum):
    """Transaction status values."""
    PENDING = "pending"
    COMPLETED = "completed"
    DECLINED = "declined"
    REVERSED = "reversed"


@dataclass
class VirtualCardResult:
    """Result of card creation or retrieval."""
    success: bool
    card_id: Optional[str] = None
    last_four: Optional[str] = None
    card_number: Optional[str] = None  # Only for initial creation
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    cvc: Optional[str] = None  # Only for initial creation
    status: Optional[CardStatus] = None
    spending_limit: Optional[Decimal] = None
    error: Optional[str] = None


@dataclass
class CardTransaction:
    """Card transaction record."""
    transaction_id: str
    card_id: str
    amount: Decimal
    currency: str
    merchant_name: str
    merchant_category: str
    status: TransactionStatus
    created_at: datetime
    authorization_code: Optional[str] = None
    decline_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SpendingControls:
    """Spending controls for a card."""
    spending_limit: Decimal
    spending_limit_interval: str  # "per_authorization", "daily", "weekly", "monthly", "all_time"
    allowed_categories: Optional[List[str]] = None
    blocked_categories: Optional[List[str]] = None
    allowed_merchants: Optional[List[str]] = None
    blocked_merchants: Optional[List[str]] = None


class CardIssuer(ABC):
    """
    Abstract interface for card issuance providers.
    
    Implementations:
    - StripeCardProvider: Stripe Issuing integration
    - MarqetaCardProvider: Marqeta integration
    - MockCardProvider: For testing
    """
    
    @abstractmethod
    async def create_cardholder(
        self,
        agent_id: str,
        name: str,
        email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a cardholder (required before issuing cards).
        
        Args:
            agent_id: Sardis agent ID
            name: Cardholder name
            email: Email address
            metadata: Additional metadata
            
        Returns:
            Provider's cardholder ID
        """
        pass
    
    @abstractmethod
    async def create_virtual_card(
        self,
        cardholder_id: str,
        spending_controls: SpendingControls,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VirtualCardResult:
        """
        Create a new virtual card.
        
        Args:
            cardholder_id: Provider's cardholder ID
            spending_controls: Spending limits and restrictions
            metadata: Additional metadata (e.g., Sardis wallet ID)
            
        Returns:
            VirtualCardResult with card details
        """
        pass
    
    @abstractmethod
    async def get_card(self, card_id: str) -> VirtualCardResult:
        """Get card details."""
        pass
    
    @abstractmethod
    async def update_card_status(
        self,
        card_id: str,
        status: CardStatus
    ) -> VirtualCardResult:
        """Update card status (freeze, unfreeze, cancel)."""
        pass
    
    @abstractmethod
    async def update_spending_controls(
        self,
        card_id: str,
        spending_controls: SpendingControls
    ) -> VirtualCardResult:
        """Update card spending controls."""
        pass
    
    @abstractmethod
    async def list_transactions(
        self,
        card_id: str,
        limit: int = 100,
        starting_after: Optional[str] = None
    ) -> List[CardTransaction]:
        """List transactions for a card."""
        pass
    
    @abstractmethod
    async def handle_authorization(
        self,
        authorization_id: str,
        approve: bool,
        amount: Optional[Decimal] = None
    ) -> bool:
        """
        Handle real-time authorization request.
        
        Args:
            authorization_id: Provider's authorization ID
            approve: Whether to approve
            amount: Approved amount (for partial approvals)
            
        Returns:
            Whether the response was processed
        """
        pass


class CardManager:
    """
    High-level card management service.
    
    Coordinates between Sardis wallets and card providers.
    """
    
    def __init__(self, provider: CardIssuer):
        self.provider = provider
        self._cardholders: Dict[str, str] = {}  # agent_id -> cardholder_id
        self._cards: Dict[str, str] = {}  # wallet_id -> card_id
    
    async def create_card_for_wallet(
        self,
        agent_id: str,
        wallet_id: str,
        agent_name: str,
        spending_limit: Decimal,
        allowed_categories: Optional[List[str]] = None
    ) -> VirtualCardResult:
        """
        Create a virtual card linked to a Sardis wallet.
        
        Args:
            agent_id: Sardis agent ID
            wallet_id: Sardis wallet ID
            agent_name: Name for the cardholder
            spending_limit: Maximum spending limit
            allowed_categories: Merchant category codes to allow
            
        Returns:
            VirtualCardResult with card details
        """
        # Get or create cardholder
        if agent_id not in self._cardholders:
            cardholder_id = await self.provider.create_cardholder(
                agent_id=agent_id,
                name=agent_name,
                metadata={"sardis_agent_id": agent_id}
            )
            self._cardholders[agent_id] = cardholder_id
        
        cardholder_id = self._cardholders[agent_id]
        
        # Create card with spending controls
        controls = SpendingControls(
            spending_limit=spending_limit,
            spending_limit_interval="per_authorization",
            allowed_categories=allowed_categories,
        )
        
        result = await self.provider.create_virtual_card(
            cardholder_id=cardholder_id,
            spending_controls=controls,
            metadata={
                "sardis_wallet_id": wallet_id,
                "sardis_agent_id": agent_id,
            }
        )
        
        if result.success and result.card_id:
            self._cards[wallet_id] = result.card_id
        
        return result
    
    async def freeze_card(self, wallet_id: str) -> VirtualCardResult:
        """Freeze a card (temporary disable)."""
        card_id = self._cards.get(wallet_id)
        if not card_id:
            return VirtualCardResult(success=False, error="Card not found")
        
        return await self.provider.update_card_status(card_id, CardStatus.FROZEN)
    
    async def unfreeze_card(self, wallet_id: str) -> VirtualCardResult:
        """Unfreeze a card."""
        card_id = self._cards.get(wallet_id)
        if not card_id:
            return VirtualCardResult(success=False, error="Card not found")
        
        return await self.provider.update_card_status(card_id, CardStatus.ACTIVE)
    
    async def cancel_card(self, wallet_id: str) -> VirtualCardResult:
        """Cancel a card (permanent)."""
        card_id = self._cards.get(wallet_id)
        if not card_id:
            return VirtualCardResult(success=False, error="Card not found")
        
        return await self.provider.update_card_status(card_id, CardStatus.CANCELED)
    
    async def update_limit(
        self,
        wallet_id: str,
        spending_limit: Decimal
    ) -> VirtualCardResult:
        """Update card spending limit."""
        card_id = self._cards.get(wallet_id)
        if not card_id:
            return VirtualCardResult(success=False, error="Card not found")
        
        controls = SpendingControls(
            spending_limit=spending_limit,
            spending_limit_interval="per_authorization",
        )
        
        return await self.provider.update_spending_controls(card_id, controls)
    
    async def get_transactions(
        self,
        wallet_id: str,
        limit: int = 100
    ) -> List[CardTransaction]:
        """Get card transactions."""
        card_id = self._cards.get(wallet_id)
        if not card_id:
            return []
        
        return await self.provider.list_transactions(card_id, limit=limit)
    
    async def handle_authorization_webhook(
        self,
        authorization_data: Dict[str, Any]
    ) -> bool:
        """
        Handle real-time authorization webhook from provider.
        
        This is called when a card is used and we need to approve/decline.
        """
        # Extract authorization details
        authorization_id = authorization_data.get("id")
        card_id = authorization_data.get("card_id")
        amount = Decimal(str(authorization_data.get("amount", 0)))
        merchant = authorization_data.get("merchant", {})
        
        # Find the associated wallet
        wallet_id = None
        for wid, cid in self._cards.items():
            if cid == card_id:
                wallet_id = wid
                break
        
        if not wallet_id:
            # Unknown card, decline
            await self.provider.handle_authorization(
                authorization_id,
                approve=False
            )
            return False
        
        # Here we would check:
        # 1. Sardis wallet has sufficient balance
        # 2. Transaction passes spending policy
        # 3. Risk checks pass
        
        # For now, approve all valid cards
        # TODO: Integrate with PaymentService and RiskService
        
        await self.provider.handle_authorization(
            authorization_id,
            approve=True,
            amount=amount
        )
        
        return True

