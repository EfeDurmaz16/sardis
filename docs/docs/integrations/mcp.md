# MCP Server Integration

Enable Claude Desktop, Cursor, Windsurf, and other MCP clients to make real payments through Sardis.

## What is MCP?

**MCP (Model Context Protocol)** is Anthropic's open standard for connecting AI assistants to external tools and data sources. The Sardis MCP server gives Claude and other MCP clients the ability to:

- Create and manage agent wallets
- Execute payments with spending policies
- Query transaction history
- Check balances
- Monitor trust scores

## Installation

### For Claude Desktop

1. Install the Sardis MCP server globally:

```bash
npm install -g @sardis/mcp-server
```

2. Add to your Claude Desktop configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"],
      "env": {
        "SARDIS_API_KEY": "sk_..."
      }
    }
  }
}
```

3. Restart Claude Desktop

### For Cursor

1. Install the package:

```bash
npm install -g @sardis/mcp-server
```

2. Add to Cursor settings (Settings → Features → MCP):

```json
{
  "sardis": {
    "command": "npx",
    "args": ["@sardis/mcp-server", "start"],
    "env": {
      "SARDIS_API_KEY": "sk_..."
    }
  }
}
```

### For Windsurf

```bash
npm install -g @sardis/mcp-server
```

Add to Windsurf MCP configuration:

```json
{
  "sardis": {
    "command": "sardis-mcp",
    "env": {
      "SARDIS_API_KEY": "sk_..."
    }
  }
}
```

## Available Tools

The Sardis MCP server provides 65+ tools organized into categories:

### Wallet Management

- `sardis_create_wallet` - Create new agent wallet
- `sardis_list_wallets` - List all wallets
- `sardis_get_wallet` - Get wallet details
- `sardis_update_policy` - Update spending policy
- `sardis_freeze_wallet` - Freeze wallet
- `sardis_unfreeze_wallet` - Unfreeze wallet
- `sardis_delete_wallet` - Delete wallet

### Payments

- `sardis_execute_payment` - Execute payment
- `sardis_estimate_gas` - Estimate transaction gas
- `sardis_simulate_payment` - Simulate payment (test policy)
- `sardis_get_payment` - Get payment details
- `sardis_list_payments` - List payments
- `sardis_cancel_payment` - Cancel pending payment

### Balances

- `sardis_get_balance` - Get token balance
- `sardis_get_all_balances` - Get all token balances
- `sardis_get_balance_history` - Historical balance data

### Trust & KYA

- `sardis_get_trust_score` - Get KYA trust score
- `sardis_trust_history` - Trust score history
- `sardis_kya_analysis` - Detailed KYA analysis
- `sardis_anomaly_alerts` - Active anomaly alerts

### Ledger & Audit

- `sardis_ledger_list` - List ledger entries
- `sardis_ledger_reconcile` - Reconciliation report
- `sardis_ledger_export` - Export ledger data
- `sardis_ledger_verify` - Verify ledger integrity

### Compliance

- `sardis_compliance_check` - Run compliance check
- `sardis_sanctions_screen` - Screen address/entity
- `sardis_kyc_status` - Get KYC status

## Usage Examples

### Creating a Wallet

In Claude Desktop, simply say:

```
Create a Sardis wallet named "my-assistant" on Base with a spending policy of max $100/day
```

Claude will call:

```json
{
  "tool": "sardis_create_wallet",
  "arguments": {
    "name": "my-assistant",
    "chain": "base",
    "policy": "Max $100/day"
  }
}
```

### Making a Payment

```
Pay $50 USDC to 0x1234...5678 from my-assistant wallet for API credits
```

Claude will call:

```json
{
  "tool": "sardis_execute_payment",
  "arguments": {
    "wallet_id": "wallet_abc123",
    "to": "0x1234...5678",
    "amount": "50",
    "token": "USDC",
    "purpose": "API credits"
  }
}
```

### Checking Balance

```
What's the balance of my-assistant wallet?
```

Claude will call:

```json
{
  "tool": "sardis_get_all_balances",
  "arguments": {
    "wallet_id": "wallet_abc123"
  }
}
```

### Viewing Transaction History

```
Show me all payments from my-assistant wallet this month
```

Claude will call:

```json
{
  "tool": "sardis_list_payments",
  "arguments": {
    "wallet_id": "wallet_abc123",
    "start_date": "2026-02-01",
    "end_date": "2026-02-28"
  }
}
```

## Natural Language Commands

The MCP server supports natural language - Claude interprets your intent and calls the right tools:

| What You Say | Tools Called |
|--------------|--------------|
| "Create a wallet for my agent" | `sardis_create_wallet` |
| "Pay OpenAI $50 for API credits" | `sardis_execute_payment` |
| "What's my balance?" | `sardis_get_all_balances` |
| "Show me today's transactions" | `sardis_list_payments` |
| "What's my trust score?" | `sardis_get_trust_score` |
| "Export this month's ledger" | `sardis_ledger_export` |
| "Freeze the wallet" | `sardis_freeze_wallet` |

## Multi-Wallet Management

Manage multiple wallets:

```
Create three wallets:
1. "dev-agent" on Base with $50/day limit
2. "prod-agent" on Ethereum with $500/day limit
3. "test-agent" on Base Sepolia with $10/day limit
```

Claude will create all three wallets in sequence.

## Safety Features

The MCP server includes safety guardrails:

1. **Confirmation for large amounts** - Payments over $1000 require explicit confirmation
2. **Policy validation** - All policies validated before wallet creation
3. **Address verification** - Ethereum addresses validated
4. **Simulation mode** - Test payments without executing

Example safety prompt:

```
User: Pay $10,000 to 0x1234...

Claude: That's a large payment ($10,000). To confirm:
- Amount: $10,000 USDC
- Recipient: 0x1234...5678
- Policy: Max $500/day
- ⚠️ This exceeds your daily policy limit

Would you like me to:
1. Cancel this payment
2. Update the policy to allow it
3. Split into smaller payments over multiple days
```

## Configuration Options

Advanced configuration in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"],
      "env": {
        "SARDIS_API_KEY": "sk_...",
        "SARDIS_ENVIRONMENT": "production",
        "SARDIS_DEFAULT_CHAIN": "base",
        "SARDIS_CONFIRMATION_THRESHOLD": "1000",
        "SARDIS_SIMULATION_MODE": "false",
        "SARDIS_LOG_LEVEL": "info"
      }
    }
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SARDIS_API_KEY` | Your Sardis API key | Required |
| `SARDIS_ENVIRONMENT` | `production` or `testnet` | `production` |
| `SARDIS_DEFAULT_CHAIN` | Default blockchain | `base` |
| `SARDIS_CONFIRMATION_THRESHOLD` | USD amount requiring confirmation | `1000` |
| `SARDIS_SIMULATION_MODE` | Test mode (no real txs) | `false` |
| `SARDIS_LOG_LEVEL` | `debug`, `info`, `warn`, `error` | `info` |

## Debugging

Enable debug logging:

```json
{
  "env": {
    "SARDIS_API_KEY": "sk_...",
    "SARDIS_LOG_LEVEL": "debug"
  }
}
```

Check logs:

**macOS:** `~/Library/Logs/Claude/mcp-server-sardis.log`
**Windows:** `%APPDATA%\Claude\Logs\mcp-server-sardis.log`

## Custom Prompts

Create custom Claude prompts that use Sardis:

### Autonomous Procurement Agent

```
You are a procurement agent with a Sardis wallet (wallet_abc123).

Your role:
- Monitor inventory levels
- Automatically reorder supplies when low
- Only purchase from approved vendors
- Stay within $500/day budget

Approved vendors:
- AWS (cloud services)
- OpenAI (API credits)
- Stripe (payment processing)

When inventory falls below threshold, execute payment to reorder.
```

### Expense Reimbursement Bot

```
You are an expense reimbursement assistant.

Process:
1. User submits expense receipt
2. Verify expense is within policy
3. Extract amount and vendor
4. Execute reimbursement payment via Sardis

Policy:
- Max $500 per expense
- Only business-related purchases
- Require receipt for amounts over $50
```

## ChatGPT Actions Integration

Use Sardis MCP server with ChatGPT Custom GPTs:

1. Export MCP tools as OpenAPI spec:

```bash
npx @sardis/mcp-server export-openapi > sardis-openapi.json
```

2. Create Custom GPT and import the OpenAPI spec

3. Configure authentication with your Sardis API key

## Windsurf Integration

Windsurf users can use Sardis for autonomous code deployment payments:

```
You are a Windsurf deployment agent.

Workflow:
1. User pushes code to production
2. Check if deployment requires paid services (Vercel, AWS, etc)
3. Estimate deployment cost
4. Execute payment via Sardis if within budget
5. Trigger deployment
6. Report success + transaction hash
```

## Performance

The MCP server is optimized for low latency:

- Tool calls: <100ms
- Payment execution: 2-5 seconds (including blockchain confirmation)
- Balance checks: <50ms
- Ledger queries: <200ms

## Security

1. **API key stored locally** - Never transmitted to Anthropic
2. **TLS encryption** - All API calls over HTTPS
3. **No key logging** - API keys never logged
4. **Tool isolation** - Each tool runs in isolated context

## Troubleshooting

### MCP Server Not Starting

```bash
# Check if server is running
npx @sardis/mcp-server status

# View logs
npx @sardis/mcp-server logs

# Restart server
npx @sardis/mcp-server restart
```

### Invalid API Key

```json
{
  "error": "Invalid API key",
  "solution": "Check SARDIS_API_KEY in claude_desktop_config.json"
}
```

### Tools Not Appearing

1. Restart Claude Desktop
2. Check MCP server status: `npx @sardis/mcp-server status`
3. Verify config file location
4. Check logs for errors

## Examples Repository

See full examples in the [Sardis MCP Examples](https://github.com/sardis-labs/sardis/tree/main/examples/mcp) repository:

- Autonomous procurement agent
- Expense reimbursement bot
- Multi-agent team with shared budget
- Subscription payment automation
- Invoice payment workflow

## Next Steps

- [LangChain Integration](langchain.md) - Build LangChain agents
- [Spending Policies](../concepts/policies.md) - Define guardrails
- [API Reference](../api/rest.md) - Direct API access
- [TypeScript SDK](../sdks/typescript.md) - SDK reference
