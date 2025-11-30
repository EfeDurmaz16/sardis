#!/usr/bin/env python3
"""
Demo runner for Sardis agent examples.

This script runs the example agents against a running Sardis API server.
Make sure the API server is running before executing this script.

Usage:
    python agent_demo/run_demos.py [demo_name]
    
    Where demo_name is one of:
    - compute: Run the compute agent demo (GPU payments)
    - data: Run the data fetcher demo (API payments)
    - marketplace: Run the agent-to-agent marketplace demo
    - all: Run all demos (default)
"""

import sys
import asyncio
from decimal import Decimal
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '.')


def print_header(title: str):
    """Print a styled header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_section(title: str):
    """Print a section header."""
    print(f"\n--- {title} ---\n")


# ==================== Setup Helpers ====================

def setup_test_agents(client):
    """Create test agents for demos."""
    import httpx
    
    agents_to_create = [
        {"name": "Compute Agent", "agent_id": "agent_compute_demo", "owner_id": "demo_owner"},
        {"name": "Data Fetcher", "agent_id": "agent_data_demo", "owner_id": "demo_owner"},
        {"name": "Provider Agent", "agent_id": "agent_provider", "owner_id": "demo_owner"},
        {"name": "Buyer Agent", "agent_id": "agent_buyer", "owner_id": "demo_owner"},
    ]
    
    created = []
    for agent_data in agents_to_create:
        try:
            # Check if agent exists
            response = httpx.get(f"http://localhost:8000/api/v1/agents/{agent_data['agent_id']}")
            if response.status_code == 200:
                print(f"  ✓ Agent {agent_data['agent_id']} already exists")
                created.append(agent_data['agent_id'])
                continue
        except:
            pass
        
        try:
            response = httpx.post(
                "http://localhost:8000/api/v1/agents",
                json={
                    "name": agent_data["name"],
                    "owner_id": agent_data["owner_id"],
                    "description": "Demo agent for testing",
                    "initial_balance": 500.0,  # Fund with 500 USDC for demos
                    "limit_per_tx": 100.0,
                    "limit_total": 1000.0
                }
            )
            if response.status_code == 201:
                data = response.json()
                print(f"  ✓ Created agent: {data['agent_id']}")
                created.append(data['agent_id'])
            else:
                print(f"  ✗ Failed to create {agent_data['name']}: {response.text}")
        except Exception as e:
            print(f"  ✗ Error creating {agent_data['name']}: {e}")
    
    return created


# Global storage for created merchant IDs
_created_merchants = {}

def setup_test_merchants(client):
    """Create test merchants for demos."""
    import httpx
    global _created_merchants
    
    merchants_to_create = [
        {"name": "GPU Provider", "key": "gpu_provider", "category": "compute"},
        {"name": "Weather API", "key": "weather_provider", "category": "data"},
        {"name": "Stock Data", "key": "stock_provider", "category": "data"},
        {"name": "News Feed", "key": "news_provider", "category": "data"},
    ]
    
    for merchant_data in merchants_to_create:
        try:
            response = httpx.post(
                "http://localhost:8000/api/v1/merchants",
                json={
                    "name": merchant_data["name"],
                    "description": f"Demo merchant for {merchant_data['category']}",
                    "category": merchant_data["category"]
                }
            )
            if response.status_code == 201:
                data = response.json()
                merchant_id = data.get('merchant_id')
                _created_merchants[merchant_data["key"]] = merchant_id
                print(f"  ✓ Created {merchant_data['name']}: {merchant_id}")
            else:
                print(f"  ✗ Failed to create {merchant_data['name']}: {response.text}")
        except Exception as e:
            print(f"  ✗ Error creating {merchant_data['name']}: {e}")
    
    return _created_merchants


# ==================== Demo Functions ====================

def run_compute_demo():
    """Run the compute agent demo."""
    from sardis_sdk import SardisClient
    import httpx
    
    print_header("Compute Agent Demo")
    print("This demo shows an AI agent paying for GPU/compute resources")
    print("using pre-authorization holds.\n")
    
    with SardisClient(base_url="http://localhost:8000") as client:
        # First create the agent
        try:
            response = httpx.post(
                "http://localhost:8000/api/v1/agents",
                json={
                    "name": "Compute Demo Agent",
                    "owner_id": "compute_demo",
                    "description": "Demo agent for GPU compute",
                    "initial_balance": 100.0,
                    "limit_per_tx": 50.0,
                    "limit_total": 500.0
                }
            )
            if response.status_code == 201:
                data = response.json()
                agent_id = data["agent"]["agent_id"]
                print(f"Created demo agent: {agent_id}")
            else:
                print(f"Could not create agent: {response.text}")
                return
        except Exception as e:
            print(f"Error creating agent: {e}")
            return
        
        try:
            # Check wallet
            print_section("Wallet Status")
            wallet = client.get_wallet_info(agent_id)
            print(f"Agent: {agent_id}")
            print(f"Balance: ${wallet.balance} {wallet.currency}")
            print(f"Limit per TX: ${wallet.limit_per_tx}")
            
            # Estimate cost
            print_section("Job Estimation")
            estimated_cost = Decimal("5.00")
            print(f"Estimated GPU job cost: ${estimated_cost}")
            
            # Create hold
            print_section("Creating Pre-Authorization Hold")
            gpu_merchant = _created_merchants.get("gpu_provider", "gpu_provider")
            hold_result = client.create_hold(
                agent_id=agent_id,
                merchant_id=gpu_merchant,
                amount=estimated_cost,
                purpose="GPU job: LLM inference"
            )
            
            if hold_result.success:
                print(f"✓ Hold created: {hold_result.hold_id}")
                print(f"  Amount held: ${hold_result.amount}")
                print(f"  Expires at: {hold_result.expires_at}")
                
                # Simulate job completion
                print_section("Simulating Job Execution")
                print("  [Running LLM inference...]")
                print("  [Job completed in 45 seconds]")
                
                actual_cost = Decimal("4.50")  # Less than estimated
                print(f"  Actual cost: ${actual_cost}")
                
                # Capture hold
                print_section("Capturing Payment")
                capture_result = client.capture_hold(hold_result.hold_id, actual_cost)
                
                if capture_result.success:
                    print(f"✓ Payment captured!")
                    print(f"  Transaction ID: {capture_result.transaction.tx_id}")
                    print(f"  Amount charged: ${actual_cost}")
                    print(f"  Savings: ${estimated_cost - actual_cost}")
                else:
                    print(f"✗ Capture failed: {capture_result.error}")
            else:
                print(f"✗ Hold failed: {hold_result.error}")
            
            # Final balance
            print_section("Final Status")
            wallet = client.get_wallet_info(agent_id)
            print(f"Final balance: ${wallet.balance}")
            
        except Exception as e:
            print(f"Error: {e}")


def run_data_demo():
    """Run the data fetcher demo."""
    from sardis_sdk import SardisClient
    import httpx
    
    print_header("Data Fetcher Agent Demo")
    print("This demo shows an AI agent paying for API/data access")
    print("using micropayments.\n")
    
    with SardisClient(base_url="http://localhost:8000") as client:
        # First create the agent
        try:
            response = httpx.post(
                "http://localhost:8000/api/v1/agents",
                json={
                    "name": "Data Fetcher Agent",
                    "owner_id": "data_demo",
                    "description": "Demo agent for API data access",
                    "initial_balance": 50.0,
                    "limit_per_tx": 10.0,
                    "limit_total": 100.0
                }
            )
            if response.status_code == 201:
                data = response.json()
                agent_id = data["agent"]["agent_id"]
                print(f"Created demo agent: {agent_id}")
            else:
                print(f"Could not create agent: {response.text}")
                return
        except Exception as e:
            print(f"Error creating agent: {e}")
            return
        
        try:
            # Check wallet
            print_section("Wallet Status")
            wallet = client.get_wallet_info(agent_id)
            print(f"Agent: {agent_id}")
            print(f"Balance: ${wallet.balance}")
            
            # Pay for weather data
            print_section("Fetching Weather Data")
            print("  API: Weather Data API")
            print("  Cost per request: $0.01")
            
            weather_merchant = _created_merchants.get("weather_provider")
            result = client.pay(
                agent_id=agent_id,
                amount=Decimal("0.01"),
                merchant_id=weather_merchant,
                purpose="Weather API: NYC forecast"
            )
            
            if result.success:
                print(f"  ✓ Payment successful: {result.transaction.tx_id}")
                print("  [Received weather data for NYC]")
            else:
                print(f"  ✗ Payment failed: {result.error}")
            
            # Pay for stock data (batch)
            print_section("Fetching Stock Data")
            print("  API: Real-time Stock Data")
            print("  Records: 10")
            print("  Cost: $0.05")
            
            stock_merchant = _created_merchants.get("stock_provider")
            result = client.pay(
                agent_id=agent_id,
                amount=Decimal("0.05"),
                merchant_id=stock_merchant,
                purpose="Stock data: AAPL, GOOG, MSFT..."
            )
            
            if result.success:
                print(f"  ✓ Payment successful: {result.transaction.tx_id}")
                print("  [Received stock quotes for 10 symbols]")
            else:
                print(f"  ✗ Payment failed: {result.error}")
            
            # Check transaction history
            print_section("Transaction History")
            transactions = client.list_transactions(agent_id, limit=5)
            for tx in transactions:
                print(f"  {tx.tx_id[:20]}... | ${tx.amount} | {tx.purpose or 'N/A'}")
            
            # Final balance
            print_section("Final Status")
            wallet = client.get_wallet_info(agent_id)
            print(f"Final balance: ${wallet.balance}")
            
        except Exception as e:
            print(f"Error: {e}")


def run_marketplace_demo():
    """Run the agent-to-agent marketplace demo."""
    from sardis_sdk import SardisClient
    import httpx
    
    print_header("Agent-to-Agent Marketplace Demo")
    print("This demo shows agents buying and selling services from each other.\n")
    
    with SardisClient(base_url="http://localhost:8000") as client:
        # Create provider agent
        try:
            response = httpx.post(
                "http://localhost:8000/api/v1/agents",
                json={
                    "name": "Service Provider Agent",
                    "owner_id": "marketplace_demo",
                    "description": "Provides document analysis services",
                    "initial_balance": 0.0,  # Provider starts with 0
                    "limit_per_tx": 100.0,
                    "limit_total": 1000.0
                }
            )
            if response.status_code == 201:
                data = response.json()
                provider_agent = data["agent"]["agent_id"]
                print(f"Created provider agent: {provider_agent}")
            else:
                print(f"Could not create provider: {response.text}")
                return
        except Exception as e:
            print(f"Error creating provider: {e}")
            return
        
        # Create buyer agent
        try:
            response = httpx.post(
                "http://localhost:8000/api/v1/agents",
                json={
                    "name": "Buyer Agent",
                    "owner_id": "marketplace_demo",
                    "description": "Buys services from other agents",
                    "initial_balance": 100.0,  # Buyer starts with funds
                    "limit_per_tx": 50.0,
                    "limit_total": 500.0
                }
            )
            if response.status_code == 201:
                data = response.json()
                buyer_agent = data["agent"]["agent_id"]
                print(f"Created buyer agent: {buyer_agent}")
            else:
                print(f"Could not create buyer: {response.text}")
                return
        except Exception as e:
            print(f"Error creating buyer: {e}")
            return
        
        try:
            # Check wallets
            print_section("Initial Wallet Status")
            provider_wallet = client.get_wallet_info(provider_agent)
            buyer_wallet = client.get_wallet_info(buyer_agent)
            
            print(f"Provider ({provider_agent}): ${provider_wallet.balance}")
            print(f"Buyer ({buyer_agent}): ${buyer_wallet.balance}")
            
            # Create a payment request (invoice)
            print_section("Provider Creates Payment Request")
            service_price = Decimal("15.00")
            print(f"  Service: Document Analysis")
            print(f"  Price: ${service_price}")
            
            # Simulate invoice (in real API this would be a request_payment call)
            print("  [Payment request created]")
            
            # Buyer pays
            print_section("Buyer Pays for Service")
            
            result = client.pay(
                agent_id=buyer_agent,
                amount=service_price,
                recipient_wallet_id=provider_wallet.wallet_id,
                purpose="Payment for Document Analysis service"
            )
            
            if result.success:
                print(f"  ✓ Payment sent!")
                print(f"  Transaction: {result.transaction.tx_id}")
                print(f"  Amount: ${result.transaction.amount}")
                print(f"  Fee: ${result.transaction.fee}")
            else:
                print(f"  ✗ Payment failed: {result.error}")
            
            # Check final balances
            print_section("Final Wallet Status")
            provider_wallet = client.get_wallet_info(provider_agent)
            buyer_wallet = client.get_wallet_info(buyer_agent)
            
            print(f"Provider ({provider_agent}): ${provider_wallet.balance}")
            print(f"Buyer ({buyer_agent}): ${buyer_wallet.balance}")
            
        except Exception as e:
            print(f"Error: {e}")


# ==================== Main ====================

def main():
    """Main entry point."""
    import httpx
    
    demo_name = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    print_header("Sardis Agent Demo Runner")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check API is running
    print_section("Checking API Server")
    try:
        response = httpx.get("http://localhost:8000/api/v1/")
        if response.status_code == 200:
            print("✓ API server is running")
            data = response.json()
            print(f"  Version: {data.get('version', 'unknown')}")
        else:
            print(f"✗ API returned status {response.status_code}")
            return
    except Exception as e:
        print(f"✗ Cannot connect to API server: {e}")
        print("\nMake sure the API is running:")
        print("  uvicorn sardis_core.api.main:app --reload")
        return
    
    # Setup merchants
    print_section("Setting Up Demo Merchants")
    setup_test_merchants(None)
    
    # Run demos
    demos = {
        "compute": run_compute_demo,
        "data": run_data_demo,
        "marketplace": run_marketplace_demo,
    }
    
    if demo_name == "all":
        for name, demo_func in demos.items():
            try:
                demo_func()
            except Exception as e:
                print(f"Error in {name} demo: {e}")
    elif demo_name in demos:
        demos[demo_name]()
    else:
        print(f"Unknown demo: {demo_name}")
        print(f"Available demos: {', '.join(demos.keys())}, all")
        return
    
    print_header("Demo Complete")
    print("All demos have finished running.")
    print("\nNext steps:")
    print("  - Check the dashboard at http://localhost:5173")
    print("  - View API docs at http://localhost:8000/docs")
    print("  - Run tests with: pytest tests/")


if __name__ == "__main__":
    main()

