"""
Agent-to-Agent Payment Scenario.

This scenario demonstrates:
- Payment requests (invoices) between agents
- Direct agent-to-agent transfers
- Service marketplaces where agents pay each other
- Escrow-style holds for service delivery
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid

from sardis_sdk import SardisClient, PaymentResult, PaymentRequest


@dataclass
class ServiceListing:
    """A service offered by an agent."""
    listing_id: str
    provider_agent_id: str
    service_name: str
    description: str
    price: Decimal
    currency: str = "USDC"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ServiceOrder:
    """An order for a service between agents."""
    order_id: str
    listing_id: str
    buyer_agent_id: str
    seller_agent_id: str
    amount: Decimal
    status: str = "pending"  # pending, paid, delivered, completed, disputed
    payment_request_id: Optional[str] = None
    hold_id: Optional[str] = None
    tx_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentMarketplace:
    """
    A marketplace where agents can offer and purchase services from each other.
    
    This demonstrates:
    - Agents listing services for sale
    - Payment requests (invoices) for services
    - Escrow-style holds until service delivery
    - Completion of transactions after delivery
    
    Example workflow:
        1. Agent A lists a service (e.g., "Data Processing")
        2. Agent B orders the service
        3. Agent A creates a payment request
        4. Agent B pays the request (funds go to escrow/hold)
        5. Agent A delivers the service
        6. Agent B confirms delivery, funds released
    
    Usage:
        ```python
        marketplace = AgentMarketplace(sardis_client)
        
        # Agent A lists a service
        listing = marketplace.list_service(
            provider_agent_id="agent_a",
            service_name="Data Analysis",
            price=Decimal("25.00")
        )
        
        # Agent B orders the service
        order = marketplace.order_service(
            buyer_agent_id="agent_b",
            listing_id=listing.listing_id
        )
        
        # Agent B pays for the order
        marketplace.pay_order(order.order_id)
        
        # After service delivery, confirm completion
        marketplace.confirm_delivery(order.order_id)
        ```
    """
    
    def __init__(self, client: SardisClient):
        """
        Initialize the marketplace.
        
        Args:
            client: Sardis SDK client
        """
        self.client = client
        self._listings: dict[str, ServiceListing] = {}
        self._orders: dict[str, ServiceOrder] = {}
    
    # ==================== Service Listings ====================
    
    def list_service(
        self,
        provider_agent_id: str,
        service_name: str,
        price: Decimal,
        description: str = ""
    ) -> ServiceListing:
        """
        List a service for sale.
        
        Args:
            provider_agent_id: Agent offering the service
            service_name: Name of the service
            price: Price in USDC
            description: Service description
            
        Returns:
            Created ServiceListing
        """
        listing_id = f"svc_{uuid.uuid4().hex[:12]}"
        
        listing = ServiceListing(
            listing_id=listing_id,
            provider_agent_id=provider_agent_id,
            service_name=service_name,
            description=description,
            price=price,
        )
        
        self._listings[listing_id] = listing
        
        print(f"[Marketplace] New listing: {service_name}")
        print(f"  Provider: {provider_agent_id}")
        print(f"  Price: ${price}")
        print(f"  Listing ID: {listing_id}")
        
        return listing
    
    def get_listing(self, listing_id: str) -> Optional[ServiceListing]:
        """Get a listing by ID."""
        return self._listings.get(listing_id)
    
    def search_listings(
        self,
        max_price: Optional[Decimal] = None,
        keyword: Optional[str] = None
    ) -> list[ServiceListing]:
        """Search available listings."""
        listings = list(self._listings.values())
        
        if max_price is not None:
            listings = [l for l in listings if l.price <= max_price]
        
        if keyword:
            keyword = keyword.lower()
            listings = [
                l for l in listings
                if keyword in l.service_name.lower() or keyword in l.description.lower()
            ]
        
        return listings
    
    # ==================== Orders ====================
    
    def order_service(
        self,
        buyer_agent_id: str,
        listing_id: str
    ) -> ServiceOrder:
        """
        Create an order for a service.
        
        Args:
            buyer_agent_id: Agent purchasing the service
            listing_id: Service to purchase
            
        Returns:
            Created ServiceOrder
        """
        listing = self._listings.get(listing_id)
        if not listing:
            raise ValueError(f"Listing {listing_id} not found")
        
        if buyer_agent_id == listing.provider_agent_id:
            raise ValueError("Cannot order own service")
        
        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        
        order = ServiceOrder(
            order_id=order_id,
            listing_id=listing_id,
            buyer_agent_id=buyer_agent_id,
            seller_agent_id=listing.provider_agent_id,
            amount=listing.price,
        )
        
        self._orders[order_id] = order
        
        print(f"\n[Marketplace] New order: {order_id}")
        print(f"  Service: {listing.service_name}")
        print(f"  Buyer: {buyer_agent_id}")
        print(f"  Seller: {listing.provider_agent_id}")
        print(f"  Amount: ${listing.price}")
        
        return order
    
    def pay_order(self, order_id: str) -> PaymentResult:
        """
        Pay for an order (buyer pays seller).
        
        Args:
            order_id: Order to pay for
            
        Returns:
            PaymentResult
        """
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status != "pending":
            raise ValueError(f"Order is not pending (status: {order.status})")
        
        listing = self._listings.get(order.listing_id)
        
        print(f"\n[Marketplace] Processing payment for order {order_id}")
        
        # Get seller's wallet
        seller_wallet = self.client.get_wallet_info(order.seller_agent_id)
        
        # Direct payment to seller
        result = self.client.pay(
            agent_id=order.buyer_agent_id,
            amount=order.amount,
            recipient_wallet_id=seller_wallet.wallet_id,
            purpose=f"Payment for {listing.service_name if listing else order.listing_id}"
        )
        
        if result.success:
            order.status = "paid"
            order.tx_id = result.transaction.tx_id if result.transaction else None
            print(f"  Payment successful!")
            print(f"  TX: {order.tx_id}")
        else:
            print(f"  Payment failed: {result.error}")
        
        return result
    
    def pay_order_with_escrow(self, order_id: str) -> bool:
        """
        Pay for an order using escrow (hold until delivery confirmed).
        
        This creates a hold on the buyer's funds that is released
        to the seller only after delivery is confirmed.
        
        Args:
            order_id: Order to pay for
            
        Returns:
            True if hold created successfully
        """
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status != "pending":
            raise ValueError(f"Order is not pending (status: {order.status})")
        
        listing = self._listings.get(order.listing_id)
        
        print(f"\n[Marketplace] Creating escrow hold for order {order_id}")
        
        # Create a hold (in reality would be to an escrow wallet)
        # For demo, we use the marketplace as a pseudo-merchant
        result = self.client.create_hold(
            agent_id=order.buyer_agent_id,
            merchant_id="marketplace_escrow",  # Escrow wallet
            amount=order.amount,
            purpose=f"Escrow: {listing.service_name if listing else order.listing_id}"
        )
        
        if result.success:
            order.status = "escrowed"
            order.hold_id = result.hold_id
            print(f"  Hold created: {result.hold_id}")
            print(f"  Funds escrowed: ${order.amount}")
            return True
        else:
            print(f"  Hold failed: {result.error}")
            return False
    
    def confirm_delivery(self, order_id: str) -> PaymentResult:
        """
        Confirm service delivery and release payment.
        
        For escrow orders, this captures the hold.
        
        Args:
            order_id: Order to confirm
            
        Returns:
            PaymentResult
        """
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        print(f"\n[Marketplace] Confirming delivery for order {order_id}")
        
        if order.status == "paid":
            # Already paid directly, just mark as complete
            order.status = "completed"
            print(f"  Order marked as completed")
            return PaymentResult(success=True)
        
        elif order.status == "escrowed":
            if not order.hold_id:
                raise ValueError("Order has no hold ID")
            
            # Capture the hold to release funds to seller
            result = self.client.capture_hold(order.hold_id)
            
            if result.success:
                order.status = "completed"
                order.tx_id = result.transaction.tx_id if result.transaction else None
                print(f"  Escrow released to seller")
                print(f"  TX: {order.tx_id}")
            else:
                print(f"  Release failed: {result.error}")
            
            return result
        
        else:
            raise ValueError(f"Order cannot be confirmed (status: {order.status})")
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order (void escrow if applicable).
        
        Args:
            order_id: Order to cancel
            
        Returns:
            True if cancelled successfully
        """
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        print(f"\n[Marketplace] Cancelling order {order_id}")
        
        if order.status == "escrowed" and order.hold_id:
            # Void the hold to release funds back to buyer
            result = self.client.void_hold(order.hold_id)
            if not result.success:
                print(f"  Failed to void hold: {result.error}")
                return False
            print(f"  Escrow voided, funds returned to buyer")
        
        order.status = "cancelled"
        print(f"  Order cancelled")
        return True
    
    def get_order(self, order_id: str) -> Optional[ServiceOrder]:
        """Get an order by ID."""
        return self._orders.get(order_id)
    
    def list_orders(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> list[ServiceOrder]:
        """List orders with optional filters."""
        orders = list(self._orders.values())
        
        if agent_id:
            orders = [
                o for o in orders
                if o.buyer_agent_id == agent_id or o.seller_agent_id == agent_id
            ]
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        return orders


def demo_agent_to_agent_payment():
    """Demonstrate agent-to-agent payments."""
    from sardis_sdk import SardisClient
    
    print("=" * 60)
    print("Agent-to-Agent Payment Demo")
    print("=" * 60)
    
    with SardisClient() as client:
        marketplace = AgentMarketplace(client)
        
        agent_a = "agent_provider"
        agent_b = "agent_buyer"
        
        # Check balances
        print("\n--- Initial Balances ---")
        try:
            balance_a = client.get_wallet_info(agent_a).balance
            balance_b = client.get_wallet_info(agent_b).balance
            print(f"Agent A (Provider): ${balance_a}")
            print(f"Agent B (Buyer): ${balance_b}")
        except Exception as e:
            print(f"Could not get balances: {e}")
            print("(Demo mode - using simulated agents)")
        
        # Agent A lists a service
        print("\n--- Agent A Lists a Service ---")
        listing = marketplace.list_service(
            provider_agent_id=agent_a,
            service_name="Document Analysis",
            price=Decimal("15.00"),
            description="AI-powered document analysis and summarization"
        )
        
        # Agent B orders the service
        print("\n--- Agent B Orders the Service ---")
        order = marketplace.order_service(
            buyer_agent_id=agent_b,
            listing_id=listing.listing_id
        )
        
        # Agent B pays for the order
        print("\n--- Agent B Pays ---")
        try:
            result = marketplace.pay_order(order.order_id)
            
            if result.success:
                # Simulate service delivery
                print("\n--- Service Delivery ---")
                print("[Agent A delivers the service...]")
                
                # Confirm delivery
                print("\n--- Confirm Delivery ---")
                marketplace.confirm_delivery(order.order_id)
        except Exception as e:
            print(f"Payment error: {e}")
        
        # Final order status
        print("\n--- Order Summary ---")
        final_order = marketplace.get_order(order.order_id)
        if final_order:
            print(f"Order ID: {final_order.order_id}")
            print(f"Status: {final_order.status}")
            print(f"Amount: ${final_order.amount}")
            if final_order.tx_id:
                print(f"Transaction: {final_order.tx_id}")
        
        print("\n" + "=" * 60)
        print("Demo Complete")
        print("=" * 60)


# Direct payment helper
def direct_agent_payment(
    client: SardisClient,
    from_agent_id: str,
    to_agent_id: str,
    amount: Decimal,
    purpose: Optional[str] = None
) -> PaymentResult:
    """
    Make a direct payment between two agents.
    
    Args:
        client: Sardis client
        from_agent_id: Paying agent
        to_agent_id: Receiving agent
        amount: Payment amount
        purpose: Optional description
        
    Returns:
        PaymentResult
    """
    # Get recipient's wallet
    recipient_wallet = client.get_wallet_info(to_agent_id)
    
    return client.pay(
        agent_id=from_agent_id,
        amount=amount,
        recipient_wallet_id=recipient_wallet.wallet_id,
        purpose=purpose or f"Payment to {to_agent_id}"
    )


if __name__ == "__main__":
    demo_agent_to_agent_payment()

