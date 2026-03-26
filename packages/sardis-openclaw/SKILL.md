---
name: sardis
description: >
  Payment OS for AI agents. Create MPC wallets, execute stablecoin payments
  with automatic policy enforcement, set spending rules in natural language,
  check balances across chains, and issue virtual cards.
  Trigger: user asks an agent to pay for something, create a wallet, check a balance,
  set a spending limit, or issue a virtual card.
  Do not trigger: general finance questions unrelated to agent payments.
version: 1.1.0
homepage: https://sardis.sh
metadata:
  openclaw:
    requires:
      env:
        - SARDIS_API_KEY
      bins:
        - curl
    primaryEnv: SARDIS_API_KEY
    emoji: "\U0001F4B3"
    homepage: https://sardis.sh
    install:
      - kind: uv
        package: sardis-openclaw
        bins: []
    user-invocable: true
    disable-model-invocation: false
---

# Sardis — Payment OS for AI Agents

> AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.

Sardis provides complete payment infrastructure for AI agents: non-custodial MPC wallets (Turnkey-backed), natural language spending policies, stablecoin transfers with automatic policy enforcement, virtual card issuance, and full audit trails with on-chain anchoring.

## Setup

```bash
export SARDIS_API_KEY="sk_your_key_here"
export SARDIS_API_URL="https://api.sardis.sh"   # optional, defaults to production
```

Get your API key at https://app.sardis.sh or via the API:

```bash
curl -X POST https://api.sardis.sh/api/v2/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "your-password"}'
```

## Security Requirements

**CRITICAL — ALWAYS ENFORCE:**
- ALWAYS check spending policy before payment execution
- NEVER bypass approval flows for transactions
- NEVER hardcode wallet addresses or private keys
- ALWAYS log transaction attempts for audit trail
- ALWAYS verify recipient address format before sending
- FAIL CLOSED on policy violations (deny by default)
- Use `X-API-Key` header for authentication on every request

---

## API Reference

Base URL: `https://api.sardis.sh`

All endpoints require the `X-API-Key` header.

### 1. Create Agent + Wallet

Provision an agent identity with an MPC wallet in one call.

```bash
curl -X POST https://api.sardis.sh/api/v2/agents \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-agent",
    "description": "Payment agent for OpenAI billing"
  }'
```

**Response:**
```json
{
  "agent_id": "agt_abc123",
  "name": "my-agent",
  "wallet_id": "wal_xyz789",
  "addresses": {"base": "0x...", "tempo": "0x..."},
  "kya_tier": "standard",
  "created_at": "2026-03-26T12:00:00Z"
}
```

Then attach a dedicated wallet if needed:

```bash
curl -X POST https://api.sardis.sh/api/v2/agents/agt_abc123/wallet \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"chain": "base", "provider": "turnkey"}'
```

### 2. Send Payment

Unified payment endpoint with automatic policy enforcement, chain routing, and FX.

```bash
curl -X POST https://api.sardis.sh/api/v2/pay \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "openai.com",
    "amount": "25.00",
    "currency": "USDC",
    "chain": "base"
  }'
```

**Response:**
```json
{
  "status": "completed",
  "tx_hash": "0xabc...def",
  "amount": "25.00",
  "currency": "USDC",
  "chain": "base",
  "policy_result": {"allowed": true, "checks_passed": ["daily_limit", "merchant_allowlist"]},
  "route": {"chain": "base", "provider": "alchemy", "gas_estimate": "0.0012"}
}
```

Omit `chain` to let Sardis auto-route to the cheapest chain:

```bash
curl -X POST https://api.sardis.sh/api/v2/pay \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"to": "anthropic.com", "amount": "100.00", "currency": "USDC"}'
```

### 3. Check Policy (Dry Run)

Pre-flight check whether a payment would be allowed by current policies.

```bash
curl -X POST https://api.sardis.sh/api/v2/policies/check \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agt_abc123",
    "amount": "50.00",
    "currency": "USDC",
    "merchant": "aws.amazon.com"
  }'
```

**Response:**
```json
{
  "allowed": true,
  "reason": "All policy checks passed",
  "checks_passed": ["daily_limit", "per_tx_limit", "merchant_allowlist"],
  "checks_failed": [],
  "remaining_daily_limit": "450.00"
}
```

### 4. Set Policy (Natural Language)

Define spending rules in plain English. Sardis parses them into enforceable constraints.

```bash
curl -X POST https://api.sardis.sh/api/v2/policies/apply \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agt_abc123",
    "natural_language": "Max $500 per day. Only allow OpenAI and Anthropic. No transactions over $200."
  }'
```

**Response:**
```json
{
  "policy_id": "pol_def456",
  "agent_id": "agt_abc123",
  "parsed_rules": [
    {"type": "daily_limit", "value": "500.00", "currency": "USD"},
    {"type": "merchant_allowlist", "merchants": ["openai.com", "anthropic.com"]},
    {"type": "per_transaction_limit", "value": "200.00", "currency": "USD"}
  ],
  "version": 3,
  "applied_at": "2026-03-26T12:05:00Z"
}
```

You can also preview before applying:

```bash
curl -X POST https://api.sardis.sh/api/v2/policies/preview \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agt_abc123", "natural_language": "Block all payments over $1000"}'
```

### 5. Check Balance

```bash
# Single-chain balance
curl -X GET "https://api.sardis.sh/api/v2/wallets/wal_xyz789/balance?chain=base" \
  -H "X-API-Key: $SARDIS_API_KEY"
```

**Response:**
```json
{
  "wallet_id": "wal_xyz789",
  "chain": "base",
  "balance": "1250.00",
  "currency": "USDC",
  "updated_at": "2026-03-26T12:00:00Z"
}
```

```bash
# Multi-chain balances (all chains at once)
curl -X GET "https://api.sardis.sh/api/v2/wallets/wal_xyz789/balances" \
  -H "X-API-Key: $SARDIS_API_KEY"
```

### 6. Issue Virtual Card

Issue a stablecoin-funded virtual Visa card for real-world purchases.

```bash
curl -X POST https://api.sardis.sh/api/v2/cards/virtual/issue \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "25.00",
    "card_type": "single_use"
  }'
```

**Response:**
```json
{
  "card_id": "crd_abc123",
  "card_number": "4242424242424242",
  "cvv": "123",
  "expiry": "12/27",
  "amount": "25.00",
  "currency": "USD",
  "card_type": "single_use",
  "status": "active"
}
```

### 7. Wallet Transfer (Direct)

Transfer stablecoins from a specific wallet (with automatic policy enforcement).

```bash
curl -X POST https://api.sardis.sh/api/v2/wallets/wal_xyz789/transfer \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "amount": "50.00",
    "token": "USDC",
    "chain": "base",
    "agent_id": "agt_abc123"
  }'
```

**Response:**
```json
{
  "tx_hash": "0xdef...abc",
  "status": "confirmed",
  "amount": "50.00",
  "token": "USDC",
  "chain": "base",
  "block_number": 12345678
}
```

### 8. Transaction Status

```bash
curl -X GET "https://api.sardis.sh/api/v2/transactions/status/0xabc...def" \
  -H "X-API-Key: $SARDIS_API_KEY"
```

### 9. Agent Spending Analytics

```bash
curl -X GET "https://api.sardis.sh/api/v2/agents/agt_abc123/spending" \
  -H "X-API-Key: $SARDIS_API_KEY"
```

### 10. Create Spending Mandate

Spending mandates define scoped, time-limited authority over funds.

```bash
curl -X POST https://api.sardis.sh/api/v2/mandates \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "wal_xyz789",
    "agent_id": "agt_abc123",
    "max_amount": "1000.00",
    "currency": "USDC",
    "expires_at": "2026-04-01T00:00:00Z",
    "merchant_allowlist": ["openai.com", "anthropic.com"]
  }'
```

---

## Complete Onboarding Flow

```bash
# 1. Create agent (auto-provisions wallet)
AGENT=$(curl -s -X POST https://api.sardis.sh/api/v2/agents \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "billing-agent", "description": "Handles API billing"}')
AGENT_ID=$(echo $AGENT | jq -r '.agent_id')
WALLET_ID=$(echo $AGENT | jq -r '.wallet_id')
echo "Agent: $AGENT_ID, Wallet: $WALLET_ID"

# 2. Set spending policy
curl -s -X POST https://api.sardis.sh/api/v2/policies/apply \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\": \"$AGENT_ID\", \"natural_language\": \"Max \$100 per transaction, \$500 per day. Only OpenAI and Anthropic.\"}"

# 3. Check balance
curl -s -X GET "https://api.sardis.sh/api/v2/wallets/$WALLET_ID/balances" \
  -H "X-API-Key: $SARDIS_API_KEY" | jq '.'

# 4. Dry-run policy check
curl -s -X POST https://api.sardis.sh/api/v2/policies/check \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\": \"$AGENT_ID\", \"amount\": \"25.00\", \"currency\": \"USDC\", \"merchant\": \"openai.com\"}"

# 5. Execute payment (policy auto-enforced)
curl -s -X POST https://api.sardis.sh/api/v2/pay \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"to": "openai.com", "amount": "25.00", "currency": "USDC", "chain": "base"}'
```

## Error Handling

Always check response status codes:

| Code | Meaning |
|------|---------|
| `200` / `201` | Success |
| `400` | Invalid parameters (check amount, address, token) |
| `401` | Invalid or missing API key |
| `403` | Policy violation — payment blocked by spending rules |
| `404` | Wallet, agent, or transaction not found |
| `429` | Rate limit exceeded |
| `500` | Internal error — contact support@sardis.sh |

Example error (policy violation):
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

| Chain | Tokens |
|-------|--------|
| Base | USDC, EURC |
| Ethereum | USDC, USDT, PYUSD, EURC |
| Arbitrum | USDC, USDT |
| Optimism | USDC, USDT |
| Polygon | USDC, USDT, EURC |
| Tempo | pathUSD |

## Related Skills

- `sardis-balance` — Read-only balance checking and analytics
- `sardis-policy` — Natural language spending policy management
- `sardis-cards` — Virtual card issuance and management
- `sardis-guardrails` — Circuit breaker and kill switch controls
- `sardis-identity` — Agent identity with TAP verification
- `sardis-escrow` — Smart contract escrow for agent-to-agent payments
- `sardis-tempo-pay` — MPP-native payments on Tempo mainnet

## Links

- Website: https://sardis.sh
- Dashboard: https://app.sardis.sh
- API Docs: https://api.sardis.sh/api/v2/docs
- GitHub: https://github.com/EfeDurmaz16/sardis
- Support: support@sardis.sh
