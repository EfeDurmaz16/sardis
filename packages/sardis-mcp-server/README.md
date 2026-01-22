# @sardis/mcp-server

> Model Context Protocol (MCP) server for Sardis - Enable AI agents to execute secure payments

## Quick Start

```bash
npx @sardis/mcp-server start
```

## What is this?

Sardis MCP Server allows AI agents (Claude, Cursor, etc.) to execute payments through your Sardis wallet using the Model Context Protocol. It provides **Financial Hallucination Prevention** through natural language spending policies.

## Installation

### For Claude Desktop

Add to your `claude_desktop_config.json`:

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

### For Cursor

Add to your MCP configuration:

```json
{
  "sardis": {
    "command": "npx @sardis/mcp-server start"
  }
}
```

## Available Tools

### `sardis_pay`

Execute a secure payment with policy validation.

```
vendor: "OpenAI"
amount: 20
purpose: "API Credits"
```

### `sardis_check_policy`

Check if a payment would be allowed before executing.

```
vendor: "Amazon"
amount: 500
```

### `sardis_get_balance`

Get current wallet balance and spending limits.

## Policy Engine

The server validates all payments against your configured spending policy:

- **Allowed Categories**: SaaS, DevTools, Cloud, API
- **Blocked Merchants**: Configurable blocklist
- **Transaction Limits**: Max per transaction and daily limits
- **Risk Scoring**: Each request gets a risk score

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
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SARDIS_API_KEY` | Your Sardis API key (optional for demo mode) |
| `SARDIS_WALLET_ID` | Your wallet ID |

## License

MIT

## Links

- [Sardis Documentation](https://docs.sardis.sh)
- [GitHub](https://github.com/EfeDurmaz16/sardis)
- [Website](https://sardis.sh)
