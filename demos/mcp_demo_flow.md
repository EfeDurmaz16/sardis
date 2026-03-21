# Sardis MCP Demo Flow — Tempo Mainnet

Step-by-step instructions for demonstrating Sardis via Claude Desktop (or Cursor) with the MCP server.

## Prerequisites

1. Sardis API running (locally or at `api.sardis.sh`)
2. MCP server configured in Claude Desktop:

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"],
      "env": {
        "SARDIS_API_KEY": "sk_...",
        "SARDIS_API_URL": "https://api.sardis.sh",
        "SARDIS_CHAIN": "tempo"
      }
    }
  }
}
```

## Demo Script

### 1. Create a Wallet on Tempo

> "Create a wallet on Tempo for my AI agent"

Claude will use `sardis_create_wallet` with chain="tempo".

**Expected output:** Wallet ID and Tempo address.

### 2. Get Deposit Address

> "How do I fund my Sardis wallet on Tempo?"

Claude will use `sardis_get_deposit_address` with chain="tempo".

**Expected output:** Deposit address + supported tokens (pathUSD, USDC.e).

### 3. Get On-Ramp URL

> "Give me a link to fund $100 into my Tempo wallet"

Claude will use `sardis_get_onramp_url` with chain="tempo" and amount_usd=100.

**Expected output:** URL to wallet.tempo.xyz/fund with pre-filled address.

### 4. Set a Spending Mandate

> "Set a spending mandate: $100/day for cloud APIs only (openai.com, anthropic.com)"

Claude will use `sardis_create_mandate`.

**Expected output:** Mandate ID with daily limit, per-tx limit, allowed merchants.

### 5. Create an MPP Payment Session

> "Create an MPP session with $100 spending limit on Tempo"

Claude will use `sardis_mpp_create_session` with spending_limit=100.

**Expected output:** Session ID, status=active, remaining=$100.

### 6. Execute a Payment

> "Pay $10 to OpenAI for API credits using the MPP session"

Claude will use `sardis_mpp_execute` with amount=10 and merchant="openai.com".

**Expected output:** Payment ID, tx_hash, remaining budget update.

### 7. Check Session Status

> "How much budget is left in my MPP session?"

Claude will use `sardis_mpp_get_session`.

**Expected output:** Remaining budget, payment count, session status.

### 8. View Audit Trail

> "Show me the audit trail for my recent payments"

Claude will use `sardis_list_transactions`.

**Expected output:** Ledger entries with tx hashes, amounts, timestamps.

### 9. Close the Session

> "Close my MPP payment session"

Claude will use `sardis_mpp_close_session`.

**Expected output:** Final spent amount, payment count, closed status.

## Key Talking Points During Demo

1. **Non-custodial:** "The wallet is an MPC wallet — Sardis never holds private keys"
2. **Policy-first:** "Every payment must pass the spending mandate before execution"
3. **MPP native:** "Using the Machine Payments Protocol — the same standard Stripe and Visa support"
4. **Tempo:** "Executing on Tempo — 100K+ TPS, sub-second finality, stablecoin gas fees"
5. **Audit trail:** "Every transaction has a merkle-anchored audit record"

## Failure Scenarios to Demo

### Policy Violation
> "Pay $200 to gambling.com"

**Expected:** BLOCKED — exceeds per-tx limit AND merchant not in allowlist.

### Budget Exhaustion
> "Pay $95 from the session" (after spending $10)

Then: "Pay $10 more"

**Expected:** Second payment fails — would exceed session budget.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SARDIS_API_KEY` | API key (sk_...) | Required |
| `SARDIS_API_URL` | API base URL | `https://api.sardis.sh` |
| `SARDIS_CHAIN` | Default chain | `base` |
| `SARDIS_WALLET_ID` | Default wallet | Auto-created |
| `SARDIS_AGENT_ID` | Default agent | Auto-created |
| `SARDIS_MODE` | `live` or `simulated` | `live` with key, `simulated` without |
