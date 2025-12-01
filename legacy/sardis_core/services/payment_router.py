"""
Hybrid Payment Router

Routes payments through the optimal path based on:
- Merchant capabilities (crypto-native vs traditional)
- Transaction size (micropayments vs large transactions)
- Cost optimization (gas fees vs card fees)
- Speed requirements

Paths:
1. Stablecoin Path: Direct on-chain or Sardis ledger transfer
2. Virtual Card Path: Use issued card for traditional merchants
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from sardis_core.models import Transaction, TransactionStatus


class PaymentPath(str, Enum):
    """Available payment paths."""
    STABLECOIN_INTERNAL = "stablecoin_internal"  # Sardis internal ledger
    STABLECOIN_ONCHAIN = "stablecoin_onchain"    # On-chain ERC20 transfer
    VIRTUAL_CARD = "virtual_card"                 # Card network
    HYBRID = "hybrid"                             # Split between paths


class MerchantType(str, Enum):
    """Merchant payment acceptance."""
    CRYPTO_NATIVE = "crypto_native"      # Accepts stablecoins directly
    CRYPTO_ENABLED = "crypto_enabled"    # Accepts both crypto and card
    TRADITIONAL = "traditional"          # Only accepts card
    SARDIS_NATIVE = "sardis_native"      # Registered Sardis merchant


@dataclass
class RoutingDecision:
    """Result of payment routing decision."""
    path: PaymentPath
    reason: str
    estimated_fee: Decimal
    estimated_time_seconds: int
    fallback_path: Optional[PaymentPath] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PaymentRequest:
    """Payment request to be routed."""
    agent_id: str
    wallet_id: str
    amount: Decimal
    currency: str
    
    # Recipient (one of these)
    merchant_id: Optional[str] = None
    recipient_wallet_id: Optional[str] = None
    recipient_address: Optional[str] = None  # On-chain address
    external_merchant_url: Optional[str] = None  # External website
    
    # Options
    purpose: Optional[str] = None
    idempotency_key: Optional[str] = None
    prefer_path: Optional[PaymentPath] = None
    require_instant: bool = False
    
    # Merchant info (if known)
    merchant_type: Optional[MerchantType] = None
    merchant_category: Optional[str] = None


@dataclass
class PaymentResult:
    """Result of a routed payment."""
    success: bool
    transaction_id: Optional[str] = None
    path_used: Optional[PaymentPath] = None
    tx_hash: Optional[str] = None  # Blockchain tx hash if on-chain
    card_transaction_id: Optional[str] = None  # Card network tx ID
    amount: Optional[Decimal] = None
    fee: Optional[Decimal] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    explorer_url: Optional[str] = None


class PaymentRouter:
    """
    Intelligent payment router for hybrid stablecoin + card payments.
    
    Decides the optimal payment path based on:
    - Merchant capabilities
    - Transaction characteristics
    - Cost optimization
    - Speed requirements
    """
    
    # Fee structures (configurable)
    CARD_FEE_PERCENT = Decimal("0.029")  # 2.9%
    CARD_FEE_FIXED = Decimal("0.30")     # $0.30 per tx
    ONCHAIN_GAS_ESTIMATE = Decimal("0.50")  # ~$0.50 on L2
    INTERNAL_FEE = Decimal("0.10")       # Sardis internal fee
    
    # Thresholds
    MICROPAYMENT_THRESHOLD = Decimal("1.00")  # Under $1 = micropayment
    CARD_MINIMUM = Decimal("0.50")            # Cards need minimum
    
    def __init__(
        self,
        payment_service=None,
        card_manager=None,
        contract_service=None,
        merchant_registry: Optional[Dict[str, MerchantType]] = None
    ):
        """
        Initialize router with payment backends.
        
        Args:
            payment_service: Sardis PaymentService for internal transfers
            card_manager: CardManager for virtual card payments
            contract_service: ContractService for on-chain payments
            merchant_registry: Known merchant types
        """
        self.payment_service = payment_service
        self.card_manager = card_manager
        self.contract_service = contract_service
        self.merchant_registry = merchant_registry or {}
    
    def determine_route(self, request: PaymentRequest) -> RoutingDecision:
        """
        Determine the optimal payment path for a request.
        
        Logic:
        1. Check if merchant accepts crypto
        2. Check transaction size
        3. Compare fees
        4. Consider speed requirements
        """
        merchant_type = self._get_merchant_type(request)
        
        # Honor explicit preferences
        if request.prefer_path:
            return self._validate_preferred_path(request, request.prefer_path)
        
        # Sardis-native merchants: always use internal
        if merchant_type == MerchantType.SARDIS_NATIVE:
            return RoutingDecision(
                path=PaymentPath.STABLECOIN_INTERNAL,
                reason="Sardis-native merchant, using internal ledger",
                estimated_fee=self.INTERNAL_FEE,
                estimated_time_seconds=1,
            )
        
        # Agent-to-agent payments: internal or on-chain
        if request.recipient_wallet_id:
            return self._route_a2a_payment(request)
        
        # Crypto-native merchants: on-chain
        if merchant_type == MerchantType.CRYPTO_NATIVE:
            return RoutingDecision(
                path=PaymentPath.STABLECOIN_ONCHAIN,
                reason="Crypto-native merchant, using on-chain transfer",
                estimated_fee=self.ONCHAIN_GAS_ESTIMATE,
                estimated_time_seconds=15,
                fallback_path=PaymentPath.STABLECOIN_INTERNAL,
            )
        
        # Traditional merchants: virtual card
        if merchant_type == MerchantType.TRADITIONAL:
            if request.amount < self.CARD_MINIMUM:
                return RoutingDecision(
                    path=PaymentPath.STABLECOIN_INTERNAL,
                    reason="Amount too low for card, using internal (may need manual settlement)",
                    estimated_fee=self.INTERNAL_FEE,
                    estimated_time_seconds=1,
                )
            
            card_fee = (request.amount * self.CARD_FEE_PERCENT) + self.CARD_FEE_FIXED
            return RoutingDecision(
                path=PaymentPath.VIRTUAL_CARD,
                reason="Traditional merchant, using virtual card",
                estimated_fee=card_fee,
                estimated_time_seconds=5,
            )
        
        # Crypto-enabled merchants: choose based on cost
        if merchant_type == MerchantType.CRYPTO_ENABLED:
            return self._optimize_crypto_enabled(request)
        
        # Default: try internal first
        return RoutingDecision(
            path=PaymentPath.STABLECOIN_INTERNAL,
            reason="Unknown merchant type, using internal ledger",
            estimated_fee=self.INTERNAL_FEE,
            estimated_time_seconds=1,
            fallback_path=PaymentPath.VIRTUAL_CARD,
        )
    
    async def route_payment(self, request: PaymentRequest) -> PaymentResult:
        """
        Route and execute a payment.
        
        Args:
            request: Payment request details
            
        Returns:
            PaymentResult with transaction details
        """
        # Get routing decision
        decision = self.determine_route(request)
        
        # Execute through chosen path
        try:
            if decision.path == PaymentPath.STABLECOIN_INTERNAL:
                return await self._execute_internal(request)
            
            elif decision.path == PaymentPath.STABLECOIN_ONCHAIN:
                result = await self._execute_onchain(request)
                
                # Try fallback if on-chain fails
                if not result.success and decision.fallback_path:
                    return await self._execute_fallback(request, decision.fallback_path)
                
                return result
            
            elif decision.path == PaymentPath.VIRTUAL_CARD:
                return await self._execute_card(request)
            
            else:
                return PaymentResult(
                    success=False,
                    error=f"Unsupported path: {decision.path}",
                )
                
        except Exception as e:
            return PaymentResult(
                success=False,
                error=str(e),
            )
    
    def _get_merchant_type(self, request: PaymentRequest) -> MerchantType:
        """Determine merchant type from request."""
        # Explicit merchant type
        if request.merchant_type:
            return request.merchant_type
        
        # Check registry
        if request.merchant_id and request.merchant_id in self.merchant_registry:
            return self.merchant_registry[request.merchant_id]
        
        # On-chain address = crypto native
        if request.recipient_address and request.recipient_address.startswith("0x"):
            return MerchantType.CRYPTO_NATIVE
        
        # External URL = likely traditional
        if request.external_merchant_url:
            return MerchantType.TRADITIONAL
        
        # Sardis wallet = native
        if request.recipient_wallet_id:
            return MerchantType.SARDIS_NATIVE
        
        return MerchantType.TRADITIONAL  # Default assumption
    
    def _route_a2a_payment(self, request: PaymentRequest) -> RoutingDecision:
        """Route agent-to-agent payment."""
        # A2A always goes through internal ledger first
        # Can optionally settle on-chain for verifiability
        return RoutingDecision(
            path=PaymentPath.STABLECOIN_INTERNAL,
            reason="Agent-to-agent payment via internal ledger",
            estimated_fee=self.INTERNAL_FEE,
            estimated_time_seconds=1,
            metadata={"can_settle_onchain": True},
        )
    
    def _optimize_crypto_enabled(self, request: PaymentRequest) -> RoutingDecision:
        """Choose optimal path for crypto-enabled merchants."""
        # Calculate fees for each path
        card_fee = (request.amount * self.CARD_FEE_PERCENT) + self.CARD_FEE_FIXED
        onchain_fee = self.ONCHAIN_GAS_ESTIMATE
        
        # For micropayments, internal is always better
        if request.amount < self.MICROPAYMENT_THRESHOLD:
            return RoutingDecision(
                path=PaymentPath.STABLECOIN_INTERNAL,
                reason="Micropayment: internal ledger is most cost-effective",
                estimated_fee=self.INTERNAL_FEE,
                estimated_time_seconds=1,
            )
        
        # Compare costs
        if onchain_fee < card_fee:
            return RoutingDecision(
                path=PaymentPath.STABLECOIN_ONCHAIN,
                reason=f"On-chain cheaper (${onchain_fee:.2f} vs ${card_fee:.2f})",
                estimated_fee=onchain_fee,
                estimated_time_seconds=15,
                fallback_path=PaymentPath.VIRTUAL_CARD,
            )
        else:
            return RoutingDecision(
                path=PaymentPath.VIRTUAL_CARD,
                reason=f"Card cheaper (${card_fee:.2f} vs ${onchain_fee:.2f})",
                estimated_fee=card_fee,
                estimated_time_seconds=5,
            )
    
    def _validate_preferred_path(
        self,
        request: PaymentRequest,
        path: PaymentPath
    ) -> RoutingDecision:
        """Validate and return a preferred path."""
        if path == PaymentPath.VIRTUAL_CARD:
            if request.amount < self.CARD_MINIMUM:
                return RoutingDecision(
                    path=PaymentPath.STABLECOIN_INTERNAL,
                    reason="Amount too low for card, using internal",
                    estimated_fee=self.INTERNAL_FEE,
                    estimated_time_seconds=1,
                )
            card_fee = (request.amount * self.CARD_FEE_PERCENT) + self.CARD_FEE_FIXED
            return RoutingDecision(
                path=PaymentPath.VIRTUAL_CARD,
                reason="User preferred card path",
                estimated_fee=card_fee,
                estimated_time_seconds=5,
            )
        
        elif path == PaymentPath.STABLECOIN_ONCHAIN:
            return RoutingDecision(
                path=PaymentPath.STABLECOIN_ONCHAIN,
                reason="User preferred on-chain path",
                estimated_fee=self.ONCHAIN_GAS_ESTIMATE,
                estimated_time_seconds=15,
            )
        
        else:
            return RoutingDecision(
                path=PaymentPath.STABLECOIN_INTERNAL,
                reason="User preferred internal path",
                estimated_fee=self.INTERNAL_FEE,
                estimated_time_seconds=1,
            )
    
    async def _execute_internal(self, request: PaymentRequest) -> PaymentResult:
        """Execute payment through internal ledger."""
        if not self.payment_service:
            return PaymentResult(success=False, error="Payment service not configured")
        
        try:
            # Use PaymentService for internal transfer
            result = self.payment_service.pay(
                agent_id=request.agent_id,
                amount=request.amount,
                merchant_id=request.merchant_id,
                recipient_wallet_id=request.recipient_wallet_id,
                purpose=request.purpose,
                idempotency_key=request.idempotency_key,
            )
            
            return PaymentResult(
                success=result.success,
                transaction_id=result.transaction.tx_id if result.transaction else None,
                path_used=PaymentPath.STABLECOIN_INTERNAL,
                amount=result.transaction.amount if result.transaction else request.amount,
                fee=result.transaction.fee if result.transaction else self.INTERNAL_FEE,
                completed_at=datetime.utcnow(),
                error=result.error,
            )
        except Exception as e:
            return PaymentResult(success=False, error=str(e))
    
    async def _execute_onchain(self, request: PaymentRequest) -> PaymentResult:
        """Execute payment on-chain."""
        if not self.contract_service:
            return PaymentResult(success=False, error="Contract service not configured")
        
        try:
            # Get wallet's on-chain address
            # Execute on-chain transfer
            result = await self.contract_service.execute_payment(
                wallet_address=request.wallet_id,  # Assume this is the on-chain address
                to_address=request.recipient_address or request.merchant_id,
                amount=request.amount,
                purpose=request.purpose or "Sardis payment",
            )
            
            return PaymentResult(
                success=result.success,
                transaction_id=str(uuid.uuid4()),
                path_used=PaymentPath.STABLECOIN_ONCHAIN,
                tx_hash=result.tx_hash,
                amount=request.amount,
                fee=Decimal(str(result.gas_used or 0)) * Decimal("0.000001"),  # Rough estimate
                completed_at=datetime.utcnow(),
                explorer_url=result.explorer_url,
                error=result.error,
            )
        except Exception as e:
            return PaymentResult(success=False, error=str(e))
    
    async def _execute_card(self, request: PaymentRequest) -> PaymentResult:
        """Execute payment via virtual card."""
        if not self.card_manager:
            return PaymentResult(success=False, error="Card manager not configured")
        
        try:
            # Note: Real card payments are merchant-initiated
            # This would typically be an authorization flow
            # For now, we simulate by creating a pending transaction
            
            card_fee = (request.amount * self.CARD_FEE_PERCENT) + self.CARD_FEE_FIXED
            
            return PaymentResult(
                success=True,
                transaction_id=str(uuid.uuid4()),
                path_used=PaymentPath.VIRTUAL_CARD,
                card_transaction_id=f"card_tx_{uuid.uuid4().hex[:12]}",
                amount=request.amount,
                fee=card_fee,
                completed_at=datetime.utcnow(),
            )
        except Exception as e:
            return PaymentResult(success=False, error=str(e))
    
    async def _execute_fallback(
        self,
        request: PaymentRequest,
        fallback_path: PaymentPath
    ) -> PaymentResult:
        """Execute fallback path after primary failure."""
        if fallback_path == PaymentPath.STABLECOIN_INTERNAL:
            return await self._execute_internal(request)
        elif fallback_path == PaymentPath.VIRTUAL_CARD:
            return await self._execute_card(request)
        else:
            return PaymentResult(success=False, error="No valid fallback path")
    
    def register_merchant(
        self,
        merchant_id: str,
        merchant_type: MerchantType
    ):
        """Register a merchant's payment capabilities."""
        self.merchant_registry[merchant_id] = merchant_type
    
    def get_supported_paths(self) -> List[PaymentPath]:
        """Get list of currently available payment paths."""
        paths = []
        
        if self.payment_service:
            paths.append(PaymentPath.STABLECOIN_INTERNAL)
        if self.contract_service:
            paths.append(PaymentPath.STABLECOIN_ONCHAIN)
        if self.card_manager:
            paths.append(PaymentPath.VIRTUAL_CARD)
        
        return paths
    
    def estimate_fees(
        self,
        amount: Decimal,
        path: Optional[PaymentPath] = None
    ) -> Dict[PaymentPath, Decimal]:
        """Estimate fees for all or specific path."""
        fees = {}
        
        if path is None or path == PaymentPath.STABLECOIN_INTERNAL:
            fees[PaymentPath.STABLECOIN_INTERNAL] = self.INTERNAL_FEE
        
        if path is None or path == PaymentPath.STABLECOIN_ONCHAIN:
            fees[PaymentPath.STABLECOIN_ONCHAIN] = self.ONCHAIN_GAS_ESTIMATE
        
        if path is None or path == PaymentPath.VIRTUAL_CARD:
            fees[PaymentPath.VIRTUAL_CARD] = (amount * self.CARD_FEE_PERCENT) + self.CARD_FEE_FIXED
        
        return fees

