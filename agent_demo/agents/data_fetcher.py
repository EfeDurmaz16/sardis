"""
Data Fetcher Agent - An agent that pays for API/data access.

This agent demonstrates:
- Micropayments for API calls
- Subscription-style recurring payments
- Pay-per-request pricing
- Data marketplace purchases
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid

from sardis_sdk import SardisClient, PaymentResult


@dataclass
class DataSource:
    """A data source the agent can purchase from."""
    source_id: str
    name: str
    merchant_id: str
    pricing_model: str  # "per_request", "subscription", "per_record"
    price_per_unit: Decimal
    currency: str = "USDC"


@dataclass
class DataPurchase:
    """Record of a data purchase."""
    purchase_id: str
    source_id: str
    units: int  # Number of requests/records/days
    total_cost: Decimal
    tx_id: Optional[str] = None
    purchased_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DataFetcherAgent:
    """
    An agent that pays for data and API access.
    
    This agent can:
    - Register data sources with pricing
    - Make micropayments for API calls
    - Purchase data packages
    - Track spending by source
    
    Example workflow:
        1. Agent registers data sources it needs
        2. When data is needed, agent pays for access
        3. Receives data after successful payment
    
    Usage:
        ```python
        agent = DataFetcherAgent("agent_data_001", sardis_client)
        
        # Register a data source
        agent.register_source(DataSource(
            source_id="weather_api",
            name="Weather Data API",
            merchant_id="weather_provider",
            pricing_model="per_request",
            price_per_unit=Decimal("0.01")
        ))
        
        # Fetch data (pays automatically)
        result = agent.fetch("weather_api", query={"city": "NYC"})
        ```
    """
    
    def __init__(self, agent_id: str, client: SardisClient):
        """
        Initialize the data fetcher agent.
        
        Args:
            agent_id: This agent's ID
            client: Sardis SDK client
        """
        self.agent_id = agent_id
        self.client = client
        self._sources: dict[str, DataSource] = {}
        self._purchases: list[DataPurchase] = []
    
    def get_balance(self) -> Decimal:
        """Get current wallet balance."""
        wallet = self.client.get_wallet_info(self.agent_id)
        return wallet.balance
    
    def register_source(self, source: DataSource):
        """
        Register a data source.
        
        Args:
            source: DataSource to register
        """
        self._sources[source.source_id] = source
        
        # Pre-authorize the merchant
        self.client.authorize_service(self.agent_id, source.merchant_id)
        
        print(f"[DataFetcher] Registered source: {source.name}")
        print(f"  Pricing: ${source.price_per_unit} per {source.pricing_model.replace('_', ' ')}")
    
    def get_source(self, source_id: str) -> Optional[DataSource]:
        """Get a registered source."""
        return self._sources.get(source_id)
    
    def list_sources(self) -> list[DataSource]:
        """List all registered sources."""
        return list(self._sources.values())
    
    def estimate_cost(self, source_id: str, units: int = 1) -> Decimal:
        """
        Estimate cost for data access.
        
        Args:
            source_id: Source to estimate for
            units: Number of units (requests, records, days)
            
        Returns:
            Estimated cost
        """
        source = self._sources.get(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not registered")
        
        return source.price_per_unit * units
    
    def fetch(
        self,
        source_id: str,
        units: int = 1,
        query: Optional[dict] = None
    ) -> tuple[bool, Optional[dict]]:
        """
        Fetch data from a source (pays automatically).
        
        Args:
            source_id: Source to fetch from
            units: Number of units to purchase
            query: Optional query parameters
            
        Returns:
            Tuple of (success, data or error)
        """
        source = self._sources.get(source_id)
        if not source:
            return False, {"error": f"Source {source_id} not registered"}
        
        cost = self.estimate_cost(source_id, units)
        
        print(f"[DataFetcher] Fetching from {source.name}")
        print(f"  Units: {units}")
        print(f"  Cost: ${cost}")
        
        # Pay for the data
        result = self.client.pay(
            agent_id=self.agent_id,
            amount=cost,
            merchant_id=source.merchant_id,
            purpose=f"Data fetch: {source_id} ({units} units)"
        )
        
        if not result.success:
            print(f"  Payment failed: {result.error}")
            return False, {"error": result.error}
        
        # Record the purchase
        purchase = DataPurchase(
            purchase_id=f"dp_{uuid.uuid4().hex[:12]}",
            source_id=source_id,
            units=units,
            total_cost=cost,
            tx_id=result.transaction.tx_id if result.transaction else None
        )
        self._purchases.append(purchase)
        
        print(f"  Payment successful: {result.transaction.tx_id if result.transaction else 'N/A'}")
        
        # In a real implementation, this would fetch the actual data
        # Here we return mock data
        mock_data = {
            "source": source_id,
            "query": query,
            "units": units,
            "data": f"[Mock data from {source.name}]",
            "purchase_id": purchase.purchase_id
        }
        
        return True, mock_data
    
    def purchase_subscription(
        self,
        source_id: str,
        days: int = 30
    ) -> PaymentResult:
        """
        Purchase a subscription to a data source.
        
        Args:
            source_id: Source to subscribe to
            days: Subscription duration in days
            
        Returns:
            PaymentResult
        """
        source = self._sources.get(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not registered")
        
        if source.pricing_model != "subscription":
            raise ValueError(f"Source {source_id} doesn't support subscriptions")
        
        cost = source.price_per_unit * days
        
        print(f"[DataFetcher] Purchasing {days}-day subscription to {source.name}")
        print(f"  Total cost: ${cost}")
        
        result = self.client.pay(
            agent_id=self.agent_id,
            amount=cost,
            merchant_id=source.merchant_id,
            purpose=f"Subscription: {source_id} ({days} days)"
        )
        
        if result.success:
            purchase = DataPurchase(
                purchase_id=f"sub_{uuid.uuid4().hex[:12]}",
                source_id=source_id,
                units=days,
                total_cost=cost,
                tx_id=result.transaction.tx_id if result.transaction else None
            )
            self._purchases.append(purchase)
            print(f"  Subscription activated!")
        else:
            print(f"  Failed: {result.error}")
        
        return result
    
    def purchase_data_package(
        self,
        source_id: str,
        package_size: int
    ) -> PaymentResult:
        """
        Purchase a package of data credits.
        
        Args:
            source_id: Source to purchase from
            package_size: Number of records/requests in package
            
        Returns:
            PaymentResult
        """
        source = self._sources.get(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not registered")
        
        cost = source.price_per_unit * package_size
        
        print(f"[DataFetcher] Purchasing {package_size} credits from {source.name}")
        print(f"  Total cost: ${cost}")
        
        result = self.client.pay(
            agent_id=self.agent_id,
            amount=cost,
            merchant_id=source.merchant_id,
            purpose=f"Data package: {source_id} ({package_size} credits)"
        )
        
        if result.success:
            purchase = DataPurchase(
                purchase_id=f"pkg_{uuid.uuid4().hex[:12]}",
                source_id=source_id,
                units=package_size,
                total_cost=cost,
                tx_id=result.transaction.tx_id if result.transaction else None
            )
            self._purchases.append(purchase)
            print(f"  Credits added!")
        else:
            print(f"  Failed: {result.error}")
        
        return result
    
    def get_spending_by_source(self) -> dict[str, Decimal]:
        """Get total spending per source."""
        spending: dict[str, Decimal] = {}
        for purchase in self._purchases:
            if purchase.source_id not in spending:
                spending[purchase.source_id] = Decimal("0")
            spending[purchase.source_id] += purchase.total_cost
        return spending
    
    def get_total_spent(self) -> Decimal:
        """Get total amount spent."""
        return sum(p.total_cost for p in self._purchases)
    
    def list_purchases(
        self,
        source_id: Optional[str] = None,
        limit: int = 50
    ) -> list[DataPurchase]:
        """List purchases, optionally filtered by source."""
        purchases = self._purchases
        if source_id:
            purchases = [p for p in purchases if p.source_id == source_id]
        return purchases[-limit:]


# Example usage
def demo_data_fetcher():
    """Demonstrate the data fetcher agent."""
    from sardis_sdk import SardisClient
    
    print("=== Data Fetcher Agent Demo ===\n")
    
    with SardisClient() as client:
        agent = DataFetcherAgent("agent_data_demo", client)
        
        # Check balance
        balance = agent.get_balance()
        print(f"Starting balance: ${balance}\n")
        
        # Register data sources
        agent.register_source(DataSource(
            source_id="weather_api",
            name="Weather Data API",
            merchant_id="weather_provider",
            pricing_model="per_request",
            price_per_unit=Decimal("0.01")
        ))
        
        agent.register_source(DataSource(
            source_id="stock_data",
            name="Real-time Stock Data",
            merchant_id="stock_provider",
            pricing_model="per_record",
            price_per_unit=Decimal("0.005")
        ))
        
        agent.register_source(DataSource(
            source_id="news_feed",
            name="News Feed Premium",
            merchant_id="news_provider",
            pricing_model="subscription",
            price_per_unit=Decimal("1.00")  # per day
        ))
        
        print()
        
        # Fetch some data
        print("\n--- Fetching Data ---\n")
        
        success, data = agent.fetch("weather_api", units=1, query={"city": "NYC"})
        if success:
            print(f"  Received: {data['data']}\n")
        
        success, data = agent.fetch("stock_data", units=10, query={"symbols": ["AAPL", "GOOG"]})
        if success:
            print(f"  Received: {data['data']}\n")
        
        # Purchase a subscription
        print("\n--- Subscription Purchase ---\n")
        result = agent.purchase_subscription("news_feed", days=7)
        
        # Summary
        print("\n--- Spending Summary ---\n")
        for source_id, amount in agent.get_spending_by_source().items():
            source = agent.get_source(source_id)
            print(f"  {source.name if source else source_id}: ${amount}")
        
        print(f"\nTotal spent: ${agent.get_total_spent()}")
        print(f"Final balance: ${agent.get_balance()}")


if __name__ == "__main__":
    demo_data_fetcher()

