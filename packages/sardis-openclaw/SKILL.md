---
name: sardis-payment
description: Enable AI agents to create wallets, make secure payments, check balances, and set spending policies through Sardis Payment OS
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
      - kind: uv
        package: sardis-openclaw
        bins: []
    user-invocable: true
    disable-model-invocation: false
---

# Sardis Payment - Payment OS for AI Agents

> AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.

Sardis provides complete payment infrastructure for AI agents with non-custodial MPC wallets, natural language spending policies, and compliance-first design.

## Core Capabilities

1. **Create Wallet**: Provision non-custodial MPC wallets for agents (Turnkey-backed)
2. **Send Payment**: Execute stablecoin transfers with automatic policy enforcement
3. **Check Balance**: Real-time multi-chain balance and spending analytics
4. **Set Spending Policy**: Natural language spending rules automatically enforced
5. **Card Management**: Issue and manage virtual cards for real-world purchases
6. **Compliance Check**: Run preflight compliance on any transaction
7. **Audit Trail**: Complete transaction history with on-chain anchoring

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

### 1. Create Wallet

```bash
# Create a non-custodial MPC wallet for an agent
curl -X POST https://api.sardis.sh/v2/wallets \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_abc123",
    "provider": "turnkey",
    "chain": "base",
    "wallet_name": "My Agent Wallet"
  }'
```

### 2. Send Payment (with policy check)

```bash
# Step 1: Policy dry-run check
POLICY_CHECK=$(curl -s -X POST https://api.sardis.sh/v2/policies/check \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_abc123", "amount": "25.00", "recipient": "0x...", "token": "USDC", "chain": "base"}')

# Step 2: Only proceed if allowed
if echo $POLICY_CHECK | grep -q '"allowed":true'; then
  curl -X POST https://api.sardis.sh/v2/wallets/$SARDIS_WALLET_ID/transfer \
    -H "Authorization: Bearer $SARDIS_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"to": "0xRecipientAddress", "amount": "25.00", "token": "USDC", "chain": "base", "agent_id": "agent_abc123"}'
else
  echo "Payment blocked by policy: $POLICY_CHECK"
fi
```

### 3. Check Balance

```bash
# Get multi-chain wallet balances
curl -X GET https://api.sardis.sh/v2/wallets/$SARDIS_WALLET_ID/balances \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Get single-chain balance
curl -X GET "https://api.sardis.sh/v2/wallets/$SARDIS_WALLET_ID/balance?chain=base" \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

### 4. Set Spending Policy

```bash
# Create policy with natural language
curl -X POST https://api.sardis.sh/v2/policies/apply \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_abc123",
    "natural_language": "Max $500/day, only OpenAI and Anthropic, no weekends"
  }'

# Policy dry-run check
curl -X POST https://api.sardis.sh/v2/policies/check \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_abc123", "amount": "50.00", "token": "USDC"}'
```

### 5. Transaction History

```bash
curl -X GET https://api.sardis.sh/v2/transactions?wallet_id=$SARDIS_WALLET_ID&limit=10 \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

## Example Commands

### Complete Agent Onboarding Flow

```bash
# 1. Create wallet
WALLET=$(curl -s -X POST https://api.sardis.sh/v2/wallets \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_abc123", "provider": "turnkey", "chain": "base"}')
WALLET_ID=$(echo $WALLET | jq -r '.wallet_id')
echo "Wallet created: $WALLET_ID"

# 2. Set spending policy
curl -s -X POST https://api.sardis.sh/v2/policies/apply \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_abc123", "natural_language": "Max $100 per transaction, $500/day, only OpenAI"}'

# 3. Check balance
curl -s -X GET "https://api.sardis.sh/v2/wallets/$WALLET_ID/balances" \
  -H "Authorization: Bearer $SARDIS_API_KEY" | jq '.'

# 4. Send payment (policy auto-enforced)
curl -s -X POST "https://api.sardis.sh/v2/wallets/$WALLET_ID/transfer" \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", "amount": "25.00", "token": "USDC", "chain": "base"}'
```

## Error Handling

Always check response status codes:

- `200 OK` / `201 Created` - Request successful
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
| Tempo | Mainnet | pathUSD |

## Related Skills

- `sardis-balance` - Read-only balance checking and analytics
- `sardis-policy` - Natural language spending policy management
- `sardis-cards` - Virtual card issuance and management
- `sardis-guardrails` - Circuit breaker and kill switch controls
- `sardis-identity` - Agent identity with TAP verification
- `sardis-escrow` - Smart contract escrow for agent-to-agent payments
- `sardis-tempo-pay` - MPP-native payments on Tempo mainnet

## Links

- Website: https://sardis.sh
- Documentation: https://sardis.sh/docs
- GitHub: https://github.com/EfeDurmaz16/sardis
- API Reference: https://api.sardis.sh/v2/docs
- Support: support@sardis.sh
