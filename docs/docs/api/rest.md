# REST API Reference

Complete HTTP API reference for Sardis Payment OS.

## Base URL

```
Production: https://api.sardis.sh/v2
Testnet:    https://api-testnet.sardis.sh/v2
```

## Authentication

All API requests require authentication via API key in the `Authorization` header:

```bash
curl https://api.sardis.sh/v2/wallets \
  -H "Authorization: Bearer sk_..."
```

### Getting an API Key

1. Sign up at [sardis.sh](https://sardis.sh)
2. Navigate to Settings → API Keys
3. Create a new key (starts with `sk_`)

**Security:** Never commit API keys to version control. Use environment variables:

```bash
export SARDIS_API_KEY="sk_..."
```

## Rate Limits

| Tier | Requests/min | Requests/hour |
|------|--------------|---------------|
| Free | 60 | 1,000 |
| Pro | 600 | 30,000 |
| Enterprise | Custom | Custom |

Rate limit headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1708531200
```

## Wallets

### Create Wallet

```http
POST /v2/wallets
```

**Request:**

```json
{
  "name": "my-agent-wallet",
  "chain": "base",
  "policy": "Max $500/day, only SaaS vendors",
  "metadata": {
    "department": "engineering",
    "cost_center": "CC-1234"
  }
}
```

**Response:**

```json
{
  "id": "wallet_abc123",
  "name": "my-agent-wallet",
  "address": "0x1234567890abcdef1234567890abcdef12345678",
  "chain": "base",
  "policy": "Max $500/day, only SaaS vendors",
  "trust_score": 75,
  "balances": {},
  "status": "active",
  "created_at": "2026-02-21T10:00:00Z",
  "metadata": {
    "department": "engineering",
    "cost_center": "CC-1234"
  }
}
```

### Get Wallet

```http
GET /v2/wallets/{wallet_id}
```

**Response:**

```json
{
  "id": "wallet_abc123",
  "name": "my-agent-wallet",
  "address": "0x1234567890abcdef1234567890abcdef12345678",
  "chain": "base",
  "policy": "Max $500/day, only SaaS vendors",
  "trust_score": 85,
  "balances": {
    "USDC": "1500.00",
    "EURC": "200.00"
  },
  "status": "active",
  "created_at": "2026-02-21T10:00:00Z"
}
```

### List Wallets

```http
GET /v2/wallets
```

**Query Parameters:**

- `limit` (integer, default: 100) - Number of results
- `offset` (integer, default: 0) - Pagination offset
- `status` (string) - Filter by status: `active`, `frozen`, `suspended`

**Response:**

```json
{
  "wallets": [
    {
      "id": "wallet_abc123",
      "name": "my-agent-wallet",
      "address": "0x...",
      "chain": "base",
      "trust_score": 85,
      "status": "active"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

### Update Wallet Policy

```http
PATCH /v2/wallets/{wallet_id}/policy
```

**Request:**

```json
{
  "policy": "Max $1000/day, SaaS and cloud providers only"
}
```

**Response:**

```json
{
  "id": "wallet_abc123",
  "policy": "Max $1000/day, SaaS and cloud providers only",
  "updated_at": "2026-02-21T11:00:00Z"
}
```

### Freeze Wallet

```http
POST /v2/wallets/{wallet_id}/freeze
```

**Request:**

```json
{
  "reason": "Suspected compromise"
}
```

**Response:**

```json
{
  "id": "wallet_abc123",
  "status": "frozen",
  "freeze_reason": "Suspected compromise",
  "frozen_at": "2026-02-21T12:00:00Z"
}
```

### Unfreeze Wallet

```http
POST /v2/wallets/{wallet_id}/unfreeze
```

**Response:**

```json
{
  "id": "wallet_abc123",
  "status": "active",
  "unfrozen_at": "2026-02-21T13:00:00Z"
}
```

### Delete Wallet

```http
DELETE /v2/wallets/{wallet_id}
```

**Response:**

```json
{
  "deleted": true,
  "wallet_id": "wallet_abc123"
}
```

## Payments

### Execute Payment

```http
POST /v2/payments
```

**Request:**

```json
{
  "wallet_id": "wallet_abc123",
  "to": "0x1234567890abcdef1234567890abcdef12345678",
  "amount": "50.00",
  "token": "USDC",
  "purpose": "API credits",
  "metadata": {
    "invoice_id": "INV-001"
  }
}
```

**Response:**

```json
{
  "id": "payment_xyz789",
  "wallet_id": "wallet_abc123",
  "to": "0x1234567890abcdef1234567890abcdef12345678",
  "amount": "50.00",
  "token": "USDC",
  "purpose": "API credits",
  "tx_hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
  "status": "success",
  "block_number": 12345678,
  "gas_used": "0.0002",
  "created_at": "2026-02-21T10:30:00Z",
  "confirmed_at": "2026-02-21T10:30:15Z"
}
```

### Get Payment

```http
GET /v2/payments/{payment_id}
```

**Response:**

```json
{
  "id": "payment_xyz789",
  "wallet_id": "wallet_abc123",
  "to": "0x...",
  "amount": "50.00",
  "token": "USDC",
  "tx_hash": "0x...",
  "status": "success",
  "created_at": "2026-02-21T10:30:00Z"
}
```

### List Payments

```http
GET /v2/payments
```

**Query Parameters:**

- `wallet_id` (string) - Filter by wallet
- `status` (string) - Filter by status: `pending`, `success`, `failed`
- `start_date` (ISO 8601) - Start date
- `end_date` (ISO 8601) - End date
- `limit` (integer, default: 100)
- `offset` (integer, default: 0)

**Response:**

```json
{
  "payments": [
    {
      "id": "payment_xyz789",
      "wallet_id": "wallet_abc123",
      "amount": "50.00",
      "token": "USDC",
      "status": "success",
      "created_at": "2026-02-21T10:30:00Z"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

### Estimate Gas

```http
POST /v2/payments/estimate-gas
```

**Request:**

```json
{
  "wallet_id": "wallet_abc123",
  "to": "0x...",
  "amount": "50.00",
  "token": "USDC"
}
```

**Response:**

```json
{
  "gas_price": "15.5",
  "gas_limit": "21000",
  "total_cost_eth": "0.0003255",
  "total_cost_usd": "0.98"
}
```

### Simulate Payment

Test payment without executing:

```http
POST /v2/payments/simulate
```

**Request:**

```json
{
  "wallet_id": "wallet_abc123",
  "to": "0x...",
  "amount": "5000.00",
  "token": "USDC"
}
```

**Response:**

```json
{
  "would_succeed": false,
  "violation": {
    "type": "daily_limit_exceeded",
    "limit": "500.00",
    "attempted": "5000.00",
    "message": "Daily limit of $500 exceeded"
  }
}
```

## Balances

### Get Balance

```http
GET /v2/wallets/{wallet_id}/balance/{token}
```

**Response:**

```json
{
  "wallet_id": "wallet_abc123",
  "token": "USDC",
  "balance": "1500.00",
  "updated_at": "2026-02-21T10:00:00Z"
}
```

### Get All Balances

```http
GET /v2/wallets/{wallet_id}/balances
```

**Response:**

```json
{
  "wallet_id": "wallet_abc123",
  "balances": {
    "USDC": "1500.00",
    "EURC": "200.00",
    "USDT": "0.00"
  },
  "updated_at": "2026-02-21T10:00:00Z"
}
```

## Trust & KYA

### Get Trust Score

```http
GET /v2/wallets/{wallet_id}/trust-score
```

**Response:**

```json
{
  "wallet_id": "wallet_abc123",
  "trust_score": 85,
  "trust_level": "good",
  "factors": {
    "transaction_history": 40,
    "behavioral_consistency": 28,
    "identity_attestation": 15,
    "external_signals": 2
  },
  "updated_at": "2026-02-21T10:00:00Z"
}
```

### Get Trust History

```http
GET /v2/wallets/{wallet_id}/trust-history
```

**Response:**

```json
{
  "history": [
    {
      "date": "2026-02-21",
      "score": 85,
      "change": "+2",
      "reason": "5 days clean behavior"
    },
    {
      "date": "2026-02-15",
      "score": 83,
      "change": "-5",
      "reason": "Anomaly detected: spending spike"
    }
  ]
}
```

### Get KYA Analysis

```http
GET /v2/wallets/{wallet_id}/kya-analysis
```

**Response:**

```json
{
  "wallet_id": "wallet_abc123",
  "trust_score": 85,
  "risk_factors": [
    "new_merchant_frequency"
  ],
  "recommendations": [
    "Add merchant allowlist to policy"
  ],
  "anomalies": [],
  "last_analyzed": "2026-02-21T10:00:00Z"
}
```

## Ledger

### List Ledger Entries

```http
GET /v2/ledger
```

**Query Parameters:**

- `wallet_id` (string, required) - Wallet to query
- `type` (string) - Filter: `debit`, `credit`
- `token` (string) - Filter by token
- `start_date` (ISO 8601)
- `end_date` (ISO 8601)
- `limit` (integer, default: 100)
- `offset` (integer, default: 0)

**Response:**

```json
{
  "entries": [
    {
      "id": "ledger_001",
      "wallet_id": "wallet_abc123",
      "type": "debit",
      "amount": "-50.00",
      "token": "USDC",
      "balance_after": "1450.00",
      "tx_hash": "0x...",
      "timestamp": "2026-02-21T10:30:00Z"
    }
  ],
  "total": 1
}
```

### Reconcile Ledger

```http
POST /v2/ledger/reconcile
```

**Request:**

```json
{
  "wallet_id": "wallet_abc123",
  "date": "2026-02-21"
}
```

**Response:**

```json
{
  "wallet_id": "wallet_abc123",
  "date": "2026-02-21",
  "opening_balance": "1500.00",
  "total_credits": "100.00",
  "total_debits": "150.00",
  "closing_balance": "1450.00",
  "verified": true
}
```

### Export Ledger

```http
POST /v2/ledger/export
```

**Request:**

```json
{
  "wallet_id": "wallet_abc123",
  "format": "csv",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31"
}
```

**Response:**

```json
{
  "export_id": "export_abc123",
  "status": "processing",
  "format": "csv",
  "download_url": null
}
```

Check status:

```http
GET /v2/ledger/export/{export_id}
```

**Response:**

```json
{
  "export_id": "export_abc123",
  "status": "complete",
  "download_url": "https://exports.sardis.sh/export_abc123.csv",
  "expires_at": "2026-02-22T10:00:00Z"
}
```

## Webhooks

### Create Webhook

```http
POST /v2/webhooks
```

**Request:**

```json
{
  "url": "https://your-app.com/sardis-webhook",
  "events": [
    "wallet.created",
    "wallet.payment.success",
    "wallet.payment.failed",
    "wallet.frozen",
    "wallet.policy.violated"
  ],
  "secret": "whsec_..."
}
```

**Response:**

```json
{
  "id": "webhook_abc123",
  "url": "https://your-app.com/sardis-webhook",
  "events": ["wallet.created", "wallet.payment.success"],
  "secret": "whsec_...",
  "status": "active",
  "created_at": "2026-02-21T10:00:00Z"
}
```

### List Webhooks

```http
GET /v2/webhooks
```

### Delete Webhook

```http
DELETE /v2/webhooks/{webhook_id}
```

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "type": "policy_violation",
    "message": "Daily limit of $500 exceeded",
    "details": {
      "limit": "500.00",
      "attempted": "5000.00"
    },
    "request_id": "req_abc123"
  }
}
```

### Error Types

| Type | HTTP Code | Description |
|------|-----------|-------------|
| `invalid_request` | 400 | Malformed request |
| `authentication_failed` | 401 | Invalid API key |
| `insufficient_permissions` | 403 | API key lacks permissions |
| `resource_not_found` | 404 | Wallet/payment not found |
| `policy_violation` | 422 | Spending policy violated |
| `insufficient_balance` | 422 | Wallet balance too low |
| `rate_limit_exceeded` | 429 | Too many requests |
| `server_error` | 500 | Internal error |

## Idempotency

Prevent duplicate payments with idempotency keys:

```bash
curl https://api.sardis.sh/v2/payments \
  -H "Authorization: Bearer sk_..." \
  -H "Idempotency-Key: unique-key-123" \
  -d '{"wallet_id": "wallet_abc123", "amount": "50", "token": "USDC", "to": "0x..."}'
```

If you retry with the same key, you'll get the original response.

## Pagination

All list endpoints support cursor-based pagination:

```http
GET /v2/payments?limit=100&offset=0
```

Response includes pagination metadata:

```json
{
  "payments": [...],
  "total": 500,
  "limit": 100,
  "offset": 0,
  "has_more": true
}
```

## Versioning

The API is versioned via URL path:

- Current: `/v2`
- Legacy: `/v1` (deprecated)

Breaking changes will result in a new version.

## SDKs

Official SDKs handle authentication, retries, and error handling:

- **Python:** `pip install sardis-sdk`
- **TypeScript:** `npm install @sardis/sdk`
- **CLI:** `pip install sardis-cli`

## OpenAPI Spec

Download the full OpenAPI specification:

```bash
curl https://api.sardis.sh/v2/openapi.json > sardis-openapi.json
```

## Next Steps

- [Webhooks Documentation](webhooks.md) - Event notifications
- [Python SDK](../sdks/python.md) - SDK reference
- [TypeScript SDK](../sdks/typescript.md) - SDK reference
