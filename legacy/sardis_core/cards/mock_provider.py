"""
Mock Card Provider for Testing

Provides a simulated card issuing implementation for development
and testing without real card network connections.
"""

import random
import string
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid

from .card_issuer import (
    CardIssuer,
    VirtualCardResult,
    CardTransaction,
    SpendingControls,
    CardStatus,
    TransactionStatus,
)


class MockCardProvider(CardIssuer):
    """
    Mock implementation of CardIssuer for testing.
    
    Simulates card creation and transactions without real API calls.
    Useful for development, testing, and demos.
    """
    
    def __init__(self):
        self._cardholders: Dict[str, Dict[str, Any]] = {}
        self._cards: Dict[str, Dict[str, Any]] = {}
        self._transactions: Dict[str, List[CardTransaction]] = {}
        self._pending_authorizations: Dict[str, Dict[str, Any]] = {}
    
    def _generate_card_number(self) -> str:
        """Generate a realistic-looking test card number."""
        # Use test card prefix (4111...)
        prefix = "4111"
        rest = "".join(random.choices(string.digits, k=12))
        return prefix + rest
    
    def _generate_cvc(self) -> str:
        """Generate a 3-digit CVC."""
        return "".join(random.choices(string.digits, k=3))
    
    async def create_cardholder(
        self,
        agent_id: str,
        name: str,
        email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a mock cardholder."""
        cardholder_id = f"ich_{uuid.uuid4().hex[:16]}"
        
        self._cardholders[cardholder_id] = {
            "id": cardholder_id,
            "agent_id": agent_id,
            "name": name,
            "email": email,
            "created_at": datetime.utcnow(),
            "metadata": metadata or {},
        }
        
        return cardholder_id
    
    async def create_virtual_card(
        self,
        cardholder_id: str,
        spending_controls: SpendingControls,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VirtualCardResult:
        """Create a mock virtual card."""
        if cardholder_id not in self._cardholders:
            return VirtualCardResult(
                success=False,
                error="Cardholder not found",
            )
        
        card_id = f"ic_{uuid.uuid4().hex[:16]}"
        card_number = self._generate_card_number()
        exp_date = datetime.utcnow() + timedelta(days=365 * 3)  # 3 years
        
        card_data = {
            "id": card_id,
            "cardholder_id": cardholder_id,
            "number": card_number,
            "last_four": card_number[-4:],
            "exp_month": exp_date.month,
            "exp_year": exp_date.year,
            "cvc": self._generate_cvc(),
            "status": CardStatus.ACTIVE,
            "spending_controls": spending_controls,
            "created_at": datetime.utcnow(),
            "metadata": metadata or {},
        }
        
        self._cards[card_id] = card_data
        self._transactions[card_id] = []
        
        return VirtualCardResult(
            success=True,
            card_id=card_id,
            last_four=card_data["last_four"],
            card_number=card_data["number"],
            exp_month=card_data["exp_month"],
            exp_year=card_data["exp_year"],
            cvc=card_data["cvc"],
            status=CardStatus.ACTIVE,
            spending_limit=spending_controls.spending_limit,
        )
    
    async def get_card(self, card_id: str) -> VirtualCardResult:
        """Get mock card details."""
        card = self._cards.get(card_id)
        if not card:
            return VirtualCardResult(success=False, error="Card not found")
        
        return VirtualCardResult(
            success=True,
            card_id=card_id,
            last_four=card["last_four"],
            exp_month=card["exp_month"],
            exp_year=card["exp_year"],
            status=card["status"],
            spending_limit=card["spending_controls"].spending_limit,
        )
    
    async def update_card_status(
        self,
        card_id: str,
        status: CardStatus
    ) -> VirtualCardResult:
        """Update mock card status."""
        card = self._cards.get(card_id)
        if not card:
            return VirtualCardResult(success=False, error="Card not found")
        
        card["status"] = status
        
        return VirtualCardResult(
            success=True,
            card_id=card_id,
            status=status,
        )
    
    async def update_spending_controls(
        self,
        card_id: str,
        spending_controls: SpendingControls
    ) -> VirtualCardResult:
        """Update mock card spending controls."""
        card = self._cards.get(card_id)
        if not card:
            return VirtualCardResult(success=False, error="Card not found")
        
        card["spending_controls"] = spending_controls
        
        return VirtualCardResult(
            success=True,
            card_id=card_id,
            spending_limit=spending_controls.spending_limit,
        )
    
    async def list_transactions(
        self,
        card_id: str,
        limit: int = 100,
        starting_after: Optional[str] = None
    ) -> List[CardTransaction]:
        """List mock transactions."""
        transactions = self._transactions.get(card_id, [])
        
        # Handle pagination
        if starting_after:
            for i, tx in enumerate(transactions):
                if tx.transaction_id == starting_after:
                    transactions = transactions[i + 1:]
                    break
        
        return transactions[:limit]
    
    async def handle_authorization(
        self,
        authorization_id: str,
        approve: bool,
        amount: Optional[Decimal] = None
    ) -> bool:
        """Handle mock authorization."""
        auth = self._pending_authorizations.get(authorization_id)
        if not auth:
            return False
        
        card_id = auth["card_id"]
        
        if approve:
            # Create a completed transaction
            tx = CardTransaction(
                transaction_id=f"ipi_{uuid.uuid4().hex[:16]}",
                card_id=card_id,
                amount=amount or auth["amount"],
                currency=auth.get("currency", "USD"),
                merchant_name=auth.get("merchant_name", "Test Merchant"),
                merchant_category=auth.get("merchant_category", "general"),
                status=TransactionStatus.COMPLETED,
                created_at=datetime.utcnow(),
                authorization_code=authorization_id,
            )
            
            if card_id in self._transactions:
                self._transactions[card_id].insert(0, tx)
        
        del self._pending_authorizations[authorization_id]
        return True
    
    # ==================== Test Helpers ====================
    
    async def simulate_purchase(
        self,
        card_id: str,
        amount: Decimal,
        merchant_name: str = "Test Merchant",
        merchant_category: str = "general",
        auto_approve: bool = True
    ) -> Optional[CardTransaction]:
        """
        Simulate a card purchase for testing.
        
        Args:
            card_id: Card to use
            amount: Purchase amount
            merchant_name: Merchant name
            merchant_category: MCC category
            auto_approve: Whether to auto-approve
            
        Returns:
            Transaction if approved, None if declined
        """
        card = self._cards.get(card_id)
        if not card:
            return None
        
        # Check card status
        if card["status"] != CardStatus.ACTIVE:
            return None
        
        # Check spending limit
        controls = card["spending_controls"]
        if amount > controls.spending_limit:
            return None
        
        # Check categories
        if controls.blocked_categories and merchant_category in controls.blocked_categories:
            return None
        if controls.allowed_categories and merchant_category not in controls.allowed_categories:
            return None
        
        # Create authorization
        auth_id = f"iauth_{uuid.uuid4().hex[:16]}"
        self._pending_authorizations[auth_id] = {
            "card_id": card_id,
            "amount": amount,
            "currency": "USD",
            "merchant_name": merchant_name,
            "merchant_category": merchant_category,
        }
        
        if auto_approve:
            await self.handle_authorization(auth_id, approve=True, amount=amount)
            # Return the created transaction
            transactions = self._transactions.get(card_id, [])
            if transactions:
                return transactions[0]
        
        return None
    
    def get_all_cards(self) -> Dict[str, Dict[str, Any]]:
        """Get all mock cards (for testing)."""
        return self._cards.copy()
    
    def get_all_transactions(self, card_id: str) -> List[CardTransaction]:
        """Get all transactions for a card (for testing)."""
        return self._transactions.get(card_id, [])
    
    def clear_all(self):
        """Clear all mock data."""
        self._cardholders.clear()
        self._cards.clear()
        self._transactions.clear()
        self._pending_authorizations.clear()

