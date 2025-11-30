"""Budget Optimizer Agent - Finds best deals and optimizes spending."""

from decimal import Decimal
from typing import Optional, Type, List
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

from .base_agent import BaseAgent
from sardis_sdk import SardisClient


# ========== Tools for Budget Optimizer Agent ==========

class SearchDealsInput(BaseModel):
    """Input for searching deals."""
    category: Optional[str] = Field(None, description="Product category")
    max_budget: Optional[float] = Field(None, description="Maximum budget in USDC")
    min_savings_percent: Optional[float] = Field(None, description="Minimum savings percentage")


class SearchDealsTool(BaseTool):
    """Search for the best deals across products."""
    
    name: str = "search_deals"
    description: str = """Search for the best deals and discounts across all products.
    Filter by category, budget, or minimum savings percentage.
    Returns products sorted by value (savings/quality ratio)."""
    args_schema: Type[BaseModel] = SearchDealsInput
    
    sardis_client: SardisClient = None
    
    def __init__(self, sardis_client: SardisClient, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
    
    def _run(
        self,
        category: Optional[str] = None,
        max_budget: Optional[float] = None,
        min_savings_percent: Optional[float] = None
    ) -> str:
        # Mock deals catalog with savings
        deals = [
            {
                "id": "deal_headphones",
                "name": "Premium Wireless Headphones",
                "category": "electronics",
                "original_price": "79.99",
                "sale_price": "49.99",
                "savings_percent": 37.5,
                "rating": 4.5,
                "merchant_id": "merchant_electronics"
            },
            {
                "id": "deal_keyboard",
                "name": "Mechanical Keyboard RGB",
                "category": "electronics",
                "original_price": "129.99",
                "sale_price": "89.99",
                "savings_percent": 30.8,
                "rating": 4.7,
                "merchant_id": "merchant_electronics"
            },
            {
                "id": "deal_notebook",
                "name": "Premium Notebook Set (5 pack)",
                "category": "office",
                "original_price": "24.99",
                "sale_price": "12.99",
                "savings_percent": 48.0,
                "rating": 4.3,
                "merchant_id": "merchant_office"
            },
            {
                "id": "deal_mouse",
                "name": "Ergonomic Wireless Mouse",
                "category": "electronics",
                "original_price": "59.99",
                "sale_price": "34.99",
                "savings_percent": 41.7,
                "rating": 4.6,
                "merchant_id": "merchant_electronics"
            },
            {
                "id": "deal_monitor_stand",
                "name": "Adjustable Monitor Stand",
                "category": "office",
                "original_price": "89.99",
                "sale_price": "54.99",
                "savings_percent": 38.9,
                "rating": 4.4,
                "merchant_id": "merchant_office"
            },
        ]
        
        # Apply filters
        if category:
            deals = [d for d in deals if d["category"].lower() == category.lower()]
        
        if max_budget:
            deals = [d for d in deals if float(d["sale_price"]) <= max_budget]
        
        if min_savings_percent:
            deals = [d for d in deals if d["savings_percent"] >= min_savings_percent]
        
        # Sort by savings percentage
        deals.sort(key=lambda x: x["savings_percent"], reverse=True)
        
        if not deals:
            return "No deals found matching your criteria."
        
        result = "Best Deals Found:\n\n"
        for d in deals:
            savings = float(d["original_price"]) - float(d["sale_price"])
            result += f"🏷️ **{d['name']}** (ID: {d['id']})\n"
            result += f"   Category: {d['category']}\n"
            result += f"   Original: ${d['original_price']} → Sale: ${d['sale_price']}\n"
            result += f"   Savings: ${savings:.2f} ({d['savings_percent']:.1f}% off)\n"
            result += f"   Rating: {d['rating']}/5.0\n\n"
        
        return result


class CompareProductsInput(BaseModel):
    """Input for comparing products."""
    product_ids: List[str] = Field(..., description="List of product IDs to compare")


class CompareProductsTool(BaseTool):
    """Compare multiple products side by side."""
    
    name: str = "compare_products"
    description: str = """Compare multiple products to find the best value.
    Analyzes price, savings, rating, and value score."""
    args_schema: Type[BaseModel] = CompareProductsInput
    
    # Product database
    PRODUCTS = {
        "deal_headphones": {"name": "Premium Headphones", "price": 49.99, "rating": 4.5, "savings": 37.5},
        "deal_keyboard": {"name": "Mechanical Keyboard", "price": 89.99, "rating": 4.7, "savings": 30.8},
        "deal_notebook": {"name": "Notebook Set", "price": 12.99, "rating": 4.3, "savings": 48.0},
        "deal_mouse": {"name": "Wireless Mouse", "price": 34.99, "rating": 4.6, "savings": 41.7},
        "deal_monitor_stand": {"name": "Monitor Stand", "price": 54.99, "rating": 4.4, "savings": 38.9},
    }
    
    def _run(self, product_ids: List[str]) -> str:
        products = []
        for pid in product_ids:
            if pid in self.PRODUCTS:
                products.append((pid, self.PRODUCTS[pid]))
        
        if not products:
            return "None of the specified products were found."
        
        # Calculate value score: (rating * savings) / price
        for pid, p in products:
            p["value_score"] = (p["rating"] * p["savings"]) / p["price"]
        
        # Sort by value score
        products.sort(key=lambda x: x[1]["value_score"], reverse=True)
        
        result = "Product Comparison:\n\n"
        result += "| Product | Price | Rating | Savings | Value Score |\n"
        result += "|---------|-------|--------|---------|-------------|\n"
        
        for pid, p in products:
            result += f"| {p['name']} | ${p['price']} | {p['rating']} | {p['savings']}% | {p['value_score']:.2f} |\n"
        
        best = products[0]
        result += f"\n**Best Value:** {best[1]['name']} with a value score of {best[1]['value_score']:.2f}"
        
        return result


class OptimizedPurchaseInput(BaseModel):
    """Input for optimized purchase."""
    product_id: str = Field(..., description="ID of the product to purchase")
    reason: Optional[str] = Field(None, description="Reason for purchase")


class OptimizedPurchaseTool(BaseTool):
    """Make an optimized purchase."""
    
    name: str = "make_purchase"
    description: str = """Purchase a product after confirming it's the best deal.
    Use after comparing options and verifying budget."""
    args_schema: Type[BaseModel] = OptimizedPurchaseInput
    
    sardis_client: SardisClient = None
    agent_id: str = None
    
    PRODUCTS = {
        "deal_headphones": (Decimal("49.99"), "merchant_electronics"),
        "deal_keyboard": (Decimal("89.99"), "merchant_electronics"),
        "deal_notebook": (Decimal("12.99"), "merchant_office"),
        "deal_mouse": (Decimal("34.99"), "merchant_electronics"),
        "deal_monitor_stand": (Decimal("54.99"), "merchant_office"),
    }
    
    def __init__(self, sardis_client: SardisClient, agent_id: str, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
        self.agent_id = agent_id
    
    def _run(self, product_id: str, reason: Optional[str] = None) -> str:
        if product_id not in self.PRODUCTS:
            return f"Product not found: {product_id}"
        
        price, merchant_id = self.PRODUCTS[product_id]
        
        # Verify affordability
        if not self.sardis_client.can_afford(self.agent_id, price):
            wallet = self.sardis_client.get_wallet_info(self.agent_id)
            return f"Cannot afford ${price}. Balance: ${wallet.balance}"
        
        try:
            result = self.sardis_client.pay(
                agent_id=self.agent_id,
                amount=price,
                merchant_id=merchant_id,
                purpose=reason or f"Optimized purchase: {product_id}"
            )
            
            if result.success:
                return f"""Purchase Complete!

Product: {product_id}
Price: ${price} USDC
Fee: ${result.transaction.fee} USDC
Total Paid: ${result.transaction.total_cost} USDC
Transaction: {result.transaction.tx_id}

You saved money by choosing this deal!"""
            else:
                return f"Purchase failed: {result.error}"
        except Exception as e:
            return f"Error: {str(e)}"


class CheckBudgetInput(BaseModel):
    """Input for budget check."""
    pass


class CheckBudgetTool(BaseTool):
    """Check current budget status."""
    
    name: str = "check_budget"
    description: str = "Check your current budget and spending status."
    args_schema: Type[BaseModel] = CheckBudgetInput
    
    sardis_client: SardisClient = None
    agent_id: str = None
    
    def __init__(self, sardis_client: SardisClient, agent_id: str, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
        self.agent_id = agent_id
    
    def _run(self) -> str:
        try:
            wallet = self.sardis_client.get_wallet_info(self.agent_id)
            return f"""Budget Overview:
- Available: ${wallet.balance} {wallet.currency}
- Already Spent: ${wallet.spent_total}
- Remaining Limit: ${wallet.remaining_limit}
- Per-Transaction Limit: ${wallet.limit_per_tx}

Shopping Recommendation:
- Can afford products up to ${min(wallet.balance, wallet.limit_per_tx)} per item
- Total remaining budget: ${wallet.remaining_limit}"""
        except Exception as e:
            return f"Error: {str(e)}"


# ========== Budget Optimizer Agent ==========

class BudgetOptimizerAgent(BaseAgent):
    """
    AI Agent that finds the best deals and optimizes spending.
    
    Specialized for:
    - Finding deals and discounts
    - Comparing products by value
    - Making optimized purchasing decisions
    """
    
    @property
    def agent_type(self) -> str:
        return "budget_optimizer"
    
    @property
    def system_prompt(self) -> str:
        return """You are a Budget Optimizer AI Agent. Your mission is to find 
the best value purchases and maximize savings.

Your capabilities:
1. Search for deals and discounts
2. Compare products by value score
3. Check budget constraints
4. Make optimized purchases

Decision Framework:
1. First, check your budget
2. Search for deals in the relevant category
3. Compare top options using value score
4. Purchase the option with best value/price ratio

Value Score = (Rating × Savings%) / Price

Always prioritize:
- Higher savings percentage
- Better ratings
- Lower absolute price when value is similar

Never exceed your budget or per-transaction limits."""
    
    def _get_tools(self) -> list:
        return [
            SearchDealsTool(sardis_client=self.sardis_client),
            CompareProductsTool(),
            CheckBudgetTool(sardis_client=self.sardis_client, agent_id=self.agent_id),
            OptimizedPurchaseTool(sardis_client=self.sardis_client, agent_id=self.agent_id),
        ]
    
    def find_best_deal(self, category: str, budget: Decimal) -> str:
        """
        Find and purchase the best deal in a category.
        
        Args:
            category: Product category
            budget: Maximum budget
        """
        return self.execute(
            f"Find the best deal in {category} category under ${budget}. "
            f"Compare options and purchase the best value item."
        )

