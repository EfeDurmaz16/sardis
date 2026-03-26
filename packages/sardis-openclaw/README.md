# sardis-openclaw

OpenClaw skills for Sardis - Payment OS for AI Agents.

> AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.

## What is this?

This package provides OpenClaw skill definitions for Sardis, enabling AI agents to create wallets, execute payments, manage spending policies, check balances, and control virtual cards with natural language commands.

## Available Skills

### [sardis](./SKILL.md) - Core Payment Skill (Primary)

The main skill combining all agent payment capabilities:

1. **Create Agent + Wallet** - Provision agent identity with MPC wallet
2. **Send Payment** - Execute stablecoin transfers with policy enforcement
3. **Check Balance** - Real-time multi-chain balance queries
4. **Set Spending Policy** - Natural language spending rules
5. **Issue Virtual Card** - Stablecoin-funded Visa cards
6. **Spending Mandates** - Scoped, time-limited fund authority

**Requirements:** `SARDIS_API_KEY`

---

### [sardis-balance](./skills/sardis-balance/SKILL.md) - Read-Only Balance & Analytics

Safe, read-only skill for monitoring wallet balances and spending patterns.

**Requirements:** `SARDIS_API_KEY`

---

### [sardis-policy](./skills/sardis-policy/SKILL.md) - Spending Policy Management

Create and manage spending policies using natural language or structured rules.

**Requirements:** `SARDIS_API_KEY`

---

### [sardis-cards](./skills/sardis-cards/SKILL.md) - Virtual Card Management

Issue virtual cards for AI agents to make real-world purchases.

**Requirements:** `SARDIS_API_KEY`

---

### [sardis-guardrails](./skills/sardis-guardrails/SKILL.md) - Security Controls

Circuit breakers, kill switches, and behavioral anomaly detection.

**Requirements:** `SARDIS_API_KEY`

---

### [sardis-identity](./skills/sardis-identity/SKILL.md) - Agent Identity

TAP-verified agent identities with reputation tracking.

**Requirements:** `SARDIS_API_KEY`

---

### [sardis-escrow](./skills/sardis-escrow/SKILL.md) - Smart Contract Escrow

Milestone-based escrow for agent-to-agent payments.

**Requirements:** `SARDIS_API_KEY`

---

### [sardis-tempo-pay](./skills/sardis-tempo-pay/SKILL.md) - MPP Payments on Tempo

Machine Payments Protocol sessions with Sardis spending mandates on Tempo mainnet.

**Requirements:** `SARDIS_API_KEY`, `SARDIS_WALLET_ID`, `SARDIS_TEMPO_RPC_URL`

---

## Quick Start

### 1. Get API Key

```bash
# Sign up at https://sardis.sh
export SARDIS_API_KEY=sk_your_key_here
```

### 2. Install SDK (Optional)

```bash
# Python
pip install sardis-openclaw

# JavaScript/TypeScript
npm install @sardis/sdk
```

### 3. Use Skills

All skills work with curl-based API calls (no SDK required):

```bash
# Create agent (auto-provisions wallet)
curl -X POST https://api.sardis.sh/api/v2/agents \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent", "description": "Payment agent"}'

# Check balance
curl -X GET "https://api.sardis.sh/api/v2/wallets/{wallet_id}/balances" \
  -H "X-API-Key: $SARDIS_API_KEY"

# Set policy (natural language)
curl -X POST https://api.sardis.sh/api/v2/policies/apply \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agt_123", "natural_language": "Max $500/day, only OpenAI"}'

# Execute payment (policy auto-enforced)
curl -X POST https://api.sardis.sh/api/v2/pay \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"to": "openai.com", "amount": "25.00", "currency": "USDC", "chain": "base"}'
```

## Skill Server

The package includes a FastAPI-based skill server for programmatic discovery and execution:

```bash
# Run the skill server
uvicorn sardis_openclaw.server:app --host 0.0.0.0 --port 8090

# Discover skills
curl http://localhost:8090/skills

# Execute a skill
curl -X POST http://localhost:8090/skills/create_wallet/execute \
  -H "Content-Type: application/json" \
  -d '{
    "params": {"agent_id": "agent_123"},
    "context": {"api_key": "sk_...", "agent_id": "agent_123"}
  }'
```

## Skill Selection Guide

| Agent Task | Recommended Skill | Why |
|------------|------------------|-----|
| "Create a wallet" | `sardis` | Wallet provisioning |
| "Pay for OpenAI API" | `sardis` | Execute crypto payment |
| "Check my balance" | `sardis-balance` | Read-only, safe |
| "Set spending limit" | `sardis-policy` | Policy creation |
| "Subscribe to GitHub Copilot" | `sardis-cards` | Traditional card payment |
| "Show spending this week" | `sardis-balance` | Analytics view |
| "Test if payment allowed" | `sardis-policy` | Dry-run check |
| "Emergency stop" | `sardis-guardrails` | Kill switch |
| "Pay on Tempo" | `sardis-tempo-pay` | MPP session |

## Publishing to ClawHub

```bash
# Install ClawHub CLI
npm install -g @openclaw/clawhub

# Publish main skill
cd packages/sardis-openclaw
clawhub publish .

# Or publish individual sub-skills
clawhub publish skills/sardis-balance
clawhub publish skills/sardis-policy
clawhub publish skills/sardis-cards
```

## Security Best Practices

All skills enforce these security principles:

1. **Policy-First**: Always check spending policy before payment
2. **Never Bypass**: No approval flow bypassing
3. **Fail Closed**: Deny by default on policy violations
4. **Audit Everything**: Complete transaction logging
5. **Read-Only When Possible**: Use `sardis-balance` for monitoring

## Supported Chains & Tokens

| Chain | Network | Tokens |
|-------|---------|--------|
| Base | Mainnet | USDC, EURC |
| Polygon | Mainnet | USDC, USDT, EURC |
| Ethereum | Mainnet | USDC, USDT, PYUSD, EURC |
| Arbitrum | One | USDC, USDT |
| Optimism | Mainnet | USDC, USDT |
| Tempo | Mainnet | pathUSD |

## Links

- [Sardis Website](https://sardis.sh)
- [Documentation](https://sardis.sh/docs)
- [API Reference](https://api.sardis.sh/api/v2/docs)
- [GitHub](https://github.com/EfeDurmaz16/sardis)
- [OpenClaw Documentation](https://docs.openclaw.ai)
- [ClawHub](https://clawhub.com)
- [Support](mailto:support@sardis.sh)

## License

MIT
