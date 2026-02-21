---
name: sardis-escrow
description: Smart contract escrow for agent-to-agent payments with delivery confirmation
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
    emoji: "🔒"
    homepage: https://sardis.sh
    install:
      npm:
        - "@sardis/sdk"
    user-invocable: true
    disable-model-invocation: false
---

# Sardis Escrow - Smart Contract Payment Protection

Secure agent-to-agent payments with smart contract escrow. Funds held until delivery confirmation, protecting both buyer and seller in autonomous transactions.

## Capabilities

- **Create Escrow**: Establish trustless payment agreements
- **Fund Escrow**: Deposit funds into smart contract custody
- **Confirm Delivery**: Seller confirms work/goods delivered
- **Release Payment**: Buyer releases funds after verification
- **Escrow Status**: Real-time escrow state tracking
- **Dispute Resolution**: Built-in arbitration for failed deliveries

## Security Model

**ESCROW-PROTECTED**: Funds locked in smart contracts until both parties confirm. No centralized custody.

## Quick Setup

```bash
export SARDIS_API_KEY=sk_your_key_here
```

## API Endpoint Patterns

Base URL: `https://api.sardis.sh/v2`

### Create Escrow

```bash
# Establish a new escrow agreement
curl -X POST https://api.sardis.sh/v2/escrow \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_wallet_id": "wallet_buyer123",
    "seller_wallet_id": "wallet_seller456",
    "amount": "500.00",
    "token": "USDC",
    "chain": "base",
    "description": "API development services - 40 hours",
    "delivery_deadline": "2026-03-01T00:00:00Z",
    "auto_release_after_hours": 72,
    "milestones": [
      {
        "description": "Phase 1: Design",
        "amount": "150.00",
        "deadline": "2026-02-25T00:00:00Z"
      },
      {
        "description": "Phase 2: Implementation",
        "amount": "250.00",
        "deadline": "2026-02-28T00:00:00Z"
      },
      {
        "description": "Phase 3: Testing & Deployment",
        "amount": "100.00",
        "deadline": "2026-03-01T00:00:00Z"
      }
    ]
  }'

# Example response:
# {
#   "escrow_id": "escrow_xyz789",
#   "contract_address": "0x1234567890abcdef...",
#   "status": "created",
#   "buyer": "wallet_buyer123",
#   "seller": "wallet_seller456",
#   "amount": "500.00",
#   "token": "USDC",
#   "chain": "base",
#   "funded": false,
#   "created_at": "2026-02-21T10:00:00Z"
# }
```

### Fund Escrow

```bash
# Buyer deposits funds into escrow contract
curl -X POST https://api.sardis.sh/v2/escrow/{escrow_id}/fund \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "escrow_id": "escrow_xyz789",
    "wallet_id": "wallet_buyer123"
  }'

# Example:
curl -X POST https://api.sardis.sh/v2/escrow/escrow_xyz789/fund \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"escrow_id": "escrow_xyz789", "wallet_id": "wallet_buyer123"}'
```

### Confirm Delivery

```bash
# Seller confirms delivery of goods/services
curl -X POST https://api.sardis.sh/v2/escrow/{escrow_id}/confirm-delivery \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "escrow_id": "escrow_xyz789",
    "wallet_id": "wallet_seller456",
    "delivery_proof": {
      "type": "github_pr",
      "url": "https://github.com/company/repo/pull/123",
      "commit_hash": "abc123def456",
      "notes": "All 3 milestones completed and tested"
    }
  }'
```

### Release Escrow

```bash
# Buyer releases funds to seller after verification
curl -X POST https://api.sardis.sh/v2/escrow/{escrow_id}/release \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "escrow_id": "escrow_xyz789",
    "wallet_id": "wallet_buyer123",
    "amount": "500.00",
    "milestone_id": null,
    "rating": 5,
    "feedback": "Excellent work, delivered ahead of schedule"
  }'

# Partial release for milestone:
curl -X POST https://api.sardis.sh/v2/escrow/escrow_xyz789/release \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "escrow_id": "escrow_xyz789",
    "wallet_id": "wallet_buyer123",
    "amount": "150.00",
    "milestone_id": "milestone_1"
  }'
```

### Get Escrow Status

```bash
# Query current escrow state and transaction history
curl -X GET https://api.sardis.sh/v2/escrow/{escrow_id} \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Example:
curl -X GET https://api.sardis.sh/v2/escrow/escrow_xyz789 \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

## Example Commands

### Complete Escrow Workflow

```bash
# 1. Create escrow agreement
ESCROW=$(curl -s -X POST https://api.sardis.sh/v2/escrow \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_wallet_id": "wallet_buyer123",
    "seller_wallet_id": "wallet_seller456",
    "amount": "500.00",
    "token": "USDC",
    "chain": "base",
    "description": "Development work"
  }')

ESCROW_ID=$(echo "$ESCROW" | jq -r '.escrow_id')
echo "Created escrow: $ESCROW_ID"

# 2. Buyer funds the escrow
echo "Funding escrow..."
curl -X POST "https://api.sardis.sh/v2/escrow/$ESCROW_ID/fund" \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"escrow_id\": \"$ESCROW_ID\", \"wallet_id\": \"wallet_buyer123\"}"

# 3. Wait for seller delivery (automated)
echo "Waiting for delivery confirmation..."

# 4. Seller confirms delivery
curl -X POST "https://api.sardis.sh/v2/escrow/$ESCROW_ID/confirm-delivery" \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"escrow_id\": \"$ESCROW_ID\", \"wallet_id\": \"wallet_seller456\"}"

# 5. Buyer verifies and releases
echo "Releasing payment to seller..."
curl -X POST "https://api.sardis.sh/v2/escrow/$ESCROW_ID/release" \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"escrow_id\": \"$ESCROW_ID\",
    \"wallet_id\": \"wallet_buyer123\",
    \"amount\": \"500.00\",
    \"rating\": 5
  }"

echo "Escrow completed!"
```

### Monitor Escrow Status

```bash
# Track escrow progress
ESCROW_ID=escrow_xyz789

while true; do
  STATUS=$(curl -s -X GET "https://api.sardis.sh/v2/escrow/$ESCROW_ID" \
    -H "Authorization: Bearer $SARDIS_API_KEY")

  STATE=$(echo "$STATUS" | jq -r '.status')
  FUNDED=$(echo "$STATUS" | jq -r '.funded')
  DELIVERED=$(echo "$STATUS" | jq -r '.delivery_confirmed')

  echo "=== Escrow Status ==="
  echo "State: $STATE"
  echo "Funded: $FUNDED"
  echo "Delivery Confirmed: $DELIVERED"

  if [[ "$STATE" == "completed" || "$STATE" == "refunded" ]]; then
    echo "Escrow finalized: $STATE"
    break
  fi

  sleep 30
done
```

### List Active Escrows

```bash
# Get all escrows for a wallet
WALLET_ID=wallet_buyer123

curl -s -X GET "https://api.sardis.sh/v2/escrow?wallet_id=$WALLET_ID&status=active" \
  -H "Authorization: Bearer $SARDIS_API_KEY" | \
  jq -r '.escrows[] | "\(.escrow_id): \(.description) - \(.amount) \(.token) [\(.status)]"'
```

### Milestone-Based Release

```bash
# Release funds incrementally as milestones complete
ESCROW_ID=escrow_xyz789

# Release milestone 1
curl -X POST "https://api.sardis.sh/v2/escrow/$ESCROW_ID/release" \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "escrow_id": "'"$ESCROW_ID"'",
    "wallet_id": "wallet_buyer123",
    "amount": "150.00",
    "milestone_id": "milestone_1",
    "feedback": "Phase 1 design approved"
  }'

echo "Milestone 1 payment released"
```

## Response Examples

### Create Escrow Response

```json
{
  "escrow_id": "escrow_xyz789",
  "contract_address": "0x1234567890abcdef1234567890abcdef12345678",
  "status": "created",
  "buyer": "wallet_buyer123",
  "seller": "wallet_seller456",
  "amount": "500.00",
  "token": "USDC",
  "chain": "base",
  "description": "API development services - 40 hours",
  "delivery_deadline": "2026-03-01T00:00:00Z",
  "auto_release_after_hours": 72,
  "milestones": [
    {
      "milestone_id": "milestone_1",
      "description": "Phase 1: Design",
      "amount": "150.00",
      "deadline": "2026-02-25T00:00:00Z",
      "status": "pending"
    },
    {
      "milestone_id": "milestone_2",
      "description": "Phase 2: Implementation",
      "amount": "250.00",
      "deadline": "2026-02-28T00:00:00Z",
      "status": "pending"
    },
    {
      "milestone_id": "milestone_3",
      "description": "Phase 3: Testing & Deployment",
      "amount": "100.00",
      "deadline": "2026-03-01T00:00:00Z",
      "status": "pending"
    }
  ],
  "funded": false,
  "delivery_confirmed": false,
  "created_at": "2026-02-21T10:00:00Z"
}
```

### Escrow Status Response

```json
{
  "escrow_id": "escrow_xyz789",
  "contract_address": "0x1234567890abcdef1234567890abcdef12345678",
  "status": "funded",
  "buyer": {
    "wallet_id": "wallet_buyer123",
    "agent_id": "agent_buyer"
  },
  "seller": {
    "wallet_id": "wallet_seller456",
    "agent_id": "agent_seller"
  },
  "amount": "500.00",
  "token": "USDC",
  "chain": "base",
  "description": "API development services - 40 hours",
  "funded": true,
  "funded_at": "2026-02-21T10:30:00Z",
  "funded_tx_hash": "0xabcdef123456...",
  "delivery_confirmed": false,
  "delivery_confirmed_at": null,
  "released_amount": "0.00",
  "remaining_amount": "500.00",
  "milestones": [
    {
      "milestone_id": "milestone_1",
      "description": "Phase 1: Design",
      "amount": "150.00",
      "deadline": "2026-02-25T00:00:00Z",
      "status": "pending",
      "released": false
    }
  ],
  "timeline": [
    {
      "event": "created",
      "timestamp": "2026-02-21T10:00:00Z"
    },
    {
      "event": "funded",
      "timestamp": "2026-02-21T10:30:00Z",
      "tx_hash": "0xabcdef123456..."
    }
  ],
  "auto_release_at": "2026-03-04T10:30:00Z",
  "created_at": "2026-02-21T10:00:00Z"
}
```

### Release Response

```json
{
  "escrow_id": "escrow_xyz789",
  "status": "completed",
  "released_amount": "500.00",
  "token": "USDC",
  "recipient": "wallet_seller456",
  "tx_hash": "0x9876543210fedcba9876543210fedcba98765432",
  "rating": 5,
  "feedback": "Excellent work, delivered ahead of schedule",
  "released_at": "2026-02-28T14:00:00Z",
  "contract_address": "0x1234567890abcdef1234567890abcdef12345678",
  "message": "Escrow released successfully. Funds transferred to seller."
}
```

## Error Handling

- `401 Unauthorized` - Invalid or missing API key
- `403 Forbidden` - Not authorized to interact with this escrow
- `404 Not Found` - Escrow not found
- `409 Conflict` - Escrow already funded/released
- `400 Bad Request` - Invalid escrow parameters or insufficient funds
- `422 Unprocessable Entity` - Deadline passed or milestone not met

## Use Cases

- **Agent-to-Agent Hiring**: Secure payments for AI agent services
- **API Integrations**: Pay for third-party API development
- **Content Creation**: Escrow for commissioned content work
- **Data Processing**: Pay for dataset processing/labeling
- **Bounty Programs**: Hold funds for completed tasks

## Related Skills

- `sardis-payment` - Direct payments without escrow
- `sardis-identity` - Verify agent identities before escrow
- `sardis-balance` - Check wallet balances for funding

## Links

- Website: https://sardis.sh
- Documentation: https://sardis.sh/docs/escrow
- Smart Contracts: https://github.com/sardis-sh/contracts
- API Reference: https://api.sardis.sh/v2/docs
- Support: support@sardis.sh
