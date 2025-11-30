"""Data Buyer Agent - Purchases API access and datasets."""

from decimal import Decimal
from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

from .base_agent import BaseAgent
from sardis_sdk import SardisClient


# ========== Tools for Data Buyer Agent ==========

class QueryDataCatalogInput(BaseModel):
    """Input for querying data catalog."""
    data_type: Optional[str] = Field(None, description="Type of data (e.g., 'weather', 'financial', 'social')")
    max_price: Optional[float] = Field(None, description="Maximum price in USDC")


class QueryDataCatalogTool(BaseTool):
    """Query available data sources and APIs."""
    
    name: str = "query_data_catalog"
    description: str = """Query available data sources and APIs for purchase.
    Filter by data type (weather, financial, social) or maximum price.
    Returns list of available data products with pricing."""
    args_schema: Type[BaseModel] = QueryDataCatalogInput
    
    sardis_client: SardisClient = None
    
    def __init__(self, sardis_client: SardisClient, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
    
    def _run(self, data_type: Optional[str] = None, max_price: Optional[float] = None) -> str:
        """Query data catalog."""
        # Mock data catalog
        data_products = [
            {
                "id": "data_weather_api",
                "name": "Weather API Access",
                "type": "weather",
                "price": "5.00",
                "description": "Real-time weather data for any location",
                "provider": "WeatherData Inc"
            },
            {
                "id": "data_stock_prices",
                "name": "Stock Market Data Feed",
                "type": "financial",
                "price": "25.00",
                "description": "Live stock prices and market data",
                "provider": "FinanceAPI"
            },
            {
                "id": "data_social_trends",
                "name": "Social Media Trends",
                "type": "social",
                "price": "15.00",
                "description": "Trending topics and sentiment analysis",
                "provider": "SocialInsights"
            },
            {
                "id": "data_news_feed",
                "name": "News API Access",
                "type": "news",
                "price": "10.00",
                "description": "Real-time news from global sources",
                "provider": "NewsAggregator"
            },
        ]
        
        # Filter by type
        if data_type:
            data_products = [d for d in data_products if d["type"].lower() == data_type.lower()]
        
        # Filter by price
        if max_price:
            data_products = [d for d in data_products if float(d["price"]) <= max_price]
        
        if not data_products:
            return "No data products found matching your criteria."
        
        result = "Available Data Products:\n\n"
        for dp in data_products:
            result += f"- **{dp['name']}** (ID: {dp['id']})\n"
            result += f"  Type: {dp['type']} | Price: ${dp['price']} USDC\n"
            result += f"  Provider: {dp['provider']}\n"
            result += f"  Description: {dp['description']}\n\n"
        
        return result


class PurchaseDataAccessInput(BaseModel):
    """Input for purchasing data access."""
    data_product_id: str = Field(..., description="ID of the data product to purchase")
    purpose: Optional[str] = Field(None, description="Reason for purchase")


class PurchaseDataAccessTool(BaseTool):
    """Purchase access to a data product."""
    
    name: str = "purchase_data_access"
    description: str = """Purchase access to a data product or API.
    Requires the data product ID from the catalog.
    Will use Sardis to process the payment."""
    args_schema: Type[BaseModel] = PurchaseDataAccessInput
    
    sardis_client: SardisClient = None
    agent_id: str = None
    
    # Mock pricing
    PRICES = {
        "data_weather_api": ("5.00", "merchant_data_weather"),
        "data_stock_prices": ("25.00", "merchant_data_finance"),
        "data_social_trends": ("15.00", "merchant_data_social"),
        "data_news_feed": ("10.00", "merchant_data_news"),
    }
    
    def __init__(self, sardis_client: SardisClient, agent_id: str, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
        self.agent_id = agent_id
    
    def _run(self, data_product_id: str, purpose: Optional[str] = None) -> str:
        """Purchase data access."""
        if data_product_id not in self.PRICES:
            return f"Unknown data product: {data_product_id}"
        
        price_str, merchant_id = self.PRICES[data_product_id]
        price = Decimal(price_str)
        
        # Check affordability
        if not self.sardis_client.can_afford(self.agent_id, price):
            wallet = self.sardis_client.get_wallet_info(self.agent_id)
            return f"Cannot afford ${price}. Balance: ${wallet.balance}"
        
        # Make purchase
        try:
            result = self.sardis_client.pay(
                agent_id=self.agent_id,
                amount=price,
                merchant_id=merchant_id,
                purpose=purpose or f"Data access: {data_product_id}"
            )
            
            if result.success:
                return f"""Purchase successful!
                
Data Product: {data_product_id}
Price: ${price} USDC
Fee: ${result.transaction.fee} USDC
Total: ${result.transaction.total_cost} USDC
Transaction ID: {result.transaction.tx_id}

Your API key has been generated: API_KEY_{data_product_id.upper()}_DEMO
You now have access to this data source."""
            else:
                return f"Purchase failed: {result.error}"
        except Exception as e:
            return f"Error: {str(e)}"


class CheckBudgetInput(BaseModel):
    """Input for checking budget."""
    pass


class CheckBudgetTool(BaseTool):
    """Check remaining budget for data purchases."""
    
    name: str = "check_budget"
    description: str = "Check your current budget and spending limits for data purchases."
    args_schema: Type[BaseModel] = CheckBudgetInput
    
    sardis_client: SardisClient = None
    agent_id: str = None
    
    def __init__(self, sardis_client: SardisClient, agent_id: str, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
        self.agent_id = agent_id
    
    def _run(self) -> str:
        """Check budget."""
        try:
            wallet = self.sardis_client.get_wallet_info(self.agent_id)
            return f"""Budget Status:
- Available Balance: ${wallet.balance} {wallet.currency}
- Per-Transaction Limit: ${wallet.limit_per_tx}
- Total Spending Limit: ${wallet.limit_total}
- Already Spent: ${wallet.spent_total}
- Remaining Limit: ${wallet.remaining_limit}"""
        except Exception as e:
            return f"Error checking budget: {str(e)}"


# ========== Data Buyer Agent ==========

class DataBuyerAgent(BaseAgent):
    """
    AI Agent that purchases API access and datasets.
    
    Specialized for:
    - Querying available data sources
    - Evaluating data products by type and price
    - Making purchases for data access
    """
    
    @property
    def agent_type(self) -> str:
        return "data_buyer"
    
    @property
    def system_prompt(self) -> str:
        return """You are a Data Buyer AI Agent. Your job is to find and purchase 
data sources, APIs, and datasets that match your requirements.

Your capabilities:
1. Query the data catalog to find available data products
2. Check your budget before making purchases
3. Purchase access to data products via Sardis payments

Important guidelines:
- Always check your budget before purchasing
- Compare prices when multiple options exist
- Consider the data type and provider reputation
- Only purchase what you need
- Report all transaction details after purchases

You have a limited budget managed by Sardis. Be cost-conscious."""
    
    def _get_tools(self) -> list:
        return [
            QueryDataCatalogTool(sardis_client=self.sardis_client),
            CheckBudgetTool(sardis_client=self.sardis_client, agent_id=self.agent_id),
            PurchaseDataAccessTool(sardis_client=self.sardis_client, agent_id=self.agent_id),
        ]
    
    def find_and_purchase(self, data_type: str, max_price: Optional[Decimal] = None) -> str:
        """
        Convenience method to find and purchase data of a specific type.
        
        Args:
            data_type: Type of data to purchase
            max_price: Maximum price willing to pay
        """
        task = f"Find and purchase {data_type} data"
        if max_price:
            task += f" under ${max_price}"
        return self.execute(task)

