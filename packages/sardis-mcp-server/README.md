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

## Available Tools (36 total)

### Wallet Tools (5)

| Tool | Description |
|------|-------------|
| `sardis_get_wallet` | Get wallet details and configuration |
| `sardis_get_balance` | Get current wallet balance and spending limits |
| `sardis_create_wallet` | Create a new MPC wallet with optional spending policy |
| `sardis_update_wallet_policy` | Update the spending policy for a wallet |
| `sardis_list_wallets` | List all wallets, optionally filtered by agent or status |

### Payment Tools (3)

| Tool | Description |
|------|-------------|
| `sardis_pay` | Execute a secure payment with policy validation |
| `sardis_get_transaction` | Get transaction status and details |
| `sardis_list_transactions` | List recent transactions for a wallet |

### Policy Tools (3)

| Tool | Description |
|------|-------------|
| `sardis_check_policy` | Check if a payment would be allowed before executing |
| `sardis_validate_limits` | Validate spending against daily/monthly limits |
| `sardis_check_compliance` | Check vendor against compliance rules |

### Hold Tools (6)

| Tool | Description |
|------|-------------|
| `sardis_create_hold` | Create a pre-authorization hold on funds |
| `sardis_capture_hold` | Capture a previously created hold |
| `sardis_void_hold` | Void/cancel a hold without capturing |
| `sardis_get_hold` | Get hold status and details |
| `sardis_list_holds` | List active holds for a wallet |
| `sardis_extend_hold` | Extend the expiration of a hold |

### Agent Tools (4)

| Tool | Description |
|------|-------------|
| `sardis_create_agent` | Create a new AI agent with identity |
| `sardis_get_agent` | Get agent details and capabilities |
| `sardis_list_agents` | List all agents in the organization |
| `sardis_update_agent` | Update agent configuration |

### Card Tools (6)

| Tool | Description |
|------|-------------|
| `sardis_issue_card` | Issue a virtual card linked to a wallet |
| `sardis_get_card` | Get virtual card details (masked) |
| `sardis_list_cards` | List all virtual cards for a wallet |
| `sardis_freeze_card` | Temporarily freeze a virtual card |
| `sardis_unfreeze_card` | Unfreeze a previously frozen card |
| `sardis_cancel_card` | Permanently cancel a virtual card |

### Fiat Tools (4)

| Tool | Description |
|------|-------------|
| `sardis_fund_wallet` | Fund a wallet from bank account, wire, or card |
| `sardis_withdraw_to_bank` | Withdraw funds to a bank account |
| `sardis_get_funding_status` | Check status of a funding transfer |
| `sardis_get_withdrawal_status` | Check status of a withdrawal |

### Approval Tools (2)

| Tool | Description |
|------|-------------|
| `sardis_request_approval` | Request human approval for payments exceeding limits |
| `sardis_get_approval_status` | Check status of a pending approval request |

### Spending Analytics Tools (3)

| Tool | Description |
|------|-------------|
| `sardis_get_spending_summary` | Get spending summary with totals and limits |
| `sardis_get_spending_by_vendor` | Get spending breakdown by vendor |
| `sardis_get_spending_by_category` | Get spending breakdown by category |

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

| Variable | Description |
|----------|-------------|
| `SARDIS_API_KEY` | Your Sardis API key (optional for demo mode) |
| `SARDIS_WALLET_ID` | Your wallet ID |
| `SARDIS_AGENT_ID` | Your agent ID |
| `SARDIS_MODE` | `live` or `simulated` (default: simulated) |

## Simulated Mode

When running without an API key, the server operates in simulated mode with:
- Mock wallet with $1000 balance
- Simulated transactions that don't execute on-chain
- Full policy validation to test your rules
- Realistic response formats

## License

MIT

## Links

- [Sardis Documentation](https://docs.sardis.sh)
- [GitHub](https://github.com/EfeDurmaz16/sardis)
- [Website](https://sardis.sh)
