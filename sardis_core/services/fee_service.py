"""Fee service for calculating and managing transaction fees."""

from decimal import Decimal
from typing import Optional

from sardis_core.config import settings


class FeeService:
    """
    Service for calculating transaction fees.
    
    This is designed to be easily extensible for more complex
    fee models in the future (e.g., tiered fees, volume discounts).
    """
    
    def __init__(self, base_fee: Optional[Decimal] = None):
        """
        Initialize the fee service.
        
        Args:
            base_fee: Override the default transaction fee
        """
        self._base_fee = base_fee or settings.transaction_fee
    
    @property
    def base_fee(self) -> Decimal:
        """Get the base transaction fee."""
        return self._base_fee
    
    def calculate_fee(
        self,
        amount: Decimal,
        currency: str = "USDC"
    ) -> Decimal:
        """
        Calculate the fee for a transaction.
        
        Currently uses a flat fee model. Future versions could
        implement percentage-based or tiered fees.
        
        Args:
            amount: Transaction amount
            currency: Currency code
            
        Returns:
            Fee amount in the same currency
        """
        # Simple flat fee for MVP
        return self._base_fee
    
    def calculate_total_cost(
        self,
        amount: Decimal,
        currency: str = "USDC"
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate total cost including fee.
        
        Args:
            amount: Transaction amount
            currency: Currency code
            
        Returns:
            Tuple of (fee, total_cost)
        """
        fee = self.calculate_fee(amount, currency)
        total = amount + fee
        return fee, total


# Global fee service instance
fee_service = FeeService()

