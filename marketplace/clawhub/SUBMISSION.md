# Sardis OpenClaw Skill - ClawHub Submission Guide

## Skill Details

- **Name:** sardis-payments
- **Category:** Finance / Payments
- **Package:** `sardis-openclaw`
- **PyPI:** `pip install sardis-openclaw`
- **GitHub:** https://github.com/sardis-labs/sardis/tree/main/packages/sardis-openclaw

## Submission Steps

### 1. Verify SKILL.md Format

The skill definition is at `packages/sardis-openclaw/SKILL.md`. Verify it follows the current OpenClaw SKILL.md specification:

```bash
# Check skill file exists and is valid
cat packages/sardis-openclaw/SKILL.md
```

### 2. Test Locally

```bash
pip install sardis-openclaw
# Verify the skill works in a local OpenClaw environment
```

### 3. Submit to ClawHub

Option A: Via GitHub (preferred)
- Fork the ClawHub skills repository
- Add `sardis-payments/SKILL.md` to the appropriate category
- Submit a Pull Request with the skill definition

Option B: Via CLI (if available)
```bash
openclaw submit sardis-payments --skill-file packages/sardis-openclaw/SKILL.md
```

Option C: Via Web
- Go to https://clawhub.com (verify URL)
- Click "Submit Skill"
- Upload SKILL.md
- Fill in metadata:
  - Name: sardis-payments
  - Description: Payment OS for AI agents - MPC wallets, spending policies, virtual cards
  - Author: Sardis Labs
  - License: Apache-2.0
  - Tags: payments, crypto, fintech, agents, wallets, USDC

### 4. Verification

After submission, verify the skill appears in ClawHub search:
```bash
openclaw search sardis
```

## Marketing Copy for Listing

**Title:** Sardis - Payment OS for AI Agents

**Short Description:** Enable AI agents to make real financial transactions with MPC wallets, natural language spending policies, and multi-chain support.

**Features:**
- Non-custodial MPC wallets (Turnkey)
- Natural language spending policies
- Multi-chain: Base, Polygon, Ethereum, Arbitrum, Optimism
- USDC, USDT, EURC, PYUSD support
- Virtual cards via Stripe Issuing
- Fiat on/off ramp via Coinbase
- KYA (Know Your Agent) verification
- Full audit trail with double-entry ledger

**Use Cases:**
- AI procurement agents with budget controls
- Automated SaaS subscription management
- Cross-border agent payments
- Agent-to-agent commerce
