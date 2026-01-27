# Claude Desktop Configuration for Sardis

Copy-paste configurations for Claude Desktop.

## Configuration File Location

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

## Quick Start (Simulated Mode)

Use this configuration to get started immediately without an API key:

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

## Production Configuration

For live transactions with your Sardis account:

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"],
      "env": {
        "SARDIS_API_KEY": "sk_live_YOUR_API_KEY_HERE",
        "SARDIS_WALLET_ID": "wal_YOUR_WALLET_ID",
        "SARDIS_MODE": "live"
      }
    }
  }
}
```

## Full Configuration (All Options)

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"],
      "env": {
        "SARDIS_API_KEY": "sk_live_YOUR_API_KEY_HERE",
        "SARDIS_WALLET_ID": "wal_YOUR_WALLET_ID",
        "SARDIS_AGENT_ID": "agt_YOUR_AGENT_ID",
        "SARDIS_MODE": "live"
      }
    }
  }
}
```

## Using with Global Install

If you installed globally with `npm install -g @sardis/mcp-server`:

```json
{
  "mcpServers": {
    "sardis": {
      "command": "sardis-mcp",
      "args": ["start"]
    }
  }
}
```

## Using with Local Project

If the package is installed in your project's node_modules:

```json
{
  "mcpServers": {
    "sardis": {
      "command": "node",
      "args": ["./node_modules/@sardis/mcp-server/dist/cli.js", "start"]
    }
  }
}
```

## Adding to Existing Configuration

If you already have other MCP servers configured:

```json
{
  "mcpServers": {
    "your-existing-server": {
      "command": "...",
      "args": ["..."]
    },
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"]
    }
  }
}
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `SARDIS_API_KEY` | Your API key from sardis.network | `sk_live_abc123...` |
| `SARDIS_WALLET_ID` | Default wallet for operations | `wal_xyz789...` |
| `SARDIS_AGENT_ID` | Agent ID for this connection | `agt_def456...` |
| `SARDIS_MODE` | `live` or `simulated` | `simulated` |

## Verifying Installation

After configuration, restart Claude Desktop. You should see Sardis tools available:

1. Open Claude Desktop
2. Start a new conversation
3. Ask: "What Sardis tools do you have access to?"
4. Claude should list the 36 Sardis payment tools

## Troubleshooting

### Tools not appearing

1. Verify the JSON syntax is valid
2. Restart Claude Desktop completely
3. Check the config file path for your OS

### "Command not found" error

1. Ensure Node.js 18+ is installed: `node --version`
2. Try using the full path to npx: `/usr/local/bin/npx` (macOS/Linux)
3. Or install globally: `npm install -g @sardis/mcp-server`

### API errors in live mode

1. Verify your API key is correct
2. Check your wallet ID exists
3. Ensure sufficient balance for operations

## Available Tools (36)

After configuration, Claude will have access to:

**Wallet**: sardis_get_wallet, sardis_get_balance, sardis_create_wallet, sardis_update_wallet_policy, sardis_list_wallets

**Payment**: sardis_pay, sardis_get_transaction, sardis_list_transactions

**Policy**: sardis_check_policy, sardis_validate_limits, sardis_check_compliance

**Hold**: sardis_create_hold, sardis_capture_hold, sardis_void_hold, sardis_get_hold, sardis_list_holds, sardis_extend_hold

**Agent**: sardis_create_agent, sardis_get_agent, sardis_list_agents, sardis_update_agent

**Card**: sardis_issue_card, sardis_get_card, sardis_list_cards, sardis_freeze_card, sardis_unfreeze_card, sardis_cancel_card

**Fiat**: sardis_fund_wallet, sardis_withdraw_to_bank, sardis_get_funding_status, sardis_get_withdrawal_status

**Approval**: sardis_request_approval, sardis_get_approval_status

**Analytics**: sardis_get_spending_summary, sardis_get_spending_by_vendor, sardis_get_spending_by_category

## Support

- Documentation: https://docs.sardis.network
- GitHub Issues: https://github.com/sardis-network/sardis/issues
- Email: support@sardis.network
