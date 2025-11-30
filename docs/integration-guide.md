# Sardis Integration Guide

This guide walks you through integrating Sardis payment capabilities into your AI agent.

---

## Quick Start (10 Lines)

```python
from sardis_sdk import SardisClient
from decimal import Decimal

client = SardisClient()
agent = client.register_agent("my_agent", "owner_1", initial_balance=Decimal("100"))
wallet = client.get_wallet_info(agent.agent.agent_id)
print(f"Balance: {wallet.balance} {wallet.currency}")

result = client.pay(agent.agent.agent_id, Decimal("10"), "merchant_1")
print(f"Success: {result.success}, TX: {result.transaction.tx_id if result.success else result.error}")
```

---

## Installation

### Prerequisites

- Python 3.11+
- Running Sardis API server

### Install SDK

```bash
pip install sardis-sdk
```

Or clone and install locally:

```bash
git clone https://github.com/your-org/sardis.git
cd sardis
pip install -e .
```

### Start API Server

```bash
cd sardis
pip install -r requirements.txt
uvicorn sardis_core.api.main:app --reload
```

---

## Basic Integration

### 1. Initialize Client

```python
from sardis_sdk import SardisClient

# Default: localhost:8000
client = SardisClient()

# Custom URL
client = SardisClient(base_url="https://api.sardis.network")
```

### 2. Register Your Agent

Every AI agent needs to be registered once:

```python
from decimal import Decimal

response = client.register_agent(
    name="shopping_agent_v1",
    owner_id="your_developer_id",
    description="E-commerce shopping assistant",
    initial_balance=Decimal("100.00"),  # Starting funds
    limit_per_tx=Decimal("25.00"),      # Max per transaction
    limit_total=Decimal("100.00")       # Max total spending
)

agent_id = response.agent.agent_id
wallet_id = response.wallet.wallet_id

print(f"Agent created: {agent_id}")
print(f"Wallet: {wallet_id}")
print(f"Balance: {response.wallet.balance} {response.wallet.currency}")
```

### 3. Check Wallet Status

Before making payments, check your agent's wallet:

```python
wallet = client.get_wallet_info(agent_id)

print(f"Balance: {wallet.balance} {wallet.currency}")
print(f"Spent: {wallet.spent_total}")
print(f"Remaining limit: {wallet.remaining_limit}")
print(f"Per-TX limit: {wallet.limit_per_tx}")
```

### 4. Make Payments

```python
# Pay a merchant
result = client.pay(
    agent_id=agent_id,
    amount=Decimal("15.99"),
    merchant_id="merchant_electronics_1",
    purpose="Purchase: Wireless Headphones"
)

if result.success:
    tx = result.transaction
    print(f"Payment successful!")
    print(f"Transaction ID: {tx.tx_id}")
    print(f"Amount: {tx.amount} {tx.currency}")
    print(f"Fee: {tx.fee}")
    print(f"Total: {tx.total_cost}")
else:
    print(f"Payment failed: {result.error}")
```

### 5. View Transaction History

```python
transactions = client.list_transactions(agent_id, limit=10)

for tx in transactions:
    print(f"{tx.created_at}: {tx.amount} {tx.currency}")
    print(f"  Status: {tx.status}")
    print(f"  Purpose: {tx.purpose}")
```

---

## Shopping Agent Example

Complete example of an autonomous shopping agent:

```python
from sardis_sdk import SardisClient
from decimal import Decimal

class ShoppingAgent:
    def __init__(self, agent_id: str, budget: Decimal):
        self.client = SardisClient()
        self.agent_id = agent_id
        self.budget = budget
    
    def browse_products(self, category: str = None, max_price: Decimal = None):
        """Browse available products."""
        return self.client.list_products(
            category=category,
            max_price=max_price
        )
    
    def check_budget(self, price: Decimal) -> bool:
        """Check if we can afford a purchase."""
        return self.client.can_afford(self.agent_id, price)
    
    def purchase(self, product_id: str) -> dict:
        """Purchase a product."""
        # Get product details
        product = self.client.get_product(product_id)
        
        # Verify we can afford it
        if not self.check_budget(product.price):
            return {"success": False, "error": "Cannot afford this product"}
        
        # Make payment
        result = self.client.pay(
            agent_id=self.agent_id,
            amount=product.price,
            merchant_id=product.merchant_id,
            purpose=f"Purchase: {product.name}"
        )
        
        return {
            "success": result.success,
            "product": product.name,
            "amount": str(product.price),
            "tx_id": result.transaction.tx_id if result.success else None,
            "error": result.error
        }
    
    def get_balance(self) -> Decimal:
        """Get current balance."""
        wallet = self.client.get_wallet_info(self.agent_id)
        return wallet.balance


# Usage
def main():
    # Create agent with $50 budget
    client = SardisClient()
    response = client.register_agent(
        name="budget_shopper",
        owner_id="demo",
        initial_balance=Decimal("50.00"),
        limit_per_tx=Decimal("30.00"),
        limit_total=Decimal("50.00")
    )
    
    agent = ShoppingAgent(
        agent_id=response.agent.agent_id,
        budget=Decimal("50.00")
    )
    
    print(f"Starting balance: {agent.get_balance()}")
    
    # Browse electronics under $20
    products = agent.browse_products(
        category="electronics",
        max_price=Decimal("20.00")
    )
    
    print(f"Found {len(products)} products")
    
    # Buy the first affordable product
    if products:
        product = products[0]
        print(f"Purchasing: {product.name} for {product.price}")
        
        result = agent.purchase(product.product_id)
        print(f"Result: {result}")
    
    print(f"Final balance: {agent.get_balance()}")


if __name__ == "__main__":
    main()
```

---

## LangChain Integration

### Using Sardis Tools

Sardis provides LangChain tools for AI agent integration:

```python
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from sardis_sdk import SardisClient
from agent_demo.tools import create_shopping_tools

# Initialize
client = SardisClient()
agent_response = client.register_agent(
    name="langchain_shopper",
    owner_id="demo",
    initial_balance=Decimal("100.00"),
    limit_per_tx=Decimal("25.00")
)
agent_id = agent_response.agent.agent_id

# Create tools
tools = create_shopping_tools(client, agent_id)

# Create LLM
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Create prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a shopping assistant. You can:
    - browse_products: Search for products
    - check_wallet: See your balance
    - purchase_product: Buy a product
    - get_transaction_history: View past purchases
    
    Always check your budget before purchasing."""),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent
agent = create_openai_functions_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Run
result = executor.invoke({"input": "Find and buy a product under $15"})
print(result["output"])
```

### Available Tools

| Tool | Description |
|------|-------------|
| `browse_products` | Search product catalog |
| `check_wallet` | View balance and limits |
| `purchase_product` | Buy a product by ID |
| `get_transaction_history` | View past transactions |

---

## Agent Marketplace Example

Example of agents paying each other:

```python
from sardis_sdk import SardisClient
from decimal import Decimal

client = SardisClient()

# Agent A: Data processor (service provider)
processor = client.register_agent(
    name="data_processor",
    owner_id="provider_corp",
    initial_balance=Decimal("0"),  # Will receive payments
    limit_per_tx=Decimal("0"),     # No outgoing limits
    limit_total=Decimal("0")
)

# Agent B: Data buyer (client)
buyer = client.register_agent(
    name="data_buyer",
    owner_id="client_corp",
    initial_balance=Decimal("500.00"),
    limit_per_tx=Decimal("100.00"),
    limit_total=Decimal("500.00")
)

# Get processor's wallet for receiving payments
processor_wallet = client.get_wallet_info(processor.agent.agent_id)

# Buyer requests data processing and pays
result = client.pay(
    agent_id=buyer.agent.agent_id,
    amount=Decimal("25.00"),
    recipient_wallet_id=processor_wallet.wallet_id,
    purpose="Data processing job #1234"
)

if result.success:
    print(f"Payment sent: {result.transaction.tx_id}")
    
    # Check processor received funds
    processor_wallet = client.get_wallet_info(processor.agent.agent_id)
    print(f"Processor balance: {processor_wallet.balance}")
```

---

## Webhooks Integration

### Setting Up Webhooks

```python
from sardis_sdk import SardisClient

client = SardisClient()

# Register webhook endpoint
webhook = client.register_webhook(
    url="https://your-app.com/webhooks/sardis",
    events=[
        "payment.completed",
        "payment.failed",
        "limit.exceeded",
        "risk.alert"
    ]
)

print(f"Webhook ID: {webhook.subscription_id}")
print(f"Secret: {webhook.secret}")  # Save this for verification!
```

### Handling Webhooks (Flask Example)

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = "whsec_your_secret_here"

def verify_signature(payload: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.route("/webhooks/sardis", methods=["POST"])
def handle_webhook():
    # Verify signature
    signature = request.headers.get("X-Sardis-Signature")
    if not verify_signature(request.data, signature):
        return jsonify({"error": "Invalid signature"}), 401
    
    # Parse event
    event = request.json
    event_type = event["type"]
    
    # Handle event
    if event_type == "payment.completed":
        tx = event["data"]["transaction"]
        print(f"Payment completed: {tx['id']} for {tx['amount']}")
        # Update your database, send confirmation, etc.
        
    elif event_type == "payment.failed":
        tx = event["data"]["transaction"]
        print(f"Payment failed: {tx['error']}")
        # Alert user, retry logic, etc.
        
    elif event_type == "limit.exceeded":
        print(f"Limit exceeded for agent {event['data']['agent_id']}")
        # Notify agent owner
        
    elif event_type == "risk.alert":
        print(f"Risk alert: {event['data']['risk_score']}")
        # Review transaction
    
    return jsonify({"received": True}), 200
```

### Handling Webhooks (FastAPI Example)

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib

app = FastAPI()
WEBHOOK_SECRET = "whsec_your_secret_here"

@app.post("/webhooks/sardis")
async def handle_webhook(request: Request):
    # Get raw body
    body = await request.body()
    signature = request.headers.get("X-Sardis-Signature")
    
    # Verify
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse and handle
    event = await request.json()
    
    match event["type"]:
        case "payment.completed":
            await handle_payment_completed(event["data"])
        case "payment.failed":
            await handle_payment_failed(event["data"])
        case _:
            pass  # Ignore unknown events
    
    return {"received": True}
```

---

## Best Practices

### 1. Set Appropriate Limits

```python
# For testing
agent = client.register_agent(
    name="test_agent",
    owner_id="dev",
    initial_balance=Decimal("10.00"),    # Small amount
    limit_per_tx=Decimal("5.00"),         # Very limited
    limit_total=Decimal("10.00")
)

# For production shopping agent
agent = client.register_agent(
    name="prod_shopper",
    owner_id="company_xyz",
    initial_balance=Decimal("1000.00"),
    limit_per_tx=Decimal("100.00"),       # Reasonable per-purchase
    limit_total=Decimal("1000.00")
)
```

### 2. Always Check Before Paying

```python
def safe_purchase(client, agent_id, amount, merchant_id):
    # Check affordability first
    if not client.can_afford(agent_id, amount):
        wallet = client.get_wallet_info(agent_id)
        return {
            "success": False,
            "error": f"Cannot afford. Balance: {wallet.balance}, Need: {amount}"
        }
    
    # Proceed with payment
    result = client.pay(agent_id, amount, merchant_id)
    return result
```

### 3. Handle Errors Gracefully

```python
from sardis_sdk import SardisClient, SardisError

try:
    result = client.pay(agent_id, amount, merchant_id)
except SardisError as e:
    if e.status_code == 400:
        print(f"Bad request: {e.detail}")
    elif e.status_code == 404:
        print(f"Not found: {e.detail}")
    elif e.status_code == 429:
        print("Rate limited, retrying...")
        time.sleep(1)
        # Retry
    else:
        raise
```

### 4. Authorize Known Services

Reduce risk scores by pre-authorizing trusted merchants:

```python
# Authorize services your agent will pay
client.authorize_service(agent_id, "merchant_amazon")
client.authorize_service(agent_id, "merchant_openai_api")
client.authorize_service(agent_id, "merchant_data_provider")

# List authorized services
services = client.list_authorized_services(agent_id)
```

### 5. Monitor Spending

```python
def check_spending_status(client, agent_id):
    wallet = client.get_wallet_info(agent_id)
    
    spent_pct = (wallet.spent_total / wallet.limit_total) * 100
    
    print(f"Spent: {wallet.spent_total} / {wallet.limit_total}")
    print(f"Usage: {spent_pct:.1f}%")
    
    if spent_pct > 80:
        print("WARNING: Approaching spending limit!")
    
    return spent_pct
```

### 6. Use Webhooks for Real-Time Updates

Instead of polling, use webhooks:

```python
# Good: Webhook-based
@app.post("/webhooks/sardis")
async def handle_payment(event):
    if event["type"] == "payment.completed":
        await update_order_status(event["data"])

# Avoid: Polling
while True:
    transactions = client.list_transactions(agent_id)
    # Check for new transactions
    time.sleep(5)  # Don't do this!
```

---

## Troubleshooting

### Payment Failed: Insufficient Balance

```python
result = client.pay(agent_id, Decimal("50.00"), merchant_id)
# Error: Insufficient balance: have 30.00, need 50.10

# Solution: Check balance first
wallet = client.get_wallet_info(agent_id)
print(f"Available: {wallet.balance}")
print(f"Fee estimate: {client.estimate_payment(Decimal('50.00')).fee}")
```

### Payment Failed: Limit Exceeded

```python
result = client.pay(agent_id, Decimal("100.00"), merchant_id)
# Error: Amount exceeds per-transaction limit of 50.00

# Solution: Check limits
wallet = client.get_wallet_info(agent_id)
print(f"Per-TX limit: {wallet.limit_per_tx}")
print(f"Remaining total: {wallet.remaining_limit}")
```

### Agent Not Found

```python
wallet = client.get_wallet_info("agent_xyz")
# Error: Agent agent_xyz not found

# Solution: Verify agent ID from registration
response = client.register_agent(...)
correct_id = response.agent.agent_id  # Use this
```

### Webhook Not Received

1. Check URL is publicly accessible
2. Verify endpoint returns 2xx status
3. Test with `POST /webhooks/{id}/test`
4. Check webhook stats for failures:

```python
webhook = client.get_webhook(subscription_id)
print(f"Total: {webhook.total_deliveries}")
print(f"Success: {webhook.successful_deliveries}")
print(f"Failed: {webhook.failed_deliveries}")
```

---

## Support

- **Docs**: https://docs.sardis.network
- **API Reference**: [docs/api-reference.md](api-reference.md)
- **GitHub**: https://github.com/your-org/sardis
- **Discord**: https://discord.gg/sardis
- **Email**: support@sardis.network

