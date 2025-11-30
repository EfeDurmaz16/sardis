"""Sardis SDK Client for integrating AI agents with Sardis payment infrastructure."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Callable
import hashlib
import hmac
import time
import httpx


# ==================== Custom Exceptions ====================

class SardisError(Exception):
    """Base exception for Sardis SDK errors."""
    pass


class SardisAPIError(SardisError):
    """Error from the Sardis API."""
    def __init__(self, status_code: int, message: str, error_code: Optional[str] = None):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        super().__init__(f"API error ({status_code}): {message}")


class InsufficientFundsError(SardisError):
    """Agent has insufficient funds for the operation."""
    def __init__(self, required: Decimal, available: Decimal):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient funds: need {required}, have {available}")


class LimitExceededError(SardisError):
    """Transaction exceeds spending limits."""
    def __init__(self, limit_type: str, limit_value: Decimal, attempted: Decimal):
        self.limit_type = limit_type
        self.limit_value = limit_value
        self.attempted = attempted
        super().__init__(f"{limit_type} limit exceeded: limit is {limit_value}, attempted {attempted}")


class TransactionNotFoundError(SardisError):
    """Transaction was not found."""
    def __init__(self, tx_id: str):
        self.tx_id = tx_id
        super().__init__(f"Transaction not found: {tx_id}")


class RefundError(SardisError):
    """Error during refund processing."""
    pass


class HoldError(SardisError):
    """Error during hold (pre-auth) processing."""
    pass


class RateLimitError(SardisError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after} seconds"
        super().__init__(msg)


# ==================== Data Classes ====================

@dataclass
class WalletInfo:
    """Wallet information returned from Sardis API."""
    wallet_id: str
    agent_id: str
    balance: Decimal
    currency: str
    limit_per_tx: Decimal
    limit_total: Decimal
    spent_total: Decimal
    remaining_limit: Decimal
    is_active: bool
    virtual_card_number: Optional[str] = None


@dataclass
class TransactionInfo:
    """Transaction information returned from Sardis API."""
    tx_id: str
    from_wallet: str
    to_wallet: str
    amount: Decimal
    fee: Decimal
    total_cost: Decimal
    currency: str
    purpose: Optional[str]
    status: str
    error_message: Optional[str] = None


@dataclass
class PaymentResult:
    """Result of a payment attempt."""
    success: bool
    transaction: Optional[TransactionInfo] = None
    error: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass
class RefundResult:
    """Result of a refund operation."""
    success: bool
    refund_id: Optional[str] = None
    original_tx_id: Optional[str] = None
    amount: Optional[Decimal] = None
    error: Optional[str] = None


@dataclass
class HoldResult:
    """Result of a pre-authorization hold."""
    success: bool
    hold_id: Optional[str] = None
    amount: Optional[Decimal] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class PaymentRequest:
    """A payment request (invoice) from another party."""
    request_id: str
    from_agent_id: Optional[str]
    amount: Decimal
    currency: str
    description: Optional[str]
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None


@dataclass
class Product:
    """Product from the catalog."""
    product_id: str
    name: str
    description: str
    price: Decimal
    currency: str
    category: str
    in_stock: bool
    merchant_id: str


class SardisClient:
    """
    SDK client for interacting with Sardis payment infrastructure.
    
    This client provides a simple interface for AI agents to:
    - Check wallet balances and limits
    - Execute payments with idempotency
    - Request refunds (full or partial)
    - Create and manage holds (pre-authorizations)
    - Request payments from other agents (invoices)
    - View transaction history
    - Browse product catalogs
    
    Features:
    - Automatic retry with exponential backoff
    - Custom exception types for error handling
    - Webhook signature verification
    - Idempotency key support
    
    Example usage:
        ```python
        client = SardisClient(base_url="http://localhost:8000")
        
        # Check wallet balance
        wallet = client.get_wallet_info("agent_123")
        print(f"Balance: {wallet.balance} {wallet.currency}")
        
        # Make a payment with idempotency
        result = client.pay(
            agent_id="agent_123",
            amount=Decimal("10.00"),
            merchant_id="merchant_456",
            purpose="Purchase product XYZ",
            idempotency_key="unique-key-123"
        )
        
        if result.success:
            print(f"Payment successful! TX: {result.transaction.tx_id}")
        else:
            print(f"Payment failed: {result.error}")
        
        # Request a refund
        refund = client.refund(result.transaction.tx_id)
        ```
    """
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 1.0
    RETRY_BACKOFF_MULTIPLIER = 2.0
    RETRYABLE_STATUS_CODES = {502, 503, 504}
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_prefix: str = "/api/v1",
        timeout: float = 30.0,
        max_retries: int = 3,
        webhook_secret: Optional[str] = None
    ):
        """
        Initialize the Sardis client.
        
        Args:
            base_url: Base URL of the Sardis API server
            api_prefix: API version prefix
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            webhook_secret: Secret for verifying webhook signatures
        """
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix
        self.timeout = timeout
        self.max_retries = max_retries
        self.webhook_secret = webhook_secret
        self._client = httpx.Client(timeout=timeout)
    
    def _url(self, path: str) -> str:
        """Build full URL for an API path."""
        return f"{self.base_url}{self.api_prefix}{path}"
    
    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response and raise appropriate exceptions."""
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(int(retry_after) if retry_after else None)
        
        if response.status_code >= 400:
            try:
                data = response.json()
                error_detail = data.get("detail", "Unknown error")
                error_code = data.get("code")
                
                # Map to specific exceptions
                if "insufficient" in error_detail.lower():
                    # Parse amounts if available
                    raise InsufficientFundsError(
                        required=Decimal("0"),
                        available=Decimal("0")
                    )
                if "limit" in error_detail.lower() and "exceeded" in error_detail.lower():
                    raise LimitExceededError("spending", Decimal("0"), Decimal("0"))
                if "not found" in error_detail.lower() and "transaction" in error_detail.lower():
                    raise TransactionNotFoundError("")
                
            except (SardisError):
                raise
            except Exception:
                error_detail = response.text
                error_code = None
            
            raise SardisAPIError(response.status_code, error_detail, error_code)
        
        return response.json()
    
    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make a request with automatic retry on transient failures."""
        last_exception = None
        delay = self.RETRY_DELAY_SECONDS
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(method, url, **kwargs)
                
                # Retry on specific status codes
                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    if attempt < self.max_retries:
                        time.sleep(delay)
                        delay *= self.RETRY_BACKOFF_MULTIPLIER
                        continue
                
                return response
                
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= self.RETRY_BACKOFF_MULTIPLIER
                    continue
                raise SardisError(f"Request timed out after {self.max_retries} retries")
            
            except httpx.NetworkError as e:
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= self.RETRY_BACKOFF_MULTIPLIER
                    continue
                raise SardisError(f"Network error after {self.max_retries} retries: {e}")
        
        raise SardisError(f"Max retries exceeded: {last_exception}")
    
    # ========== Agent/Wallet Methods ==========
    
    def get_wallet_info(self, agent_id: str) -> WalletInfo:
        """
        Get wallet information for an agent.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            WalletInfo with balance and limits
        """
        response = self._client.get(self._url(f"/agents/{agent_id}/wallet"))
        data = self._handle_response(response)
        
        return WalletInfo(
            wallet_id=data["wallet_id"],
            agent_id=data["agent_id"],
            balance=Decimal(data["balance"]),
            currency=data["currency"],
            limit_per_tx=Decimal(data["limit_per_tx"]),
            limit_total=Decimal(data["limit_total"]),
            spent_total=Decimal(data["spent_total"]),
            remaining_limit=Decimal(data["remaining_limit"]),
            is_active=data["is_active"],
            virtual_card_number=data.get("virtual_card", {}).get("masked_number") if data.get("virtual_card") else None
        )
    
    def get_balance(self, agent_id: str) -> Decimal:
        """
        Get just the current balance for an agent.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            Current balance as Decimal
        """
        wallet = self.get_wallet_info(agent_id)
        return wallet.balance
    
    def can_afford(self, agent_id: str, amount: Decimal) -> bool:
        """
        Check if an agent can afford a purchase.
        
        Args:
            agent_id: The agent ID
            amount: Amount to check
            
        Returns:
            True if agent has sufficient balance and limits
        """
        try:
            wallet = self.get_wallet_info(agent_id)
            # Check both balance and limits
            # Add estimated fee (0.10 USDC)
            estimated_fee = Decimal("0.10")
            total_needed = amount + estimated_fee
            
            return (
                wallet.balance >= total_needed and
                amount <= wallet.limit_per_tx and
                amount <= wallet.remaining_limit
            )
        except Exception:
            return False
    
    # ========== Payment Methods ==========
    
    def pay(
        self,
        agent_id: str,
        amount: Decimal,
        merchant_id: Optional[str] = None,
        recipient_wallet_id: Optional[str] = None,
        currency: str = "USDC",
        purpose: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> PaymentResult:
        """
        Execute a payment from an agent.
        
        Args:
            agent_id: The agent making the payment
            amount: Payment amount
            merchant_id: Merchant to pay (use this OR recipient_wallet_id)
            recipient_wallet_id: Direct wallet to pay
            currency: Currency code (default: USDC)
            purpose: Optional payment description
            idempotency_key: Optional key for safe retries
            
        Returns:
            PaymentResult with success status and transaction details
        """
        if not merchant_id and not recipient_wallet_id:
            return PaymentResult(
                success=False,
                error="Must specify either merchant_id or recipient_wallet_id"
            )
        
        payload = {
            "agent_id": agent_id,
            "amount": str(amount),
            "currency": currency,
        }
        
        if merchant_id:
            payload["merchant_id"] = merchant_id
        if recipient_wallet_id:
            payload["recipient_wallet_id"] = recipient_wallet_id
        if purpose:
            payload["purpose"] = purpose
        
        headers = {}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        
        try:
            response = self._request_with_retry(
                "POST", self._url("/payments"), json=payload, headers=headers
            )
            data = self._handle_response(response)
            
            tx_info = None
            if data.get("transaction"):
                tx = data["transaction"]
                tx_info = TransactionInfo(
                    tx_id=tx["tx_id"],
                    from_wallet=tx["from_wallet"],
                    to_wallet=tx["to_wallet"],
                    amount=Decimal(tx["amount"]),
                    fee=Decimal(tx["fee"]),
                    total_cost=Decimal(tx["total_cost"]),
                    currency=tx["currency"],
                    purpose=tx.get("purpose"),
                    status=tx["status"],
                    error_message=tx.get("error_message")
                )
            
            return PaymentResult(
                success=data["success"],
                transaction=tx_info,
                error=data.get("error"),
                idempotency_key=idempotency_key
            )
            
        except SardisError:
            raise
        except Exception as e:
            return PaymentResult(success=False, error=str(e))
    
    def estimate_payment(
        self,
        amount: Decimal,
        currency: str = "USDC"
    ) -> dict:
        """
        Estimate the total cost of a payment including fees.
        
        Args:
            amount: Payment amount
            currency: Currency code
            
        Returns:
            Dict with amount, fee, and total
        """
        response = self._request_with_retry(
            "GET",
            self._url("/payments/estimate"),
            params={"amount": str(amount), "currency": currency}
        )
        return self._handle_response(response)
    
    # ========== Refund Methods ==========
    
    def refund(
        self,
        tx_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        """
        Refund a previous payment (full or partial).
        
        Args:
            tx_id: Transaction ID to refund
            amount: Amount to refund (None = full refund)
            reason: Optional reason for the refund
            
        Returns:
            RefundResult with status
            
        Raises:
            TransactionNotFoundError: If transaction doesn't exist
            RefundError: If refund fails
        """
        payload = {"reason": reason}
        if amount is not None:
            payload["amount"] = str(amount)
        
        try:
            response = self._request_with_retry(
                "POST",
                self._url(f"/payments/{tx_id}/refund"),
                json=payload
            )
            data = self._handle_response(response)
            
            return RefundResult(
                success=data.get("success", True),
                refund_id=data.get("refund_id"),
                original_tx_id=tx_id,
                amount=Decimal(data["amount"]) if data.get("amount") else amount,
                error=data.get("error")
            )
            
        except TransactionNotFoundError:
            raise
        except SardisAPIError as e:
            raise RefundError(str(e))
        except Exception as e:
            return RefundResult(success=False, error=str(e))
    
    def get_refundable_amount(self, tx_id: str) -> Decimal:
        """
        Get the amount available for refund on a transaction.
        
        Args:
            tx_id: Transaction ID
            
        Returns:
            Amount that can still be refunded
        """
        response = self._request_with_retry(
            "GET",
            self._url(f"/payments/{tx_id}/refundable")
        )
        data = self._handle_response(response)
        return Decimal(data["refundable_amount"])
    
    # ========== Hold (Pre-Authorization) Methods ==========
    
    def create_hold(
        self,
        agent_id: str,
        merchant_id: str,
        amount: Decimal,
        currency: str = "USDC",
        purpose: Optional[str] = None
    ) -> HoldResult:
        """
        Create a pre-authorization hold on funds.
        
        Reserves funds without transferring. The hold can later
        be captured (to complete payment) or voided (to release).
        
        Args:
            agent_id: Agent to hold funds from
            merchant_id: Merchant this hold is for
            amount: Amount to hold
            currency: Currency code
            purpose: Optional description
            
        Returns:
            HoldResult with hold_id if successful
        """
        payload = {
            "agent_id": agent_id,
            "merchant_id": merchant_id,
            "amount": str(amount),
            "currency": currency,
        }
        if purpose:
            payload["purpose"] = purpose
        
        try:
            response = self._request_with_retry(
                "POST",
                self._url("/payments/holds"),
                json=payload
            )
            data = self._handle_response(response)
            
            expires_at = None
            if data.get("expires_at"):
                expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
            
            return HoldResult(
                success=data.get("success", True),
                hold_id=data.get("hold_id"),
                amount=Decimal(data["amount"]) if data.get("amount") else amount,
                expires_at=expires_at,
                error=data.get("error")
            )
            
        except SardisAPIError as e:
            raise HoldError(str(e))
        except Exception as e:
            return HoldResult(success=False, error=str(e))
    
    def capture_hold(
        self,
        hold_id: str,
        amount: Optional[Decimal] = None
    ) -> PaymentResult:
        """
        Capture (complete) a pre-authorization hold.
        
        Args:
            hold_id: Hold to capture
            amount: Amount to capture (None = full amount)
            
        Returns:
            PaymentResult with completed transaction
        """
        payload = {}
        if amount is not None:
            payload["amount"] = str(amount)
        
        try:
            response = self._request_with_retry(
                "POST",
                self._url(f"/payments/holds/{hold_id}/capture"),
                json=payload
            )
            data = self._handle_response(response)
            
            tx_info = None
            if data.get("transaction"):
                tx = data["transaction"]
                tx_info = TransactionInfo(
                    tx_id=tx["tx_id"],
                    from_wallet=tx["from_wallet"],
                    to_wallet=tx["to_wallet"],
                    amount=Decimal(tx["amount"]),
                    fee=Decimal(tx["fee"]),
                    total_cost=Decimal(tx["total_cost"]),
                    currency=tx["currency"],
                    purpose=tx.get("purpose"),
                    status=tx["status"]
                )
            
            return PaymentResult(
                success=data.get("success", True),
                transaction=tx_info,
                error=data.get("error")
            )
            
        except SardisAPIError as e:
            raise HoldError(str(e))
        except Exception as e:
            return PaymentResult(success=False, error=str(e))
    
    def void_hold(self, hold_id: str) -> HoldResult:
        """
        Void (cancel) a pre-authorization hold.
        
        Args:
            hold_id: Hold to void
            
        Returns:
            HoldResult indicating success
        """
        try:
            response = self._request_with_retry(
                "POST",
                self._url(f"/payments/holds/{hold_id}/void")
            )
            data = self._handle_response(response)
            
            return HoldResult(
                success=data.get("success", True),
                hold_id=hold_id,
                amount=Decimal(data["amount"]) if data.get("amount") else None,
                error=data.get("error")
            )
            
        except Exception as e:
            return HoldResult(success=False, error=str(e))
    
    # ========== Payment Request Methods ==========
    
    def request_payment(
        self,
        from_agent_id: Optional[str],
        amount: Decimal,
        description: Optional[str] = None,
        currency: str = "USDC",
        expires_in_hours: int = 24
    ) -> PaymentRequest:
        """
        Create a payment request (invoice) for another agent.
        
        Args:
            from_agent_id: Specific agent to request from (None = any)
            amount: Amount to request
            description: Description of what the payment is for
            currency: Currency code
            expires_in_hours: Hours until request expires
            
        Returns:
            PaymentRequest object
        """
        payload = {
            "amount": str(amount),
            "currency": currency,
            "expires_in_hours": expires_in_hours,
        }
        if from_agent_id:
            payload["from_agent_id"] = from_agent_id
        if description:
            payload["description"] = description
        
        response = self._request_with_retry(
            "POST",
            self._url("/payments/requests"),
            json=payload
        )
        data = self._handle_response(response)
        
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        
        return PaymentRequest(
            request_id=data["request_id"],
            from_agent_id=data.get("from_agent_id"),
            amount=Decimal(data["amount"]),
            currency=data["currency"],
            description=data.get("description"),
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            expires_at=expires_at
        )
    
    def get_payment_request(self, request_id: str) -> PaymentRequest:
        """Get a payment request by ID."""
        response = self._request_with_retry(
            "GET",
            self._url(f"/payments/requests/{request_id}")
        )
        data = self._handle_response(response)
        
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        
        return PaymentRequest(
            request_id=data["request_id"],
            from_agent_id=data.get("from_agent_id"),
            amount=Decimal(data["amount"]),
            currency=data["currency"],
            description=data.get("description"),
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            expires_at=expires_at
        )
    
    def pay_payment_request(
        self,
        request_id: str,
        agent_id: str
    ) -> PaymentResult:
        """
        Pay a payment request.
        
        Args:
            request_id: Payment request to fulfill
            agent_id: Agent making the payment
            
        Returns:
            PaymentResult with transaction details
        """
        payload = {"agent_id": agent_id}
        
        try:
            response = self._request_with_retry(
                "POST",
                self._url(f"/payments/requests/{request_id}/pay"),
                json=payload
            )
            data = self._handle_response(response)
            
            tx_info = None
            if data.get("transaction"):
                tx = data["transaction"]
                tx_info = TransactionInfo(
                    tx_id=tx["tx_id"],
                    from_wallet=tx["from_wallet"],
                    to_wallet=tx["to_wallet"],
                    amount=Decimal(tx["amount"]),
                    fee=Decimal(tx["fee"]),
                    total_cost=Decimal(tx["total_cost"]),
                    currency=tx["currency"],
                    purpose=tx.get("purpose"),
                    status=tx["status"]
                )
            
            return PaymentResult(
                success=data.get("success", True),
                transaction=tx_info,
                error=data.get("error")
            )
            
        except Exception as e:
            return PaymentResult(success=False, error=str(e))
    
    # ========== Service Authorization ==========
    
    def authorize_service(
        self,
        agent_id: str,
        service_id: str
    ) -> bool:
        """
        Authorize a service for an agent.
        
        Pre-authorizing services reduces risk scoring.
        
        Args:
            agent_id: Agent to authorize for
            service_id: Service/merchant to authorize
            
        Returns:
            True if successful
        """
        response = self._request_with_retry(
            "POST",
            self._url(f"/risk/agents/{agent_id}/authorize"),
            json={"service_id": service_id}
        )
        data = self._handle_response(response)
        return data.get("success", True)
    
    def revoke_service(
        self,
        agent_id: str,
        service_id: str
    ) -> bool:
        """Revoke a previously authorized service."""
        response = self._request_with_retry(
            "POST",
            self._url(f"/risk/agents/{agent_id}/revoke"),
            json={"service_id": service_id}
        )
        data = self._handle_response(response)
        return data.get("success", True)
    
    def list_transactions(
        self,
        agent_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list[TransactionInfo]:
        """
        List transactions for an agent.
        
        Args:
            agent_id: The agent ID
            limit: Maximum transactions to return
            offset: Pagination offset
            
        Returns:
            List of TransactionInfo objects
        """
        response = self._request_with_retry(
            "GET",
            self._url(f"/payments/agent/{agent_id}"),
            params={"limit": limit, "offset": offset}
        )
        data = self._handle_response(response)
        
        return [
            TransactionInfo(
                tx_id=tx["tx_id"],
                from_wallet=tx["from_wallet"],
                to_wallet=tx["to_wallet"],
                amount=Decimal(tx["amount"]),
                fee=Decimal(tx["fee"]),
                total_cost=Decimal(tx["total_cost"]),
                currency=tx["currency"],
                purpose=tx.get("purpose"),
                status=tx["status"],
                error_message=tx.get("error_message")
            )
            for tx in data
        ]
    
    def get_transaction(self, tx_id: str) -> TransactionInfo:
        """
        Get a specific transaction by ID.
        
        Args:
            tx_id: Transaction ID
            
        Returns:
            TransactionInfo object
            
        Raises:
            TransactionNotFoundError: If transaction doesn't exist
        """
        response = self._request_with_retry(
            "GET",
            self._url(f"/payments/{tx_id}")
        )
        tx = self._handle_response(response)
        
        return TransactionInfo(
            tx_id=tx["tx_id"],
            from_wallet=tx["from_wallet"],
            to_wallet=tx["to_wallet"],
            amount=Decimal(tx["amount"]),
            fee=Decimal(tx["fee"]),
            total_cost=Decimal(tx["total_cost"]),
            currency=tx["currency"],
            purpose=tx.get("purpose"),
            status=tx["status"],
            error_message=tx.get("error_message")
        )
    
    # ========== Catalog Methods ==========
    
    def list_products(
        self,
        category: Optional[str] = None,
        max_price: Optional[Decimal] = None,
        in_stock_only: bool = True
    ) -> list[Product]:
        """
        List products from the catalog.
        
        Args:
            category: Optional category filter
            max_price: Optional maximum price filter
            in_stock_only: Only return in-stock items
            
        Returns:
            List of Product objects
        """
        params = {"in_stock_only": in_stock_only}
        if category:
            params["category"] = category
        if max_price is not None:
            params["max_price"] = str(max_price)
        
        response = self._request_with_retry(
            "GET",
            self._url("/catalog/products"),
            params=params
        )
        data = self._handle_response(response)
        
        return [
            Product(
                product_id=p["product_id"],
                name=p["name"],
                description=p["description"],
                price=Decimal(p["price"]),
                currency=p["currency"],
                category=p["category"],
                in_stock=p["in_stock"],
                merchant_id=p["merchant_id"]
            )
            for p in data
        ]
    
    def get_product(self, product_id: str) -> Product:
        """
        Get a specific product by ID.
        
        Args:
            product_id: The product ID
            
        Returns:
            Product object
        """
        response = self._request_with_retry(
            "GET",
            self._url(f"/catalog/products/{product_id}")
        )
        p = self._handle_response(response)
        
        return Product(
            product_id=p["product_id"],
            name=p["name"],
            description=p["description"],
            price=Decimal(p["price"]),
            currency=p["currency"],
            category=p["category"],
            in_stock=p["in_stock"],
            merchant_id=p["merchant_id"]
        )
    
    # ========== Webhook Verification ==========
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None
    ) -> bool:
        """
        Verify a webhook signature.
        
        Use this to verify that webhooks are genuinely from Sardis.
        
        Args:
            payload: Raw request body
            signature: Signature from X-Sardis-Signature header
            timestamp: Optional timestamp from X-Sardis-Timestamp header
            
        Returns:
            True if signature is valid
            
        Raises:
            ValueError: If webhook_secret not configured
        """
        if not self.webhook_secret:
            raise ValueError("webhook_secret not configured")
        
        # Build the signed content
        if timestamp:
            signed_content = f"{timestamp}.".encode() + payload
        else:
            signed_content = payload
        
        # Compute expected signature
        expected = hmac.new(
            self.webhook_secret.encode(),
            signed_content,
            hashlib.sha256
        ).hexdigest()
        
        # Compare (timing-safe)
        return hmac.compare_digest(expected, signature)
    
    @staticmethod
    def compute_webhook_signature(
        payload: bytes,
        secret: str,
        timestamp: Optional[str] = None
    ) -> str:
        """
        Compute a webhook signature (for testing).
        
        Args:
            payload: Request body
            secret: Webhook secret
            timestamp: Optional timestamp
            
        Returns:
            Signature string
        """
        if timestamp:
            signed_content = f"{timestamp}.".encode() + payload
        else:
            signed_content = payload
        
        return hmac.new(
            secret.encode(),
            signed_content,
            hashlib.sha256
        ).hexdigest()
    
    # ========== Lifecycle ==========
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# ==================== Async Client ====================

class AsyncSardisClient:
    """
    Async version of the Sardis SDK client.
    
    Provides the same interface as SardisClient but with async methods.
    Use this for high-performance applications with many concurrent requests.
    
    Example:
        ```python
        async with AsyncSardisClient() as client:
            wallet = await client.get_wallet_info("agent_123")
            result = await client.pay(...)
        ```
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_prefix: str = "/api/v1",
        timeout: float = 30.0,
        max_retries: int = 3,
        webhook_secret: Optional[str] = None
    ):
        """Initialize the async client."""
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix
        self.timeout = timeout
        self.max_retries = max_retries
        self.webhook_secret = webhook_secret
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    def _url(self, path: str) -> str:
        """Build full URL for an API path."""
        return f"{self.base_url}{self.api_prefix}{path}"
    
    async def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response."""
        if response.status_code >= 400:
            try:
                data = response.json()
                error_detail = data.get("detail", "Unknown error")
            except Exception:
                error_detail = response.text
            raise SardisAPIError(response.status_code, error_detail)
        return response.json()
    
    async def get_wallet_info(self, agent_id: str) -> WalletInfo:
        """Get wallet information for an agent."""
        client = await self._get_client()
        response = await client.get(self._url(f"/agents/{agent_id}/wallet"))
        data = await self._handle_response(response)
        
        return WalletInfo(
            wallet_id=data["wallet_id"],
            agent_id=data["agent_id"],
            balance=Decimal(data["balance"]),
            currency=data["currency"],
            limit_per_tx=Decimal(data["limit_per_tx"]),
            limit_total=Decimal(data["limit_total"]),
            spent_total=Decimal(data["spent_total"]),
            remaining_limit=Decimal(data["remaining_limit"]),
            is_active=data["is_active"],
        )
    
    async def pay(
        self,
        agent_id: str,
        amount: Decimal,
        merchant_id: Optional[str] = None,
        recipient_wallet_id: Optional[str] = None,
        currency: str = "USDC",
        purpose: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> PaymentResult:
        """Execute a payment from an agent."""
        if not merchant_id and not recipient_wallet_id:
            return PaymentResult(
                success=False,
                error="Must specify either merchant_id or recipient_wallet_id"
            )
        
        payload = {
            "agent_id": agent_id,
            "amount": str(amount),
            "currency": currency,
        }
        
        if merchant_id:
            payload["merchant_id"] = merchant_id
        if recipient_wallet_id:
            payload["recipient_wallet_id"] = recipient_wallet_id
        if purpose:
            payload["purpose"] = purpose
        
        headers = {}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        
        try:
            client = await self._get_client()
            response = await client.post(
                self._url("/payments"),
                json=payload,
                headers=headers
            )
            data = await self._handle_response(response)
            
            tx_info = None
            if data.get("transaction"):
                tx = data["transaction"]
                tx_info = TransactionInfo(
                    tx_id=tx["tx_id"],
                    from_wallet=tx["from_wallet"],
                    to_wallet=tx["to_wallet"],
                    amount=Decimal(tx["amount"]),
                    fee=Decimal(tx["fee"]),
                    total_cost=Decimal(tx["total_cost"]),
                    currency=tx["currency"],
                    purpose=tx.get("purpose"),
                    status=tx["status"]
                )
            
            return PaymentResult(
                success=data["success"],
                transaction=tx_info,
                error=data.get("error"),
                idempotency_key=idempotency_key
            )
            
        except SardisError:
            raise
        except Exception as e:
            return PaymentResult(success=False, error=str(e))
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()

