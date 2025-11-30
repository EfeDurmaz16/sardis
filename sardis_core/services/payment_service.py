"""Payment service for processing agent payments."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sardis_core.config import settings
from sardis_core.models import Transaction, TransactionStatus
from sardis_core.ledger import InMemoryLedger
from .wallet_service import WalletService
from .fee_service import FeeService


@dataclass
class PaymentResult:
    """Result of a payment attempt."""
    success: bool
    transaction: Optional[Transaction] = None
    error: Optional[str] = None
    
    @classmethod
    def succeeded(cls, transaction: Transaction) -> "PaymentResult":
        """Create a successful payment result."""
        return cls(success=True, transaction=transaction)
    
    @classmethod
    def failed(cls, error: str, transaction: Optional[Transaction] = None) -> "PaymentResult":
        """Create a failed payment result."""
        return cls(success=False, error=error, transaction=transaction)


class PaymentService:
    """
    Service for processing payments from agents to merchants.
    
    This is the main entry point for executing payments, handling:
    - Limit validation
    - Fee calculation
    - Ledger transfers
    - Transaction recording
    """
    
    def __init__(
        self,
        ledger: InMemoryLedger,
        wallet_service: WalletService,
        fee_service: Optional[FeeService] = None
    ):
        """
        Initialize the payment service.
        
        Args:
            ledger: The ledger for executing transfers
            wallet_service: Service for wallet operations
            fee_service: Optional fee service (uses default if not provided)
        """
        self._ledger = ledger
        self._wallet_service = wallet_service
        self._fee_service = fee_service or FeeService()
    
    def pay(
        self,
        agent_id: str,
        amount: Decimal,
        recipient_wallet_id: str,
        currency: str = "USDC",
        purpose: Optional[str] = None
    ) -> PaymentResult:
        """
        Process a payment from an agent to a recipient.
        
        This is the primary method for executing payments:
        1. Validates the agent exists and has a wallet
        2. Calculates the fee
        3. Checks spending limits
        4. Executes the transfer on the ledger
        
        Args:
            agent_id: The agent making the payment
            amount: Payment amount
            recipient_wallet_id: Wallet ID to receive payment
            currency: Currency code (default: USDC)
            purpose: Optional payment description
            
        Returns:
            PaymentResult with success status and transaction details
        """
        # Validate amount
        if amount <= Decimal("0"):
            return PaymentResult.failed("Amount must be positive")
        
        # Get agent wallet
        wallet = self._wallet_service.get_agent_wallet(agent_id)
        if not wallet:
            return PaymentResult.failed(f"Wallet not found for agent {agent_id}")
        
        # Calculate fee
        fee = self._fee_service.calculate_fee(amount, currency)
        
        # Check spending limits
        can_spend, reason = wallet.can_spend(amount, fee)
        if not can_spend:
            return PaymentResult.failed(reason)
        
        # Execute transfer on ledger
        try:
            transaction = self._ledger.transfer(
                from_wallet_id=wallet.wallet_id,
                to_wallet_id=recipient_wallet_id,
                amount=amount,
                fee=fee,
                currency=currency,
                purpose=purpose
            )
            
            return PaymentResult.succeeded(transaction)
            
        except ValueError as e:
            return PaymentResult.failed(str(e))
        except Exception as e:
            return PaymentResult.failed(f"Payment failed: {str(e)}")
    
    def pay_merchant(
        self,
        agent_id: str,
        merchant_id: str,
        amount: Decimal,
        currency: str = "USDC",
        purpose: Optional[str] = None
    ) -> PaymentResult:
        """
        Pay a registered merchant.
        
        Convenience method that looks up the merchant's wallet.
        
        Args:
            agent_id: The agent making the payment
            merchant_id: The merchant to pay
            amount: Payment amount
            currency: Currency code
            purpose: Optional payment description
            
        Returns:
            PaymentResult with success status and transaction details
        """
        merchant = self._wallet_service.get_merchant(merchant_id)
        if not merchant:
            return PaymentResult.failed(f"Merchant {merchant_id} not found")
        
        if not merchant.wallet_id:
            return PaymentResult.failed(f"Merchant {merchant_id} has no wallet")
        
        return self.pay(
            agent_id=agent_id,
            amount=amount,
            recipient_wallet_id=merchant.wallet_id,
            currency=currency,
            purpose=purpose or f"Payment to {merchant.name}"
        )
    
    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """Get a transaction by ID."""
        return self._ledger.get_transaction(tx_id)
    
    def list_agent_transactions(
        self,
        agent_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list[Transaction]:
        """
        List transactions for an agent.
        
        Args:
            agent_id: The agent to list transactions for
            limit: Maximum transactions to return
            offset: Pagination offset
            
        Returns:
            List of transactions
        """
        wallet = self._wallet_service.get_agent_wallet(agent_id)
        if not wallet:
            return []
        
        return self._ledger.list_transactions(wallet.wallet_id, limit, offset)
    
    def estimate_payment(
        self,
        amount: Decimal,
        currency: str = "USDC"
    ) -> dict:
        """
        Estimate the total cost of a payment.
        
        Args:
            amount: Payment amount
            currency: Currency code
            
        Returns:
            Dict with amount, fee, and total
        """
        fee = self._fee_service.calculate_fee(amount, currency)
        return {
            "amount": str(amount),
            "fee": str(fee),
            "total": str(amount + fee),
            "currency": currency
        }

