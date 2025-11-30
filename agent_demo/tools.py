"""LangChain tools for Sardis shopping agent."""

from decimal import Decimal
from typing import Optional
from langchain_core.tools import tool

from sardis_sdk import SardisClient


def create_shopping_tools(sardis_client: SardisClient, agent_id: str) -> list:
    """
    Create all shopping tools for an agent.
    
    Args:
        sardis_client: The Sardis SDK client
        agent_id: The agent's ID for wallet operations
        
    Returns:
        List of LangChain tools
    """
    
    @tool
    def browse_products(
        category: Optional[str] = None,
        max_price: Optional[float] = None
    ) -> str:
        """Browse available products in the catalog.
        
        Args:
            category: Filter by category (e.g., 'electronics', 'office')
            max_price: Maximum price filter in USDC
        
        Returns a list of products with their names, descriptions, and prices.
        """
        try:
            max_price_decimal = Decimal(str(max_price)) if max_price else None
            products = sardis_client.list_products(
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
    
    @tool
    def check_wallet() -> str:
        """Check your current wallet balance and spending limits.
        
        Returns your available balance, per-transaction limit, and remaining spending limit.
        """
        try:
            wallet = sardis_client.get_wallet_info(agent_id)
            
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
    
    @tool
    def purchase_product(
        product_id: str,
        purpose: Optional[str] = None
    ) -> str:
        """Purchase a product by its ID.
        
        Args:
            product_id: The ID of the product to purchase (e.g., 'prod_001')
            purpose: Optional note about the purchase
        
        This will deduct the product price plus a small transaction fee from your wallet.
        Make sure you have checked your wallet balance first to ensure you can afford the purchase.
        """
        try:
            # First get the product details
            product = sardis_client.get_product(product_id)
            
            # Check if we can afford it
            estimate = sardis_client.estimate_payment(product.price)
            
            if not sardis_client.can_afford(agent_id, product.price):
                wallet = sardis_client.get_wallet_info(agent_id)
                return f"""Cannot afford this purchase.
Product: {product.name} costs {product.price} {product.currency}
Estimated total with fee: {estimate['total']} {product.currency}
Your balance: {wallet.balance} {wallet.currency}
Your per-tx limit: {wallet.limit_per_tx} {wallet.currency}
Your remaining limit: {wallet.remaining_limit} {wallet.currency}"""
            
            # Execute the payment
            purchase_purpose = purpose or f"Purchase: {product.name}"
            result = sardis_client.pay(
                agent_id=agent_id,
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
    
    @tool
    def get_transaction_history(limit: int = 5) -> str:
        """View your recent transaction history.
        
        Args:
            limit: Number of transactions to retrieve (default: 5)
        
        Returns details of your past purchases and payments.
        """
        try:
            transactions = sardis_client.list_transactions(agent_id, limit=limit)
            
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
    
    return [
        browse_products,
        check_wallet,
        purchase_product,
        get_transaction_history,
    ]
