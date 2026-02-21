---
name: sardis-cards
description: Virtual card issuance and management for AI agents to make real-world purchases
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
    emoji: "💳"
    homepage: https://sardis.sh
    install:
      npm:
        - "@sardis/sdk"
    user-invocable: true
    disable-model-invocation: false
---

# Sardis Cards - Virtual Card Management for AI Agents

Issue virtual cards for AI agents to make real-world purchases with automatic spending controls, fraud detection, and instant freeze capabilities.

## Capabilities

- **Instant Card Issuance**: Create virtual cards in seconds
- **Spending Controls**: Per-transaction, daily, monthly limits
- **Merchant Restrictions**: Category-based and merchant-specific controls
- **Freeze/Unfreeze**: Instant card control for security
- **Transaction Monitoring**: Real-time transaction alerts and history
- **Automatic Fraud Detection**: Block suspicious activity automatically

## Security Model

**ALWAYS ENFORCE:**
- NEVER expose full card numbers in logs or responses
- ALWAYS freeze cards on anomaly detection
- ALWAYS use spending limits (never unlimited)
- ALWAYS log card creation and transactions
- FAIL CLOSED on fraud detection (freeze immediately)

## Quick Setup

```bash
export SARDIS_API_KEY=sk_your_key_here
```

## API Endpoint Patterns

Base URL: `https://api.sardis.sh/v2`

### Issue Virtual Card

```bash
# Create a new virtual card
curl -X POST https://api.sardis.sh/v2/cards \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_abc123",
    "name": "SaaS Subscriptions Card",
    "spending_limit": {
      "per_transaction": "100.00",
      "daily": "500.00",
      "monthly": "2000.00"
    },
    "merchant_controls": {
      "allowed_categories": ["software", "saas", "cloud_services"],
      "blocked_merchants": []
    },
    "expires_in_months": 12
  }'

# Response includes masked card number (full number retrieved separately)
```

### Get Card Details

```bash
# Get card information (masked)
curl -X GET https://api.sardis.sh/v2/cards/{card_id} \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Response:
# {
#   "id": "card_abc123",
#   "last_four": "4242",
#   "status": "active",
#   "spending_limit": {...},
#   "current_spend": {"daily": "125.00", "monthly": "450.00"}
# }
```

### Retrieve Card Number (Sensitive)

```bash
# Get full card details for use (SENSITIVE - log carefully)
curl -X GET https://api.sardis.sh/v2/cards/{card_id}/reveal \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Response:
# {
#   "number": "4111111111111111",
#   "cvv": "123",
#   "exp_month": "12",
#   "exp_year": "2027",
#   "billing_address": {...}
# }

# WARNING: Never log or display this response
```

### Freeze Card

```bash
# Immediately freeze card (blocks all transactions)
curl -X POST https://api.sardis.sh/v2/cards/{card_id}/freeze \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Suspicious activity detected"
  }'
```

### Unfreeze Card

```bash
# Unfreeze card (resume normal operation)
curl -X POST https://api.sardis.sh/v2/cards/{card_id}/unfreeze \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

### Update Spending Limits

```bash
# Modify card spending limits
curl -X PATCH https://api.sardis.sh/v2/cards/{card_id}/limits \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "per_transaction": "150.00",
    "daily": "750.00",
    "monthly": "3000.00"
  }'
```

### List Card Transactions

```bash
# Get transaction history for a card
curl -X GET "https://api.sardis.sh/v2/cards/{card_id}/transactions?limit=20" \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

### List All Cards

```bash
# Get all cards for an agent
curl -X GET "https://api.sardis.sh/v2/agents/{agent_id}/cards" \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

### Terminate Card

```bash
# Permanently close card (cannot be reversed)
curl -X DELETE https://api.sardis.sh/v2/cards/{card_id} \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Agent deactivated"
  }'
```

## Example Commands

### Issue Card with Conservative Limits

```bash
# Create a card for a procurement agent
AGENT_ID=agent_abc123

CARD=$(curl -s -X POST https://api.sardis.sh/v2/cards \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "'$AGENT_ID'",
    "name": "Procurement Agent Card",
    "spending_limit": {
      "per_transaction": "50.00",
      "daily": "200.00",
      "monthly": "1000.00"
    },
    "merchant_controls": {
      "allowed_categories": ["office_supplies", "software"],
      "allowed_merchants": ["amazon.com", "staples.com"]
    },
    "expires_in_months": 6
  }')

CARD_ID=$(echo $CARD | jq -r '.id')
echo "Card created: $CARD_ID"
echo "Last 4 digits: $(echo $CARD | jq -r '.last_four')"
```

### Monitor Card Spending

```bash
# Check current spend against limits
CARD_ID=card_abc123

CARD_INFO=$(curl -s -X GET https://api.sardis.sh/v2/cards/$CARD_ID \
  -H "Authorization: Bearer $SARDIS_API_KEY")

DAILY_SPENT=$(echo $CARD_INFO | jq -r '.current_spend.daily')
DAILY_LIMIT=$(echo $CARD_INFO | jq -r '.spending_limit.daily')

echo "Daily spending: $DAILY_SPENT / $DAILY_LIMIT"

# Alert if approaching limit
if (( $(echo "$DAILY_SPENT > $DAILY_LIMIT * 0.8" | bc -l) )); then
  echo "WARNING: Card approaching daily limit"
fi
```

### Freeze on Anomaly Detection

```bash
# Freeze card if suspicious activity detected
CARD_ID=card_abc123

# Get recent transactions
TRANSACTIONS=$(curl -s -X GET "https://api.sardis.sh/v2/cards/$CARD_ID/transactions?limit=5" \
  -H "Authorization: Bearer $SARDIS_API_KEY")

# Check for multiple rapid transactions
TX_COUNT=$(echo $TRANSACTIONS | jq '.transactions | length')

if [ $TX_COUNT -gt 3 ]; then
  echo "ALERT: Multiple rapid transactions detected"

  # Freeze card immediately
  curl -X POST https://api.sardis.sh/v2/cards/$CARD_ID/freeze \
    -H "Authorization: Bearer $SARDIS_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "reason": "Anomaly: Multiple rapid transactions"
    }'

  echo "Card frozen for review"
fi
```

### Card Dashboard

```bash
# Get overview of all cards for an agent
AGENT_ID=agent_abc123

echo "=== Card Dashboard ==="
curl -s -X GET "https://api.sardis.sh/v2/agents/$AGENT_ID/cards" \
  -H "Authorization: Bearer $SARDIS_API_KEY" | \
  jq -r '.cards[] | "Card \(.last_four): \(.status) - Daily: $\(.current_spend.daily)/$\(.spending_limit.daily)"'
```

### Bulk Card Freeze

```bash
# Freeze all cards for an agent (emergency shutdown)
AGENT_ID=agent_abc123

echo "Freezing all cards for agent $AGENT_ID..."

curl -s -X GET "https://api.sardis.sh/v2/agents/$AGENT_ID/cards" \
  -H "Authorization: Bearer $SARDIS_API_KEY" | \
  jq -r '.cards[].id' | \
  while read CARD_ID; do
    curl -X POST https://api.sardis.sh/v2/cards/$CARD_ID/freeze \
      -H "Authorization: Bearer $SARDIS_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"reason": "Emergency shutdown"}'
    echo "Frozen: $CARD_ID"
  done
```

## Merchant Category Codes

Common categories for `allowed_categories`:

- `software` - Software purchases and subscriptions
- `saas` - SaaS subscriptions
- `cloud_services` - Cloud computing (AWS, GCP, Azure)
- `office_supplies` - Office equipment and supplies
- `online_marketplaces` - Amazon, eBay, etc.
- `advertising` - Google Ads, Facebook Ads
- `telecommunications` - Phone, internet services
- `utilities` - Electricity, water, gas
- `travel` - Flights, hotels, transportation
- `restaurants` - Food and dining
- `groceries` - Grocery stores
- `fuel` - Gas stations
- `entertainment` - Movies, games, events

Blocked categories:
- `gambling` - Casinos, betting, lottery
- `adult` - Adult content and services
- `crypto_exchange` - Cryptocurrency exchanges
- `cash_advance` - ATM withdrawals, cash advances
- `wire_transfer` - Wire transfer services

## Response Examples

### Card Creation Response

```json
{
  "id": "card_abc123",
  "agent_id": "agent_xyz789",
  "name": "SaaS Subscriptions Card",
  "last_four": "4242",
  "status": "active",
  "spending_limit": {
    "per_transaction": "100.00",
    "daily": "500.00",
    "monthly": "2000.00"
  },
  "current_spend": {
    "daily": "0.00",
    "monthly": "0.00"
  },
  "merchant_controls": {
    "allowed_categories": ["software", "saas", "cloud_services"],
    "blocked_merchants": []
  },
  "expires": "2027-12-31",
  "created_at": "2026-02-21T10:30:00Z"
}
```

### Card Transactions Response

```json
{
  "card_id": "card_abc123",
  "transactions": [
    {
      "id": "tx_abc123",
      "amount": "29.99",
      "merchant": "OpenAI",
      "merchant_category": "software",
      "status": "approved",
      "created_at": "2026-02-21T09:15:00Z"
    },
    {
      "id": "tx_def456",
      "amount": "150.00",
      "merchant": "Unknown Merchant",
      "merchant_category": "gambling",
      "status": "declined",
      "decline_reason": "Blocked merchant category",
      "created_at": "2026-02-21T08:30:00Z"
    }
  ],
  "total": 47,
  "page": 1
}
```

### Card Reveal Response (SENSITIVE)

```json
{
  "number": "4111111111111111",
  "cvv": "123",
  "exp_month": "12",
  "exp_year": "2027",
  "billing_address": {
    "line1": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "postal_code": "94105",
    "country": "US"
  },
  "warning": "Never log or display this data. Use immediately and discard."
}
```

## Security Best Practices

### DO:
- Issue cards with minimum required limits
- Use merchant category restrictions
- Freeze cards on anomalies
- Monitor transactions in real-time
- Set expiration dates
- Use descriptive card names
- Log all card operations

### DON'T:
- Log full card numbers or CVVs
- Issue unlimited cards
- Allow all merchant categories
- Ignore transaction alerts
- Share cards across agents
- Leave unused cards active

## Error Handling

- `400 Bad Request` - Invalid spending limits or merchant categories
- `401 Unauthorized` - Invalid API key
- `403 Forbidden` - Card frozen or spending limit exceeded
- `404 Not Found` - Card does not exist
- `409 Conflict` - Card already frozen/terminated
- `429 Too Many Requests` - Rate limit exceeded

### Transaction Decline Reasons

- `insufficient_balance` - Wallet balance too low
- `spending_limit_exceeded` - Card limit reached
- `blocked_merchant` - Merchant on blocklist
- `blocked_category` - Merchant category blocked
- `card_frozen` - Card is frozen
- `card_expired` - Card past expiration date
- `invalid_cvv` - Incorrect CVV provided
- `fraud_suspected` - Fraud detection triggered

## Use Cases

- **SaaS Subscriptions**: Automated subscription management
- **Cloud Services**: AWS/GCP/Azure spending for agents
- **Procurement Agents**: Safe purchasing with controls
- **Marketing Agents**: Google Ads, Facebook Ads spending
- **Travel Agents**: Flight and hotel bookings
- **Employee Cards**: Virtual cards for agent "employees"

## Related Skills

- `sardis-payment` - Crypto payments and wallet management
- `sardis-policy` - Spending policy creation and management
- `sardis-balance` - Transaction monitoring and analytics

## Links

- Website: https://sardis.sh
- Documentation: https://sardis.sh/docs/virtual-cards
- API Reference: https://api.sardis.sh/v2/docs
- Support: support@sardis.sh
