---
name: sardis-tempo-pay
description: MPP-native payments on Tempo mainnet with Sardis spending mandates and policy enforcement
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - SARDIS_API_KEY
        - SARDIS_WALLET_ID
        - SARDIS_TEMPO_RPC_URL
      bins:
        - curl
        - jq
    primaryEnv: SARDIS_API_KEY
    emoji: "⚡"
    homepage: https://sardis.sh
    install:
      npm:
        - "@sardis/sdk"
    user-invocable: true
    disable-model-invocation: false
---

# Sardis Tempo Pay - MPP-Native Payments on Tempo

> Machine Payments Protocol (MPP) sessions meet Sardis spending mandates. Policy-controlled agent payments on the fastest L1.

Execute payments through the Machine Payments Protocol (MPP) on Tempo mainnet (chain ID 4217). MPP was co-authored by Stripe and Tempo as an open standard for machine-to-machine payments. Sardis enforces spending mandates and policy checks on every MPP session before execution.

## Capabilities

- **MPP Session Creation**: Open MPP payment sessions with Sardis policy enforcement
- **Tempo Mainnet Execution**: Native payments on Tempo L1 (100K+ TPS, sub-second finality)
- **pathUSD Transfers**: Send pathUSD (Tempo's native stablecoin) with mandate controls
- **Spending Mandates**: Bind MPP sessions to Sardis mandates (amount, merchant, time, rail)
- **Stream Channels**: Deploy and manage TempoStreamChannel contracts for recurring MPP flows
- **Policy Dry Run**: Test MPP sessions against spending policies without execution
- **Cross-Rail Portability**: Mandates work across Tempo, Base, Polygon, and other supported chains

## Security Model

**MANDATE-FIRST**: Every MPP session is bound to a Sardis spending mandate. No mandate, no payment. The system is fail-closed by default.

**CRITICAL - ALWAYS ENFORCE:**
- ALWAYS verify a spending mandate exists before opening an MPP session
- ALWAYS check policy via dry run before executing MPP payments
- NEVER bypass mandate controls, even for low-value transactions
- NEVER hardcode wallet addresses or private keys
- ALWAYS log MPP session IDs for audit trail
- FAIL CLOSED on any policy or mandate violation

## Quick Setup

```bash
export SARDIS_API_KEY=sk_your_key_here
export SARDIS_WALLET_ID=wallet_abc123
export SARDIS_TEMPO_RPC_URL=https://rpc.tempo.xyz
```

## API Endpoint Patterns

All API calls use the base URL: `https://api.sardis.sh/v2`

### Create MPP Session with Mandate

```bash
# Open an MPP session bound to a spending mandate
curl -X POST https://api.sardis.sh/v2/mpp/sessions \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "'$SARDIS_WALLET_ID'",
    "chain": "tempo",
    "protocol": "mpp",
    "mandate_id": "mandate_abc123",
    "to": "0xRecipientAddress",
    "amount": "50.00",
    "token": "pathUSD",
    "purpose": "Anthropic API credits",
    "mpp_params": {
      "session_type": "single",
      "expiry_seconds": 3600
    }
  }'

# Response:
# {
#   "session_id": "mpp_sess_xyz789",
#   "mandate_id": "mandate_abc123",
#   "status": "authorized",
#   "chain": "tempo",
#   "chain_id": 4217,
#   "token": "pathUSD",
#   "amount": "50.00",
#   "policy_checks": {"all_passed": true},
#   "expires_at": "2026-03-19T11:00:00Z"
# }
```

### Execute MPP Payment

```bash
# Execute a previously authorized MPP session
curl -X POST https://api.sardis.sh/v2/mpp/sessions/{session_id}/execute \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "mpp_sess_xyz789",
    "wallet_id": "'$SARDIS_WALLET_ID'"
  }'

# Response:
# {
#   "session_id": "mpp_sess_xyz789",
#   "status": "completed",
#   "tx_hash": "0xabc123...",
#   "chain": "tempo",
#   "chain_id": 4217,
#   "amount": "50.00",
#   "token": "pathUSD",
#   "settled_at": "2026-03-19T10:01:00Z"
# }
```

### Policy Dry Run for MPP

```bash
# Check if an MPP session would be allowed WITHOUT creating it
curl -X POST https://api.sardis.sh/v2/mpp/sessions/check \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "'$SARDIS_WALLET_ID'",
    "chain": "tempo",
    "amount": "50.00",
    "token": "pathUSD",
    "vendor": "anthropic.com",
    "mandate_id": "mandate_abc123"
  }'

# Response:
# {
#   "allowed": true,
#   "mandate_status": "active",
#   "remaining_daily": "450.00",
#   "remaining_mandate_total": "950.00",
#   "checks": {
#     "mandate_valid": "pass",
#     "amount_within_limit": "pass",
#     "vendor_allowed": "pass",
#     "time_restriction": "pass"
#   }
# }
```

### Create Streaming MPP Session

```bash
# Open a streaming MPP session for recurring payments (e.g., API usage metering)
curl -X POST https://api.sardis.sh/v2/mpp/sessions \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "'$SARDIS_WALLET_ID'",
    "chain": "tempo",
    "protocol": "mpp",
    "mandate_id": "mandate_abc123",
    "to": "0xServiceProvider",
    "token": "pathUSD",
    "purpose": "LLM inference metered billing",
    "mpp_params": {
      "session_type": "stream",
      "max_amount": "200.00",
      "rate_limit_per_minute": "5.00",
      "expiry_seconds": 86400
    }
  }'
```

### List MPP Sessions

```bash
# List all MPP sessions for a wallet
curl -X GET "https://api.sardis.sh/v2/mpp/sessions?wallet_id=$SARDIS_WALLET_ID&chain=tempo" \
  -H "Authorization: Bearer $SARDIS_API_KEY"
```

### Close MPP Session

```bash
# Close an active streaming session (unused funds returned to mandate budget)
curl -X POST https://api.sardis.sh/v2/mpp/sessions/{session_id}/close \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "mpp_sess_xyz789",
    "wallet_id": "'$SARDIS_WALLET_ID'"
  }'
```

## Example Commands

### Safe MPP Payment Flow

```bash
# Step 1: Check mandate + policy FIRST
CHECK=$(curl -s -X POST https://api.sardis.sh/v2/mpp/sessions/check \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "'$SARDIS_WALLET_ID'",
    "chain": "tempo",
    "amount": "25.00",
    "token": "pathUSD",
    "vendor": "openai.com",
    "mandate_id": "mandate_abc123"
  }')

# Step 2: Only proceed if allowed
if echo $CHECK | jq -e '.allowed == true' > /dev/null; then
  # Step 3: Create and execute MPP session
  SESSION=$(curl -s -X POST https://api.sardis.sh/v2/mpp/sessions \
    -H "Authorization: Bearer $SARDIS_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "wallet_id": "'$SARDIS_WALLET_ID'",
      "chain": "tempo",
      "protocol": "mpp",
      "mandate_id": "mandate_abc123",
      "to": "0xOpenAIReceiver",
      "amount": "25.00",
      "token": "pathUSD",
      "purpose": "GPT-4 API credits"
    }')

  SESSION_ID=$(echo "$SESSION" | jq -r '.session_id')

  # Step 4: Execute
  curl -X POST "https://api.sardis.sh/v2/mpp/sessions/$SESSION_ID/execute" \
    -H "Authorization: Bearer $SARDIS_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"session_id\": \"$SESSION_ID\", \"wallet_id\": \"$SARDIS_WALLET_ID\"}"

  echo "MPP payment completed on Tempo"
else
  echo "Payment blocked by mandate/policy: $(echo $CHECK | jq -r '.reason')"
fi
```

### Metered API Billing with Streaming

```bash
# Open a streaming session for metered API usage
WALLET_ID=$SARDIS_WALLET_ID
MANDATE_ID=mandate_abc123

# Create stream session with rate limit
SESSION=$(curl -s -X POST https://api.sardis.sh/v2/mpp/sessions \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "'$WALLET_ID'",
    "chain": "tempo",
    "protocol": "mpp",
    "mandate_id": "'$MANDATE_ID'",
    "to": "0xAPIProvider",
    "token": "pathUSD",
    "purpose": "Metered LLM inference billing",
    "mpp_params": {
      "session_type": "stream",
      "max_amount": "100.00",
      "rate_limit_per_minute": "2.00",
      "expiry_seconds": 86400
    }
  }')

SESSION_ID=$(echo "$SESSION" | jq -r '.session_id')
echo "Streaming session opened: $SESSION_ID"
echo "Max budget: $100.00 pathUSD, rate limit: $2.00/min"

# ... agent uses API, charges accumulate via stream ...

# Close session when done
curl -X POST "https://api.sardis.sh/v2/mpp/sessions/$SESSION_ID/close" \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"wallet_id\": \"$WALLET_ID\"}"

echo "Session closed. Unused budget returned to mandate."
```

## Tempo Network Details

| Property | Value |
|----------|-------|
| Chain | Tempo |
| Chain ID | 4217 |
| RPC URL | https://rpc.tempo.xyz |
| Testnet RPC | https://rpc.testnet.tempo.xyz |
| Testnet Chain ID | 42429 |
| Native Stablecoin | pathUSD |
| Throughput | 100K+ TPS |
| Finality | Sub-second |
| Protocol | MPP (Machine Payments Protocol) |
| MPP Authors | Stripe + Tempo (open standard, MIT) |

## Supported Tokens on Tempo

| Token | Type | Status |
|-------|------|--------|
| pathUSD | Native stablecoin | Mainnet live |
| USDC | Circle bridged | Coming soon |

## Response Examples

### MPP Session Created

```json
{
  "session_id": "mpp_sess_xyz789",
  "mandate_id": "mandate_abc123",
  "status": "authorized",
  "chain": "tempo",
  "chain_id": 4217,
  "protocol": "mpp",
  "wallet_id": "wallet_abc123",
  "to": "0xRecipientAddress",
  "amount": "50.00",
  "token": "pathUSD",
  "purpose": "Anthropic API credits",
  "policy_checks": {
    "all_passed": true,
    "mandate_valid": "pass",
    "amount_within_limit": "pass",
    "vendor_allowed": "pass"
  },
  "mpp_params": {
    "session_type": "single",
    "expiry_seconds": 3600
  },
  "expires_at": "2026-03-19T11:00:00Z",
  "created_at": "2026-03-19T10:00:00Z"
}
```

### MPP Session Executed

```json
{
  "session_id": "mpp_sess_xyz789",
  "mandate_id": "mandate_abc123",
  "status": "completed",
  "chain": "tempo",
  "chain_id": 4217,
  "tx_hash": "0xabc123def456789...",
  "amount": "50.00",
  "token": "pathUSD",
  "gas_used": "0.00",
  "settled_at": "2026-03-19T10:01:00Z",
  "finality": "confirmed",
  "audit_entry_id": "audit_abc123"
}
```

### MPP Policy Check (Blocked)

```json
{
  "allowed": false,
  "reason": "Mandate daily limit exceeded",
  "mandate_id": "mandate_abc123",
  "checks": {
    "mandate_valid": "pass",
    "amount_within_limit": "fail",
    "vendor_allowed": "pass"
  },
  "details": {
    "mandate_daily_limit": "500.00",
    "current_daily_spend": "480.00",
    "requested": "50.00",
    "would_exceed_by": "30.00"
  }
}
```

## Error Handling

- `200 OK` - Session created/executed successfully
- `400 Bad Request` - Invalid MPP parameters, missing mandate, or unsupported token
- `401 Unauthorized` - Invalid or missing API key
- `403 Forbidden` - Mandate violation or policy rejection
- `404 Not Found` - Session, wallet, or mandate not found
- `409 Conflict` - Session already executed or closed
- `429 Too Many Requests` - Rate limit exceeded (stream channel or API)
- `503 Service Unavailable` - Tempo RPC unreachable

## Use Cases

- **LLM API Billing**: Metered streaming payments for inference costs
- **Agent-to-Agent Commerce**: MPP sessions between autonomous agents with mandate controls
- **SaaS Subscriptions**: Recurring mandate-bound payments for cloud services
- **Data Marketplace**: Pay-per-query with streaming sessions and rate limits
- **Cross-Chain Settlement**: Mandate created on any chain, settled on Tempo for speed

## Related Skills

- `sardis-payment` - Direct payments on Base, Polygon, Ethereum, and other EVM chains
- `sardis-policy` - Create and manage spending policies and mandates
- `sardis-escrow` - Smart contract escrow for milestone-based payments
- `sardis-guardrails` - Advanced guardrail configuration for agent transactions

## Links

- Website: https://sardis.sh
- Tempo Network: https://tempo.xyz
- MPP Specification: https://github.com/tempo-labs/mpp
- Documentation: https://sardis.sh/docs/tempo
- API Reference: https://api.sardis.sh/v2/docs
- Support: support@sardis.sh
