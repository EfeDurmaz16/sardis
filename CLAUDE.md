# Sardis - Claude Code Project Configuration

## Project Overview

**Sardis** is the Payment OS for the Agent Economy - infrastructure enabling AI agents to make real financial transactions safely through non-custodial MPC wallets with natural language spending policies.

**Tagline:** "AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust."

## Quick Context

- **Type:** Open-core fintech infrastructure platform
- **Primary Language:** Python 3.12 (backend), TypeScript (SDKs/frontend)
- **Framework:** FastAPI
- **Database:** PostgreSQL (Neon serverless)
- **Smart Contracts:** Solidity + Foundry
- **Frontend:** React + Vite
- **Deployment:** Vercel

## Repository Structure

```
sardis/
├── .claude/                # Claude Code configuration
│   ├── agents/             # Autonomous agent definitions
│   │   ├── social-media-agent.md
│   │   ├── product-hunt-agent.md
│   │   ├── competitor-watch-agent.md
│   │   ├── developer-relations-agent.md
│   │   └── launch-orchestrator-agent.md
│   └── skills/             # Reusable skill definitions
│       ├── social-media-content.md
│       ├── product-hunt-launch.md
│       ├── content-repurpose.md
│       ├── competitor-analysis.md
│       ├── developer-advocacy.md
│       └── launch-coordinator.md
├── sardis/                 # Simple Python SDK (public interface)
├── packages/               # Core monorepo packages
│   ├── sardis-core/        # Domain models, config, database
│   ├── sardis-api/         # FastAPI REST endpoints
│   ├── sardis-chain/       # Blockchain execution, chain routing
│   ├── sardis-protocol/    # AP2/TAP protocol verification
│   ├── sardis-wallet/      # Wallet management, MPC
│   ├── sardis-ledger/      # Append-only audit trail
│   ├── sardis-compliance/  # KYC (Persona) + AML (Elliptic)
│   ├── sardis-cards/       # Virtual cards (Lithic)
│   ├── sardis-mcp-server/  # MCP server for Claude/Cursor
│   ├── sardis-sdk-python/  # Full Python SDK
│   ├── sardis-sdk-js/      # TypeScript SDK
│   ├── sardis-cli/         # Command-line tool
│   └── sardis-checkout/    # Merchant checkout flows
├── contracts/              # Solidity smart contracts
│   └── src/
│       ├── SardisWalletFactory.sol
│       ├── SardisAgentWallet.sol
│       └── SardisEscrow.sol
├── dashboard/              # React admin dashboard
├── landing/                # Marketing website
├── api/                    # Vercel API routes
├── tests/                  # Integration tests
├── examples/               # Usage examples
├── demos/                  # Demo applications
├── docs/                   # Documentation
│   └── marketing/          # GTM content and strategies
└── scripts/                # Utility scripts
```

## Key Protocols

### AP2 (Agent Payment Protocol)
- Google, PayPal, Mastercard, Visa consortium standard
- Mandate chain: Intent → Cart → Payment
- Sardis verifies full mandate chain before execution

### TAP (Trust Anchor Protocol)
- Ed25519 and ECDSA-P256 identity verification
- Agent identity attestation

## Supported Chains & Tokens

| Chain | Tokens |
|-------|--------|
| Base | USDC, EURC |
| Polygon | USDC, USDT, EURC |
| Ethereum | USDC, USDT, PYUSD, EURC |
| Arbitrum | USDC, USDT |
| Optimism | USDC, USDT |

## Development Commands

```bash
# Python environment
uv sync                              # Install dependencies
uv run pytest tests/                 # Run tests
uv run python examples/simple_payment.py

# TypeScript SDK
pnpm install                         # Install deps
pnpm --filter @sardis/sdk build      # Build SDK
pnpm --filter @sardis/sdk test       # Test SDK

# API Server
uvicorn sardis_api.main:create_app --factory --port 8000

# Smart Contracts
cd contracts && forge build          # Compile
cd contracts && forge test           # Test

# Landing Page
cd landing && pnpm dev               # Dev server
cd landing && pnpm build             # Production build

# Dashboard
cd dashboard && pnpm dev             # Dev server
```

## Code Style Guidelines

### Python
- Use dataclasses with `@dataclass` for domain models
- Async/await for all I/O operations
- Type hints required for all functions
- Pydantic for API request/response validation
- Abstract base classes for provider interfaces

### TypeScript
- Strict TypeScript with no `any`
- Zod for runtime validation
- Async/await patterns
- Comprehensive error types

### Solidity
- Solidity 0.8.x
- OpenZeppelin contracts for standards
- Foundry for testing
- NatSpec documentation required

## Environment Variables

```bash
# Required
SARDIS_API_KEY=sk_...
DATABASE_URL=postgresql://...
TURNKEY_API_KEY=...
TURNKEY_ORGANIZATION_ID=...

# Optional
PERSONA_API_KEY=...          # KYC
ELLIPTIC_API_KEY=...         # Sanctions
LITHIC_API_KEY=...           # Virtual cards
UPSTASH_REDIS_URL=...        # Caching
```

## Architecture Principles

1. **Non-Custodial First:** Never store private keys, use MPC signing
2. **Policy Before Execution:** Every transaction must pass policy checks
3. **Fail-Closed:** Default deny on compliance/policy failures
4. **Audit Everything:** Append-only ledger for all transactions
5. **Provider Abstraction:** All external services behind interfaces

## Testing Requirements

- Unit tests for all core business logic
- Integration tests for API endpoints
- Contract tests with Foundry
- Minimum 70% coverage target

## Security Considerations

- No hardcoded secrets - use environment variables
- API keys hashed with SHA-256
- HMAC webhook signatures
- Rate limiting on all endpoints
- Replay protection via mandate cache

## Common Tasks

### Adding a New Chain
1. Add chain config to `sardis-core/src/sardis_v2_core/config.py`
2. Add token addresses to `tokens.py`
3. Update chain executor in `sardis-chain`
4. Add tests

### Adding a New Token
1. Add token to `SupportedToken` enum
2. Add contract addresses per chain
3. Update SDK types

### Creating a New API Endpoint
1. Add route in `sardis-api/src/sardis_v2_api/routes/`
2. Add request/response models
3. Add tests
4. Update OpenAPI docs

## Important Files

### Core Code
- `packages/sardis-core/src/sardis_v2_core/config.py` - Central configuration
- `packages/sardis-core/src/sardis_v2_core/spending_policy.py` - Policy engine
- `packages/sardis-chain/src/sardis_v2_chain/executor.py` - Chain execution
- `packages/sardis-protocol/src/sardis_v2_protocol/ap2.py` - AP2 verification
- `contracts/src/SardisAgentWallet.sol` - Agent wallet contract

### Marketing & GTM
- `docs/marketing/gtm-content.md` - GTM strategy, X/Reddit/PH content templates

## External Services

| Service | Purpose | Status |
|---------|---------|--------|
| Turnkey | MPC custody | ✅ Integrated |
| Persona | KYC verification | ✅ Integrated |
| Elliptic | Sanctions screening | ✅ Integrated |
| Lithic | Virtual cards | ✅ Sandbox |
| Neon | PostgreSQL | ✅ Production |
| Upstash | Redis cache | ✅ Production |

## MCP Server Usage

For Claude Desktop/Cursor integration:
```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"]
    }
  }
}
```

## Claude Code Agents & Skills

### Available Agents

| Agent | Purpose | Trigger |
|-------|---------|---------|
| `social-media-agent` | Autonomous social media content creation and scheduling | Daily 9am + events |
| `product-hunt-agent` | Product Hunt launch day management | Launch day |
| `competitor-watch-agent` | Monitor competitor activity and generate reports | Daily 8am + weekly |
| `developer-relations-agent` | DevRel, community management, documentation | Daily + GitHub/Discord events |
| `launch-orchestrator-agent` | Multi-platform launch coordination | Launch events |

### Available Skills

| Skill | Purpose |
|-------|---------|
| `/social-media-content` | Generate platform-optimized social posts |
| `/product-hunt-launch` | PH launch checklist and templates |
| `/content-repurpose` | Transform content for multiple platforms |
| `/competitor-analysis` | Analyze competitor positioning |
| `/developer-advocacy` | Create developer-focused content |
| `/launch-coordinator` | Coordinate multi-platform launches |

### Using Agents

Agents can be invoked via Claude Code Task tool:
```
Use the social-media-agent to create Twitter content for our new feature launch
```

### Using Skills

Skills are invoked with slash commands:
```
/social-media-content - Generate a Twitter thread about our MCP server
```

## Links

- Website: https://sardis.sh
- Docs: https://sardis.sh/docs
- API Docs: `/api/v2/docs`
