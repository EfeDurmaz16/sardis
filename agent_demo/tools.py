"""LangChain tools for Sardis shopping agent."""

from decimal import Decimal
from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

from sardis_sdk import SardisClient


class BrowseProductsInput(BaseModel):
    """Input for browsing products."""
    category: Optional[str] = Field(None, description="Filter by category (e.g., 'electronics', 'office')")
    max_price: Optional[float] = Field(None, description="Maximum price filter in USDC")


class BrowseProductsTool(BaseTool):
    """Tool for browsing the product catalog."""
    
    name: str = "browse_products"
    description: str = """Browse available products in the catalog. 
    You can filter by category (e.g., 'electronics', 'office') and maximum price.
    Returns a list of products with their names, descriptions, and prices."""
    args_schema: Type[BaseModel] = BrowseProductsInput
    
    sardis_client: SardisClient = None
    
    def __init__(self, sardis_client: SardisClient, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
    
    def _run(
        self,
        category: Optional[str] = None,
        max_price: Optional[float] = None
    ) -> str:
        """Browse products with optional filters."""
        try:
            max_price_decimal = Decimal(str(max_price)) if max_price else None
            products = self.sardis_client.list_products(
                category=category,
                max_price=max_price_decimal
            )
            
            if not products:
                return "No products found matching the criteria."
            
            result = "Available products:\n\n"
            for p in products:
                result += f"- **{p.name}** (ID: {p.product_id})\n"
                result += f"  Price: {p.price} {p.currency}\n"
                result += f"  Category: {p.category}\n"
                result += f"  Description: {p.description}\n"
                result += f"  Merchant: {p.merchant_id}\n\n"
            
            return result
            
        except Exception as e:
            return f"Error browsing products: {str(e)}"


class CheckWalletInput(BaseModel):
    """Input for checking wallet balance."""
    pass  # No input needed, uses agent's wallet


class CheckWalletTool(BaseTool):
    """Tool for checking wallet balance and limits."""
    
    name: str = "check_wallet"
    description: str = """Check your current wallet balance and spending limits.
    Returns your available balance, per-transaction limit, and remaining spending limit."""
    args_schema: Type[BaseModel] = CheckWalletInput
    
    sardis_client: SardisClient = None
    agent_id: str = None
    
    def __init__(self, sardis_client: SardisClient, agent_id: str, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
        self.agent_id = agent_id
    
    def _run(self) -> str:
        """Check wallet balance and limits."""
        try:
            wallet = self.sardis_client.get_wallet_info(self.agent_id)
            
            return f"""Wallet Status:
- Balance: {wallet.balance} {wallet.currency}
- Per-Transaction Limit: {wallet.limit_per_tx} {wallet.currency}
- Total Spending Limit: {wallet.limit_total} {wallet.currency}
- Already Spent: {wallet.spent_total} {wallet.currency}
- Remaining Limit: {wallet.remaining_limit} {wallet.currency}
- Virtual Card: {wallet.virtual_card_number or 'N/A'}
- Active: {'Yes' if wallet.is_active else 'No'}"""
            
        except Exception as e:
            return f"Error checking wallet: {str(e)}"


class PurchaseProductInput(BaseModel):
    """Input for purchasing a product."""
    product_id: str = Field(..., description="The ID of the product to purchase (e.g., 'prod_001')")
    purpose: Optional[str] = Field(None, description="Optional note about the purchase")


class PurchaseProductTool(BaseTool):
    """Tool for purchasing a product."""
    
    name: str = "purchase_product"
    description: str = """Purchase a product by its ID. 
    This will deduct the product price plus a small transaction fee from your wallet.
    Make sure you have checked your wallet balance first to ensure you can afford the purchase."""
    args_schema: Type[BaseModel] = PurchaseProductInput
    
    sardis_client: SardisClient = None
    agent_id: str = None
    
    def __init__(self, sardis_client: SardisClient, agent_id: str, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
        self.agent_id = agent_id
    
    def _run(
        self,
        product_id: str,
        purpose: Optional[str] = None
    ) -> str:
        """Purchase a product."""
        try:
            # First get the product details
            product = self.sardis_client.get_product(product_id)
            
            # Check if we can afford it
            estimate = self.sardis_client.estimate_payment(product.price)
            
            if not self.sardis_client.can_afford(self.agent_id, product.price):
                wallet = self.sardis_client.get_wallet_info(self.agent_id)
                return f"""Cannot afford this purchase.
Product: {product.name} costs {product.price} {product.currency}
Estimated total with fee: {estimate['total']} {product.currency}
Your balance: {wallet.balance} {wallet.currency}
Your per-tx limit: {wallet.limit_per_tx} {wallet.currency}
Your remaining limit: {wallet.remaining_limit} {wallet.currency}"""
            
            # Execute the payment
            purchase_purpose = purpose or f"Purchase: {product.name}"
            result = self.sardis_client.pay(
                agent_id=self.agent_id,
                amount=product.price,
                merchant_id=product.merchant_id,
                purpose=purchase_purpose
            )
            
            if result.success:
                tx = result.transaction
                return f"""Purchase successful!

Product: {product.name}
Price: {tx.amount} {tx.currency}
Fee: {tx.fee} {tx.currency}
Total Paid: {tx.total_cost} {tx.currency}
Transaction ID: {tx.tx_id}
Status: {tx.status}"""
            else:
                return f"Purchase failed: {result.error}"
                
        except Exception as e:
            return f"Error making purchase: {str(e)}"


class GetTransactionHistoryInput(BaseModel):
    """Input for getting transaction history."""
    limit: int = Field(5, description="Number of transactions to retrieve")


class GetTransactionHistoryTool(BaseTool):
    """Tool for viewing transaction history."""
    
    name: str = "get_transaction_history"
    description: str = """View your recent transaction history.
    Returns details of your past purchases and payments."""
    args_schema: Type[BaseModel] = GetTransactionHistoryInput
    
    sardis_client: SardisClient = None
    agent_id: str = None
    
    def __init__(self, sardis_client: SardisClient, agent_id: str, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
        self.agent_id = agent_id
    
    def _run(self, limit: int = 5) -> str:
        """Get transaction history."""
        try:
            transactions = self.sardis_client.list_transactions(self.agent_id, limit=limit)
            
            if not transactions:
                return "No transactions found."
            
            result = f"Recent Transactions (last {len(transactions)}):\n\n"
            for tx in transactions:
                result += f"- Transaction: {tx.tx_id}\n"
                result += f"  Amount: {tx.amount} {tx.currency}\n"
                result += f"  Fee: {tx.fee} {tx.currency}\n"
                result += f"  Status: {tx.status}\n"
                if tx.purpose:
                    result += f"  Purpose: {tx.purpose}\n"
                result += "\n"
            
            return result
            
        except Exception as e:
            return f"Error getting transaction history: {str(e)}"


def create_shopping_tools(sardis_client: SardisClient, agent_id: str) -> list[BaseTool]:
    """
    Create all shopping tools for an agent.
    
    Args:
        sardis_client: The Sardis SDK client
        agent_id: The agent's ID for wallet operations
        
    Returns:
        List of LangChain tools
    """
    return [
        BrowseProductsTool(sardis_client=sardis_client),
        CheckWalletTool(sardis_client=sardis_client, agent_id=agent_id),
        PurchaseProductTool(sardis_client=sardis_client, agent_id=agent_id),
        GetTransactionHistoryTool(sardis_client=sardis_client, agent_id=agent_id),
    ]

