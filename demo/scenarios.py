"""Realistic multi-step demo scenarios."""

import asyncio
import time
from decimal import Decimal
from typing import Optional

from demo.console import console, Color
from sardis_sdk import SardisClient


class ScenarioRunner:
    """Runs specific demo scenarios."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.client = SardisClient(base_url=api_url)
    
    def close(self):
        self.client.close()
    
    async def run_shopping_scenario(self):
        """
        Scenario: AI Shopping Agent
        
        An AI agent browses a catalog, compares prices,
        checks its budget, and makes an optimized purchase.
        """
        console.header("SCENARIO: AI Shopping Agent")
        console.info("Demonstrating autonomous product discovery and purchase")
        console.divider()
        
        # Setup
        console.step(1, "Register Shopping Agent")
        
        agent = self.client.register_agent(
            name="smart_shopper",
            owner_id="scenario_owner",
            description="Intelligent shopping agent",
            initial_balance=Decimal("75.00"),
            limit_per_tx=Decimal("40.00"),
            limit_total=Decimal("75.00")
        )
        agent_id = agent.agent.agent_id
        
        console.agent_info("shopping", agent_id)
        console.wallet_status(
            balance="75.00",
            spent="0.00",
            remaining="75.00"
        )
        
        # Register merchant
        merchant = self.client.register_merchant(
            name="Smart Electronics",
            category="electronics"
        )
        
        # Step 2: Browse catalog
        console.step(2, "Browse Product Catalog")
        console.thinking("Agent analyzing available products...")
        time.sleep(1)
        
        # Simulated catalog browsing
        products = [
            {"name": "Wireless Mouse", "price": "29.99", "rating": 4.5},
            {"name": "USB Hub", "price": "19.99", "rating": 4.2},
            {"name": "Webcam HD", "price": "49.99", "rating": 4.7},
        ]
        
        console._print("\n📦 Products Found:", Color.BRIGHT_CYAN)
        for p in products:
            console._print(
                f"   • {p['name']}: ${p['price']} (★{p['rating']})",
                Color.WHITE
            )
        
        # Step 3: Budget check
        console.step(3, "Check Budget Constraints")
        
        wallet = self.client.get_wallet_info(agent_id)
        console.info(f"Available: ${wallet.balance}")
        console.info(f"Per-TX Limit: ${wallet.limit_per_tx}")
        
        # Step 4: Decision making
        console.step(4, "Agent Decision Making")
        console.thinking("Evaluating best value purchase...")
        time.sleep(1)
        
        console._print("\n🧠 Agent Analysis:", Color.BRIGHT_YELLOW)
        console._print("   • Webcam exceeds limit ($49.99 > $40)", Color.WHITE)
        console._print("   • USB Hub offers good value", Color.WHITE)
        console._print("   • Mouse has best rating in budget", Color.WHITE)
        console._print("\n   Decision: Purchase Wireless Mouse", Color.BRIGHT_GREEN, bold=True)
        
        # Step 5: Purchase
        console.step(5, "Execute Purchase")
        
        result = self.client.pay(
            agent_id=agent_id,
            amount=Decimal("29.99"),
            merchant_id=merchant.merchant_id,
            purpose="Wireless Mouse - Best value purchase"
        )
        
        if result.success:
            console.success("Purchase completed!")
            console.transaction(
                tx_id=result.transaction.tx_id,
                amount=str(result.transaction.amount),
                status="completed"
            )
        
        # Step 6: Updated status
        console.step(6, "Updated Wallet Status")
        
        wallet = self.client.get_wallet_info(agent_id)
        console.wallet_status(
            balance=str(wallet.balance),
            spent=str(wallet.spent_total),
            remaining=str(wallet.remaining_limit)
        )
        
        console.divider()
        console.success("Shopping scenario complete!")
    
    async def run_data_marketplace_scenario(self):
        """
        Scenario: Data Marketplace
        
        An AI agent discovers data sources, evaluates pricing,
        and purchases API access for its operations.
        """
        console.header("SCENARIO: Data Marketplace")
        console.info("AI agent purchasing API access and data")
        console.divider()
        
        # Setup
        console.step(1, "Setup Data Buyer Agent")
        
        agent = self.client.register_agent(
            name="data_analyst",
            owner_id="data_scenario_owner",
            initial_balance=Decimal("50.00"),
            limit_per_tx=Decimal("20.00"),
            limit_total=Decimal("50.00")
        )
        agent_id = agent.agent.agent_id
        
        # Data provider merchant
        provider = self.client.register_merchant(
            name="DataStream API",
            category="data_services"
        )
        
        console.agent_info("data_buyer", agent_id)
        
        # Step 2: Discover data sources
        console.step(2, "Discover Data Sources")
        console.thinking("Searching data marketplace...")
        time.sleep(1)
        
        data_sources = [
            {"name": "Weather API", "price": "5.00", "type": "weather"},
            {"name": "Stock Data Feed", "price": "15.00", "type": "financial"},
            {"name": "Social Trends", "price": "10.00", "type": "social"},
        ]
        
        console._print("\n📊 Data Sources Available:", Color.BRIGHT_CYAN)
        for ds in data_sources:
            console._print(
                f"   • {ds['name']}: ${ds['price']}/month ({ds['type']})",
                Color.WHITE
            )
        
        # Step 3: Evaluate needs
        console.step(3, "Evaluate Data Requirements")
        console.thinking("Analyzing data needs...")
        time.sleep(0.5)
        
        console._print("\n🎯 Agent Requirements:", Color.BRIGHT_YELLOW)
        console._print("   • Need weather data for predictions", Color.WHITE)
        console._print("   • Budget: Under $20 per source", Color.WHITE)
        console._print("   • Priority: Weather > Social > Financial", Color.WHITE)
        
        # Step 4: Purchase access
        console.step(4, "Purchase Data Access")
        
        # Purchase weather API
        result1 = self.client.pay(
            agent_id=agent_id,
            amount=Decimal("5.00"),
            merchant_id=provider.merchant_id,
            purpose="Weather API - Monthly access"
        )
        
        if result1.success:
            console.success("Weather API access granted!")
            console._print(f"   API Key: WEATHER_API_{agent_id[:8]}", Color.DIM)
        
        # Purchase social trends
        result2 = self.client.pay(
            agent_id=agent_id,
            amount=Decimal("10.00"),
            merchant_id=provider.merchant_id,
            purpose="Social Trends API - Monthly access"
        )
        
        if result2.success:
            console.success("Social Trends API access granted!")
            console._print(f"   API Key: SOCIAL_API_{agent_id[:8]}", Color.DIM)
        
        # Step 5: Summary
        console.step(5, "Access Summary")
        
        wallet = self.client.get_wallet_info(agent_id)
        
        console._print("\n🔑 Purchased Access:", Color.BRIGHT_GREEN)
        console._print("   ✓ Weather API (Real-time)", Color.WHITE)
        console._print("   ✓ Social Trends (Daily)", Color.WHITE)
        
        console.wallet_status(
            balance=str(wallet.balance),
            spent=str(wallet.spent_total),
            remaining=str(wallet.remaining_limit)
        )
        
        console.divider()
        console.success("Data marketplace scenario complete!")
    
    async def run_agent_to_agent_scenario(self):
        """
        Scenario: Agent-to-Agent Payment
        
        One AI agent pays another for completing a task.
        """
        console.header("SCENARIO: Agent-to-Agent Payment")
        console.info("AI agents transacting with each other")
        console.divider()
        
        # Setup two agents
        console.step(1, "Register Two AI Agents")
        
        # Agent A - the customer
        agent_a = self.client.register_agent(
            name="agent_customer",
            owner_id="a2a_owner",
            initial_balance=Decimal("100.00"),
            limit_per_tx=Decimal("50.00"),
            limit_total=Decimal("100.00")
        )
        
        # Agent B - the service provider (as merchant)
        agent_b = self.client.register_merchant(
            name="Agent B Service Provider",
            category="ai_services"
        )
        
        console._print("\n🤖 Agent A (Customer):", Color.BRIGHT_CYAN)
        console._print(f"   ID: {agent_a.agent.agent_id}", Color.DIM)
        console._print(f"   Balance: $100.00 USDC", Color.WHITE)
        
        console._print("\n🤖 Agent B (Service Provider):", Color.BRIGHT_MAGENTA)
        console._print(f"   ID: {agent_b.merchant_id}", Color.DIM)
        console._print(f"   Service: Document Summarization", Color.WHITE)
        
        # Step 2: Service request
        console.step(2, "Agent A Requests Service")
        console.thinking("Agent A needs document summarization...")
        time.sleep(0.5)
        
        console._print("\n📋 Service Request:", Color.BRIGHT_YELLOW)
        console._print("   Task: Summarize 10 documents", Color.WHITE)
        console._print("   Price: $5.00 per document", Color.WHITE)
        console._print("   Total: $50.00 USDC", Color.WHITE)
        
        # Step 3: Payment
        console.step(3, "Agent A Pays Agent B")
        
        result = self.client.pay(
            agent_id=agent_a.agent.agent_id,
            amount=Decimal("50.00"),
            merchant_id=agent_b.merchant_id,
            purpose="Document summarization - 10 documents"
        )
        
        if result.success:
            console.success("Payment completed!")
            console.transaction(
                tx_id=result.transaction.tx_id,
                amount="50.00",
                status="completed"
            )
        
        # Step 4: Service delivery
        console.step(4, "Agent B Delivers Service")
        console.thinking("Agent B processing documents...")
        time.sleep(1)
        
        console._print("\n✅ Service Delivered:", Color.BRIGHT_GREEN)
        console._print("   • 10 documents summarized", Color.WHITE)
        console._print("   • Results returned to Agent A", Color.WHITE)
        
        # Step 5: Final status
        console.step(5, "Transaction Complete")
        
        wallet = self.client.get_wallet_info(agent_a.agent.agent_id)
        
        console._print("\n🤖 Agent A Status:", Color.BRIGHT_CYAN)
        console._print(f"   Remaining: ${wallet.balance} USDC", Color.WHITE)
        console._print(f"   Spent: ${wallet.spent_total} USDC", Color.WHITE)
        
        console._print("\n🤖 Agent B Status:", Color.BRIGHT_MAGENTA)
        console._print("   Received: $50.00 USDC", Color.WHITE)
        console._print("   Task: Completed", Color.WHITE)
        
        console.divider()
        console.success("Agent-to-agent scenario complete!")


async def run_all_scenarios():
    """Run all demo scenarios."""
    runner = ScenarioRunner()
    
    try:
        console.logo()
        console.header("SARDIS SCENARIO DEMONSTRATIONS")
        console.info("Running realistic multi-step scenarios")
        console.divider()
        
        await runner.run_shopping_scenario()
        time.sleep(1)
        
        await runner.run_data_marketplace_scenario()
        time.sleep(1)
        
        await runner.run_agent_to_agent_scenario()
        
        console.header("ALL SCENARIOS COMPLETE")
        console.success("Successfully demonstrated all Sardis capabilities!")
        
    finally:
        runner.close()


if __name__ == "__main__":
    asyncio.run(run_all_scenarios())

