# sardis-openclaw

OpenClaw skills for Sardis - Payment OS for AI Agents.

> AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.

## What is this?

This package provides OpenClaw skill definitions for Sardis, enabling AI agents to execute payments, manage spending policies, check balances, and control virtual cards with natural language commands.

## Available Skills

### 💳 [sardis-payment](./SKILL.md) - Core Payment Execution

Execute secure, policy-controlled payments across multiple blockchains.

**Capabilities:**
- Send USDC/USDT/EURC on Base, Polygon, Ethereum, Arbitrum, Optimism
- Policy enforcement before every transaction
- Real-time balance checking
- Transaction history and audit trail

**Requirements:** `SARDIS_API_KEY`, `SARDIS_WALLET_ID`

**Use when:** Agent needs to execute payments or manage wallets

---

### 💰 [sardis-balance](./skills/sardis-balance/SKILL.md) - Read-Only Balance & Analytics

Safe, read-only skill for monitoring wallet balances and spending patterns.

**Capabilities:**
- Check wallet balances across chains
- Spending summaries (daily, weekly, monthly)
- Transaction history with filters
- Budget remaining against policy limits
- Multi-wallet monitoring

**Requirements:** `SARDIS_API_KEY` (no wallet ID needed)

**Use when:** Agent needs to check balances without payment risk

---

### 🛡️ [sardis-policy](./skills/sardis-policy/SKILL.md) - Spending Policy Management

Create and manage spending policies using natural language or structured rules.

**Capabilities:**
- Natural language policy creation ("Max $500/day, only Amazon")
- Pre-built policy templates (procurement, API service, trial, employee)
- Policy testing (dry-run transactions)
- Multi-layer limits (per-transaction, daily, weekly, monthly)
- Vendor and category restrictions

**Requirements:** `SARDIS_API_KEY`

**Use when:** Agent needs to create spending rules or test transactions

---

### 💳 [sardis-cards](./skills/sardis-cards/SKILL.md) - Virtual Card Management

Issue and manage virtual cards for real-world purchases.

**Capabilities:**
- Instant virtual card issuance
- Spending controls (per-transaction, daily, monthly limits)
- Merchant category restrictions
- Freeze/unfreeze cards instantly
- Transaction monitoring and alerts

**Requirements:** `SARDIS_API_KEY`

**Use when:** Agent needs to make traditional card purchases (SaaS, cloud services, etc.)

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
pip install sardis

# JavaScript/TypeScript
npm install @sardis/sdk
```

### 3. Use Skills

All skills work with curl-based API calls (no SDK required):

```bash
# Check balance (sardis-balance)
curl -X GET https://api.sardis.sh/v2/wallets/{wallet_id}/balance \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Create policy (sardis-policy)
curl -X POST https://api.sardis.sh/v2/policies \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Daily Limit", "description": "Max $500/day"}'

# Execute payment (sardis-payment)
curl -X POST https://api.sardis.sh/v2/payments \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"wallet_id": "wallet_123", "to": "0x...", "amount": "25.00", "token": "USDC"}'

# Issue virtual card (sardis-cards)
curl -X POST https://api.sardis.sh/v2/cards \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_123", "spending_limit": {"daily": "500.00"}}'
```

## Skill Selection Guide

| Agent Task | Recommended Skill | Why |
|------------|------------------|-----|
| "Pay for OpenAI API" | `sardis-payment` | Execute crypto payment |
| "Check my balance" | `sardis-balance` | Read-only, safe |
| "Set spending limit" | `sardis-policy` | Policy creation |
| "Subscribe to GitHub Copilot" | `sardis-cards` | Traditional card payment |
| "Show spending this week" | `sardis-balance` | Analytics view |
| "Test if payment allowed" | `sardis-policy` | Dry-run check |

## Publishing to ClawHub

To publish these skills to the OpenClaw ClawHub:

### Main Skill (sardis-payment)
1. Navigate to ClawHub submission page
2. Upload `SKILL.md`
3. Set category: payments, fintech, infrastructure
4. Tags: payments, crypto, USDC, spending-policy, agent-payments
5. Submit for review

### Additional Skills
Repeat for each skill in the `skills/` directory:
- `skills/sardis-balance/SKILL.md`
- `skills/sardis-policy/SKILL.md`
- `skills/sardis-cards/SKILL.md`

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

## Links

- [Sardis Website](https://sardis.sh)
- [Documentation](https://sardis.sh/docs)
- [API Reference](https://api.sardis.sh/v2/docs)
- [GitHub](https://github.com/EfeDurmaz16/sardis)
- [OpenClaw Documentation](https://docs.openclaw.ai)
- [ClawHub](https://clawhub.ai)
- [Support](mailto:support@sardis.sh)

## License

MIT
