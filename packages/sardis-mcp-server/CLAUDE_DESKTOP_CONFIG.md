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
| `SARDIS_API_KEY` | Your API key from sardis.sh | `sk_live_abc123...` |
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

## Available Tools (50+)

After configuration, Claude gets access to wallet, payment, policy, hold,
card, fiat, approval, analytics, group-governance, and sandbox tools.

To inspect the exact current tool catalog in your environment, run:

```bash
npx @sardis/mcp-server start
```

Then query the `sardis://tools` MCP resource from your client.

## Support

- Documentation: https://sardis.sh/docs
- GitHub Issues: https://github.com/EfeDurmaz16/sardis/issues
- Email: support@sardis.sh
