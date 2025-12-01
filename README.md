# Sardis - AI Agent Payment Infrastructure

**The Money Pipes of the AI Economy**

Sardis is a universal payment infrastructure for AI agents, enabling them to transition from planning tools to economic actors that transact in the real world.

---

## 🎯 Project Status

### ✅ Completed Phases

**Phase 1: Core Infrastructure** ✓
- Multi-token wallet system (USDC, USDT, PYUSD, EURC)
- Transaction ledger with PostgreSQL persistence
- Spending limits and risk controls
- RESTful API with FastAPI
- Python SDK for integration

**Phase 2: Blockchain Integration** ✓
- Multi-chain support (Base, Ethereum, Polygon, Solana)
- Chain abstraction layer
- On-chain settlement tracking
- Blockchain service with Web3 integration

**Phase 3: AI Agent Logic** ✓
- OpenAI GPT-4o integration for natural language processing
- Tool execution framework (pay_merchant, check_balance, list_merchants)
- Agent instruction processing via `/agents/{id}/instruct` endpoint
- Intelligent spending validation and security checks

**Phase 4: Frontend Dashboard** ✓
- React + TypeScript dashboard with Vite
- Agent management UI (create, list, view)
- Real-time chat interface for natural language commands
- Merchant and webhook management pages
- Beautiful, modern UI with Tailwind CSS

### 🚧 Current Phase: Production Readiness

**What Works Now:**
- ✅ Create AI agents with wallets and spending limits
- ✅ Chat with agents using natural language
- ✅ Agents can check balances and list merchants
- ✅ Agents validate transactions against limits
- ✅ Full database persistence (PostgreSQL)
- ✅ System wallets (treasury, fees, settlement)
- ✅ Multi-token support
- ✅ Transaction history and audit trail

**Known Limitations:**
- ⚠️ AI agents don't have conversation memory (stateless)
- ⚠️ Real blockchain transactions not yet enabled (simulated)
- ⚠️ No merchant catalog/product listings
- ⚠️ Webhook delivery not fully implemented
- ⚠️ No authentication/authorization (API keys exist but not enforced everywhere)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Node.js 18+ (for dashboard)
- OpenAI API key (for AI features)

### 1. Backend Setup

```bash
# Clone repository
git clone https://github.com/your-org/sardis.git
cd sardis

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env and add:
# - DATABASE_URL=postgresql://user:pass@localhost/sardis
# - OPENAI_API_KEY=sk-...
# - SARDIS_ADMIN_PASSWORD=your-secure-password

# Initialize database
python init_system_wallets.py

# Start backend
uvicorn sardis_core.api.main:app --reload
```

### 2. Frontend Setup

```bash
# Navigate to dashboard
cd dashboard

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Access Dashboard

Open http://localhost:3000 in your browser.

**Default credentials:**
- Username: `admin`
- Password: (set in `SARDIS_ADMIN_PASSWORD`)

---

## 💡 Core Features

### 1. AI-Powered Financial Agents

Create autonomous agents that understand natural language:

```bash
# Via Dashboard: Click "New Agent"
# Or via API:
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_sardis_demo_abc123xyz789" \
  -d '{
    "name": "Shopping Assistant",
    "owner_id": "user_123",
    "initial_balance": "100.00",
    "limit_per_tx": "50.00",
    "limit_total": "100.00"
  }'
```

### 2. Natural Language Commands

Chat with your agents:

```
User: "What's my balance?"
Agent: "Your balance is 100.00 USDC."

User: "Send 25 USDC to TechStore Electronics"
Agent: "Successfully paid 25.00 USDC to TechStore Electronics."
```

### 3. Multi-Token Wallets

Each agent has a wallet supporting:
- USDC (USD Coin)
- USDT (Tether)
- PYUSD (PayPal USD)
- EURC (Euro Coin)

### 4. Spending Controls

- **Per-transaction limits**: Maximum amount per payment
- **Total spending caps**: Lifetime spending limit
- **Balance validation**: Prevents overdrafts
- **Risk scoring**: Fraud prevention

### 5. Multi-Chain Support

Transactions can settle on:
- Base (Optimized L2, ~$0.001 fees)
- Ethereum (Mainnet, ~$1-5 fees)
- Polygon (Fast L2, ~$0.01 fees)
- Solana (High throughput, ~$0.0001 fees)

---

## 📚 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SARDIS PLATFORM                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   React      │  │   FastAPI    │  │  PostgreSQL  │      │
│  │  Dashboard   │──│   Backend    │──│   Database   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────┐        │
│  │            AI Agent Service (OpenAI)             │        │
│  └─────────────────────────────────────────────────┘        │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────┐        │
│  │         Payment & Wallet Services                │        │
│  └─────────────────────────────────────────────────┘        │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────┐        │
│  │           Blockchain Layer (Web3)                │        │
│  │  Base | Ethereum | Polygon | Solana             │        │
│  └─────────────────────────────────────────────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for detailed architecture.

---

## 🛠️ API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents` | POST | Create new agent |
| `/api/v1/agents` | GET | List all agents |
| `/api/v1/agents/{id}` | GET | Get agent details |
| `/api/v1/agents/{id}/wallet` | GET | Get agent wallet |
| `/api/v1/agents/{id}/instruct` | POST | Send natural language command |
| `/api/v1/payments` | POST | Execute payment |
| `/api/v1/merchants` | POST | Register merchant |
| `/api/v1/webhooks` | POST | Create webhook |

Full API documentation: [docs/api-reference.md](docs/api-reference.md)

---

## 🧪 Development

### Run Tests

```bash
pytest tests/ -v
```

### Project Structure

```
sardis/
├── sardis_core/              # Core backend
│   ├── ai/                   # AI agent logic
│   ├── api/                  # FastAPI routes
│   ├── chains/               # Blockchain integration
│   ├── database/             # SQLAlchemy models
│   ├── ledger/               # Transaction ledger
│   ├── models/               # Pydantic models
│   ├── services/             # Business logic
│   └── webhooks/             # Event system
├── dashboard/                # React frontend
│   ├── src/
│   │   ├── api/              # API client
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom hooks
│   │   └── pages/            # Page components
│   └── public/
├── docs/                     # Documentation
├── tests/                    # Unit tests
└── requirements.txt          # Python dependencies
```

### Database Scripts

```bash
# Initialize system wallets
python init_system_wallets.py

# Create demo API key
python create_demo_key.py

# Clean database (keep only system wallets)
python full_cleanup.py
```

---

## 📋 Roadmap

### ✅ Phase 1-4: COMPLETED
- Core infrastructure
- Blockchain integration
- AI agent logic
- Frontend dashboard

### 🎯 Phase 5: Production Readiness (CURRENT)

**Priority 1: Core Stability**
- [ ] Add conversation memory to AI agents
- [ ] Implement proper authentication/authorization
- [ ] Add rate limiting
- [ ] Comprehensive error handling
- [ ] Production logging and monitoring

**Priority 2: Features**
- [ ] Merchant product catalog
- [ ] Shopping cart functionality
- [ ] Transaction receipts
- [ ] Email notifications
- [ ] Agent performance analytics

**Priority 3: Blockchain**
- [ ] Enable real on-chain settlements
- [ ] MPC wallet integration
- [ ] Gas optimization
- [ ] Cross-chain bridging

### 🚀 Phase 6: Scale & Enterprise

- [ ] Multi-tenancy support
- [ ] Organization management
- [ ] Team collaboration
- [ ] Advanced analytics dashboard
- [ ] SLA guarantees
- [ ] Enterprise API tier

### 🌍 Phase 7: Ecosystem

- [ ] Agent marketplace
- [ ] Service discovery protocol
- [ ] Reputation system
- [ ] Programmable payment rules
- [ ] Network governance

---

## 🔒 Security

- **API Key Authentication**: All endpoints require valid API keys
- **Spending Limits**: Per-transaction and total caps
- **Risk Scoring**: Fraud detection and prevention
- **Audit Trail**: Complete transaction history
- **Secure Key Storage**: Environment-based secrets

See [docs/compliance.md](docs/compliance.md) for KYC/AML framework.

---

## 📖 Documentation

- [Architecture](docs/architecture.md) - System design and scaling
- [Blockchain Integration](docs/blockchain-integration.md) - Multi-chain setup
- [Compliance](docs/compliance.md) - KYC/AML framework
- [API Reference](docs/api-reference.md) - Complete API docs
- [Integration Guide](docs/integration-guide.md) - Developer onboarding

---

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 📞 Contact

- Website: [sardis.network](https://sardis.network)
- Twitter: [@sardis_network](https://twitter.com/sardis_network)
- Email: hello@sardis.network

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [OpenAI](https://openai.com/) - AI agent intelligence
- [React](https://react.dev/) - Frontend framework
- [PostgreSQL](https://www.postgresql.org/) - Database
- [Web3.py](https://web3py.readthedocs.io/) - Blockchain integration
