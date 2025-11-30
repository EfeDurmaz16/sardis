"""
Card service for virtual card management.

Provides:
- Card issuance and lifecycle management
- Authorization/capture/void flows
- Card-to-wallet linkage
- Spending limit enforcement
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import threading
import uuid

from sardis_core.models.virtual_card import (
    VirtualCard,
    CardType,
    CardStatus,
)


@dataclass
class AuthorizationResult:
    """Result of a card authorization."""
    success: bool
    auth_id: Optional[str] = None
    card_id: Optional[str] = None
    amount: Optional[Decimal] = None
    merchant_id: Optional[str] = None
    error: Optional[str] = None
    
    @classmethod
    def approved(cls, auth_id: str, card_id: str, amount: Decimal, merchant_id: str):
        return cls(success=True, auth_id=auth_id, card_id=card_id, 
                  amount=amount, merchant_id=merchant_id)
    
    @classmethod
    def declined(cls, error: str, card_id: Optional[str] = None):
        return cls(success=False, error=error, card_id=card_id)


@dataclass
class CaptureResult:
    """Result of capturing an authorization."""
    success: bool
    capture_id: Optional[str] = None
    auth_id: Optional[str] = None
    amount: Optional[Decimal] = None
    error: Optional[str] = None


@dataclass
class PendingAuth:
    """A pending authorization on a card."""
    auth_id: str
    card_id: str
    wallet_id: str
    amount: Decimal
    merchant_id: str
    created_at: datetime
    expires_at: datetime
    status: str = "pending"  # pending, captured, voided, expired


class CardService:
    """
    Service for managing virtual cards and authorization flows.
    
    Provides the core card operations:
    - Issue new cards (single-use, multi-use, merchant-locked)
    - Authorize transactions (create holds)
    - Capture authorizations (complete payments)
    - Void authorizations (cancel holds)
    - Manage card lifecycle (suspend, cancel, reactivate)
    """
    
    # Authorization expiry (7 days)
    AUTH_EXPIRY_HOURS = 168
    
    def __init__(self):
        """Initialize the card service."""
        self._lock = threading.RLock()
        
        # Card storage: card_id -> VirtualCard
        self._cards: dict[str, VirtualCard] = {}
        
        # Wallet to cards mapping
        self._wallet_cards: dict[str, list[str]] = {}
        
        # Pending authorizations: auth_id -> PendingAuth
        self._authorizations: dict[str, PendingAuth] = {}
    
    # ==================== Card Issuance ====================
    
    def issue_card(
        self,
        wallet_id: str,
        card_type: CardType = CardType.MULTI_USE,
        limit_per_tx: Decimal = Decimal("500.00"),
        limit_daily: Decimal = Decimal("2000.00"),
        limit_monthly: Decimal = Decimal("10000.00"),
        locked_merchant_id: Optional[str] = None
    ) -> VirtualCard:
        """
        Issue a new virtual card for a wallet.
        
        Args:
            wallet_id: Wallet to link the card to
            card_type: Type of card to issue
            limit_per_tx: Per-transaction limit
            limit_daily: Daily spending limit
            limit_monthly: Monthly spending limit
            locked_merchant_id: For merchant-locked cards
            
        Returns:
            The newly issued VirtualCard
        """
        card = VirtualCard(
            wallet_id=wallet_id,
            card_type=card_type,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
            locked_merchant_id=locked_merchant_id,
        )
        
        with self._lock:
            self._cards[card.card_id] = card
            
            if wallet_id not in self._wallet_cards:
                self._wallet_cards[wallet_id] = []
            self._wallet_cards[wallet_id].append(card.card_id)
        
        return card
    
    def issue_single_use_card(
        self,
        wallet_id: str,
        amount: Decimal,
        merchant_id: Optional[str] = None
    ) -> VirtualCard:
        """
        Issue a single-use card for a specific amount.
        
        Useful for one-time purchases with specific limits.
        """
        return self.issue_card(
            wallet_id=wallet_id,
            card_type=CardType.SINGLE_USE,
            limit_per_tx=amount,
            limit_daily=amount,
            limit_monthly=amount,
            locked_merchant_id=merchant_id,
        )
    
    def issue_merchant_locked_card(
        self,
        wallet_id: str,
        merchant_id: str,
        limit_per_tx: Decimal = Decimal("500.00"),
        limit_daily: Decimal = Decimal("2000.00")
    ) -> VirtualCard:
        """Issue a card locked to a specific merchant."""
        return self.issue_card(
            wallet_id=wallet_id,
            card_type=CardType.MERCHANT_LOCKED,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            locked_merchant_id=merchant_id,
        )
    
    # ==================== Card Retrieval ====================
    
    def get_card(self, card_id: str) -> Optional[VirtualCard]:
        """Get a card by ID."""
        return self._cards.get(card_id)
    
    def get_cards_for_wallet(self, wallet_id: str) -> list[VirtualCard]:
        """Get all cards for a wallet."""
        card_ids = self._wallet_cards.get(wallet_id, [])
        return [self._cards[cid] for cid in card_ids if cid in self._cards]
    
    def get_active_card_for_wallet(self, wallet_id: str) -> Optional[VirtualCard]:
        """Get the primary active card for a wallet."""
        cards = self.get_cards_for_wallet(wallet_id)
        for card in cards:
            if card.status == CardStatus.ACTIVE and card.card_type == CardType.MULTI_USE:
                return card
        return None
    
    # ==================== Authorization Flow ====================
    
    def authorize(
        self,
        card_id: str,
        amount: Decimal,
        merchant_id: str,
        description: Optional[str] = None
    ) -> AuthorizationResult:
        """
        Authorize a transaction on a card.
        
        Creates a hold for the amount, reducing available balance.
        The authorization can later be captured or voided.
        
        Args:
            card_id: Card to authorize on
            amount: Amount to authorize
            merchant_id: Merchant requesting authorization
            description: Optional transaction description
            
        Returns:
            AuthorizationResult with auth_id if approved
        """
        with self._lock:
            card = self._cards.get(card_id)
            if not card:
                return AuthorizationResult.declined("Card not found")
            
            # Check authorization eligibility
            can_auth, reason = card.can_authorize(amount, merchant_id)
            if not can_auth:
                return AuthorizationResult.declined(reason, card_id)
            
            # Create authorization
            auth_id = f"auth_{uuid.uuid4().hex[:16]}"
            
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(hours=self.AUTH_EXPIRY_HOURS)
            
            auth = PendingAuth(
                auth_id=auth_id,
                card_id=card_id,
                wallet_id=card.wallet_id,
                amount=amount,
                merchant_id=merchant_id,
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at,
            )
            
            # Hold funds on card
            card.authorize(amount)
            
            self._authorizations[auth_id] = auth
            
            return AuthorizationResult.approved(
                auth_id=auth_id,
                card_id=card_id,
                amount=amount,
                merchant_id=merchant_id,
            )
    
    def capture(
        self,
        auth_id: str,
        amount: Optional[Decimal] = None
    ) -> CaptureResult:
        """
        Capture an authorization.
        
        Completes the transaction, converting the hold to a charge.
        Can capture less than authorized (partial capture).
        
        Args:
            auth_id: Authorization to capture
            amount: Amount to capture (default: full authorization)
            
        Returns:
            CaptureResult with status
        """
        with self._lock:
            auth = self._authorizations.get(auth_id)
            if not auth:
                return CaptureResult(success=False, error="Authorization not found")
            
            if auth.status != "pending":
                return CaptureResult(success=False, error=f"Authorization is {auth.status}")
            
            # Check expiry
            if datetime.now(timezone.utc) > auth.expires_at:
                auth.status = "expired"
                # Release the hold
                card = self._cards.get(auth.card_id)
                if card:
                    card.void_authorization(auth.amount)
                return CaptureResult(success=False, error="Authorization has expired")
            
            capture_amount = amount if amount is not None else auth.amount
            if capture_amount > auth.amount:
                return CaptureResult(
                    success=False, 
                    error=f"Capture amount {capture_amount} exceeds authorization {auth.amount}"
                )
            
            # Get the card
            card = self._cards.get(auth.card_id)
            if not card:
                return CaptureResult(success=False, error="Card not found")
            
            # If partial capture, release difference
            if capture_amount < auth.amount:
                card.void_authorization(auth.amount - capture_amount)
            
            # Capture the amount
            card.capture(capture_amount)
            
            auth.status = "captured"
            
            capture_id = f"cap_{uuid.uuid4().hex[:12]}"
            
            return CaptureResult(
                success=True,
                capture_id=capture_id,
                auth_id=auth_id,
                amount=capture_amount,
            )
    
    def void(self, auth_id: str) -> CaptureResult:
        """
        Void an authorization.
        
        Releases the hold without charging the card.
        
        Args:
            auth_id: Authorization to void
            
        Returns:
            CaptureResult indicating success
        """
        with self._lock:
            auth = self._authorizations.get(auth_id)
            if not auth:
                return CaptureResult(success=False, error="Authorization not found")
            
            if auth.status != "pending":
                return CaptureResult(success=False, error=f"Authorization is {auth.status}")
            
            # Get the card and release hold
            card = self._cards.get(auth.card_id)
            if card:
                card.void_authorization(auth.amount)
            
            auth.status = "voided"
            
            return CaptureResult(
                success=True,
                auth_id=auth_id,
                amount=auth.amount,
            )
    
    def get_authorization(self, auth_id: str) -> Optional[PendingAuth]:
        """Get an authorization by ID."""
        return self._authorizations.get(auth_id)
    
    def list_pending_authorizations(
        self,
        card_id: Optional[str] = None,
        wallet_id: Optional[str] = None
    ) -> list[PendingAuth]:
        """List pending authorizations with optional filters."""
        auths = [a for a in self._authorizations.values() if a.status == "pending"]
        
        if card_id:
            auths = [a for a in auths if a.card_id == card_id]
        if wallet_id:
            auths = [a for a in auths if a.wallet_id == wallet_id]
        
        return auths
    
    # ==================== Card Lifecycle ====================
    
    def suspend_card(self, card_id: str) -> bool:
        """Suspend a card."""
        with self._lock:
            card = self._cards.get(card_id)
            if not card:
                return False
            card.suspend()
            return True
    
    def reactivate_card(self, card_id: str) -> bool:
        """Reactivate a suspended card."""
        with self._lock:
            card = self._cards.get(card_id)
            if not card:
                return False
            card.reactivate()
            return True
    
    def cancel_card(self, card_id: str) -> bool:
        """Permanently cancel a card."""
        with self._lock:
            card = self._cards.get(card_id)
            if not card:
                return False
            
            # Void any pending authorizations
            for auth in self._authorizations.values():
                if auth.card_id == card_id and auth.status == "pending":
                    self.void(auth.auth_id)
            
            card.cancel()
            return True
    
    def update_limits(
        self,
        card_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_daily: Optional[Decimal] = None,
        limit_monthly: Optional[Decimal] = None
    ) -> Optional[VirtualCard]:
        """Update spending limits on a card."""
        with self._lock:
            card = self._cards.get(card_id)
            if not card:
                return None
            
            if limit_per_tx is not None:
                card.limit_per_tx = limit_per_tx
            if limit_daily is not None:
                card.limit_daily = limit_daily
            if limit_monthly is not None:
                card.limit_monthly = limit_monthly
            
            return card


# Global card service instance
_card_service: Optional[CardService] = None


def get_card_service() -> CardService:
    """Get the global card service instance."""
    global _card_service
    if _card_service is None:
        _card_service = CardService()
    return _card_service

