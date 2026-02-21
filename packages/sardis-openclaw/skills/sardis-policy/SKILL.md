---
name: sardis-policy
description: Natural language spending policy creation and management for Sardis agent wallets
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
    emoji: "🛡️"
    homepage: https://sardis.sh
    install:
      npm:
        - "@sardis/sdk"
    user-invocable: true
    disable-model-invocation: false
---

# Sardis Policy - Natural Language Spending Controls

Create and manage spending policies for AI agents using natural language. Define limits, restrictions, and approval workflows without complex configuration.

## Capabilities

- **Natural Language Policies**: "Max $500/day, only Amazon and OpenAI, no weekends"
- **Policy Templates**: Pre-built templates for common scenarios
- **Policy Testing**: Dry-run transactions against policies without execution
- **Multi-Layer Policies**: Combine transaction, daily, weekly, monthly limits
- **Vendor Restrictions**: Allowlists, blocklists, category controls
- **Time-Based Rules**: Weekend blocks, business hours only, time-of-day limits

## Security Model

Policies are IMMUTABLE once created. To change a policy, create a new version and migrate the wallet.

## Quick Setup

```bash
export SARDIS_API_KEY=sk_your_key_here
```

## API Endpoint Patterns

Base URL: `https://api.sardis.sh/v2`

### Create Policy with Natural Language

```bash
# Create a new spending policy from natural language
curl -X POST https://api.sardis.sh/v2/policies \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Procurement Agent Policy",
    "description": "Max $500/day, only Amazon and OpenAI, no weekends",
    "wallet_id": "wallet_abc123"
  }'

# The natural language in "description" is automatically parsed into rules
```

### Create Policy with Explicit Rules

```bash
# Create policy with structured rules
curl -X POST https://api.sardis.sh/v2/policies \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SaaS Subscription Policy",
    "wallet_id": "wallet_abc123",
    "rules": {
      "per_transaction_limit": "100.00",
      "daily_limit": "500.00",
      "weekly_limit": "2000.00",
      "monthly_limit": "8000.00",
      "allowed_vendors": ["openai.com", "anthropic.com", "github.com"],
      "blocked_categories": ["gambling", "crypto-exchange"],
      "time_restrictions": {
        "allow_weekends": false,
        "business_hours_only": true,
        "timezone": "America/New_York"
      },
      "require_approval_above": "200.00"
    }
  }'
```

### List Policies

```bash
# Get all policies for a wallet
curl -X GET https://api.sardis.sh/v2/wallets/{wallet_id}/policies \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

### Test Policy (Dry Run)

```bash
# Check if a transaction would be allowed WITHOUT executing it
curl -X POST https://api.sardis.sh/v2/policies/check \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "wallet_abc123",
    "amount": "75.00",
    "vendor": "openai.com",
    "token": "USDC",
    "chain": "base"
  }'

# Response:
# {
#   "allowed": true,
#   "reason": "Transaction approved",
#   "remaining_daily": "425.00",
#   "remaining_weekly": "1925.00"
# }
```

### Get Policy Details

```bash
# Get detailed policy rules
curl -X GET https://api.sardis.sh/v2/policies/{policy_id} \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

## Policy Templates

### Template: Conservative Procurement

```bash
curl -X POST https://api.sardis.sh/v2/policies/from-template \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "conservative-procurement",
    "wallet_id": "wallet_abc123",
    "params": {
      "daily_limit": "300.00",
      "allowed_vendors": ["amazon.com", "walmart.com"]
    }
  }'

# Template rules:
# - Low per-transaction limit ($50)
# - Moderate daily limit (configurable)
# - Vendor allowlist only
# - Require approval above $100
# - Business hours only
```

### Template: API Service Agent

```bash
curl -X POST https://api.sardis.sh/v2/policies/from-template \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "api-service-agent",
    "wallet_id": "wallet_abc123",
    "params": {
      "daily_limit": "1000.00",
      "allowed_vendors": ["openai.com", "anthropic.com", "stripe.com"]
    }
  }'

# Template rules:
# - Higher per-transaction ($500)
# - API vendor allowlist
# - 24/7 allowed (services don't sleep)
# - Auto-approve under $100
```

### Template: Restricted Trial

```bash
curl -X POST https://api.sardis.sh/v2/policies/from-template \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "restricted-trial",
    "wallet_id": "wallet_abc123",
    "params": {
      "total_limit": "50.00",
      "expires_at": "2026-03-21T00:00:00Z"
    }
  }'

# Template rules:
# - Very low total limit
# - Expires after period
# - Require approval for all transactions
# - Vendor allowlist only
```

### Template: Employee Card

```bash
curl -X POST https://api.sardis.sh/v2/policies/from-template \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "employee-card",
    "wallet_id": "wallet_abc123",
    "params": {
      "daily_limit": "200.00",
      "blocked_categories": ["gambling", "adult", "crypto-exchange"]
    }
  }'

# Template rules:
# - Moderate limits
# - Category blocklist
# - Weekend spending allowed
# - Detailed audit logging
```

## Example Commands

### Create Simple Policy

```bash
# Quick policy creation with natural language
WALLET_ID=wallet_abc123

curl -X POST https://api.sardis.sh/v2/policies \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Marketing Agent",
    "description": "Max $100 per transaction, $500/day, only Google Ads and Meta",
    "wallet_id": "'$WALLET_ID'"
  }'
```

### Test Before Payment

```bash
# Always test policy before executing payment
WALLET_ID=wallet_abc123
AMOUNT=75.00
VENDOR=openai.com

CHECK_RESULT=$(curl -s -X POST https://api.sardis.sh/v2/policies/check \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "'$WALLET_ID'",
    "amount": "'$AMOUNT'",
    "vendor": "'$VENDOR'"
  }')

if echo $CHECK_RESULT | jq -e '.allowed == true' > /dev/null; then
  echo "Payment would be approved"
  echo "Remaining daily: $(echo $CHECK_RESULT | jq -r '.remaining_daily')"
else
  echo "Payment would be BLOCKED"
  echo "Reason: $(echo $CHECK_RESULT | jq -r '.reason')"
fi
```

### Batch Policy Testing

```bash
# Test multiple scenarios
WALLET_ID=wallet_abc123

TRANSACTIONS='[
  {"amount": "25.00", "vendor": "openai.com"},
  {"amount": "150.00", "vendor": "amazon.com"},
  {"amount": "500.00", "vendor": "stripe.com"}
]'

echo "$TRANSACTIONS" | jq -c '.[]' | while read tx; do
  AMOUNT=$(echo $tx | jq -r '.amount')
  VENDOR=$(echo $tx | jq -r '.vendor')

  RESULT=$(curl -s -X POST https://api.sardis.sh/v2/policies/check \
    -H "Authorization: Bearer $SARDIS_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "wallet_id": "'$WALLET_ID'",
      "amount": "'$AMOUNT'",
      "vendor": "'$VENDOR'"
    }')

  ALLOWED=$(echo $RESULT | jq -r '.allowed')
  echo "$AMOUNT to $VENDOR: $ALLOWED"
done
```

### Update Policy (Create New Version)

```bash
# Policies are immutable, so create new version
OLD_POLICY_ID=policy_abc123
WALLET_ID=wallet_abc123

# Create new policy
NEW_POLICY=$(curl -s -X POST https://api.sardis.sh/v2/policies \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Procurement Policy",
    "description": "Max $750/day, only Amazon OpenAI and Anthropic, no weekends",
    "wallet_id": "'$WALLET_ID'",
    "replaces": "'$OLD_POLICY_ID'"
  }')

echo "New policy created: $(echo $NEW_POLICY | jq -r '.id')"
```

## Response Examples

### Policy Check Response (Allowed)

```json
{
  "allowed": true,
  "reason": "Transaction approved within limits",
  "policy_id": "policy_abc123",
  "checks": {
    "per_transaction_limit": "pass",
    "daily_limit": "pass",
    "vendor_allowlist": "pass",
    "time_restriction": "pass"
  },
  "remaining": {
    "daily": "425.00",
    "weekly": "1925.00",
    "monthly": "7425.00"
  }
}
```

### Policy Check Response (Blocked)

```json
{
  "allowed": false,
  "reason": "Daily spending limit exceeded",
  "policy_id": "policy_abc123",
  "checks": {
    "per_transaction_limit": "pass",
    "daily_limit": "fail",
    "vendor_allowlist": "pass"
  },
  "details": {
    "limit": "500.00",
    "current_spend": "475.00",
    "requested": "50.00",
    "would_exceed_by": "25.00"
  }
}
```

### Policy Details Response

```json
{
  "id": "policy_abc123",
  "name": "SaaS Subscription Policy",
  "wallet_id": "wallet_abc123",
  "rules": {
    "per_transaction_limit": "100.00",
    "daily_limit": "500.00",
    "weekly_limit": "2000.00",
    "monthly_limit": "8000.00",
    "allowed_vendors": ["openai.com", "anthropic.com", "github.com"],
    "blocked_categories": ["gambling", "crypto-exchange"],
    "time_restrictions": {
      "allow_weekends": false,
      "business_hours_only": true,
      "business_hours": "09:00-17:00",
      "timezone": "America/New_York"
    },
    "require_approval_above": "200.00"
  },
  "created_at": "2026-02-21T10:00:00Z",
  "version": 2
}
```

## Natural Language Parser Examples

The policy description field supports these patterns:

```
"Max $500/day, only Amazon and OpenAI"
→ daily_limit: 500, allowed_vendors: [amazon.com, openai.com]

"$100 per transaction, $1000/week, no weekends"
→ per_transaction_limit: 100, weekly_limit: 1000, allow_weekends: false

"Only verified merchants, require approval above $200"
→ verified_only: true, require_approval_above: 200

"Block gambling and crypto, business hours only"
→ blocked_categories: [gambling, crypto-exchange], business_hours_only: true

"Total budget $5000, expires March 1st"
→ total_limit: 5000, expires_at: 2026-03-01T00:00:00Z
```

## Available Templates

| Template | Use Case | Key Features |
|----------|----------|--------------|
| `conservative-procurement` | Purchasing agent | Low limits, vendor allowlist, approval required |
| `api-service-agent` | API/SaaS agent | Higher limits, 24/7, auto-approve |
| `restricted-trial` | Trial/demo | Very low limits, expires |
| `employee-card` | Employee spending | Moderate limits, category blocks |
| `unrestricted` | Trusted agent | High limits, minimal restrictions |

## Error Handling

- `400 Bad Request` - Invalid policy syntax or conflicting rules
- `401 Unauthorized` - Invalid API key
- `403 Forbidden` - Cannot modify policy (immutable)
- `404 Not Found` - Policy or wallet not found

## Use Cases

- **Agentic Procurement**: Safe purchasing with automatic guardrails
- **API Service Agents**: Control cloud spending for LLM/SaaS
- **Employee Cards**: Virtual cards with spending controls
- **Trial Accounts**: Time-limited, low-budget wallets
- **Multi-Tier Agents**: Different policies for different agent roles

## Related Skills

- `sardis-payment` - Execute payments with policy enforcement
- `sardis-balance` - Monitor spending against policy limits
- `sardis-cards` - Virtual cards with policy controls

## Links

- Website: https://sardis.sh
- Documentation: https://sardis.sh/docs/policies
- API Reference: https://api.sardis.sh/v2/docs
- Support: support@sardis.sh
