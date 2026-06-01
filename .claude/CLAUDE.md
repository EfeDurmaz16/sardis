# Sardis - Claude Code Project Configuration

## ⚠️ Diligence Rule (READ FIRST)

**Before making any factual claim about this codebase — integrations, packages, chain support, deployment state, version numbers, or traction metrics — you MUST verify against the live system, not this doc.**

- **Package list?** Run `ls packages/` — there are exactly **3** published packages: `sardis` (Python umbrella), `sardis-js` (TS SDK, npm name `sardis`), `sardis-mcp-server`. The old 30+ `sardis-*` packages were consolidated into these in May 2026. Not "56", not "12+".
- **Chain support?** Read `packages/sardis/src/sardis/core/config.py` (`ChainConfig` entries) and `packages/sardis/src/sardis/core/tokens.py` (`contract_addresses` maps) — not this file.
- **Integrations?** Glob `packages/sardis/src/sardis/integrations/` — they are submodules now, not separate packages.
- **Deployment state?** Check Cloud Run / Vercel / block explorers — not memory, not docs.
- **Repo structure?** Read [`ARCHITECTURE.md`](../ARCHITECTURE.md) — the canonical, code-accurate map.

This doc is a **starting point**, not the source of truth. It drifts. It has drifted. If you catch a claim here that conflicts with the codebase, **trust the code and update this file.**

## Project Overview

**Sardis** is the Payment OS for the Agent Economy - infrastructure enabling AI agents to make real financial transactions safely through non-custodial MPC wallets with natural language spending policies.

**Tagline:** "AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust."

## Quick Context

- **Type:** Open-core fintech infrastructure platform
- **Primary Language:** Python 3.12 (backend), TypeScript (SDKs/frontend)
- **Framework:** FastAPI
- **Database:** PostgreSQL (Neon serverless)
- **Smart Contracts:** Solidity + Foundry
- **Frontend:** Next.js public landing/docs surfaces; hosted product UI source is private
- **Deployment:** Vercel

## Repository Structure

Canonical, code-accurate map: [`ARCHITECTURE.md`](../ARCHITECTURE.md). The
current tree (post May-2026 consolidation):

```
sardis/
├── apps/api/server/        # Reference FastAPI service (routes/, providers/, dependencies.py, lifespan.py)
├── apps/landing/           # Public landing/docs website
├── packages/               # Exactly 3 published packages
│   ├── sardis/              # Python umbrella: thin Sardis client + in-repo runtime core
│   │   └── src/sardis/      #   core/ chain/ protocol/ wallet/ ledger/ cards/ compliance/
│   │       └── integrations/#   langchain, crewai, openai_agents, anthropic, adk, a2a, ... (submodules)
│   ├── sardis-js/           # TypeScript SDK (npm name: `sardis`)
│   └── sardis-mcp-server/   # MCP server (npm: `@sardis/mcp-server`)
├── contracts/              # Solidity (Foundry): SardisWalletFactory / SardisAgentWallet / SardisEscrow
├── examples/               # Single-concept runnable scripts (see examples/README.md)
├── demos/                  # Larger end-to-end scenarios (see demos/README.md)
├── docs/                   # Public docs incl. docs/oss/ (OSS policy) and docs/architecture/
├── tests/                  # Legacy root migration backlog; prefer package tests
└── scripts/                # Contributor gate + repo-hygiene checkers
```

The old per-package tree (`sardis-core`, `sardis-langchain`, `sardis-coinbase`,
…, 30+ entries) no longer exists — those are now submodules under
`packages/sardis/src/sardis/`. Do not cite them as packages.

## Key Protocols

### AP2 (Agent Payment Protocol)
- Google, PayPal, Mastercard, Visa consortium standard
- Mandate chain: Intent → Cart → Payment
- Sardis verifies full mandate chain before execution

### TAP (Trust Anchor Protocol)
- Ed25519 and ECDSA-P256 identity verification
- Agent identity attestation

## Supported Chains & Tokens

**Source of truth:** `packages/sardis/src/sardis/core/config.py` (`ChainConfig` list) and `packages/sardis/src/sardis/core/tokens.py` (`contract_addresses` map). Verify against the code before quoting in any pitch / investor deck / marketing copy — this table drifts.

**Production mainnets (live, from `config.py`):**

| Chain | Chain ID | Tokens | Status |
|-------|---------|--------|--------|
| **Base** | 8453 | USDC, EURC | ✅ Production (primary) |
| **Tempo** | 4217 | USDC, USDC.e, EURC | ✅ Production (MPP launch day, 2026-03-18) |

**Additional mainnets with token contracts configured in `tokens.py`:**

| Chain | Tokens |
|-------|--------|
| Ethereum | USDC, USDT, PYUSD, EURC |
| Polygon | USDC, USDT, EURC |
| Arbitrum | USDC, USDT |
| Optimism | USDC, USDT |

**Testnets:** `base_sepolia` (84532), `tempo_testnet` (42429), `arc_testnet`.

## Development Commands

```bash
# Python environment
uv sync                              # Install dependencies
pnpm run check:contributor           # Public OSS contributor gate
uv run pytest apps/api/tests/ -q
uv run python examples/simple_payment.py

# TypeScript SDK
pnpm install                         # Install deps
pnpm --filter @sardis/sdk build      # Build SDK
pnpm --filter @sardis/sdk test       # Test SDK

# API Server
uv run uvicorn --app-dir apps/api server.main:create_app --factory --port 8000

# Smart Contracts
cd contracts && forge build          # Compile
cd contracts && forge test           # Test

# Landing Page
pnpm dev:landing                     # Dev server
pnpm build:landing                   # Production build
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
1. Add chain config to `packages/sardis/src/sardis/core/config.py`
2. Add token addresses to `tokens.py`
3. Update chain executor in `sardis-chain`
4. Add tests

### Adding a New Token
1. Add token to `SupportedToken` enum
2. Add contract addresses per chain
3. Update SDK types

### Creating a New API Endpoint
1. Add route in `apps/api/server/routes/`
2. Add request/response models
3. Add tests
4. Update OpenAPI docs

## Important Files

### Core Code
- `packages/sardis/src/sardis/core/config.py` - Central configuration
- `packages/sardis/src/sardis/core/spending_policy.py` - Policy engine
- `packages/sardis/src/sardis/core/orchestrator.py` - PaymentOrchestrator (single authority path)
- `packages/sardis/src/sardis/chain/executor.py` - Chain execution
- `packages/sardis/src/sardis/protocol/verifier.py` - AP2 mandate verification
- `apps/api/server/providers/` - Provider port layer + adapters
- `contracts/src/SardisAgentWallet.sol` - Agent wallet contract

### OSS Policy
- `docs/oss/public-private-boundary.md` - Public/private repository boundary
- `docs/oss/contribution-map.md` - Package contribution paths and validation
- `docs/oss/testing.md` - Maintained public test suites

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

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
