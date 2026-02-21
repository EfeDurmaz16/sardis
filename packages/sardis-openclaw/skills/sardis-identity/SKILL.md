---
name: sardis-identity
description: Agent identity management with TAP protocol verification and reputation tracking
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
    emoji: "🆔"
    homepage: https://sardis.sh
    install:
      npm:
        - "@sardis/sdk"
    user-invocable: true
    disable-model-invocation: false
---

# Sardis Identity - Agent Identity & Reputation

Complete identity lifecycle management for AI agents using TAP (Trust Anchor Protocol). Register agents, verify credentials, build reputation, and issue identity cards.

## Capabilities

- **Agent Registration**: Create verified agent identities with TAP attestation
- **Identity Retrieval**: Get agent credentials and verification status
- **Reputation Tracking**: Submit and query agent reputation scores
- **Identity Cards**: Generate shareable agent identity cards
- **TAP Verification**: Ed25519 and ECDSA-P256 cryptographic verification

## Security Model

**IDENTITY-CRITICAL**: Agent identities are cryptographically verified and tied to payment capabilities. Handle with care.

## Quick Setup

```bash
export SARDIS_API_KEY=sk_your_key_here
```

## API Endpoint Patterns

Base URL: `https://api.sardis.sh/v2`

### Register Agent

```bash
# Create a new agent identity with TAP verification
curl -X POST https://api.sardis.sh/v2/agents/identity/register \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Support Bot",
    "description": "Handles customer inquiries and refunds",
    "public_key": "302a300506032b6570032100...",
    "key_type": "ed25519",
    "capabilities": ["payments", "refunds", "support"],
    "metadata": {
      "version": "2.1.0",
      "provider": "Anthropic",
      "model": "claude-opus-4"
    }
  }'

# Example response:
# {
#   "agent_id": "agent_abc123xyz",
#   "name": "Customer Support Bot",
#   "public_key": "302a300506032b6570032100...",
#   "tap_verified": true,
#   "wallet_id": "wallet_def456",
#   "created_at": "2026-02-21T10:00:00Z",
#   "identity_card_url": "https://sardis.sh/id/agent_abc123xyz",
#   "status": "active"
# }
```

### Get Agent Identity

```bash
# Retrieve complete agent identity and verification status
curl -X GET https://api.sardis.sh/v2/agents/identity/{agent_id} \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Example:
curl -X GET https://api.sardis.sh/v2/agents/identity/agent_abc123xyz \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

### Submit Reputation

```bash
# Submit reputation feedback after an interaction
curl -X POST https://api.sardis.sh/v2/agents/identity/{agent_id}/reputation \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_abc123xyz",
    "score": 5,
    "category": "payment_reliability",
    "comment": "Processed refund quickly and accurately",
    "transaction_id": "tx_refund789"
  }'

# Categories:
# - payment_reliability: Successful transaction execution
# - policy_compliance: Adherence to spending policies
# - response_quality: Quality of agent responses
# - security_awareness: Security best practices
# - overall: General performance

# Score: 1-5 (5 being best)
```

### Get Reputation Score

```bash
# Query agent's reputation metrics
curl -X GET https://api.sardis.sh/v2/agents/identity/{agent_id}/reputation \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Example:
curl -X GET https://api.sardis.sh/v2/agents/identity/agent_abc123xyz/reputation \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

### Get Agent Card

```bash
# Generate shareable identity card
curl -X GET https://api.sardis.sh/v2/agents/identity/{agent_id}/card \
  -H "Authorization: Bearer $SARDIS_API_KEY"

# Returns a JSON card with agent info, reputation, and verification status
# Can be rendered as HTML or displayed in agent marketplaces
```

## Example Commands

### Complete Agent Onboarding

```bash
# 1. Generate TAP keypair (example using openssl)
openssl genpkey -algorithm ed25519 -out agent_key.pem
openssl pkey -in agent_key.pem -pubout -out agent_pub.pem

# Extract public key hex
PUBLIC_KEY=$(openssl pkey -pubin -in agent_pub.pem -text | grep -A 10 'pub:' | tail -n +2 | tr -d ' :\n')

# 2. Register agent
AGENT=$(curl -s -X POST https://api.sardis.sh/v2/agents/identity/register \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"My Support Agent\",
    \"description\": \"Customer support automation\",
    \"public_key\": \"$PUBLIC_KEY\",
    \"key_type\": \"ed25519\",
    \"capabilities\": [\"payments\", \"support\"]
  }")

AGENT_ID=$(echo "$AGENT" | jq -r '.agent_id')
echo "Agent registered: $AGENT_ID"

# 3. Display identity card
curl -s -X GET "https://api.sardis.sh/v2/agents/identity/$AGENT_ID/card" \
  -H "Authorization: Bearer $SARDIS_API_KEY" | jq '.'
```

### Reputation Dashboard

```bash
# Check reputation across all categories
AGENT_ID=agent_abc123xyz

echo "=== Agent Reputation Dashboard ==="
REP=$(curl -s -X GET "https://api.sardis.sh/v2/agents/identity/$AGENT_ID/reputation" \
  -H "Authorization: Bearer $SARDIS_API_KEY")

echo "$REP" | jq -r '"Overall Score: \(.overall_score)/5"'
echo "$REP" | jq -r '"Total Ratings: \(.total_ratings)"'
echo "$REP" | jq -r '"Trust Level: \(.trust_level)"'

echo -e "\n=== Category Breakdown ==="
echo "$REP" | jq -r '.categories | to_entries[] | "\(.key): \(.value.score)/5 (\(.value.count) ratings)"'
```

### Submit Rating After Transaction

```bash
# Rate agent performance after a payment
AGENT_ID=agent_abc123xyz
TX_ID=tx_payment123

curl -X POST "https://api.sardis.sh/v2/agents/identity/$AGENT_ID/reputation" \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"agent_id\": \"$AGENT_ID\",
    \"score\": 5,
    \"category\": \"payment_reliability\",
    \"comment\": \"Transaction completed successfully\",
    \"transaction_id\": \"$TX_ID\"
  }"
```

### Verify Agent Identity

```bash
# Check if an agent is properly verified
AGENT_ID=agent_abc123xyz

IDENTITY=$(curl -s -X GET "https://api.sardis.sh/v2/agents/identity/$AGENT_ID" \
  -H "Authorization: Bearer $SARDIS_API_KEY")

TAP_VERIFIED=$(echo "$IDENTITY" | jq -r '.tap_verified')
STATUS=$(echo "$IDENTITY" | jq -r '.status')

if [[ "$TAP_VERIFIED" == "true" && "$STATUS" == "active" ]]; then
  echo "✓ Agent identity verified and active"
  echo "Public Key: $(echo "$IDENTITY" | jq -r '.public_key' | head -c 16)..."
  echo "Wallet: $(echo "$IDENTITY" | jq -r '.wallet_id')"
else
  echo "⚠ Agent verification incomplete or inactive"
fi
```

### Multi-Agent Identity Listing

```bash
# List all agent identities with reputation
curl -s -X GET "https://api.sardis.sh/v2/agents/identity?include_reputation=true&limit=10" \
  -H "Authorization: Bearer $SARDIS_API_KEY" | \
  jq -r '.agents[] | "\(.name) [\(.agent_id)]: \(.reputation.overall_score)/5 - \(.status)"'
```

## Response Examples

### Agent Registration Response

```json
{
  "agent_id": "agent_abc123xyz",
  "name": "Customer Support Bot",
  "description": "Handles customer inquiries and refunds",
  "public_key": "302a300506032b657003210033e0bb8dcb3b2c760f83a2f0bcf2b1e6e1c6d8f9a0b1c2d3e4f5a6b7c8d9e0f1",
  "key_type": "ed25519",
  "tap_verified": true,
  "wallet_id": "wallet_def456",
  "capabilities": ["payments", "refunds", "support"],
  "metadata": {
    "version": "2.1.0",
    "provider": "Anthropic",
    "model": "claude-opus-4"
  },
  "created_at": "2026-02-21T10:00:00Z",
  "status": "active",
  "identity_card_url": "https://sardis.sh/id/agent_abc123xyz"
}
```

### Agent Identity Response

```json
{
  "agent_id": "agent_abc123xyz",
  "name": "Customer Support Bot",
  "description": "Handles customer inquiries and refunds",
  "public_key": "302a300506032b657003210033e0bb8dcb3b2c760f83a2f0bcf2b1e6e1c6d8f9a0b1c2d3e4f5a6b7c8d9e0f1",
  "key_type": "ed25519",
  "tap_verified": true,
  "tap_attestation": {
    "verified_at": "2026-02-21T10:00:00Z",
    "verifier": "sardis_tap_v1",
    "signature": "a1b2c3d4..."
  },
  "wallet_id": "wallet_def456",
  "capabilities": ["payments", "refunds", "support"],
  "status": "active",
  "created_at": "2026-02-21T10:00:00Z",
  "last_active": "2026-02-21T15:30:00Z",
  "transaction_count": 1247,
  "total_volume_usd": "45230.50"
}
```

### Reputation Response

```json
{
  "agent_id": "agent_abc123xyz",
  "overall_score": 4.8,
  "total_ratings": 523,
  "trust_level": "high",
  "categories": {
    "payment_reliability": {
      "score": 4.9,
      "count": 523,
      "trend": "stable"
    },
    "policy_compliance": {
      "score": 4.7,
      "count": 450,
      "trend": "improving"
    },
    "response_quality": {
      "score": 4.8,
      "count": 312,
      "trend": "stable"
    },
    "security_awareness": {
      "score": 5.0,
      "count": 89,
      "trend": "stable"
    }
  },
  "recent_ratings": [
    {
      "score": 5,
      "category": "payment_reliability",
      "comment": "Fast and accurate refund processing",
      "timestamp": "2026-02-21T14:30:00Z"
    }
  ],
  "badges": ["verified", "trusted_agent", "high_volume"],
  "last_updated": "2026-02-21T15:30:00Z"
}
```

### Agent Card Response

```json
{
  "agent_id": "agent_abc123xyz",
  "card_version": "1.0",
  "display": {
    "name": "Customer Support Bot",
    "avatar_url": "https://sardis.sh/avatars/agent_abc123xyz.png",
    "tagline": "Handles customer inquiries and refunds",
    "verified": true
  },
  "identity": {
    "public_key_fingerprint": "33e0:bb8d:cb3b:2c76",
    "tap_verified": true,
    "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "created": "2026-02-21"
  },
  "reputation": {
    "overall_score": 4.8,
    "total_ratings": 523,
    "trust_level": "high",
    "badges": ["verified", "trusted_agent"]
  },
  "activity": {
    "transaction_count": 1247,
    "total_volume_usd": "45230.50",
    "success_rate": "99.2%",
    "avg_response_time": "1.2s"
  },
  "capabilities": ["payments", "refunds", "support"],
  "qr_code_url": "https://sardis.sh/id/agent_abc123xyz/qr",
  "share_url": "https://sardis.sh/id/agent_abc123xyz"
}
```

## Error Handling

- `401 Unauthorized` - Invalid or missing API key
- `400 Bad Request` - Invalid public key or TAP verification failed
- `409 Conflict` - Agent with this public key already exists
- `404 Not Found` - Agent identity not found
- `422 Unprocessable Entity` - Invalid reputation score or category

## Use Cases

- **Agent Onboarding**: Register new AI agents with verified identities
- **Trust Verification**: Confirm agent credentials before transactions
- **Reputation Systems**: Build trust through performance tracking
- **Agent Marketplaces**: Display identity cards in agent directories
- **Compliance**: Meet KYC/AML requirements for agent identities

## Related Skills

- `sardis-payment` - Execute payments from verified agents
- `sardis-policy` - Manage spending policies per agent
- `sardis-guardrails` - Monitor verified agent behavior

## Links

- Website: https://sardis.sh
- Documentation: https://sardis.sh/docs/identity
- TAP Protocol: https://sardis.sh/docs/tap
- API Reference: https://api.sardis.sh/v2/docs
- Support: support@sardis.sh
