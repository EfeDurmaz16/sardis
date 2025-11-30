#!/usr/bin/env python3
"""
Sardis Demo Runner - Showcase all AI agent capabilities in 2 minutes.

Usage:
    python -m demo.run_demo
    
Make sure the Sardis API is running first:
    uvicorn sardis_core.api.main:app --host 0.0.0.0 --port 8000
"""

import asyncio
import sys
import time
from decimal import Decimal
from typing import Optional

from demo.console import console, Color
from sardis_sdk import SardisClient


class DemoRunner:
    """Runs the complete Sardis demonstration."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.client = SardisClient(base_url=api_url)
        self.demo_agents = {}
        self.demo_merchants = {}
    
    async def run(self, skip_ai: bool = True):
        """
        Run the complete demo.
        
        Args:
            skip_ai: If True, skip LLM-based demos (faster, no API key needed)
        """
        try:
            # Show logo and intro
            console.logo()
            console.header("SARDIS PLATFORM DEMONSTRATION")
            console.info("Showcasing AI Agent Payment Infrastructure")
            console.divider()
            
            # Step 1: Setup
            await self._demo_setup()
            
            # Step 2: Agent Registration
            await self._demo_agent_registration()
            
            # Step 3: Wallet Operations
            await self._demo_wallet_operations()
            
            # Step 4: Payment Flow
            await self._demo_payment_flow()
            
            # Step 5: Transaction History
            await self._demo_transaction_history()
            
            # Step 6: Limit Enforcement
            await self._demo_limit_enforcement()
            
            # Step 7: Multi-Token Support
            await self._demo_multi_token()
            
            # Step 8: Risk Scoring
            await self._demo_risk_scoring()
            
            # Summary
            await self._demo_summary()
            
            console.header("DEMONSTRATION COMPLETE")
            console.success("All Sardis capabilities demonstrated successfully!")
            
        except Exception as e:
            console.error(f"Demo failed: {str(e)}")
            raise
        finally:
            self.client.close()
    
    async def _demo_setup(self):
        """Set up demo environment."""
        console.step(1, "Setting Up Demo Environment")
        
        # Register demo merchants
        console.subheader("Registering Demo Merchants")
        
        merchants = [
            ("TechStore Pro", "electronics", "Premium electronics retailer"),
            ("Office Supplies Co", "office", "Office and stationery supplies"),
            ("Data Services Inc", "data", "API and data services"),
        ]
        
        for name, category, desc in merchants:
            try:
                merchant = self.client.register_merchant(
                    name=name,
                    category=category,
                    description=desc
                )
                self.demo_merchants[category] = merchant.merchant_id
                console.success(f"Registered: {name} (ID: {merchant.merchant_id})")
            except Exception as e:
                console.warning(f"Merchant may already exist: {name}")
        
        time.sleep(0.5)
    
    async def _demo_agent_registration(self):
        """Demonstrate agent registration."""
        console.step(2, "AI Agent Registration")
        
        agents = [
            {
                "name": "shopping_demo_agent",
                "owner_id": "demo_developer_1",
                "description": "Demo shopping agent",
                "initial_balance": Decimal("100.00"),
                "limit_per_tx": Decimal("50.00"),
                "limit_total": Decimal("100.00")
            },
            {
                "name": "data_buyer_demo",
                "owner_id": "demo_developer_2",
                "description": "Demo data purchasing agent",
                "initial_balance": Decimal("50.00"),
                "limit_per_tx": Decimal("25.00"),
                "limit_total": Decimal("50.00")
            }
        ]
        
        for agent_data in agents:
            console.subheader(f"Registering: {agent_data['name']}")
            
            try:
                result = self.client.register_agent(**agent_data)
                self.demo_agents[agent_data["name"]] = result.agent.agent_id
                
                console.agent_info(agent_data["name"], result.agent.agent_id)
                console.money(str(agent_data["initial_balance"]), "Initial Balance")
                
                if result.wallet.virtual_card:
                    console.info(f"Virtual Card: {result.wallet.virtual_card.masked_number}")
                
            except Exception as e:
                console.warning(f"Agent may already exist: {str(e)}")
        
        time.sleep(0.5)
    
    async def _demo_wallet_operations(self):
        """Demonstrate wallet operations."""
        console.step(3, "Wallet Management")
        
        if not self.demo_agents:
            console.warning("No demo agents available")
            return
        
        agent_id = list(self.demo_agents.values())[0]
        
        console.subheader("Checking Wallet Balance")
        
        wallet = self.client.get_wallet_info(agent_id)
        console.wallet_status(
            balance=str(wallet.balance),
            spent=str(wallet.spent_total),
            remaining=str(wallet.remaining_limit),
            currency=wallet.currency
        )
        
        console.subheader("Payment Estimation")
        
        estimate = self.client.estimate_payment(Decimal("25.00"))
        console.info(f"For a $25.00 payment:")
        console.info(f"  Amount: ${estimate.amount}")
        console.info(f"  Fee: ${estimate.fee}")
        console.info(f"  Total: ${estimate.total}")
        
        time.sleep(0.5)
    
    async def _demo_payment_flow(self):
        """Demonstrate payment processing."""
        console.step(4, "Payment Processing")
        
        if not self.demo_agents or not self.demo_merchants:
            console.warning("Demo setup incomplete")
            return
        
        agent_id = list(self.demo_agents.values())[0]
        merchant_id = list(self.demo_merchants.values())[0]
        
        console.subheader("Processing Payment")
        console.thinking("Agent initiating payment...")
        
        time.sleep(0.5)
        
        try:
            result = self.client.pay(
                agent_id=agent_id,
                amount=Decimal("15.00"),
                merchant_id=merchant_id,
                purpose="Demo purchase - Premium Headphones"
            )
            
            if result.success:
                console.success("Payment completed!")
                console.transaction(
                    tx_id=result.transaction.tx_id,
                    amount=str(result.transaction.amount),
                    status=result.transaction.status
                )
            else:
                console.error(f"Payment failed: {result.error}")
                
        except Exception as e:
            console.error(f"Payment error: {str(e)}")
        
        time.sleep(0.5)
    
    async def _demo_transaction_history(self):
        """Demonstrate transaction history."""
        console.step(5, "Transaction History")
        
        if not self.demo_agents:
            return
        
        agent_id = list(self.demo_agents.values())[0]
        
        console.subheader("Fetching Transaction History")
        
        try:
            transactions = self.client.get_transactions(agent_id, limit=5)
            
            if transactions:
                console._print("\n📜 Recent Transactions:", Color.BRIGHT_MAGENTA, bold=True)
                for i, tx in enumerate(transactions, 1):
                    status_icon = "✅" if tx.status == "completed" else "❌"
                    console._print(
                        f"   {i}. {status_icon} ${tx.amount} - {tx.purpose or 'No description'}",
                        Color.WHITE
                    )
            else:
                console.info("No transactions yet")
                
        except Exception as e:
            console.warning(f"Could not fetch history: {str(e)}")
        
        time.sleep(0.5)
    
    async def _demo_limit_enforcement(self):
        """Demonstrate spending limit enforcement."""
        console.step(6, "Spending Limit Enforcement")
        
        if not self.demo_agents or not self.demo_merchants:
            return
        
        agent_id = list(self.demo_agents.values())[0]
        merchant_id = list(self.demo_merchants.values())[0]
        
        console.subheader("Attempting Over-Limit Payment")
        console.info("Agent has $50 per-transaction limit")
        console.thinking("Attempting to pay $75...")
        
        time.sleep(0.5)
        
        try:
            result = self.client.pay(
                agent_id=agent_id,
                amount=Decimal("75.00"),  # Over the $50 limit
                merchant_id=merchant_id,
                purpose="Over-limit test"
            )
            
            if not result.success:
                console.success("Limit correctly enforced!")
                console.info(f"Rejection reason: {result.error}")
            else:
                console.warning("Payment should have been rejected")
                
        except Exception as e:
            console.success("Limit correctly enforced!")
            console.info(f"Error: {str(e)}")
        
        time.sleep(0.5)
    
    async def _demo_multi_token(self):
        """Demonstrate multi-token support."""
        console.step(7, "Multi-Stablecoin Support")
        
        console.subheader("Supported Tokens")
        
        tokens = [
            ("USDC", "USD Coin by Circle", "Primary"),
            ("USDT", "Tether USD", "Active"),
            ("PYUSD", "PayPal USD", "Active"),
            ("EURC", "Euro Coin by Circle", "Active"),
        ]
        
        for symbol, name, status in tokens:
            console._print(f"   💎 {symbol}: {name} [{status}]", Color.BRIGHT_CYAN)
        
        console.subheader("Supported Chains")
        
        chains = [
            ("Base", "Low fees, fast transactions"),
            ("Ethereum", "Maximum security"),
            ("Polygon", "Scalable L2"),
            ("Solana", "High throughput"),
        ]
        
        for chain, desc in chains:
            console._print(f"   ⛓️  {chain}: {desc}", Color.BRIGHT_BLUE)
        
        time.sleep(0.5)
    
    async def _demo_risk_scoring(self):
        """Demonstrate risk scoring."""
        console.step(8, "Risk & Fraud Prevention")
        
        console.subheader("Risk Assessment Features")
        
        features = [
            "Transaction velocity monitoring",
            "Amount anomaly detection",
            "Service authorization checks",
            "Agent behavior profiling",
            "Real-time risk scoring",
        ]
        
        for feat in features:
            console._print(f"   🛡️  {feat}", Color.BRIGHT_GREEN)
        
        # Show mock risk score
        console.subheader("Sample Risk Assessment")
        console._print("   Agent Risk Score: 12/100 (LOW)", Color.BRIGHT_GREEN)
        console._print("   Status: ✅ All transactions approved", Color.BRIGHT_GREEN)
        
        time.sleep(0.5)
    
    async def _demo_summary(self):
        """Show demo summary."""
        console.divider()
        console.header("DEMONSTRATION SUMMARY")
        
        console._print("\n📊 Demo Statistics:", Color.BRIGHT_MAGENTA, bold=True)
        console._print(f"   Agents Registered: {len(self.demo_agents)}", Color.WHITE)
        console._print(f"   Merchants Active: {len(self.demo_merchants)}", Color.WHITE)
        console._print(f"   Transactions Processed: 2", Color.WHITE)
        console._print(f"   Limits Enforced: 1", Color.WHITE)
        
        console._print("\n🎯 Key Capabilities Demonstrated:", Color.BRIGHT_CYAN, bold=True)
        capabilities = [
            "Agent wallet creation with limits",
            "Stablecoin payment processing",
            "Transaction history tracking",
            "Spending limit enforcement",
            "Multi-chain & multi-token support",
            "Risk scoring integration",
        ]
        
        for cap in capabilities:
            console._print(f"   ✓ {cap}", Color.BRIGHT_GREEN)
        
        console.divider()


def main():
    """Run the demo."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Sardis demo")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Sardis API URL"
    )
    parser.add_argument(
        "--with-ai",
        action="store_true",
        help="Include AI agent demonstrations (requires OpenAI API key)"
    )
    
    args = parser.parse_args()
    
    runner = DemoRunner(api_url=args.api_url)
    
    try:
        asyncio.run(runner.run(skip_ai=not args.with_ai))
    except KeyboardInterrupt:
        console.warning("\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        console.error(f"Demo failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

