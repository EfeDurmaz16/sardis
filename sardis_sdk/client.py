"""Sardis SDK Client for integrating AI agents with Sardis payment infrastructure."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import httpx


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
    error_message: Optional[str]


@dataclass
class PaymentResult:
    """Result of a payment attempt."""
    success: bool
    transaction: Optional[TransactionInfo] = None
    error: Optional[str] = None


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
    - Execute payments
    - View transaction history
    - Browse product catalogs
    
    Example usage:
        ```python
        client = SardisClient(base_url="http://localhost:8000")
        
        # Check wallet balance
        wallet = client.get_wallet_info("agent_123")
        print(f"Balance: {wallet.balance} {wallet.currency}")
        
        # Make a payment
        result = client.pay(
            agent_id="agent_123",
            amount=Decimal("10.00"),
            merchant_id="merchant_456",
            purpose="Purchase product XYZ"
        )
        
        if result.success:
            print(f"Payment successful! TX: {result.transaction.tx_id}")
        else:
            print(f"Payment failed: {result.error}")
        ```
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_prefix: str = "/api/v1",
        timeout: float = 30.0
    ):
        """
        Initialize the Sardis client.
        
        Args:
            base_url: Base URL of the Sardis API server
            api_prefix: API version prefix
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
    
    def _url(self, path: str) -> str:
        """Build full URL for an API path."""
        return f"{self.base_url}{self.api_prefix}{path}"
    
    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response and raise errors if needed."""
        if response.status_code >= 400:
            try:
                error_detail = response.json().get("detail", "Unknown error")
            except Exception:
                error_detail = response.text
            raise Exception(f"API error ({response.status_code}): {error_detail}")
        return response.json()
    
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
        purpose: Optional[str] = None
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
        
        try:
            response = self._client.post(self._url("/payments"), json=payload)
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
                error=data.get("error")
            )
            
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
        response = self._client.get(
            self._url("/payments/estimate"),
            params={"amount": str(amount), "currency": currency}
        )
        return self._handle_response(response)
    
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
        response = self._client.get(
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
        
        response = self._client.get(
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
        response = self._client.get(self._url(f"/catalog/products/{product_id}"))
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
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()

