---
name: sardis-payment
description: Enable AI agents to make secure, policy-controlled payments through Sardis Payment OS
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - SARDIS_API_KEY
        - SARDIS_WALLET_ID
      bins:
        - curl
      config:
        - ~/.sardis/config.json
    primaryEnv: SARDIS_API_KEY
    emoji: "💳"
    homepage: https://sardis.sh
    install:
      npm:
        - "@sardis/sdk"
    user-invocable: true
    disable-model-invocation: false
---

# Sardis Payment - Core Payment Execution Skill

> AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.

Sardis provides complete payment infrastructure for AI agents with non-custodial MPC wallets, natural language spending policies, and compliance-first design.

## Capabilities

- **Payment Execution**: Send USDC/USDT/EURC across 5+ chains (Base, Polygon, Ethereum, Arbitrum, Optimism)
- **Balance Checking**: Real-time wallet balance and spending analytics
- **Policy Enforcement**: Natural language spending rules automatically enforced
- **Card Management**: Issue and manage virtual cards for real-world purchases
- **Audit Trail**: Complete transaction history with compliance logging

## Security Requirements

**CRITICAL - ALWAYS ENFORCE:**
- ALWAYS check spending policy before payment execution
- NEVER bypass approval flows for transactions
- NEVER hardcode wallet addresses or private keys
- ALWAYS log transaction attempts for audit trail
- ALWAYS verify recipient address format
- FAIL CLOSED on policy violations (deny by default)

## Quick Setup

```bash
export SARDIS_API_KEY=sk_your_key_here
export SARDIS_WALLET_ID=wallet_abc123
```

## API Endpoint Patterns

All API calls use the base URL: `https://api.sardis.sh/v2`

### Payment Execution

```bash
# Execute a payment (policy automatically enforced)
curl -X POST https://api.sardis.sh/v2/payments \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "'$SARDIS_WALLET_ID'",
    "to": "0xRecipientAddress",
    "amount": "25.00",
    "token": "USDC",
    "chain": "base",
    "purpose": "OpenAI API credits"
  }'
```

### Check Balance

```bash
# Get wallet balance
curl -X GET https://api.sardis.sh/v2/wallets/$SARDIS_WALLET_ID/balance \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

### Policy Check (Dry Run)

```bash
# Check if payment would be allowed WITHOUT executing
curl -X POST https://api.sardis.sh/v2/policies/check \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "'$SARDIS_WALLET_ID'",
    "amount": "50.00",
    "vendor": "openai.com",
    "token": "USDC"
  }'
```

### Transaction History

```bash
# List recent transactions
curl -X GET https://api.sardis.sh/v2/wallets/$SARDIS_WALLET_ID/transactions?limit=10 \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

## Example Commands

### Safe Payment Flow

```bash
# Step 1: Check policy FIRST
POLICY_CHECK=$(curl -s -X POST https://api.sardis.sh/v2/policies/check \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"wallet_id": "'$SARDIS_WALLET_ID'", "amount": "25.00", "vendor": "openai.com"}')

# Step 2: Only proceed if allowed
if echo $POLICY_CHECK | grep -q '"allowed":true'; then
  curl -X POST https://api.sardis.sh/v2/payments \
    -H "Authorization: Bearer $SARDIS_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"wallet_id": "'$SARDIS_WALLET_ID'", "to": "0x...", "amount": "25.00", "token": "USDC", "chain": "base"}'
else
  echo "Payment blocked by policy: $POLICY_CHECK"
fi
```

### Check Spending Summary

```bash
# Get daily spending summary
curl -X GET https://api.sardis.sh/v2/wallets/$SARDIS_WALLET_ID/spending/summary?period=day \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

## Error Handling

Always check response status codes:

- `200 OK` - Request successful
- `400 Bad Request` - Invalid parameters (check amount, address format, token)
- `401 Unauthorized` - Invalid or missing API key
- `403 Forbidden` - Policy violation (payment blocked by spending rules)
- `404 Not Found` - Wallet or transaction not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Contact support@sardis.sh

### Example Error Response

```json
{
  "error": {
    "code": "POLICY_VIOLATION",
    "message": "Daily spending limit of $500 exceeded. Current: $475, Requested: $50",
    "details": {
      "limit": "500.00",
      "current": "475.00",
      "requested": "50.00"
    }
  }
}
```

## Supported Chains & Tokens

| Chain | Network | Tokens |
|-------|---------|--------|
| Base | Mainnet | USDC, EURC |
| Polygon | Mainnet | USDC, USDT, EURC |
| Ethereum | Mainnet | USDC, USDT, PYUSD, EURC |
| Arbitrum | One | USDC, USDT |
| Optimism | Mainnet | USDC, USDT |

## Related Skills

- `sardis-balance` - Read-only balance checking and analytics
- `sardis-policy` - Natural language spending policy management
- `sardis-cards` - Virtual card issuance and management

## Links

- Website: https://sardis.sh
- Documentation: https://sardis.sh/docs
- GitHub: https://github.com/EfeDurmaz16/sardis
- API Reference: https://api.sardis.sh/v2/docs
- Support: support@sardis.sh
