---
name: sardis-balance
description: Read-only balance checking and spending analytics for Sardis agent wallets
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - SARDIS_API_KEY
      bins:
        - curl
        - jq
    primaryEnv: SARDIS_API_KEY
    emoji: "💰"
    homepage: https://sardis.sh
    install:
      npm:
        - "@sardis/sdk"
    user-invocable: true
    disable-model-invocation: false
---

# Sardis Balance - Read-Only Wallet Analytics

Safe, read-only skill for checking wallet balances, spending summaries, and transaction history. Perfect for monitoring without payment execution risk.

## Capabilities

- **Balance Checking**: Real-time wallet balance across all supported chains
- **Spending Summary**: Daily, weekly, monthly spending analytics
- **Transaction History**: Complete audit trail with filters
- **Budget Tracking**: Remaining daily/weekly/monthly limits
- **Multi-Wallet**: Check balances across multiple agent wallets

## Security Model

**READ-ONLY**: This skill cannot execute payments or modify wallet state. Safe for unrestricted use.

## Quick Setup

```bash
export SARDIS_API_KEY=sk_your_key_here
```

Note: No WALLET_ID required - can query any wallet you have access to.

## API Endpoint Patterns

Base URL: `https://api.sardis.sh/v2`

### Check Wallet Balance

```bash
# Get current balance for a specific wallet
curl -X GET https://api.sardis.sh/v2/wallets/{wallet_id}/balance \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Example response:
# {
#   "wallet_id": "wallet_abc123",
#   "balances": {
#     "base": {"USDC": "1250.00", "EURC": "500.00"},
#     "polygon": {"USDC": "750.00"}
#   },
#   "total_usd": "2500.00"
# }
```

### Spending Summary

```bash
# Get spending summary for a time period
curl -X GET "https://api.sardis.sh/v2/wallets/{wallet_id}/spending/summary?period=day" \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Available periods: hour, day, week, month, year
```

### Transaction History

```bash
# List recent transactions with filters
curl -X GET "https://api.sardis.sh/v2/wallets/{wallet_id}/transactions?limit=20&status=completed" \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Filters:
# - limit: Number of transactions (default 10, max 100)
# - status: completed, pending, failed
# - from_date: ISO 8601 timestamp
# - to_date: ISO 8601 timestamp
# - min_amount: Minimum transaction amount
# - max_amount: Maximum transaction amount
```

### Spending by Vendor

```bash
# Get spending breakdown by vendor
curl -X GET "https://api.sardis.sh/v2/wallets/{wallet_id}/spending/by-vendor?period=month" \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Returns top vendors by spend amount
```

### Budget Remaining

```bash
# Check remaining budget against policy limits
curl -X GET "https://api.sardis.sh/v2/wallets/{wallet_id}/budget/remaining" \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Example response:
# {
#   "daily_limit": "500.00",
#   "daily_spent": "325.00",
#   "daily_remaining": "175.00",
#   "weekly_limit": "2000.00",
#   "weekly_spent": "1200.00",
#   "weekly_remaining": "800.00"
# }
```

## Example Commands

### Quick Balance Check

```bash
# Single wallet balance
WALLET_ID=wallet_abc123
curl -s -X GET https://api.sardis.sh/v2/wallets/$WALLET_ID/balance \
  -H "Authorization: Bearer $SARDIS_API_KEY" | jq '.total_usd'
```

### Daily Spending Report

```bash
# Get today's spending with vendor breakdown
WALLET_ID=wallet_abc123

echo "=== Daily Spending Report ==="
curl -s -X GET "https://api.sardis.sh/v2/wallets/$WALLET_ID/spending/summary?period=day" \
  -H "Authorization: Bearer $SARDIS_API_KEY" | jq '.'

echo -e "\n=== Top Vendors ==="
curl -s -X GET "https://api.sardis.sh/v2/wallets/$WALLET_ID/spending/by-vendor?period=day" \
  -H "Authorization: Bearer $SARDIS_API_KEY" | jq '.vendors[] | "\(.name): $\(.amount)"'
```

### Multi-Wallet Dashboard

```bash
# Check balances across multiple wallets
for wallet in wallet_abc123 wallet_def456 wallet_ghi789; do
  echo "Wallet: $wallet"
  curl -s -X GET https://api.sardis.sh/v2/wallets/$wallet/balance \
    -H "Authorization: Bearer $SARDIS_API_KEY" | jq '.total_usd'
  echo "---"
done
```

### Budget Alert Check

```bash
# Check if approaching spending limits
WALLET_ID=wallet_abc123
REMAINING=$(curl -s -X GET https://api.sardis.sh/v2/wallets/$WALLET_ID/budget/remaining \
  -H "Authorization: Bearer $SARDIS_API_KEY" | jq -r '.daily_remaining')

if (( $(echo "$REMAINING < 100" | bc -l) )); then
  echo "WARNING: Only $REMAINING left in daily budget"
fi
```

## Response Examples

### Balance Response

```json
{
  "wallet_id": "wallet_abc123",
  "agent_id": "agent_xyz789",
  "balances": {
    "base": {
      "USDC": "1250.00",
      "EURC": "500.00"
    },
    "polygon": {
      "USDC": "750.00",
      "USDT": "250.00"
    }
  },
  "total_usd": "2750.00",
  "last_updated": "2026-02-21T10:30:00Z"
}
```

### Spending Summary Response

```json
{
  "period": "day",
  "start_date": "2026-02-21T00:00:00Z",
  "end_date": "2026-02-21T23:59:59Z",
  "total_spent": "325.00",
  "transaction_count": 12,
  "average_transaction": "27.08",
  "largest_transaction": "75.00",
  "by_chain": {
    "base": "200.00",
    "polygon": "125.00"
  },
  "by_token": {
    "USDC": "275.00",
    "USDT": "50.00"
  }
}
```

### Transaction History Response

```json
{
  "transactions": [
    {
      "id": "tx_abc123",
      "wallet_id": "wallet_abc123",
      "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
      "amount": "25.00",
      "token": "USDC",
      "chain": "base",
      "status": "completed",
      "purpose": "OpenAI API credits",
      "tx_hash": "0x1234...",
      "created_at": "2026-02-21T09:15:00Z",
      "completed_at": "2026-02-21T09:15:30Z"
    }
  ],
  "total": 47,
  "page": 1,
  "limit": 20
}
```

## Error Handling

- `401 Unauthorized` - Invalid or missing API key
- `403 Forbidden` - No access to this wallet
- `404 Not Found` - Wallet does not exist
- `429 Too Many Requests` - Rate limit exceeded

## Use Cases

- **Budget Monitoring**: Track agent spending against limits
- **Anomaly Detection**: Identify unusual spending patterns
- **Multi-Agent Dashboards**: Monitor fleet of agent wallets
- **Compliance Reporting**: Generate spending reports for audits
- **Alert Systems**: Trigger notifications on budget thresholds

## Related Skills

- `sardis-payment` - Execute payments and manage wallets
- `sardis-policy` - Create and manage spending policies
- `sardis-cards` - Virtual card management

## Links

- Website: https://sardis.sh
- Documentation: https://sardis.sh/docs/balance-api
- API Reference: https://api.sardis.sh/v2/docs
- Support: support@sardis.sh
