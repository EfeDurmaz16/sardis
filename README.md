# Sardis - Payment Infrastructure for AI Agents

Sardis is a payment layer that enables AI agents to pay for things online using stablecoins with strict spending limits. This MVP demonstrates a realistic infrastructure where agents can browse products, check their wallet balance, and execute purchases through a controlled payment system.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SARDIS INFRASTRUCTURE                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   API Layer  │───▶│  Core Logic  │───▶│    Ledger    │       │
│  │   (FastAPI)  │    │ (Limits/Fees)│    │  (In-Memory) │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         ▲                                       │                │
│         │                                       ▼                │
│  ┌──────────────┐                      ┌──────────────┐         │
│  │ SardisClient │                      │   Wallets    │         │
│  │    (SDK)     │                      │  + V-Cards   │         │
│  └──────────────┘                      └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
         ▲
         │
┌────────┴────────┐
│  Shopping Agent │  (LangChain + OpenAI GPT-4)
│   + Mock Store  │
└─────────────────┘
```

## Features

- **Agent Wallets**: Each AI agent gets its own wallet with USDC balance
- **Spending Limits**: Per-transaction and total spending limits prevent runaway costs
- **Transaction Fees**: Configurable fee model (0.10 USDC per transaction in MVP)
- **Virtual Cards**: Each wallet has a virtual card identity for payment abstraction
- **Audit Trail**: Full transaction history for compliance and debugging
- **REST API**: Developer-friendly API for integrations
- **Python SDK**: Simple client library for agent integration
- **LangChain Tools**: Ready-to-use tools for AI agents

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key (for the agent demo)

### Installation

```bash
# Clone the repository
cd sardis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the API Server

```bash
# Start the Sardis API server
uvicorn sardis_core.api.main:app --reload

# The API will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sardis_core
```

### Running the Shopping Agent Demo

```bash
# Set your OpenAI API key
export OPENAI_API_KEY='your-api-key-here'

# Make sure the API server is running in another terminal
# Then run the demo
python -m agent_demo.shopping_agent
```

## API Reference

### Base URL
```
http://localhost:8000/api/v1
```

### Agents

#### Register an Agent
```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "shopping_agent_1",
    "owner_id": "developer_123",
    "description": "My shopping assistant",
    "initial_balance": "100.00",
    "limit_per_tx": "20.00",
    "limit_total": "100.00"
  }'
```

Response:
```json
{
  "agent": {
    "agent_id": "agent_abc123",
    "name": "shopping_agent_1",
    "owner_id": "developer_123",
    "wallet_id": "wallet_xyz789",
    "is_active": true
  },
  "wallet": {
    "wallet_id": "wallet_xyz789",
    "balance": "100.00",
    "currency": "USDC",
    "limit_per_tx": "20.00",
    "limit_total": "100.00",
    "spent_total": "0.00",
    "remaining_limit": "100.00"
  }
}
```

#### Get Agent Wallet
```bash
curl http://localhost:8000/api/v1/agents/{agent_id}/wallet
```

### Payments

#### Make a Payment
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_abc123",
    "amount": "14.99",
    "merchant_id": "merchant_xyz",
    "purpose": "Purchase: Wireless Headphones"
  }'
```

Response:
```json
{
  "success": true,
  "transaction": {
    "tx_id": "tx_abc123def456",
    "from_wallet": "wallet_xyz789",
    "to_wallet": "merchant_wallet_xyz",
    "amount": "14.99",
    "fee": "0.10",
    "total_cost": "15.09",
    "currency": "USDC",
    "status": "completed"
  }
}
```

#### Estimate Payment Cost
```bash
curl "http://localhost:8000/api/v1/payments/estimate?amount=10.00"
```

#### List Agent Transactions
```bash
curl http://localhost:8000/api/v1/payments/agent/{agent_id}
```

### Catalog

#### Browse Products
```bash
# List all products
curl http://localhost:8000/api/v1/catalog/products

# Filter by category and max price
curl "http://localhost:8000/api/v1/catalog/products?category=electronics&max_price=30"
```

### Merchants

#### Register a Merchant
```bash
curl -X POST http://localhost:8000/api/v1/merchants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TechStore",
    "description": "Electronics retailer",
    "category": "electronics"
  }'
```

## SDK Usage

### Basic Usage

```python
from decimal import Decimal
from sardis_sdk import SardisClient

# Initialize the client
client = SardisClient(base_url="http://localhost:8000")

# Check wallet balance
wallet = client.get_wallet_info("agent_123")
print(f"Balance: {wallet.balance} {wallet.currency}")

# Check if agent can afford a purchase
if client.can_afford("agent_123", Decimal("10.00")):
    # Make a payment
    result = client.pay(
        agent_id="agent_123",
        amount=Decimal("10.00"),
        merchant_id="merchant_456",
        purpose="Purchase item XYZ"
    )
    
    if result.success:
        print(f"Payment successful! TX: {result.transaction.tx_id}")
    else:
        print(f"Payment failed: {result.error}")

# Browse products
products = client.list_products(max_price=Decimal("20.00"))
for product in products:
    print(f"{product.name}: {product.price} {product.currency}")

# Get transaction history
transactions = client.list_transactions("agent_123")
for tx in transactions:
    print(f"{tx.tx_id}: {tx.amount} {tx.currency} - {tx.status}")
```

### Using with LangChain Agents

```python
from agent_demo.shopping_agent import ShoppingAgent

# Create a shopping agent
agent = ShoppingAgent(
    agent_id="agent_123",  # Must be pre-registered with Sardis
    sardis_url="http://localhost:8000",
    verbose=True
)

# Give the agent a shopping task
result = agent.shop("Find and buy a product under $15")
print(result)
```

## Project Structure

```
sardis/
├── sardis_core/              # Core backend infrastructure
│   ├── models/               # Data models (Agent, Wallet, Transaction)
│   ├── ledger/               # Blockchain abstraction layer
│   ├── services/             # Business logic (payments, limits, fees)
│   ├── api/                  # FastAPI routes and schemas
│   └── config.py             # Configuration settings
├── sardis_sdk/               # Python SDK for developers
│   └── client.py             # SardisClient class
├── agent_demo/               # Example AI shopping agent
│   ├── tools.py              # LangChain tools for Sardis
│   └── shopping_agent.py     # Shopping agent implementation
├── tests/                    # Unit tests
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Configuration

Configuration is done via environment variables or a `.env` file:

```bash
# API Settings
SARDIS_API_HOST=0.0.0.0
SARDIS_API_PORT=8000

# Fee Settings
SARDIS_TRANSACTION_FEE=0.10

# OpenAI (for agent demo)
OPENAI_API_KEY=your-api-key-here
```

## Fee Model

The MVP uses a simple flat fee model:
- **Transaction Fee**: 0.10 USDC per transaction
- Fees are collected in a system fee pool
- Fee logic is centralized in `FeeService` for easy modification

## Security Considerations (MVP)

This MVP implements basic security patterns:
- **Custodial Wallets**: The system controls all funds
- **Input Validation**: All API inputs are validated
- **Spending Limits**: Enforced at multiple levels
- **No Private Keys**: No cryptographic keys in code

For production, you would add:
- API key authentication
- Rate limiting
- Audit logging
- Real blockchain integration

## Future Enhancements

The architecture is designed for extension:

1. **Real Blockchain Integration**: The `BaseLedger` interface allows swapping the in-memory ledger for a real blockchain (Base, Polygon, etc.)

2. **Advanced Fee Models**: The `FeeService` can be extended for percentage-based or tiered fees

3. **Multiple Currencies**: The currency field supports future multi-token support

4. **Real Card Networks**: Virtual cards can be connected to actual card issuers

5. **Enhanced Agent Frameworks**: Swap LangChain for other agent frameworks

## Demo Flow

1. **Developer registers an agent** with Sardis (100 USDC balance, 20 USDC/tx limit)
2. **Shopping Agent receives a goal**: "Find and buy a product under $15"
3. **Agent browses** the product catalog via API
4. **Agent selects** a product matching the constraints
5. **Agent calls Sardis** to execute the payment
6. **Sardis validates** balance and limits, applies fee, records transaction
7. **Agent receives** confirmation of successful purchase

## License

MIT

