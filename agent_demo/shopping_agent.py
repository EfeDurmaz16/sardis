"""Shopping agent that uses Sardis for payments."""

import os
from decimal import Decimal
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from sardis_sdk import SardisClient
from .tools import create_shopping_tools


class ShoppingAgent:
    """
    AI Shopping Agent powered by LangChain and Sardis payments.
    
    This agent can:
    - Browse product catalogs
    - Check wallet balance and limits
    - Make purchasing decisions based on goals
    - Execute payments through Sardis
    
    Example usage:
        ```python
        agent = ShoppingAgent(
            agent_id="agent_123",
            sardis_url="http://localhost:8000"
        )
        
        result = agent.shop("Find and buy a product under $15")
        print(result)
        ```
    """
    
    SYSTEM_PROMPT = """You are a shopping assistant AI agent. You have access to a wallet 
through the Sardis payment system and can browse products and make purchases.

Your responsibilities:
1. Understand the user's shopping goal
2. Browse available products to find suitable options
3. Check your wallet balance to ensure you can afford the purchase
4. Make smart purchasing decisions based on the goal and constraints
5. Execute the purchase through the Sardis payment system

Important rules:
- ALWAYS check your wallet balance before making a purchase
- NEVER exceed your spending limits
- Choose products that best match the user's requirements
- If multiple products match, prefer the one that provides best value
- If you cannot afford a product, explain why and suggest alternatives
- Report the transaction details after a successful purchase

When browsing products, you can filter by:
- Category (e.g., 'electronics', 'office')
- Maximum price

When making a purchase, you'll pay:
- Product price
- Small transaction fee (0.10 USDC)

Be helpful, efficient, and transparent about all financial operations."""

    def __init__(
        self,
        agent_id: str,
        sardis_url: str = "http://localhost:8000",
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        verbose: bool = True
    ):
        """
        Initialize the shopping agent.
        
        Args:
            agent_id: The Sardis agent ID (must be registered with Sardis)
            sardis_url: URL of the Sardis API server
            openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: OpenAI model to use
            temperature: LLM temperature (0.0 for deterministic)
            verbose: Whether to print agent reasoning
        """
        self.agent_id = agent_id
        self.sardis_url = sardis_url
        self.verbose = verbose
        
        # Initialize Sardis client
        self.sardis_client = SardisClient(base_url=sardis_url)
        
        # Initialize LLM
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY or pass openai_api_key.")
        
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key
        )
        
        # Create tools
        self.tools = create_shopping_tools(self.sardis_client, agent_id)
        
        # Create agent using LangGraph's prebuilt ReAct agent
        # Use prompt parameter instead of state_modifier
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=self.SYSTEM_PROMPT
        )
    
    def shop(self, goal: str) -> str:
        """
        Execute a shopping task.
        
        Args:
            goal: Natural language shopping goal
                  (e.g., "Find and buy a product under $15")
        
        Returns:
            Agent's response with shopping results
        """
        # Run the agent
        result = self.agent.invoke({"messages": [("human", goal)]})
        
        # Extract the final response
        messages = result.get("messages", [])
        if messages:
            # Get the last AI message
            for msg in reversed(messages):
                if hasattr(msg, 'content') and msg.content:
                    return msg.content
        
        return "No response from agent"
    
    def check_balance(self) -> str:
        """Quick helper to check current wallet balance."""
        try:
            wallet = self.sardis_client.get_wallet_info(self.agent_id)
            return f"Balance: {wallet.balance} {wallet.currency}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def close(self):
        """Close the Sardis client connection."""
        self.sardis_client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


def run_demo():
    """Run a demo of the shopping agent."""
    import httpx
    
    print("=" * 60)
    print("SARDIS SHOPPING AGENT DEMO")
    print("=" * 60)
    
    # Configuration
    SARDIS_URL = os.getenv("SARDIS_URL", "http://localhost:8000")
    AGENT_NAME = "shopping_demo_agent"
    OWNER_ID = "demo_developer"
    INITIAL_BALANCE = Decimal("100.00")
    LIMIT_PER_TX = Decimal("20.00")
    
    print(f"\n1. Connecting to Sardis API at {SARDIS_URL}...")
    
    # First, register the agent with Sardis via API
    with httpx.Client() as http_client:
        try:
            # Check if server is running
            health = http_client.get(f"{SARDIS_URL}/health")
            if health.status_code != 200:
                print("ERROR: Sardis API is not running!")
                print("Please start the API server first:")
                print("  cd sardis && ./venv/bin/uvicorn sardis_core.api.main:app --reload")
                return
        except httpx.ConnectError:
            print("ERROR: Cannot connect to Sardis API!")
            print("Please start the API server first:")
            print("  cd sardis && ./venv/bin/uvicorn sardis_core.api.main:app --reload")
            return
        
        print("\n2. Registering agent with Sardis...")
        response = http_client.post(
            f"{SARDIS_URL}/api/v1/agents",
            json={
                "name": AGENT_NAME,
                "owner_id": OWNER_ID,
                "description": "Demo shopping agent",
                "initial_balance": str(INITIAL_BALANCE),
                "limit_per_tx": str(LIMIT_PER_TX),
                "limit_total": str(INITIAL_BALANCE)
            }
        )
        
        if response.status_code != 201:
            print(f"Failed to register agent: {response.text}")
            return
        
        agent_data = response.json()
        agent_id = agent_data["agent"]["agent_id"]
        wallet = agent_data["wallet"]
        
        print(f"   Agent ID: {agent_id}")
        print(f"   Wallet ID: {wallet['wallet_id']}")
        print(f"   Balance: {wallet['balance']} {wallet['currency']}")
        print(f"   Limit per TX: {wallet['limit_per_tx']} {wallet['currency']}")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\nERROR: OPENAI_API_KEY environment variable not set!")
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        return
    
    print("\n3. Creating shopping agent...")
    with ShoppingAgent(
        agent_id=agent_id,
        sardis_url=SARDIS_URL,
        verbose=True
    ) as agent:
        
        print(f"\n4. Current balance: {agent.check_balance()}")
        
        # Shopping goals to demonstrate
        goals = [
            "Check my wallet balance and available spending limits.",
            "Browse all available products and tell me what's available.",
            "Find and buy a product that costs under $15. Choose the best value option."
        ]
        
        for i, goal in enumerate(goals, 1):
            print(f"\n{'=' * 60}")
            print(f"TASK {i}: {goal}")
            print("=" * 60)
            
            result = agent.shop(goal)
            print(f"\nRESULT:\n{result}")
        
        print(f"\n5. Final balance: {agent.check_balance()}")
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
