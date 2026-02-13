# @sardis/mcp-server

[![npm version](https://img.shields.io/npm/v/@sardis/mcp-server.svg)](https://www.npmjs.com/package/@sardis/mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/@sardis/mcp-server.svg)](https://www.npmjs.com/package/@sardis/mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Model Context Protocol (MCP) server for Sardis - Enable AI agents to execute secure payments with Financial Hallucination Prevention

## Table of Contents

- [Quick Start](#quick-start)
- [What is this?](#what-is-this)
- [Installation](#installation)
- [Available Tools](#available-tools-50-total)
- [Policy Engine](#policy-engine)
- [Example Session](#example-session)
- [Environment Variables](#environment-variables)
- [Simulated Mode](#simulated-mode)
- [API Reference](#api-reference)
- [License](#license)

## Quick Start

```bash
npx @sardis/mcp-server start
```

## What is this?

Sardis MCP Server allows AI agents (Claude, Cursor, etc.) to execute payments through your Sardis wallet using the Model Context Protocol. It provides **Financial Hallucination Prevention** through natural language spending policies.

## Installation

### Option 1: npx (Recommended)

No installation required - run directly:

```bash
npx @sardis/mcp-server start
```

### Option 2: Global Install

```bash
npm install -g @sardis/mcp-server
sardis-mcp start
```

### Option 3: Local Install

```bash
npm install @sardis/mcp-server
npx sardis-mcp start
```

## Configuration

### Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

#### Minimal Configuration (Simulated Mode)

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

#### Production Configuration

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"],
      "env": {
        "SARDIS_API_KEY": "sk_live_your_api_key_here",
        "SARDIS_WALLET_ID": "wal_your_wallet_id",
        "SARDIS_MODE": "live"
      }
    }
  }
}
```

### Cursor

Add to your Cursor MCP settings (`.cursor/mcp.json` or Cursor settings):

#### Minimal Configuration

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

#### Production Configuration

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"],
      "env": {
        "SARDIS_API_KEY": "sk_live_your_api_key_here",
        "SARDIS_WALLET_ID": "wal_your_wallet_id",
        "SARDIS_MODE": "live"
      }
    }
  }
}
```

### Other MCP Clients

For any MCP-compatible client, use:

- **Command**: `npx`
- **Arguments**: `["@sardis/mcp-server", "start"]`
- **Transport**: `stdio`

## Available Tools (50+ total)

Current tool coverage includes:

- Wallet operations
- Payments and transaction history
- Policy and compliance checks
- Holds and two-phase capture flows
- Agent and group governance
- Virtual cards
- Fiat on/off-ramp
- Human approval workflows
- Spending analytics
- Sandbox onboarding flows

To inspect the exact tool list for your installed version, use the `sardis://tools`
resource from your MCP client after server startup.

## Policy Engine

The server validates all payments against your configured spending policy:

- **Allowed Categories**: SaaS, DevTools, Cloud, API
- **Blocked Merchants**: Configurable blocklist
- **Transaction Limits**: Max per transaction and daily limits
- **Risk Scoring**: Each request gets a risk score
- **Approval Workflows**: Human-in-the-loop for high-value transactions

## Example Session

```
Agent: I need to pay $20 for OpenAI API credits

[sardis_pay] vendor="OpenAI", amount=20, purpose="API Credits"

Result: {
  "success": true,
  "status": "APPROVED",
  "card": {
    "number": "4242 **** **** 9999",
    "cvv": "847",
    "expiry": "12/26"
  }
}

Agent: Can I buy a $500 Amazon gift card?

[sardis_pay] vendor="Amazon", amount=500

Result: {
  "success": false,
  "status": "BLOCKED",
  "error": "POLICY_VIOLATION",
  "message": "Merchant \"Amazon\" is not in the approved vendor list",
  "prevention": "Financial Hallucination PREVENTED"
}

Agent: What's my spending this month?

[sardis_get_spending_summary] period="month"

Result: {
  "total_spent": "450.00",
  "transaction_count": 12,
  "remaining_daily_limit": "50.00",
  "remaining_monthly_limit": "550.00",
  "top_vendor": "OpenAI"
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SARDIS_API_KEY` | No | - | Your Sardis API key. Get one at [sardis.sh](https://sardis.sh) |
| `SARDIS_WALLET_ID` | No | - | Default wallet ID for operations |
| `SARDIS_AGENT_ID` | No | - | Agent ID for this MCP connection |
| `SARDIS_MODE` | No | `simulated` | `live` for real transactions, `simulated` for testing |
| `SARDIS_API_URL` | No | `https://api.sardis.sh` | API endpoint (for enterprise/self-hosted) |

### Getting Your API Key

1. Sign up at [sardis.sh](https://sardis.sh)
2. Go to Settings > API Keys
3. Create a new API key with appropriate permissions
4. Add it to your MCP configuration

## Simulated Mode

When running without an API key, the server operates in simulated mode with:
- Mock wallet with $1000 balance
- Simulated transactions that don't execute on-chain
- Full policy validation to test your rules
- Realistic response formats

## API Reference

### Tools Schema

Each tool follows the MCP tool specification:

```typescript
interface Tool {
  name: string;
  description: string;
  inputSchema: JSONSchema;
}
```

### Common Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `wallet_id` | `string` | The wallet ID to operate on |
| `amount` | `string` | Amount in USD (e.g., "100.00") |
| `vendor` | `string` | Merchant/vendor name |
| `purpose` | `string` | Description of the payment purpose |

### Response Format

All tools return responses in this format:

```typescript
interface ToolResponse {
  success: boolean;
  status: 'APPROVED' | 'BLOCKED' | 'PENDING' | 'ERROR';
  data?: Record<string, unknown>;
  error?: string;
  message?: string;
}
```

## Requirements

- Node.js 18.0.0 or higher
- Claude Desktop, Cursor, or any MCP-compatible client

## Troubleshooting

### Server not starting

1. Ensure Node.js 18+ is installed: `node --version`
2. Clear npx cache: `npx clear-npx-cache`
3. Try global install: `npm install -g @sardis/mcp-server`

### Tools not appearing in Claude

1. Restart Claude Desktop after configuration changes
2. Check the configuration file path is correct for your OS
3. Verify JSON syntax is valid

### API errors

1. Check your API key is valid
2. Ensure `SARDIS_MODE` is set to `live` for production
3. Verify wallet ID exists in your account

## Support

- [Documentation](https://sardis.sh/docs)
- [GitHub Issues](https://github.com/EfeDurmaz16/sardis/issues)
- [Discord Community](https://discord.gg/XMA9JwDJ)
- Email: support@sardis.sh

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

MIT - see [LICENSE](./LICENSE) for details.
