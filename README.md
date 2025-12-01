# Sardis

# Sardis

**The Money Pipes of the AI Economy.**

Sardis is the universal payment infrastructure for AI agents, enabling them to transition from planning tools to economic actors that transact in the real world.

---

## Core Value Proposition

### 1. Universal Payment Infrastructure for AI Agents
Sardis is the foundational layer that enables all autonomous agents to make payments in a secure and controlled manner.

### 2. Built-in Wallet for Every Agent
Developers can create stablecoin-backed wallets for their agents with a single line of code, managing balances and spending limits effortlessly.

### 3. Real Economy Integration
Enables agents to pay for real-world services such as SaaS, APIs, datasets, cloud services, or e-commerce products.

### 4. Secure Transaction Flows and Spending Guardrails
All spending is automatically audited against limits, permission policies, and risk rules. Unauthorized spending is blocked.

### 5. Virtual Card and Transaction Authorization Layer
Manages both on-chain and off-chain payments under one roof by issuing virtual cards to agents.

### 6. Onchain Settlement and Traceability
Every transaction is recorded. Companies and developers can fully track spending history.

### 7. Developer-Focused Integration
Add payment capabilities to agents in minutes via a simple SDK and API. Solves complex fintech integrations in one place.

### 8. Cross-Platform and Ecosystem Compatibility
Different agent frameworks, LLMs, and orchestrator platforms can use Sardis's standard budgeting and payment interface.

### 9. Full Control for Enterprise
Companies can centrally manage spending limits, permissions, and budget allocation for hundreds of agents via Sardis.

### 10. The Money Pipes of the AI Economy
Sardis enables agents to become true economic actors.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         SARDIS                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Agent     │  │   Wallet    │  │   Payment   │         │
│  │  Service    │  │   Service   │  │   Service   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │               │               │                   │
│         └───────────────┼───────────────┘                   │
│                         │                                    │
│  ┌──────────────────────┴──────────────────────┐            │
│  │              LEDGER LAYER                    │            │
│  └──────────────────────┬──────────────────────┘            │
│                         │                                    │
│  ┌──────────────────────┴──────────────────────┐            │
│  │         CHAIN ABSTRACTION LAYER             │            │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐    │            │
│  │  │ Base │  │ ETH  │  │ Poly │  │ Sol  │    │            │
│  │  └──────┘  └──────┘  └──────┘  └──────┘    │            │
│  └─────────────────────────────────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Payments
- [x] Agent wallet creation with spending limits
- [x] Stablecoin transfers (USDC, USDT, PYUSD, EURC)
- [x] Multi-chain support (Base, Ethereum, Polygon, Solana)
- [x] Transaction fee collection
- [x] Transaction history and audit trail

### Security & Control
- [x] Per-transaction spending limits
- [x] Total spending caps
- [x] Service authorization (whitelist recipients)
- [x] Risk scoring and fraud prevention
- [x] Virtual card abstraction
- [x] **Enterprise Organization Management** (New)

### Developer Experience
- [x] RESTful API with OpenAPI docs
- [x] Python SDK (SardisClient)
- [x] Webhook event notifications
- [x] LangChain tool integration
- [x] Shopping agent demo

### Production Ready
- [x] Architecture documentation
- [x] Blockchain integration guide
- [x] Compliance framework (KYC/AML)
- [x] Unit test coverage

---

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/your-org/sardis.git
cd sardis
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the API Server

```bash
uvicorn sardis_core.api.main:app --reload
```

### 3. Create an Agent

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_shopping_agent",
    "owner_id": "developer_1",
    "initial_balance": "100.00",
    "limit_per_tx": "20.00",
    "limit_total": "100.00"
  }'
```

### 4. Make a Payment

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_xxxxx",
    "merchant_id": "merchant_yyyyy",
    "amount": "15.99",
    "currency": "USDC",
    "purpose": "Test purchase"
  }'
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents` | POST | Register a new agent |
| `/api/v1/agents/{id}/wallet` | GET | Get wallet info |
| `/api/v1/payments` | POST | Execute a payment |
| `/api/v1/payments/request` | POST | Create payment request |
| `/api/v1/merchants` | POST | Register a merchant |
| `/api/v1/catalog/products` | GET | Browse products |
| `/api/v1/webhooks` | POST | Create webhook subscription |
| `/api/v1/risk/agents/{id}/score` | GET | Get agent risk score |

See [API Reference](docs/api-reference.md) for complete documentation.

---

## SDK Usage

```python
from sardis_sdk import SardisClient
from decimal import Decimal

# Initialize client
client = SardisClient(base_url="http://localhost:8000")

# Register an agent
response = client.register_agent(
    name="data_buyer_agent",
    owner_id="company_abc",
    initial_balance=Decimal("500.00"),
    limit_per_tx=Decimal("50.00"),
    limit_total=Decimal("500.00")
)
agent_id = response.agent.agent_id

# Check wallet balance
wallet = client.get_wallet_info(agent_id)
print(f"Balance: {wallet.balance} {wallet.currency}")

# Make a payment
result = client.pay(
    agent_id=agent_id,
    amount=Decimal("25.00"),
    merchant_id="data_provider_123",
    purpose="API access fee"
)

if result.success:
    print(f"Paid! TX: {result.transaction.tx_id}")
else:
    print(f"Failed: {result.error}")

# View transaction history
transactions = client.list_transactions(agent_id)
for tx in transactions:
    print(f"{tx.created_at}: {tx.amount} {tx.currency} - {tx.status}")
```

---

## Shopping Agent Demo

Sardis includes a LangChain-powered shopping agent that demonstrates autonomous purchasing:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Run the demo
python -m agent_demo.shopping_agent
```

The agent will:
1. Browse the product catalog
2. Check its wallet balance and limits
3. Select a product within budget
4. Execute the purchase through Sardis
5. Confirm the transaction

---

## Webhooks

Subscribe to real-time events:

```python
# Register a webhook
webhook = client.register_webhook(
    url="https://your-app.com/webhooks",
    events=["payment.completed", "payment.failed", "limit.exceeded"]
)

# Webhook payload example
{
    "id": "evt_abc123",
    "type": "payment.completed",
    "data": {
        "transaction": {
            "id": "tx_xyz789",
            "from_wallet": "wallet_agent_1",
            "to_wallet": "wallet_merchant_1",
            "amount": "15.99",
            "fee": "0.10",
            "currency": "USDC",
            "status": "completed"
        }
    },
    "created_at": "2024-01-15T10:30:00Z"
}
```

---

## Roadmap

### Phase 1: MVP (Current)
- [x] Single-chain, USDC, basic API
- [x] Agent wallets with limits
- [x] Shopping agent demo
- [x] SDK and documentation

### Phase 2: Production Ready
- [x] Multi-chain support (Base, ETH, Polygon, Solana)
- [x] Multi-token (USDC, USDT, PYUSD, EURC)
- [x] Webhooks and risk scoring
- [x] Enhanced API endpoints

### Phase 3: Scale
- [ ] Real blockchain integration (MPC wallets)
- [ ] Payment routing optimization
- [ ] Enterprise API and SLAs
- [ ] AML/Compliance layer

### Phase 4: Ecosystem
- [ ] Agent marketplace protocol
- [ ] Cross-chain bridging
- [ ] Programmable payment rules
- [ ] Network governance

---

## Revenue Model

1. **Transaction Fees**: Small percentage per transaction
2. **Subscription**: Enterprise API tiers
3. **Liquidity Spread**: Cross-chain/token conversion margins

---

## Documentation

- [Architecture](docs/architecture.md) - System design and scaling
- [Blockchain Integration](docs/blockchain-integration.md) - MPC, custody, chains
- [Compliance](docs/compliance.md) - KYC/AML framework
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Integration Guide](docs/integration-guide.md) - Developer onboarding

---

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Project Structure

```
sardis/
├── sardis_core/           # Core library
│   ├── api/               # FastAPI routes
│   ├── chains/            # Chain abstraction
│   ├── ledger/            # Transaction ledger
│   ├── models/            # Data models
│   ├── services/          # Business logic
│   └── webhooks/          # Event system
├── sardis_sdk/            # Python SDK
├── agent_demo/            # Shopping agent demo
├── tests/                 # Unit tests
├── docs/                  # Documentation
└── requirements.txt
```

---

## Why Now?

- OpenAI, Google, Anthropic are rapidly developing agent capabilities
- Stripe acquired Bridge for $1B, validating stablecoin payments
- Visa, Solana, Circle partnerships growing
- Stablecoin volumes up 30%, approaching 1/5 of Mastercard volume
- Developers want programmable money
- Regulatory clarity improving

**The agent economy needs a payment layer. Sardis is building it.**

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Contact

- Website: [sardis.network](https://sardis.network)
- Twitter: [@sardis_network](https://twitter.com/sardis_network)
- Email: hello@sardis.network
