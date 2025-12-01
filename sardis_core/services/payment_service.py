"""Payment service for processing agent payments."""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
import asyncio # Changed from threading
import uuid

from sardis_core.config import settings
from sardis_core.models import Transaction, TransactionStatus, OnChainRecord
from sardis_core.ledger import InMemoryLedger
from .wallet_service import WalletService
from .fee_service import FeeService
from .blockchain_service import blockchain_service


@dataclass
class PaymentResult:
    """Result of a payment attempt."""
    success: bool
    transaction: Optional[Transaction] = None
    error: Optional[str] = None
    idempotency_key: Optional[str] = None
    
    @classmethod
    def succeeded(cls, transaction: Transaction, idempotency_key: Optional[str] = None) -> "PaymentResult":
        """Create a successful payment result."""
        return cls(success=True, transaction=transaction, idempotency_key=idempotency_key)
    
    @classmethod
    def failed(cls, error: str, transaction: Optional[Transaction] = None) -> "PaymentResult":
        """Create a failed payment result."""
        return cls(success=False, error=error, transaction=transaction)


@dataclass
class HoldResult:
    """Result of a pre-authorization hold."""
    success: bool
    hold_id: Optional[str] = None
    agent_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "USDC"
    merchant_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None
    
    @classmethod
    def succeeded(cls, hold_id: str, agent_id: str, amount: Decimal, 
                  currency: str, merchant_id: str, expires_at: datetime) -> "HoldResult":
        return cls(
            success=True, hold_id=hold_id, agent_id=agent_id,
            amount=amount, currency=currency, merchant_id=merchant_id,
            expires_at=expires_at
        )
    
    @classmethod
    def failed(cls, error: str) -> "HoldResult":
        return cls(success=False, error=error)


@dataclass
class RefundResult:
    """Result of a refund operation."""
    success: bool
    refund_id: Optional[str] = None
    original_tx_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "USDC"
    error: Optional[str] = None
    
    @classmethod
    def succeeded(cls, refund_id: str, original_tx_id: str, 
                  amount: Decimal, currency: str) -> "RefundResult":
        return cls(
            success=True, refund_id=refund_id, original_tx_id=original_tx_id,
            amount=amount, currency=currency
        )
    
    @classmethod
    def failed(cls, error: str) -> "RefundResult":
        return cls(success=False, error=error)


@dataclass
class PaymentHold:
    """A pre-authorization hold on funds."""
    hold_id: str
    agent_id: str
    wallet_id: str
    merchant_id: str
    amount: Decimal
    currency: str
    status: str = "active"  # active, captured, voided, expired
    purpose: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    captured_at: Optional[datetime] = None
    voided_at: Optional[datetime] = None
    capture_tx_id: Optional[str] = None


class PaymentService:
    """
    Service for processing payments from agents to merchants.
    
    This is the main entry point for executing payments, handling:
    - Idempotency for safe retries
    - Limit validation
    - Fee calculation
    - Pre-authorization (hold, capture, void)
    - Refunds (full and partial)
    - Ledger transfers
    - Transaction recording
    - Webhook event emission
    """
    
    # Hold expiration time (default 7 days)
    HOLD_EXPIRATION_HOURS = 168
    
    # Idempotency key expiration (24 hours)
    IDEMPOTENCY_EXPIRATION_HOURS = 24
    
    def __init__(
        self,
        ledger: InMemoryLedger,
        wallet_service: WalletService,
        fee_service: Optional[FeeService] = None,
        webhook_manager = None
    ):
        """
        Initialize the payment service.
        
        Args:
            ledger: The ledger for executing transfers
            wallet_service: Service for wallet operations
            fee_service: Optional fee service (uses default if not provided)
            webhook_manager: Optional webhook manager for event emission
        """
        self._ledger = ledger
        self._wallet_service = wallet_service
        self._fee_service = fee_service or FeeService()
        self._webhook_manager = webhook_manager
        self._lock = asyncio.Lock()
        
        # Idempotency cache: key -> (result, timestamp)
        self._idempotency_cache: dict[str, tuple[PaymentResult, datetime]] = {}
        
        # Payment holds: hold_id -> PaymentHold
        self._holds: dict[str, PaymentHold] = {}
        
        # Refund tracking: original_tx_id -> list of refund amounts
        self._refunds: dict[str, list[Decimal]] = {}
    
    async def pay(
        self,
        agent_id: str,
        amount: Decimal,
        recipient_wallet_id: str,
        currency: str = "USDC",
        purpose: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        execute_on_chain: bool = False,
        chain: str = "base"
    ) -> PaymentResult:
        """
        Process a payment from an agent to a recipient.
        
        This is the primary method for executing payments:
        1. Check idempotency key for duplicate requests
        2. Validates the agent exists and has a wallet
        3. Calculates the fee
        4. Checks spending limits
        5. Executes the transfer on the ledger
        6. Emits webhook events
        
        Args:
            agent_id: The agent making the payment
            amount: Payment amount
            recipient_wallet_id: Wallet ID to receive payment
            currency: Currency code (default: USDC)
            purpose: Optional payment description
            idempotency_key: Optional key for idempotent retries
            
        Returns:
            PaymentResult with success status and transaction details
        """
        # Check idempotency
        if idempotency_key:
            cached_result = self._check_idempotency(idempotency_key)
            if cached_result:
                return cached_result
        
        # Validate amount
        if amount <= Decimal("0"):
            return PaymentResult.failed("Amount must be positive")
        
        # Get agent wallet
        wallet = await self._wallet_service.get_agent_wallet(agent_id)
        if not wallet:
            return PaymentResult.failed(f"Wallet not found for agent {agent_id}")
        
        # Calculate fee
        fee = self._fee_service.calculate_fee(amount, currency)
        
        # Check spending limits
        can_spend, reason = wallet.can_spend(amount, fee)
        if not can_spend:
            result = PaymentResult.failed(reason)
            self._emit_payment_event("payment.failed", None, error=reason)
            return result
        
        # Determine actual recipient for ledger transfer
        ledger_recipient_id = recipient_wallet_id
        if execute_on_chain:
            # If on-chain, we move funds to settlement wallet
            ledger_recipient_id = settings.settlement_wallet_id
            
            # Validate recipient_wallet_id is an address
            if not recipient_wallet_id.startswith("0x"):
                 return PaymentResult.failed("Recipient must be a valid 0x address for on-chain payment")

        # Execute transfer on ledger
        try:
            transaction = await self._ledger.transfer(
                from_wallet_id=wallet.wallet_id,
                to_wallet_id=ledger_recipient_id,
                amount=amount,
                fee=fee,
                currency=currency,
                purpose=purpose
            )
            
            # If on-chain, execute blockchain tx
            if execute_on_chain:
                try:
                    # TODO: Get token address from config based on currency/chain
                    # For MVP, assuming USDC on Base Sepolia
                    token_address = "0x036CbD53842c5426634e7929541eC2318f3dCF7e" # Base Sepolia USDC
                    
                    tx_hash = await blockchain_service.transfer_token(
                        chain=chain,
                        token_address=token_address,
                        to_address=recipient_wallet_id,
                        amount_units=int(amount * 10**6), # USDC has 6 decimals
                        private_key=settings.relayer_private_key
                    )
                    
                    # Update transaction with hash
                    record = OnChainRecord(
                        chain=chain,
                        tx_hash=tx_hash,
                        from_address="relayer", # TODO: Use actual relayer address
                        to_address=recipient_wallet_id,
                        status="pending"
                    )
                    transaction.add_on_chain_record(record)
                    
                except Exception as e:
                    # TODO: Refund the ledger transfer if blockchain fails
                    # await self.refund(transaction.tx_id, reason="Blockchain failure")
                    raise e

            result = PaymentResult.succeeded(transaction, idempotency_key)
            
            # Cache idempotency result
            if idempotency_key:
                self._cache_idempotency(idempotency_key, result)
            
            # Emit success event
            self._emit_payment_event("payment.completed", transaction)
            
            return result
            
        except ValueError as e:
            result = PaymentResult.failed(str(e))
            self._emit_payment_event("payment.failed", None, error=str(e))
            return result
        except Exception as e:
            result = PaymentResult.failed(f"Payment failed: {str(e)}")
            self._emit_payment_event("payment.failed", None, error=str(e))
            return result
    
    async def pay_merchant(
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
        
        return await self.pay(
            agent_id=agent_id,
            amount=amount,
            recipient_wallet_id=merchant.wallet_id,
            currency=currency,
            purpose=purpose or f"Payment to {merchant.name}"
        )
    
    async def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """Get a transaction by ID."""
        return await self._ledger.get_transaction(tx_id)
    
    async def list_agent_transactions(
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
        wallet = await self._wallet_service.get_agent_wallet(agent_id)
        if not wallet:
            return []
        
        return await self._ledger.list_transactions(wallet.wallet_id, limit, offset)
    
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
    
    # ==================== Pre-Authorization (Hold/Capture/Void) ====================
    
    async def create_hold(
        self,
        agent_id: str,
        merchant_id: str,
        amount: Decimal,
        currency: str = "USDC",
        purpose: Optional[str] = None,
        expiration_hours: Optional[int] = None
    ) -> HoldResult:
        """
        Create a pre-authorization hold on funds.
        
        The hold reserves funds without transferring them. The merchant
        can later capture (complete) or void (cancel) the hold.
        
        Args:
            agent_id: Agent to hold funds from
            merchant_id: Merchant this hold is for
            amount: Amount to hold
            currency: Currency code
            purpose: Optional description
            expiration_hours: Hours until hold expires (default: 168 / 7 days)
            
        Returns:
            HoldResult with hold details
        """
        if amount <= Decimal("0"):
            return HoldResult.failed("Amount must be positive")
        
        # Get agent wallet
        wallet = await self._wallet_service.get_agent_wallet(agent_id)
        if not wallet:
            return HoldResult.failed(f"Wallet not found for agent {agent_id}")
        
        # Verify merchant exists
        merchant = self._wallet_service.get_merchant(merchant_id)
        if not merchant:
            return HoldResult.failed(f"Merchant {merchant_id} not found")
        
        # Calculate fee for estimation
        fee = self._fee_service.calculate_fee(amount, currency)
        total_hold = amount + fee
        
        # Check if agent can afford the hold
        can_spend, reason = wallet.can_spend(amount, fee)
        if not can_spend:
            return HoldResult.failed(reason)
        
        # Calculate expiration
        hours = expiration_hours or self.HOLD_EXPIRATION_HOURS
        expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        
        # Create the hold
        hold_id = f"hold_{uuid.uuid4().hex[:16]}"
        
        async with self._lock:
            hold = PaymentHold(
                hold_id=hold_id,
                agent_id=agent_id,
                wallet_id=wallet.wallet_id,
                merchant_id=merchant_id,
                amount=amount,
                currency=currency,
                purpose=purpose,
                expires_at=expires_at,
            )
            self._holds[hold_id] = hold
            
            # Reserve funds (increase spent_total to reduce available)
            # This doesn't actually transfer, just reserves
            wallet.spent_total += amount
            await self._ledger.update_wallet(wallet)
        
        self._emit_payment_event("hold.created", None, hold=hold)
        
        return HoldResult.succeeded(
            hold_id=hold_id,
            agent_id=agent_id,
            amount=amount,
            currency=currency,
            merchant_id=merchant_id,
            expires_at=expires_at,
        )
    
    async def capture_hold(
        self,
        hold_id: str,
        amount: Optional[Decimal] = None,
        purpose: Optional[str] = None
    ) -> PaymentResult:
        """
        Capture (complete) a pre-authorization hold.
        
        Transfers the held funds to the merchant. Can capture
        less than the held amount (partial capture).
        
        Args:
            hold_id: The hold to capture
            amount: Amount to capture (default: full hold amount)
            purpose: Optional updated purpose
            
        Returns:
            PaymentResult with the completed transaction
        """
        async with self._lock:
            hold = self._holds.get(hold_id)
            if not hold:
                return PaymentResult.failed(f"Hold {hold_id} not found")
            
            if hold.status != "active":
                return PaymentResult.failed(f"Hold is {hold.status}, cannot capture")
            
            # Check expiration
            if hold.expires_at and datetime.now(timezone.utc) > hold.expires_at:
                hold.status = "expired"
                return PaymentResult.failed("Hold has expired")
            
            capture_amount = amount if amount is not None else hold.amount
            if capture_amount > hold.amount:
                return PaymentResult.failed(
                    f"Capture amount {capture_amount} exceeds hold amount {hold.amount}"
                )
            
            # Get merchant wallet
            merchant = self._wallet_service.get_merchant(hold.merchant_id)
            if not merchant or not merchant.wallet_id:
                return PaymentResult.failed(f"Merchant wallet not found")
            
            # Release the hold reservation
            wallet = await self._wallet_service.get_agent_wallet(hold.agent_id)
            if wallet:
                wallet.spent_total -= hold.amount
                await self._ledger.update_wallet(wallet)
            
            # Execute the actual payment
            result = await self.pay(
                agent_id=hold.agent_id,
                amount=capture_amount,
                recipient_wallet_id=merchant.wallet_id,
                currency=hold.currency,
                purpose=purpose or hold.purpose or f"Capture of hold {hold_id}",
            )
            
            if result.success:
                hold.status = "captured"
                hold.captured_at = datetime.now(timezone.utc)
                hold.capture_tx_id = result.transaction.tx_id
                self._emit_payment_event("hold.captured", result.transaction, hold=hold)
            else:
                # Restore the hold if capture failed
                if wallet:
                    wallet.spent_total += hold.amount
                    await self._ledger.update_wallet(wallet)
            
            return result
    
    async def void_hold(self, hold_id: str) -> HoldResult:
        """
        Void (cancel) a pre-authorization hold.
        
        Releases the reserved funds back to the agent.
        
        Args:
            hold_id: The hold to void
            
        Returns:
            HoldResult indicating success
        """
        async with self._lock:
            hold = self._holds.get(hold_id)
            if not hold:
                return HoldResult.failed(f"Hold {hold_id} not found")
            
            if hold.status != "active":
                return HoldResult.failed(f"Hold is {hold.status}, cannot void")
            
            # Release the hold reservation
            wallet = await self._wallet_service.get_agent_wallet(hold.agent_id)
            if wallet:
                wallet.spent_total -= hold.amount
                await self._ledger.update_wallet(wallet)
            
            hold.status = "voided"
            hold.voided_at = datetime.now(timezone.utc)
            
            self._emit_payment_event("hold.voided", None, hold=hold)
            
            return HoldResult.succeeded(
                hold_id=hold_id,
                agent_id=hold.agent_id,
                amount=hold.amount,
                currency=hold.currency,
                merchant_id=hold.merchant_id,
                expires_at=hold.expires_at,
            )
    
    def get_hold(self, hold_id: str) -> Optional[PaymentHold]:
        """Get a hold by ID."""
        return self._holds.get(hold_id)
    
    def list_holds(
        self,
        agent_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> list[PaymentHold]:
        """List holds with optional filters."""
        holds = list(self._holds.values())
        
        if agent_id:
            holds = [h for h in holds if h.agent_id == agent_id]
        if merchant_id:
            holds = [h for h in holds if h.merchant_id == merchant_id]
        if status:
            holds = [h for h in holds if h.status == status]
        
        return holds
    
    # ==================== Refunds ====================
    
    async def refund(
        self,
        tx_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        """
        Refund a previous payment (full or partial).
        
        Creates a reverse transaction from the recipient back to the sender.
        Multiple partial refunds can be issued up to the original amount.
        
        Args:
            tx_id: Original transaction to refund
            amount: Amount to refund (None = full refund)
            reason: Optional reason for refund
            
        Returns:
            RefundResult with refund details
        """
        # Get original transaction
        original_tx = await self._ledger.get_transaction(tx_id)
        if not original_tx:
            return RefundResult.failed(f"Transaction {tx_id} not found")
        
        if original_tx.status != TransactionStatus.COMPLETED:
            return RefundResult.failed(
                f"Cannot refund transaction with status {original_tx.status.value}"
            )
        
        original_amount = original_tx.amount
        refund_amount = amount if amount is not None else original_amount
        
        if refund_amount <= Decimal("0"):
            return RefundResult.failed("Refund amount must be positive")
        
        # Check total refunds don't exceed original
        async with self._lock:
            previous_refunds = sum(self._refunds.get(tx_id, []))
            available_to_refund = original_amount - previous_refunds
            
            if refund_amount > available_to_refund:
                return RefundResult.failed(
                    f"Refund amount {refund_amount} exceeds available {available_to_refund}"
                )
            
            # Execute refund (reverse transfer)
            try:
                refund_tx = await self._ledger.transfer(
                    from_wallet_id=original_tx.to_wallet,
                    to_wallet_id=original_tx.from_wallet,
                    amount=refund_amount,
                    fee=Decimal("0"),  # No fee for refunds
                    currency=original_tx.currency,
                    purpose=reason or f"Refund of {tx_id}"
                )
                
                # Track refund
                if tx_id not in self._refunds:
                    self._refunds[tx_id] = []
                self._refunds[tx_id].append(refund_amount)
                
                # Update original transaction status if fully refunded
                if previous_refunds + refund_amount >= original_amount:
                    original_tx.status = TransactionStatus.REFUNDED
                
                refund_id = f"ref_{uuid.uuid4().hex[:16]}"
                
                self._emit_payment_event("payment.refunded", refund_tx, 
                                        original_tx_id=tx_id, refund_amount=refund_amount)
                
                return RefundResult.succeeded(
                    refund_id=refund_id,
                    original_tx_id=tx_id,
                    amount=refund_amount,
                    currency=original_tx.currency,
                )
                
            except ValueError as e:
                return RefundResult.failed(str(e))
            except Exception as e:
                return RefundResult.failed(f"Refund failed: {str(e)}")
    
    def get_refund_total(self, tx_id: str) -> Decimal:
        """Get total amount refunded for a transaction."""
        return sum(self._refunds.get(tx_id, []))
    
    async def get_refundable_amount(self, tx_id: str) -> Optional[Decimal]:
        """Get amount available for refund on a transaction."""
        tx = await self._ledger.get_transaction(tx_id)
        if not tx:
            return None
        return tx.amount - self.get_refund_total(tx_id)
    
    # ==================== Idempotency Helpers ====================
    
    def _check_idempotency(self, key: str) -> Optional[PaymentResult]:
        """Check if we have a cached result for this idempotency key."""
        with self._lock:
            if key in self._idempotency_cache:
                result, timestamp = self._idempotency_cache[key]
                expiry = timestamp + timedelta(hours=self.IDEMPOTENCY_EXPIRATION_HOURS)
                if datetime.now(timezone.utc) < expiry:
                    return result
                else:
                    # Expired, remove from cache
                    del self._idempotency_cache[key]
        return None
    
    def _cache_idempotency(self, key: str, result: PaymentResult) -> None:
        """Cache a result for idempotency."""
        with self._lock:
            self._idempotency_cache[key] = (result, datetime.now(timezone.utc))
            
            # Clean up old entries periodically
            self._cleanup_idempotency_cache()
    
    def _cleanup_idempotency_cache(self) -> None:
        """Remove expired idempotency entries."""
        now = datetime.now(timezone.utc)
        expiry_delta = timedelta(hours=self.IDEMPOTENCY_EXPIRATION_HOURS)
        
        expired_keys = [
            key for key, (_, timestamp) in self._idempotency_cache.items()
            if now > timestamp + expiry_delta
        ]
        
        for key in expired_keys:
            del self._idempotency_cache[key]
    
    # ==================== Webhook Helpers ====================
    
    def _emit_payment_event(
        self,
        event_type: str,
        transaction: Optional[Transaction],
        **kwargs
    ) -> None:
        """Emit a payment-related webhook event."""
        if not self._webhook_manager:
            return
        
        try:
            from sardis_core.webhooks.events import WebhookEvent, EventType
            
            # Map string event types to enum
            event_type_map = {
                "payment.initiated": EventType.PAYMENT_INITIATED,
                "payment.completed": EventType.PAYMENT_COMPLETED,
                "payment.failed": EventType.PAYMENT_FAILED,
                "payment.refunded": EventType.PAYMENT_REFUNDED,
                "hold.created": EventType.HOLD_CREATED,
                "hold.captured": EventType.HOLD_CAPTURED,
                "hold.voided": EventType.HOLD_VOIDED,
            }
            
            event_enum = event_type_map.get(event_type)
            if not event_enum:
                return
            
            # Build event data
            data = {}
            if transaction:
                data["transaction"] = {
                    "id": transaction.tx_id,
                    "from_wallet": transaction.from_wallet,
                    "to_wallet": transaction.to_wallet,
                    "amount": str(transaction.amount),
                    "fee": str(transaction.fee),
                    "currency": transaction.currency,
                    "status": transaction.status.value,
                }
            
            data.update(kwargs)
            
            event = WebhookEvent(event_type=event_enum, data=data)
            
            # Emit asynchronously (non-blocking)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._webhook_manager.emit(event))
                else:
                    asyncio.run(self._webhook_manager.emit(event))
            except RuntimeError:
                # No event loop, skip webhook
                pass
                
        except ImportError:
            # Webhook module not available
            pass
        except Exception:
            # Don't let webhook errors affect payment flow
            pass

