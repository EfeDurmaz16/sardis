# @sardis/mcp-server

[![npm version](https://img.shields.io/npm/v/@sardis/mcp-server.svg)](https://www.npmjs.com/package/@sardis/mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/@sardis/mcp-server.svg)](https://www.npmjs.com/package/@sardis/mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Payment tools for AI agents — works with Claude, ChatGPT, Cursor, VS Code, and any MCP-compatible client.**

Enable AI agents to execute secure payments, manage wallets, and enforce spending policies through the Model Context Protocol. Non-custodial, policy-enforced, and audit-ready.

---

## Quick Start (30 seconds)

### Claude Desktop

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["-y", "@sardis/mcp-server"],
      "env": {
        "SARDIS_API_KEY": "sk_live_your_api_key_here"
      }
    }
  }
}
```

### Cursor

`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["-y", "@sardis/mcp-server"],
      "env": {
        "SARDIS_API_KEY": "sk_live_your_api_key_here"
      }
    }
  }
}
```

### Windsurf

`.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["-y", "@sardis/mcp-server"],
      "env": {
        "SARDIS_API_KEY": "sk_live_your_api_key_here"
      }
    }
  }
}
```

### VS Code

Install the [MCP Extension](https://marketplace.visualstudio.com/items?itemName=modelcontextprotocol.mcp) and add to settings:

```json
{
  "mcp.servers": {
    "sardis": {
      "command": "npx",
      "args": ["-y", "@sardis/mcp-server"],
      "env": {
        "SARDIS_API_KEY": "sk_live_your_api_key_here"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add sardis -- npx -y @sardis/mcp-server
```

Then set your API key:

```bash
export SARDIS_API_KEY=sk_live_your_api_key_here
```

### ChatGPT

1. Open ChatGPT Settings
2. Navigate to **MCP Servers**
3. Click **Add Custom**
4. Enter:
   - **Name**: `sardis`
   - **Command**: `npx -y @sardis/mcp-server`
   - **Environment Variable**: `SARDIS_API_KEY=sk_live_your_api_key_here`

---

## Available Tools

### Payments

| Tool | Description |
|------|-------------|
| `sardis_pay` | Execute a payment to a merchant or wallet address |
| `sardis_get_transaction` | Retrieve details of a specific transaction |
| `sardis_list_transactions` | List recent transactions with filters |

### Wallets

| Tool | Description |
|------|-------------|
| `sardis_create_wallet` | Create a new non-custodial MPC wallet |
| `sardis_get_balance` | Get wallet balance across chains and tokens |
| `sardis_fund_wallet` | Fund wallet via on-ramp or transfer |

### Cards

| Tool | Description |
|------|-------------|
| `sardis_issue_card` | Issue a virtual card for an agent |
| `sardis_create_card` | Create a virtual card with spending limits |
| `sardis_freeze_card` | Temporarily freeze a card |
| `sardis_cancel_card` | Permanently cancel a card |

### Policy

| Tool | Description |
|------|-------------|
| `sardis_check_policy` | Validate a transaction against spending policies |
| `sardis_validate_limits` | Check if transaction is within limits |
| `sardis_get_policies` | List all active spending policies |

### Holds

| Tool | Description |
|------|-------------|
| `sardis_create_hold` | Create a payment hold (authorize without capture) |
| `sardis_capture_hold` | Capture a previously authorized hold |
| `sardis_release_hold` | Release a hold without capturing |
| `sardis_void_hold` | Void an authorization |

### Approvals

| Tool | Description |
|------|-------------|
| `sardis_request_approval` | Request human approval for a transaction |
| `sardis_check_approval` | Check status of a pending approval request |
| `sardis_list_pending_approvals` | List all pending approval requests |

### Analytics

| Tool | Description |
|------|-------------|
| `sardis_get_spending_summary` | Get spending summary for a time period |
| `sardis_get_spending_trends` | Analyze spending trends and patterns |

### Groups

| Tool | Description |
|------|-------------|
| `sardis_create_group` | Create an agent group with shared budget |
| `sardis_add_agent_to_group` | Add an agent to a spending group |
| `sardis_get_group_spending` | Get spending summary for a group |

### Fiat

| Tool | Description |
|------|-------------|
| `sardis_onramp` | Convert fiat to crypto via on-ramp |
| `sardis_offramp` | Convert crypto to fiat via off-ramp |
| `sardis_fiat_balance` | Check fiat balance in connected accounts |

### Sandbox

| Tool | Description |
|------|-------------|
| `sardis_sandbox_*` | Sandbox tools for testing (no API key needed) |

---

## Demo Mode

Try Sardis without an API key using sandbox tools:

```bash
npx @sardis/mcp-server --demo
```

Sandbox tools include simulated payments, wallet creation, and policy validation. Perfect for testing integrations before going live.

---

## What Can You Do?

Example prompts to try with your AI agent:

**Wallet Management**
- "Check my agent's wallet balance"
- "Create a new wallet for my procurement agent"
- "What's my USDC balance on Base?"

**Payments**
- "Pay $50 USDC to merchant@example.com on Base"
- "Send 100 USDC to 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
- "Show me my last 10 transactions"

**Policy Enforcement**
- "Create a spending policy: max $500/day for API services"
- "Can I spend $1000 on AWS right now?"
- "What are my current spending limits?"

**Virtual Cards**
- "Issue a virtual card for my procurement agent"
- "Create a card with a $200 monthly limit for SaaS subscriptions"
- "Freeze card ending in 1234"

**Analytics**
- "Show spending summary for the last 30 days"
- "What are my top 5 vendors this month?"
- "Analyze spending trends for Q1"

**Approvals**
- "Request approval for a $2500 payment to Stripe"
- "Check status of pending approval requests"
- "List all transactions waiting for approval"

---

## Security

### Non-Custodial Architecture

Sardis uses Turnkey MPC (Multi-Party Computation) for key management. Private keys are never exposed or stored—they exist only as distributed key shares across secure enclaves.

### Policy Enforcement

Every transaction is validated against:
- **Spending limits** (per-transaction, daily, monthly)
- **Allowed categories** (SaaS, DevTools, Cloud, API, etc.)
- **Blocked merchants** (configurable blocklist)
- **Risk scoring** (KYA trust scoring for agents)

### KYA (Know Your Agent) Trust Scoring

Agents are assigned trust scores based on:
- Transaction history
- Policy compliance rate
- Approval patterns
- Anomaly detection

### Audit Trail

All transactions are logged to an append-only ledger for:
- Compliance reporting
- Dispute resolution
- Forensic analysis
- Regulatory audits

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SARDIS_API_KEY` | No | - | Your Sardis API key ([get one](https://sardis.sh)) |
| `SARDIS_WALLET_ID` | No | - | Default wallet ID for operations |
| `SARDIS_AGENT_ID` | No | - | Agent ID for this MCP connection |
| `SARDIS_MODE` | No | `sandbox` | `live` for real transactions, `sandbox` for testing |
| `SARDIS_API_URL` | No | `https://api.sardis.sh` | API endpoint (for enterprise/self-hosted) |

---

## Links

- **Website**: [sardis.sh](https://sardis.sh)
- **Documentation**: [docs.sardis.sh](https://docs.sardis.sh)
- **GitHub**: [github.com/EfeDurmaz16/sardis](https://github.com/EfeDurmaz16/sardis)
- **Discord**: [discord.gg/XMA9JwDJ](https://discord.gg/XMA9JwDJ)
- **Support**: support@sardis.sh

---

## Requirements

- Node.js 18.0.0 or higher
- MCP-compatible client (Claude Desktop, Cursor, VS Code, etc.)

---

## Troubleshooting

### Server not starting

1. Ensure Node.js 18+ is installed: `node --version`
2. Clear npx cache: `npx clear-npx-cache`
3. Try global install: `npm install -g @sardis/mcp-server`

### Tools not appearing

1. Restart your MCP client after configuration changes
2. Verify JSON syntax in config file
3. Check file path is correct for your OS

### API errors

1. Verify API key is valid at [sardis.sh/settings/api-keys](https://sardis.sh/settings/api-keys)
2. Ensure `SARDIS_MODE` is set to `live` for production
3. Check wallet ID exists in your account

---

## License

MIT - see [LICENSE](./LICENSE) for details.

---

**Built with the Model Context Protocol (MCP)** — enabling AI agents to safely interact with external tools and services.
